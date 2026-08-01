"""
Material, appearance, custom-property, export, and screenshot tools for
Solidworks MCP server.

API usage adapted from Eduardo Font Cruz's Eduardof0nt/Solidworks-MCP-Server
(MIT License), https://github.com/Eduardof0nt/Solidworks-MCP-Server -
re-verified against a live Solidworks COM session before being ported into
this codebase's conventions.
"""
import os
import tempfile

import win32com.client
import pythoncom

from solidworks_mcp.api.connection import get_sw_app, get_active_doc, wrap_as

SW_SOLID_BODY = 0
SW_SAVE_SILENT = 1  # swSaveAsOptions_Silent
SW_CUSTOM_INFO_TEXT = 30
SW_CUSTOM_PROPERTY_REPLACE_VALUE = 1


def _export_file(doc, output_path: str) -> None:
    errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    no_config = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
    result = doc.Extension.SaveAs(output_path, 0, SW_SAVE_SILENT, no_config, errors, warnings)
    if not result:
        raise RuntimeError(f"Export failed to '{output_path}'. Error code: {errors.value}")


def register_materials_export_tools(mcp):
    @mcp.tool()
    def export_step(output_path: str, version: str = "AP214") -> str:
        """Export the active document directly to a STEP file.

        Args:
            output_path: Absolute output file path, must end in .step or .stp
            version: STEP schema version - AP203, AP214, or AP242
        """
        try:
            app = get_sw_app()
            doc = get_active_doc()
            version_map = {"AP203": 0, "AP214": 1, "AP242": 2}
            try:
                # 228 = swStepAP_e system preference
                app.SetUserPreferenceIntegerValue(228, version_map.get(version.upper(), 1))
            except Exception:
                pass
            _export_file(doc, output_path)
            return f"Exported STEP ({version}) to {output_path}"
        except Exception as e:
            return f"Error exporting STEP: {e}"

    @mcp.tool()
    def export_stl(output_path: str, binary: bool = True, quality: str = "fine") -> str:
        """Export the active document directly to an STL file.

        Args:
            output_path: Absolute output file path, must end in .stl
            binary: True for compact binary STL, False for verbose ASCII STL
            quality: Mesh quality - coarse, fine, or custom (uses current custom settings)
        """
        try:
            app = get_sw_app()
            doc = get_active_doc()
            try:
                # 74 = swSTLExportFormat_e (0=Binary, 1=ASCII), 75 = swSTLQuality_e
                app.SetUserPreferenceIntegerValue(74, 0 if binary else 1)
                quality_map = {"coarse": 0, "fine": 1, "custom": 2}
                app.SetUserPreferenceIntegerValue(75, quality_map.get(quality.lower(), 1))
            except Exception:
                pass
            _export_file(doc, output_path)
            return f"Exported STL ({'binary' if binary else 'ASCII'}, {quality}) to {output_path}"
        except Exception as e:
            return f"Error exporting STL: {e}"

    @mcp.tool()
    def get_material() -> str:
        """Read the material currently assigned to the active part.

        Note: GetMaterialPropertyName2 lives on the IPartDoc interface, not the generic
        IModelDoc2 that most other tools operate on - only works on parts, not assemblies/drawings.
        """
        try:
            doc = get_active_doc()
            part = wrap_as(doc, "IPartDoc")
            db_out = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BSTR, "")
            material = part.GetMaterialPropertyName2("", db_out)
            return f"Material: {material}, database: {db_out.value}"
        except Exception as e:
            return f"Error reading material: {e}"

    @mcp.tool()
    def set_material(material_name: str, database_name: str = "SOLIDWORKS Materials") -> str:
        """Apply a material to the active part from a Solidworks materials database.

        Note: only works on parts, not assemblies/drawings (SetMaterialPropertyName2 lives on IPartDoc).

        Args:
            material_name: Exact material name, e.g. "AISI 1020", "Aluminum 6061", "ABS", "PLA"
            database_name: Materials database to look in, default "SOLIDWORKS Materials"
        """
        try:
            doc = get_active_doc()
            part = wrap_as(doc, "IPartDoc")
            part.SetMaterialPropertyName2("", database_name, material_name)
            return f"Material set to '{material_name}' from '{database_name}'"
        except Exception as e:
            return f"Error setting material: {e}"

    @mcp.tool()
    def set_appearance_color(r: int, g: int, b: int, transparency: float = 0.0) -> str:
        """Set a single solid-color appearance on every solid body in the active part.

        Args:
            r: Red component, 0-255
            g: Green component, 0-255
            b: Blue component, 0-255
            transparency: 0.0 (opaque) to 1.0 (fully transparent)
        """
        try:
            doc = get_active_doc()
            props = [r / 255.0, g / 255.0, b / 255.0, 1.0, 1.0, 0.6, 0.4, transparency, 0.0]
            try:
                bodies = doc.GetBodies2(SW_SOLID_BODY, True)
                applied = 0
                if bodies:
                    iterable = bodies if hasattr(bodies, "__iter__") else [bodies]
                    for body in iterable:
                        body.MaterialPropertyValues = props
                        applied += 1
                if applied == 0:
                    raise RuntimeError("no solid bodies found via GetBodies2")
            except Exception:
                doc.MaterialPropertyValues = props
            return f"Appearance set to RGB({r},{g},{b}), transparency={transparency}"
        except Exception as e:
            return f"Error setting appearance color: {e}"

    @mcp.tool()
    def get_custom_properties(prop_name: str = "", configuration: str = "") -> str:
        """Read one or all custom properties of the active document.

        Args:
            prop_name: Specific property name to read; leave blank to list all properties
            configuration: Configuration-specific properties to read; blank = document-level
        """
        try:
            import json
            doc = get_active_doc()
            mgr = doc.Extension.CustomPropertyManager(configuration)
            if prop_name:
                val_out = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BSTR, "")
                res_out = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BSTR, "")
                mgr.Get4(prop_name, False, val_out, res_out)
                return json.dumps({"name": prop_name, "value": val_out.value, "resolved": res_out.value})
            names = mgr.GetNames()
            if not names:
                return json.dumps({"properties": {}})
            props = {}
            for name in names:
                val_out = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BSTR, "")
                res_out = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BSTR, "")
                mgr.Get4(name, False, val_out, res_out)
                props[name] = res_out.value
            return json.dumps({"properties": props})
        except Exception as e:
            return f"Error reading custom properties: {e}"

    @mcp.tool()
    def set_custom_property(prop_name: str, value: str, configuration: str = "") -> str:
        """Set (or create) a custom property on the active document.

        Args:
            prop_name: Property name
            value: Property value (stored as text)
            configuration: Configuration to set it on; blank = document-level
        """
        try:
            doc = get_active_doc()
            mgr = doc.Extension.CustomPropertyManager(configuration)
            result = mgr.Add3(prop_name, SW_CUSTOM_INFO_TEXT, value, SW_CUSTOM_PROPERTY_REPLACE_VALUE)
            return f"Custom property '{prop_name}' set to '{value}' (result={result})"
        except Exception as e:
            return f"Error setting custom property: {e}"

    @mcp.tool()
    def capture_screenshot(output_path: str = "", width: int = 1920, height: int = 1080) -> str:
        """Capture a screenshot of the active Solidworks graphics view to a BMP file.

        Args:
            output_path: Absolute output file path; defaults to a temp file if blank
            width: Image width in pixels
            height: Image height in pixels
        """
        try:
            doc = get_active_doc()
            path = output_path or os.path.join(tempfile.gettempdir(), "sw_screenshot.bmp")
            doc.ViewZoomtofit2()
            if doc.SaveBMP(path, width, height):
                return f"Screenshot saved to {path}"
            return f"Error: SaveBMP returned failure for {path}"
        except Exception as e:
            return f"Error capturing screenshot: {e}"
