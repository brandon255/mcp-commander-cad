"""
Drawing tools for Solidworks MCP server.
Provides drawing creation, view insertion, annotations, BOM, and export tools.
"""
from solidworks_mcp.api.connection import get_sw_app, get_active_doc, open_document

# Sheet size constants
SW_SHEET_A = 0
SW_SHEET_B = 1
SW_SHEET_C = 2
SW_SHEET_D = 3
SW_SHEET_E = 4

# Drawing view type constants
SW_DRAWING_VIEW_FRONT = 1
SW_DRAWING_VIEW_TOP = 3
SW_DRAWING_VIEW_RIGHT = 4
SW_DRAWING_VIEW_LEFT = 5
SW_DRAWING_VIEW_BOTTOM = 6
SW_DRAWING_VIEW_BACK = 7
SW_DRAWING_VIEW_ISOMETRIC = 8
SW_DRAWING_VIEW_SECTION = 9
SW_DRAWING_VIEW_DETAIL = 10
SW_DRAWING_VIEW_BROKEN = 11
SW_DRAWING_VIEW_PROJECTED = 2


def register_drawing_tools(mcp):
    @mcp.tool()
    def create_drawing(part_filepath: str = "", sheet_size: str = "A") -> str:
        """Create a new drawing document, optionally from a part or assembly.

        If part_filepath is given, opens that document first (so views can
        reference it), then creates a new blank drawing sheet - SolidWorks'
        NewDrawing2 itself has no "base this drawing on a file" parameter;
        the model has to already be open, and views are added to it
        separately via add_standard_views/add_isometric_view.

        Args:
            part_filepath: Path to the part/assembly file to base the drawing on (empty for blank drawing)
            sheet_size: Sheet size - A, B, C, D, or E
        """
        try:
            sw_app = get_sw_app()

            size_map = {
                "a": SW_SHEET_A, "b": SW_SHEET_B,
                "c": SW_SHEET_C, "d": SW_SHEET_D, "e": SW_SHEET_E,
            }
            size_val = size_map.get(sheet_size.lower(), SW_SHEET_A)

            if part_filepath:
                open_document(part_filepath)

            # NewDrawing2(TemplateToUse, TemplateName, PaperSize, Width, Height):
            # TemplateToUse=False means "use PaperSize", not a custom template.
            doc = sw_app.NewDrawing2(False, "", size_val, 0, 0)

            if doc:
                # NewDrawing2 does not reliably make the new document the
                # active one under automation - explicitly activate it by
                # its own title so get_active_doc() (used by every other
                # drawing tool) actually returns this drawing, not whatever
                # was active before.
                try:
                    sw_app.ActivateDoc3(doc.GetTitle, False, 0, None)
                except Exception:
                    pass
                return f"Drawing document created (size {sheet_size.upper()})" + (f" from {part_filepath}" if part_filepath else "")
            return "Failed to create drawing document"
        except Exception as e:
            return f"Error creating drawing: {e}"

    @mcp.tool()
    def add_standard_views(
        model_path: str = "",
        pos_x: float = 0.15,
        pos_y: float = 0.15,
        scale: float = 1.0,
        spacing: float = 0.15,
    ) -> str:
        """Add front, top, and right (side) views to the drawing sheet.

        SolidWorks has no single "standard 3 views" API call - each named
        view (*Front, *Top, *Right) is created independently via
        CreateDrawViewFromModelView3, laid out left-to-right on the sheet.

        Args:
            model_path: Full path to the part/assembly these views reference
                (required - CreateDrawViewFromModelView3 needs an explicit model)
            pos_x, pos_y: Position for the front view on the sheet (meters)
            scale: View scale factor (applied to each view after creation)
            spacing: Horizontal gap between views (meters)
        """
        try:
            doc = get_active_doc()
            created = []
            for i, view_name in enumerate(("*Front", "*Top", "*Right")):
                view = doc.CreateDrawViewFromModelView3(
                    model_path, view_name, pos_x + i * spacing, pos_y, 0
                )
                if view is None:
                    return f"Failed to create {view_name} view" + (f" (created so far: {created})" if created else "")
                try:
                    view.ScaleDecimal = scale
                except Exception:
                    pass
                created.append(view_name)
            return f"Created views {created} starting at ({pos_x}, {pos_y}), scale {scale}"
        except Exception as e:
            return f"Error adding standard views: {e}"

    @mcp.tool()
    def add_isometric_view(model_path: str = "", pos_x: float = 0.4, pos_y: float = 0.15, scale: float = 1.0) -> str:
        """Add an isometric view to the drawing sheet.

        Args:
            model_path: Full path to the part/assembly this view references
            pos_x: X position on the sheet
            pos_y: Y position on the sheet
            scale: View scale factor
        """
        try:
            doc = get_active_doc()

            view = doc.CreateDrawViewFromModelView3(
                model_path, "*Isometric", pos_x, pos_y, 0
            )

            if view:
                try:
                    view.ScaleDecimal = scale
                except Exception:
                    pass
                return f"Isometric view added at ({pos_x}, {pos_y}), scale {scale}"
            return "Failed to create isometric view"
        except Exception as e:
            return f"Error adding isometric view: {e}"

    @mcp.tool()
    def add_section_view(
        parent_view_x: float = 0.15,
        parent_view_y: float = 0.15,
        section_line_x1: float = 0.1,
        section_line_y1: float = 0.05,
        section_line_x2: float = 0.1,
        section_line_y2: float = 0.25,
        pos_x: float = 0.35,
        pos_y: float = 0.15,
        label: str = "A"
    ) -> str:
        """Create a section view from a drawing view.
        
        Args:
            parent_view_x, parent_view_y: Position of the parent view
            section_line_x1, section_line_y1: Start of section line
            section_line_x2, section_line_y2: End of section line
            pos_x, pos_y: Position for the section view
            label: Section label (e.g. 'A', 'B')
        """
        try:
            doc = get_active_doc()
            drawing = doc
            
            view = drawing.CreateSectionViewAt5(
                pos_x, pos_y,      # section view position
                label,              # section label
                True,               # show section line
                False,              # partial section
                0                   # number of segment points
            )
            
            if view:
                return f"Section view '{label}' created at ({pos_x}, {pos_y})"
            return "Failed to create section view. Select a parent view and draw a section line first."
        except Exception as e:
            return f"Error creating section view: {e}"

    @mcp.tool()
    def add_detail_view(
        center_x: float = 0.2,
        center_y: float = 0.2,
        radius: float = 0.05,
        pos_x: float = 0.4,
        pos_y: float = 0.35,
        scale: float = 2.0,
        label: str = "B"
    ) -> str:
        """Create a detail (circle) view zoomed into a specific area.
        
        Args:
            center_x, center_y: Center of the detail circle
            radius: Radius of the detail circle
            pos_x, pos_y: Position for the detail view
            scale: Detail view scale
            label: Detail view label
        """
        try:
            doc = get_active_doc()
            drawing = doc
            
            view = drawing.CreateDetailViewAt4(
                pos_x, pos_y,      # position
                scale,             # scale
                True,              # full outline
                label,             # label
                0                  # profile type
            )
            
            if view:
                return f"Detail view '{label}' created at ({pos_x}, {pos_y}), scale {scale}"
            return "Failed to create detail view"
        except Exception as e:
            return f"Error creating detail view: {e}"

    @mcp.tool()
    def add_broken_view(
        pos_x: float = 0.15,
        pos_y: float = 0.15,
        depth: float = 10.0
    ) -> str:
        """Create a broken-out section view to show internal details.
        
        Args:
            pos_x, pos_y: Position of the parent view
            depth: Depth of the broken-out section
        """
        try:
            doc = get_active_doc()
            drawing = doc
            
            view = drawing.CreateBrokenOutSectionViewAt2(
                pos_x, pos_y,      # position
                depth,             # depth
                True,              # show cutting plane
                0                  # number of splines
            )
            
            if view:
                return f"Broken-out section view created at ({pos_x}, {pos_y}), depth={depth}"
            return "Failed to create broken-out section. Draw a closed spline on the parent view first."
        except Exception as e:
            return f"Error creating broken-out section: {e}"

    @mcp.tool()
    def set_sheet_format(sheet_size: str = "A", template_path: str = "") -> str:
        """Set the drawing sheet size and optionally load a sheet format template.
        
        Args:
            sheet_size: Sheet size - A, B, C, D, or E
            template_path: Path to a sheet format template file (.slddrt)
        """
        try:
            doc = get_active_doc()
            
            size_map = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4}
            size_val = size_map.get(sheet_size.lower(), 0)
            
            sheet = doc.GetCurrentSheet()
            if sheet is None:
                return "No active sheet found"
            
            if template_path:
                result = doc.SetupSheet6(
                    template_path,   # template
                    size_val,        # size
                    0,               # first angle
                    1,               # width
                    1,               # height
                    False            # custom
                )
                return f"Sheet format set to {sheet_size.upper()} using template {template_path}"
            else:
                result = doc.SetupSheet6(
                    "", size_val, 0,
                    0.2794,          # width in meters
                    0.2159,          # height in meters
                    False
                )
                return f"Sheet size set to {sheet_size.upper()}"
        except Exception as e:
            return f"Error setting sheet format: {e}"

    @mcp.tool()
    def add_weld_symbol(
        pos_x: float = 0.2,
        pos_y: float = 0.1,
        symbol_type: str = "fillet",
        size: float = 5.0,
        length: float = 10.0,
        pitch: float = 0.0
    ) -> str:
        """Add a weld symbol annotation to the drawing.
        
        Args:
            pos_x, pos_y: Position for the weld symbol
            symbol_type: Type of weld - fillet, groove, plug, slot, spot, seam
            size: Weld size
            length: Weld length
            pitch: Weld pitch (0 = no pitch)
        """
        try:
            doc = get_active_doc()
            
            type_map = {
                "fillet": 0, "groove": 1, "plug": 2,
                "slot": 3, "spot": 4, "seam": 5
            }
            w_type = type_map.get(symbol_type.lower(), 0)
            
            # Use annotation object to create weld symbol
            model_view = doc.GetFirstView()
            if model_view is None:
                return "No views found on the drawing sheet"
            
            view = model_view.GetNextView()
            if view is None:
                return "No drawing views found"
            
            annotation = view.AddWeldSymbol(
                pos_x, pos_y, 0,
                w_type, size, length, pitch,
                "", "", "", False, False
            )
            
            if annotation:
                return f"Weld symbol ({symbol_type}) added at ({pos_x}, {pos_y})"
            return "Failed to add weld symbol"
        except Exception as e:
            return f"Error adding weld symbol: {e}"

    @mcp.tool()
    def add_surface_finish(
        pos_x: float = 0.2,
        pos_y: float = 0.15,
        symbol_type: str = "machined",
        value: str = "Ra 3.2",
        lay_symbol: str = ""
    ) -> str:
        """Add a surface finish symbol to the drawing.
        
        Args:
            pos_x, pos_y: Position for the symbol
            symbol_type: 'machined', 'not_machined', or 'any'
            value: Surface finish value text (e.g. 'Ra 3.2', 'Ra 1.6')
            lay_symbol: Lay symbol character
        """
        try:
            doc = get_active_doc()
            model_view = doc.GetFirstView()
            if model_view is None:
                return "No views found on the drawing sheet"
            
            view = model_view.GetNextView()
            if view is None:
                return "No drawing views found"
            
            type_map = {"machined": 0, "not_machined": 1, "any": 2}
            s_type = type_map.get(symbol_type.lower(), 0)
            
            annotation = view.AddSurfaceFinishSymbol(
                pos_x, pos_y, 0,
                s_type, value, lay_symbol,
                "", False, False
            )
            
            if annotation:
                return f"Surface finish symbol ({value}) added at ({pos_x}, {pos_y})"
            return "Failed to add surface finish symbol"
        except Exception as e:
            return f"Error adding surface finish symbol: {e}"

    @mcp.tool()
    def create_bom(
        pos_x: float = 0.5,
        pos_y: float = 0.15,
        bom_type: str = "top_level",
        template_path: str = ""
    ) -> str:
        """Insert a bill of materials table for assembly drawings.
        
        Args:
            pos_x, pos_y: Top-left corner position of the BOM table
            bom_type: 'top_level', 'parts_only', or 'indented'
            template_path: Path to a BOM template file
        """
        try:
            doc = get_active_doc()
            
            type_map = {"top_level": 0, "parts_only": 1, "indented": 2}
            b_type = type_map.get(bom_type.lower(), 0)
            
            feature = doc.FeatureManager
            bom = feature.InsertBomTable2(
                template_path if template_path else "",
                pos_x, pos_y,      # anchor position
                b_type,            # bom type
                "",                # configuration
                ""                 # custom properties
            )
            
            if bom:
                return f"BOM table created at ({pos_x}, {pos_y}), type={bom_type}"
            return "Failed to create BOM. Ensure the drawing references an assembly."
        except Exception as e:
            return f"Error creating BOM: {e}"

    @mcp.tool()
    def add_balloon(
        pos_x: float = 0.3,
        pos_y: float = 0.2,
        auto_balloon: bool = False,
        style: str = "circular"
    ) -> str:
        """Add balloons to the drawing. Can auto-balance all items or place manually.
        
        Args:
            pos_x, pos_y: Position for manual balloon placement
            auto_balloon: If True, auto-balance all BOM items
            style: Balloon style - 'circular', 'triangle', 'hexagon', 'diamond'
        """
        try:
            doc = get_active_doc()
            model_view = doc.GetFirstView()
            if model_view is None:
                return "No views found on the drawing sheet"
            
            if auto_balloon:
                # Auto-balance all views
                result = True
                view = model_view.GetNextView()
                while view:
                    balloons = view.AddAutoBalloon(style)
                    view = view.GetNextView()
                return "Auto-balloons added to all drawing views"
            else:
                view = model_view.GetNextView()
                if view is None:
                    return "No drawing views found"
                balloon = view.AddBalloon(pos_x, pos_y, 0)
                if balloon:
                    return f"Balloon added at ({pos_x}, {pos_y})"
                return "Failed to add balloon"
        except Exception as e:
            return f"Error adding balloon: {e}"

    @mcp.tool()
    def add_centerline(
        line_x1: float = 0.1,
        line_y1: float = 0.1,
        line_x2: float = 0.3,
        line_y2: float = 0.3,
        add_center_marks: bool = True
    ) -> str:
        """Add centerlines and center marks to the drawing.
        
        Args:
            line_x1, line_y1: Start point of the centerline
            line_x2, line_y2: End point of the centerline
            add_center_marks: Also add center marks to circular edges
        """
        try:
            doc = get_active_doc()
            model_view = doc.GetFirstView()
            if model_view is None:
                return "No views found on the drawing sheet"
            
            view = model_view.GetNextView()
            if view is None:
                return "No drawing views found"
            
            result = view.AddCenterLine(line_x1, line_y1, 0, line_x2, line_y2, 0)
            
            msg = f"Centerline added from ({line_x1}, {line_y1}) to ({line_x2}, {line_y2})"
            
            if add_center_marks:
                view.AddCenterMarks(0, 0, True, True)
                msg += " with center marks"
            
            return msg
        except Exception as e:
            return f"Error adding centerline: {e}"

    @mcp.tool()
    def export_drawing_pdf(filepath: str = "") -> str:
        """Export the active drawing to PDF format.
        
        Args:
            filepath: Output PDF file path (absolute path). If empty, uses same name with .pdf extension.
        """
        try:
            doc = get_active_doc()
            sw_app = get_sw_app()
            
            if not filepath:
                title = doc.GetTitle()
                filepath = title.rsplit(".", 1)[0] + ".pdf"
            
            errors = sw_app.ActiveDoc.Extension.SaveAs(
                filepath,
                0,          # save as PDF
                0,          # options
                None,       # data
                None,       # data2
                errors      # errors
            )
            
            return f"Drawing exported to PDF: {filepath}"
        except Exception as e:
            return f"Error exporting to PDF: {e}"

    @mcp.tool()
    def export_drawing_dxf(filepath: str = "", sheet_scale: float = 1.0) -> str:
        """Export the active drawing sheet to DXF format.
        
        Args:
            filepath: Output DXF file path (absolute path)
            sheet_scale: Scale factor for the export
        """
        try:
            doc = get_active_doc()
            sw_app = get_sw_app()
            
            if not filepath:
                title = doc.GetTitle()
                filepath = title.rsplit(".", 1)[0] + ".dxf"
            
            errors = sw_app.ActiveDoc.Extension.SaveAs(
                filepath,
                0,          # save as DXF
                0,          # options
                None,
                None,
                errors
            )
            
            return f"Drawing exported to DXF: {filepath}"
        except Exception as e:
            return f"Error exporting to DXF: {e}"
