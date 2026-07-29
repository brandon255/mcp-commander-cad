"""
Dimension tools for Solidworks MCP server.
Provides smart dimensioning, ordinate, baseline, chain, tolerance, and GDT tools.
"""
from solidworks_mcp.api.connection import get_sw_app, get_active_doc

# Dimension type constants
SW_DIM_SMART = 0
SW_DIM_HORIZONTAL = 1
SW_DIM_VERTICAL = 2
SW_DIM_ORDINATE = 3
SW_DIM_BASELINE = 4
SW_DIM_CHAIN = 5

# Tolerance type constants
SW_TOL_NONE = 0
SW_TOL_BILATERAL = 1
SW_TOL_UNILATERAL = 2
SW_TOL_LIMITS = 3
SW_TOL_FIT = 4
SW_TOL_FIT_WITH_TOL = 5
SW_TOL_MAX = 6
SW_TOL_MIN = 7

# GDT frame type constants
SW_GDT_STRAIGHTNESS = 0
SW_GDT_FLATNESS = 1
SW_GDT_CIRCULARITY = 2
SW_GDT_CYLINDRICITY = 3
SW_GDT_PERPENDICULARITY = 4
SW_GDT_ANGULARITY = 5
SW_GDT_PARALLELISM = 6
SW_GDT_POSITION = 7
SW_GDT_CONCENTRICITY = 8
SW_GDT_SYMMETRY = 9
SW_GDT_CIRCULAR_RUNOUT = 10
SW_GDT_TOTAL_RUNOUT = 11
SW_GDT_PROFILE_LINE = 12
SW_GDT_PROFILE_SURFACE = 13


def register_dimension_tools(mcp):
    @mcp.tool()
    def auto_dim_sketch() -> str:
        """Auto-dimension all entities in the active sketch.
        Automatically adds dimensions to fully define the sketch.
        """
        try:
            doc = get_active_doc()
            sketch_mgr = doc.SketchManager
            
            result = sketch_mgr.AutoDimension(
                0,      # scheme
                0,      # horizontal placement
                0,      # vertical placement
                0       # dimension type
            )
            
            if result:
                return "Auto-dimension applied to all sketch entities"
            return "Auto-dimension failed. Ensure a sketch is active with entities."
        except Exception as e:
            return f"Error auto-dimensioning: {e}"

    @mcp.tool()
    def add_smart_dim(
        x1: float, y1: float,
        x2: float, y2: float,
        dim_value: float = 0.0,
        offset_x: float = 0.0,
        offset_y: float = 0.0
    ) -> str:
        """Add a smart dimension between two points or edges.
        
        Args:
            x1, y1: First point coordinates
            x2, y2: Second point coordinates
            dim_value: Override dimension value (0 = measured value)
            offset_x, offset_y: Dimension line offset position
        """
        try:
            doc = get_active_doc()
            
            dim = doc.AddDimension2(
                x1, y1, 0,
                x2, y2, 0,
                offset_x, offset_y, 0
            )
            
            if dim:
                value_text = f" = {dim_value}" if dim_value > 0 else ""
                return f"Smart dimension added between ({x1}, {y1}) and ({x2}, {y2}){value_text}"
            return "Failed to add smart dimension"
        except Exception as e:
            return f"Error adding smart dimension: {e}"

    @mcp.tool()
    def add_ordinate_dim(
        origin_x: float = 0.0,
        origin_y: float = 0.0,
        points: list[list[float]] | None = None
    ) -> str:
        """Add an ordinate dimension set from a common origin.
        
        Args:
            origin_x, origin_y: Origin point for ordinate dimensions
            points: List of [x, y] points to dimension
        """
        try:
            if points is None:
                points = [[10.0, 0.0], [20.0, 5.0], [30.0, 0.0]]
            
            doc = get_active_doc()
            count = 0
            
            for pt in points:
                px, py = pt
                dim = doc.AddDimension2(
                    origin_x, origin_y, 0,
                    px, py, 0,
                    px, origin_y - 0.02, 0
                )
                if dim:
                    count += 1
            
            return f"Added {count} ordinate dimensions from origin ({origin_x}, {origin_y})"
        except Exception as e:
            return f"Error adding ordinate dimension: {e}"

    @mcp.tool()
    def add_baseline_dim(
        start_x: float = 0.0,
        start_y: float = 0.0,
        points: list[list[float]] | None = None
    ) -> str:
        """Add baseline (datum) dimensions from a reference edge.
        
        Args:
            start_x, start_y: Start point of the baseline reference
            points: List of [x, y] points to dimension from the baseline
        """
        try:
            if points is None:
                points = [[10.0, 0.0], [25.0, 0.0], [40.0, 0.0]]
            
            doc = get_active_doc()
            count = 0
            
            for pt in points:
                px, py = pt
                dim = doc.AddDimension2(
                    start_x, start_y, 0,
                    px, py, 0,
                    px, start_y + 0.03, 0
                )
                if dim:
                    count += 1
            
            return f"Added {count} baseline dimensions from ({start_x}, {start_y})"
        except Exception as e:
            return f"Error adding baseline dimension: {e}"

    @mcp.tool()
    def add_chain_dim(
        points: list[list[float]] | None = None,
        offset: float = 0.03
    ) -> str:
        """Add chain dimensions between consecutive points.
        
        Args:
            points: List of [x, y] points to chain-dimension
            offset: Offset distance for dimension lines
        """
        try:
            if points is None:
                points = [[0.0, 0.0], [10.0, 0.0], [25.0, 0.0], [40.0, 0.0]]
            
            if len(points) < 2:
                return "Error: at least 2 points required"
            
            doc = get_active_doc()
            count = 0
            
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                dim = doc.AddDimension2(
                    x1, y1, 0,
                    x2, y2, 0,
                    (x1 + x2) / 2, y1 + offset, 0
                )
                if dim:
                    count += 1
            
            return f"Added {count} chain dimensions"
        except Exception as e:
            return f"Error adding chain dimension: {e}"

    @mcp.tool()
    def set_dim_tolerance(
        tolerance_type: str = "bilateral",
        tolerance_plus: float = 0.01,
        tolerance_minus: float = 0.01,
        fits_hole: str = "",
        fits_shaft: str = ""
    ) -> str:
        """Set tolerance on the selected dimension.
        
        Args:
            tolerance_type: Type - bilateral, unilateral, limits, fit, none
            tolerance_plus: Upper/positive tolerance value
            tolerance_minus: Lower/negative tolerance value
            fits_hole: Hole fit designation (e.g. 'H7') for fit tolerances
            fits_shaft: Shaft fit designation (e.g. 'g6') for fit tolerances
        """
        try:
            doc = get_active_doc()
            sw_app = get_sw_app()
            
            sel_mgr = sw_app.ISelectionManager
            if sel_mgr is None:
                sel_mgr = doc.SelectionManager
            
            sel_obj = sel_mgr.GetSelectedObject6(0, -1)
            if sel_obj is None:
                return "No dimension selected. Select a dimension first."
            
            dim = doc.GetDimensionByName(sel_obj.GetNameForSelection())
            if dim is None:
                return "Selected object is not a dimension"
            
            tol_map = {
                "none": SW_TOL_NONE,
                "bilateral": SW_TOL_BILATERAL,
                "unilateral": SW_TOL_UNILATERAL,
                "limits": SW_TOL_LIMITS,
                "fit": SW_TOL_FIT,
                "fit_with_tolerance": SW_TOL_FIT_WITH_TOL,
                "max": SW_TOL_MAX,
                "min": SW_TOL_MIN,
            }
            
            tol_type = tol_map.get(tolerance_type.lower(), SW_TOL_NONE)
            dim.ToleranceType = tol_type
            
            if tol_type == SW_TOL_BILATERAL:
                dim.ToleranceMaxValue = tolerance_plus
                dim.ToleranceMinValue = tolerance_minus
            elif tol_type == SW_TOL_UNILATERAL:
                dim.ToleranceMaxValue = tolerance_plus
            elif tol_type == SW_TOL_LIMITS:
                dim.ToleranceMaxValue = tolerance_plus
                dim.ToleranceMinValue = tolerance_minus
            elif tol_type in (SW_TOL_FIT, SW_TOL_FIT_WITH_TOL):
                dim.ToleranceFitHole = fits_hole
                dim.ToleranceFitShaft = fits_shaft
            
            doc.GraphicsRedraw2()
            
            return f"Tolerance set: {tolerance_type}, +{tolerance_plus}/-{tolerance_minus}"
        except Exception as e:
            return f"Error setting dimension tolerance: {e}"

    @mcp.tool()
    def add_gdt(
        gdt_type: str = "position",
        tolerance_value: float = 0.0,
        datum_a: str = "",
        datum_b: str = "",
        datum_c: str = "",
        pos_x: float = 0.2,
        pos_y: float = 0.2,
        material_condition: str = ""
    ) -> str:
        """Add a geometric dimensioning and tolerancing (GDT) frame.
        
        Args:
            gdt_type: GDT symbol type - straightness, flatness, circularity, cylindricity,
                     perpendicularity, angularity, parallelism, position, concentricity,
                     symmetry, circular_runout, total_runout, profile_line, profile_surface
            tolerance_value: Tolerance value
            datum_a, datum_b, datum_c: Primary, secondary, tertiary datum references
            pos_x, pos_y: Position for the GDT frame
            material_condition: Material condition modifier - 'mmc' (maximum), 'lmc' (least), 'rfs' (regardless)
        """
        try:
            type_map = {
                "straightness": SW_GDT_STRAIGHTNESS,
                "flatness": SW_GDT_FLATNESS,
                "circularity": SW_GDT_CIRCULARITY,
                "cylindricity": SW_GDT_CYLINDRICITY,
                "perpendicularity": SW_GDT_PERPENDICULARITY,
                "angularity": SW_GDT_ANGULARITY,
                "parallelism": SW_GDT_PARALLELISM,
                "position": SW_GDT_POSITION,
                "concentricity": SW_GDT_CONCENTRICITY,
                "symmetry": SW_GDT_SYMMETRY,
                "circular_runout": SW_GDT_CIRCULAR_RUNOUT,
                "total_runout": SW_GDT_TOTAL_RUNOUT,
                "profile_line": SW_GDT_PROFILE_LINE,
                "profile_surface": SW_GDT_PROFILE_SURFACE,
            }
            
            g_val = type_map.get(gdt_type.lower())
            if g_val is None:
                return f"Error: unknown GDT type '{gdt_type}'. Valid: {', '.join(type_map.keys())}"
            
            mc_map = {"mmc": 1, "lmc": 2, "rfs": 0}
            mc_val = mc_map.get(material_condition.lower(), 0)
            
            doc = get_active_doc()
            model_view = doc.GetFirstView()
            if model_view is None:
                return "No views found on the drawing"
            
            view = model_view.GetNextView()
            if view is None:
                return "No drawing views found"
            
            gdt_frame = view.AddGDT(
                g_val,             # frame symbol
                tolerance_value,   # tolerance
                mc_val,            # material condition
                0,                 # second frame
                0, 0, 0,          # datum material conditions
                datum_a,           # datum A
                datum_b,           # datum B
                datum_c,           # datum C
                "",                # zone
                pos_x, pos_y, 0   # position
            )
            
            if gdt_frame:
                datums = ", ".join(d for d in [datum_a, datum_b, datum_c] if d)
                return f"GDT frame added: {gdt_type}, tolerance={tolerance_value}, datums=[{datums}]"
            return "Failed to add GDT frame"
        except Exception as e:
            return f"Error adding GDT frame: {e}"

    @mcp.tool()
    def add_datum(
        datum_letter: str = "A",
        pos_x: float = 0.1,
        pos_y: float = 0.1
    ) -> str:
        """Add a datum feature symbol to the drawing.
        
        Args:
            datum_letter: Datum identifier letter (e.g. 'A', 'B', 'C')
            pos_x, pos_y: Position for the datum symbol
        """
        try:
            doc = get_active_doc()
            model_view = doc.GetFirstView()
            if model_view is None:
                return "No views found on the drawing"
            
            view = model_view.GetNextView()
            if view is None:
                return "No drawing views found"
            
            datum = view.AddDatumTag(
                datum_letter.upper(),
                pos_x, pos_y, 0
            )
            
            if datum:
                return f"Datum symbol '{datum_letter.upper()}' added at ({pos_x}, {pos_y})"
            return "Failed to add datum symbol"
        except Exception as e:
            return f"Error adding datum symbol: {e}"

    @mcp.tool()
    def set_dim_precision(precision: int = 2) -> str:
        """Set the number of decimal places for the selected dimension.
        
        Args:
            precision: Number of decimal places (0-8)
        """
        try:
            if precision < 0 or precision > 8:
                return "Error: precision must be between 0 and 8"
            
            doc = get_active_doc()
            sw_app = get_sw_app()
            
            sel_mgr = sw_app.ISelectionManager
            if sel_mgr is None:
                sel_mgr = doc.SelectionManager
            
            sel_obj = sel_mgr.GetSelectedObject6(0, -1)
            if sel_obj is None:
                return "No dimension selected. Select a dimension first."
            
            dim = doc.GetDimensionByName(sel_obj.GetNameForSelection())
            if dim is None:
                return "Selected object is not a dimension"
            
            dim.SetPrecision2(0, precision, True)
            doc.GraphicsRedraw2()
            
            return f"Dimension precision set to {precision} decimal places"
        except Exception as e:
            return f"Error setting dimension precision: {e}"
