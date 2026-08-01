"""
Configuration, equation/global-variable, design-table, and reference-geometry
tools for Solidworks MCP server.

Feature inspiration came from Eduardo Font Cruz's Eduardof0nt/Solidworks-MCP-Server
(MIT License), https://github.com/Eduardof0nt/Solidworks-MCP-Server - but method
names/signatures were re-derived from this machine's real, generated SolidWorks
2026 COM type library and verified against a live SolidWorks session, since that
repo targeted SolidWorks 2024 and several relevant methods differ in 2026:
InsertAxis2 lives on the document directly (not FeatureManager) and takes a
single AutoSize flag, not an axis-type enum; InsertFamilyTableOpen2 does not
exist at all (real methods are InsertFamilyTableNew/InsertFamilyTableOpen);
InsertReferencePoint does not accept explicit XYZ coordinates - it places a
point based on selected reference geometry and a type code, not free placement
(free-XYZ point placement is a SketchManager operation requiring an active
sketch, out of scope for this file).

add_configuration/add_equation/set_global_variable's method names were
confirmed to exist on this machine (AddConfiguration3, GetEquationMgr) but
their exact argument signatures were not independently re-verified against
live calls the way the rest of this file was - flagged here rather than
silently assumed correct.
"""
from solidworks_mcp.api.connection import get_active_doc

MM_TO_M = 0.001
SW_REF_PLANE_OFFSET = 8  # swRefPlaneReferenceConstraints_Offset


def register_configuration_tools(mcp):
    @mcp.tool()
    def add_configuration(config_name: str, comment: str = "") -> str:
        """Add a new configuration to the active document.

        Args:
            config_name: Name for the new configuration
            comment: Optional comment/description
        """
        try:
            doc = get_active_doc()
            config = doc.AddConfiguration3(config_name, comment, "", 0)
            if config is None:
                return f"Error: Failed to add configuration '{config_name}'."
            return f"Configuration '{config_name}' created"
        except Exception as e:
            return f"Error adding configuration: {e}"

    @mcp.tool()
    def create_design_table(excel_path: str = "") -> str:
        """Insert a design table into the active document.

        Args:
            excel_path: Path to an existing Excel file to link; blank auto-generates a new design table
        """
        try:
            doc = get_active_doc()
            if excel_path:
                result = doc.InsertFamilyTableOpen(excel_path)
            else:
                result = doc.InsertFamilyTableNew()
            if not result:
                return "Error: Failed to create design table."
            return f"Design table created{' from ' + excel_path if excel_path else ' (auto-generated)'}"
        except Exception as e:
            return f"Error creating design table: {e}"

    @mcp.tool()
    def add_equation(equation: str) -> str:
        """Add an equation to the active document's equation manager, e.g. '"D1@Sketch1" = 25mm'.

        Args:
            equation: Full equation text, matching Solidworks equation syntax
        """
        try:
            doc = get_active_doc()
            eqn_mgr = doc.GetEquationMgr()
            idx = eqn_mgr.Add2(-1, equation, True)
            doc.EditRebuild3()
            return f"Equation added at index {idx}: {equation}"
        except Exception as e:
            return f"Error adding equation: {e}"

    @mcp.tool()
    def set_global_variable(name: str, value: float) -> str:
        """Set an existing global variable's value, or create it if it doesn't exist yet.

        Args:
            name: Global variable name (without quotes)
            value: Numeric value to assign
        """
        try:
            doc = get_active_doc()
            eqn_mgr = doc.GetEquationMgr()
            count = eqn_mgr.GetCount() or 0
            target = f'"{name}"'
            for i in range(count):
                eqn = eqn_mgr.Equation(i)
                if eqn and eqn.startswith(target):
                    eqn_mgr.Equation = (i, f'"{name}" = {value}')
                    doc.EditRebuild3()
                    return f"Global variable '{name}' updated to {value}"
            idx = eqn_mgr.Add2(-1, f'"{name}" = {value}', True)
            doc.EditRebuild3()
            return f"Global variable '{name}' created with value {value} at index {idx}"
        except Exception as e:
            return f"Error setting global variable: {e}"

    @mcp.tool()
    def create_reference_plane(offset_distance: float = 0.0, reference_plane: str = "Front Plane") -> str:
        """Create a new reference plane offset from an existing plane.

        Args:
            offset_distance: Offset distance in mm
            reference_plane: Name of the existing plane to offset from, e.g. "Front Plane"
        """
        try:
            doc = get_active_doc()
            doc.Extension.SelectByID2(reference_plane, "PLANE", 0, 0, 0, False, 0, None, 0)
            feat = doc.FeatureManager.InsertRefPlane(
                SW_REF_PLANE_OFFSET, offset_distance * MM_TO_M, 0, 0.0, 0, 0.0
            )
            if feat is None:
                return f"Error: Failed to create reference plane offset from '{reference_plane}'."
            return f"Reference plane created: feature={feat.Name}, offset_mm={offset_distance}"
        except Exception as e:
            return f"Error creating reference plane: {e}"

    @mcp.tool()
    def create_reference_axis(auto_size: bool = True) -> str:
        """Create a reference axis from currently selected entities (two planes, a cylindrical
        face, two points, or a point+face - Solidworks infers the axis type from what's selected).

        Select the required entities first.

        Args:
            auto_size: Let Solidworks automatically size the axis to the model
        """
        try:
            doc = get_active_doc()
            feat = doc.InsertAxis2(auto_size)
            if feat is None:
                return "Error: Failed to create reference axis. Select the required entities first (two planes, a cylindrical face, or two points)."
            return f"Reference axis created: feature={feat.Name}"
        except Exception as e:
            return f"Error creating reference axis: {e}"

    @mcp.tool()
    def create_reference_point(ref_point_type: int = 0, along_curve_type: int = 0,
                                distance_or_percent: float = 0.0, number_of_points: int = 1) -> str:
        """Create reference point(s) from currently selected reference geometry (a vertex, curve,
        face, or center of a selected entity) - this does not place a point at arbitrary XYZ
        coordinates, it derives position from what's selected plus these parameters.

        Select the reference geometry first.

        Args:
            ref_point_type: 0 = at selected vertex/center, 1 = along a curve by distance/percent,
                             2 = at intersection of selections (see Solidworks API docs for full enum)
            along_curve_type: 0 = distance, 1 = percentage (only used when ref_point_type=1)
            distance_or_percent: Distance in mm, or percentage (0-100), depending on along_curve_type
            number_of_points: Number of evenly-spaced points to create when placing along a curve
        """
        try:
            doc = get_active_doc()
            feat = doc.FeatureManager.InsertReferencePoint(
                ref_point_type, along_curve_type, distance_or_percent, number_of_points
            )
            if feat is None:
                return "Error: Failed to create reference point. Select reference geometry first."
            return f"Reference point created: feature={feat.Name}"
        except Exception as e:
            return f"Error creating reference point: {e}"
