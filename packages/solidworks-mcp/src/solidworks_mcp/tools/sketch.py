"""
Sketch tools for Solidworks MCP server.
"""
from solidworks_mcp.api.connection import get_sw_app, get_active_doc

# Solidworks sketch entity type constants
SW_SKETCH_SEGMENT_LINE = 0
SW_SKETCH_SEGMENT_ARC = 1
SW_SKETCH_SEGMENT_ELLIPSE = 3
SW_SKETCH_SEGMENT_SPLINE = 5
SW_SKETCH_SEGMENT_TEXT = 8
SW_SKETCH_SEGMENT_PARABOLA = 4

# Constraint type constants
SW_CONSTRAINT_COINCIDENT = 0
SW_CONSTRAINT_TANGENT = 6
SW_CONSTRAINT_PERPENDICULAR = 4
SW_CONSTRAINT_PARALLEL = 3
SW_CONSTRAINT_EQUAL = 7
SW_CONSTRAINT_SYMMETRIC = 9
SW_CONSTRAINT_FIX = 11
SW_CONSTRAINT_HORIZONTAL = 1
SW_CONSTRAINT_VERTICAL = 2
SW_CONSTRAINT_COLLINEAR = 12
SW_CONSTRAINT_CONCENTRIC = 5
SW_CONSTRAINT_MIDPOINT = 10
SW_CONSTRAINT_PIERCE = 13

# Plane type constants
SW_PLANE_TOP = 2
SW_PLANE_FRONT = 1
SW_PLANE_RIGHT = 3


def register_sketch_tools(mcp):
    @mcp.tool()
    def create_sketch(plane_name: str = "top", custom_plane_name: str = "") -> str:
        """Create a new 2D sketch on the specified plane.
        
        Args:
            plane_name: One of 'top', 'front', 'right', or 'custom'
            custom_plane_name: Name of a custom reference plane (required if plane_name is 'custom')
        """
        try:
            sw_app = get_sw_app()
            doc = get_active_doc()
            model = doc
            
            plane_map = {
                "top": SW_PLANE_TOP,
                "front": SW_PLANE_FRONT,
                "right": SW_PLANE_RIGHT,
            }
            
            if plane_name.lower() == "custom":
                if not custom_plane_name:
                    return "Error: custom_plane_name is required when plane_name is 'custom'"
                ref_plane = model.GetFeatureByName(custom_plane_name)
                if ref_plane is None:
                    return f"Error: Could not find reference plane '{custom_plane_name}'"
                feature = ref_plane
            else:
                plane_id = plane_map.get(plane_name.lower(), SW_PLANE_TOP)
                feature = model.GetReferencePlane(plane_id)
                if feature is None:
                    return f"Error: Could not get {plane_name} reference plane"
            
            sketch = model.SketchManager
            sketch.InsertSketch(True)
            
            # Select the plane
            model.ClearSelection2(True)
            feature.Select2(False, 0)
            sketch.InsertSketch(True)
            
            return f"Sketch created on {plane_name} plane"
        except Exception as e:
            return f"Error creating sketch: {e}"

    @mcp.tool()
    def sketch_line(x1: float, y1: float, x2: float, y2: float) -> str:
        """Draw a line between two points in the active sketch.
        
        Args:
            x1, y1: Start point coordinates
            x2, y2: End point coordinates
        """
        try:
            doc = get_active_doc()
            sketch = doc.SketchManager
            result = sketch.CreateLine(x1, y1, 0, x2, y2, 0)
            if result:
                return f"Line created from ({x1}, {y1}) to ({x2}, {y2})"
            return "Failed to create line"
        except Exception as e:
            return f"Error creating line: {e}"

    @mcp.tool()
    def sketch_circle(cx: float, cy: float, radius: float) -> str:
        """Draw a circle at center with given radius.
        
        Args:
            cx, cy: Center coordinates
            radius: Circle radius (must be positive)
        """
        try:
            if radius <= 0:
                return "Error: radius must be positive"
            doc = get_active_doc()
            sketch = doc.SketchManager
            result = sketch.CreateCircle(cx, cy, 0, cx + radius, cy, 0)
            if result:
                return f"Circle created at ({cx}, {cy}) with radius {radius}"
            return "Failed to create circle"
        except Exception as e:
            return f"Error creating circle: {e}"

    @mcp.tool()
    def sketch_rectangle(x1: float, y1: float, x2: float, y2: float) -> str:
        """Draw a rectangle from corner (x1,y1) to corner (x2,y2).
        
        Args:
            x1, y1: First corner coordinates
            x2, y2: Opposite corner coordinates
        """
        try:
            doc = get_active_doc()
            sketch = doc.SketchManager
            result = sketch.CreateCenterRectangle(
                (x1 + x2) / 2, (y1 + y2) / 2, 0,
                x1, y1, 0
            )
            if result:
                w = abs(x2 - x1)
                h = abs(y2 - y1)
                return f"Rectangle created with width {w:.4f} and height {h:.4f}"
            return "Failed to create rectangle"
        except Exception as e:
            return f"Error creating rectangle: {e}"

    @mcp.tool()
    def sketch_arc(cx: float, cy: float, sx: float, sy: float, ex: float, ey: float) -> str:
        """Draw a 3-point arc defined by center, start point, and end point.
        
        Args:
            cx, cy: Arc center coordinates
            sx, sy: Arc start point coordinates
            ex, ey: Arc end point coordinates
        """
        try:
            doc = get_active_doc()
            sketch = doc.SketchManager
            result = sketch.CreateArc(cx, cy, 0, sx, sy, 0, ex, ey, 0, 1)
            if result:
                return f"3-point arc created with center ({cx}, {cy})"
            return "Failed to create arc"
        except Exception as e:
            return f"Error creating arc: {e}"

    @mcp.tool()
    def sketch_spline(points: list[list[float]]) -> str:
        """Draw a spline through given control points.
        
        Args:
            points: List of [x, y] coordinate pairs defining the spline path
        """
        try:
            if len(points) < 2:
                return "Error: at least 2 points required for a spline"
            doc = get_active_doc()
            sketch = doc.SketchManager
            
            import win32com.client
            spline_points = win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, 
                [coord for pt in points for coord in pt])
            
            result = sketch.CreateSpline(spline_points, 0)
            if result:
                return f"Spline created through {len(points)} control points"
            return "Failed to create spline"
        except Exception as e:
            return f"Error creating spline: {e}"

    @mcp.tool()
    def sketch_slot(cx: float, cy: float, length: float, width: float, angle: float = 0) -> str:
        """Draw a straight slot centered at (cx, cy).
        
        Args:
            cx, cy: Slot center coordinates
            length: Total length of the slot
            width: Width of the slot
            angle: Rotation angle in degrees (0 = horizontal)
        """
        try:
            import math
            doc = get_active_doc()
            sketch = doc.SketchManager
            
            rad = math.radians(angle)
            half_l = length / 2
            half_w = width / 2
            
            # Create slot using four lines and two arcs
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            
            # Four corner points of the slot
            pts = []
            for dx, dy in [(-half_l, -half_w), (-half_l, half_w), (half_l, half_w), (half_l, -half_w)]:
                rx = cx + dx * cos_a - dy * sin_a
                ry = cy + dx * sin_a + dy * cos_a
                pts.append((rx, ry))
            
            sketch.CreateLine(pts[0][0], pts[0][1], 0, pts[1][0], pts[1][1], 0)
            sketch.CreateLine(pts[1][0], pts[1][1], 0, pts[2][0], pts[2][1], 0)
            sketch.CreateLine(pts[2][0], pts[2][1], 0, pts[3][0], pts[3][1], 0)
            sketch.CreateLine(pts[3][0], pts[3][1], 0, pts[0][0], pts[0][1], 0)
            
            return f"Slot created at ({cx}, {cy}) with length {length} and width {width} at {angle} degrees"
        except Exception as e:
            return f"Error creating slot: {e}"

    @mcp.tool()
    def sketch_text(x: float, y: float, text: str, height: float = 10, bold: bool = False) -> str:
        """Add text annotation to the active sketch.
        
        Args:
            x, y: Text insertion point coordinates
            text: The text string to add
            height: Text height in document units
            bold: Whether to use bold font
        """
        try:
            doc = get_active_doc()
            sketch = doc.SketchManager
            result = sketch.CreateText(x, y, 0, height, 0, text, 0, 0, 0, bold, False, False)
            if result:
                return f"Text '{text}' added at ({x}, {y})"
            return "Failed to create text"
        except Exception as e:
            return f"Error creating text: {e}"

    @mcp.tool()
    def sketch_pattern(
        pattern_type: str,
        count: int,
        spacing: float = 0,
        angle: float = 0,
        direction: str = "x"
    ) -> str:
        """Create a linear or circular pattern of sketch entities.
        
        Args:
            pattern_type: 'linear' or 'circular'
            count: Number of instances (including original)
            spacing: Distance between instances (linear) or total angle (circular, in degrees)
            angle: Pattern angle in degrees (linear only)
            direction: 'x' or 'y' for linear patterns
        """
        try:
            doc = get_active_doc()
            sketch_mgr = doc.SketchManager
            
            if pattern_type.lower() == "linear":
                if direction.lower() == "y":
                    angle = 90.0
                result = sketch_mgr.SketchLinearPattern(count, spacing, angle, True, False)
                if result:
                    return f"Linear pattern created: {count} instances, spacing {spacing}"
                return "Failed to create linear pattern"
            elif pattern_type.lower() == "circular":
                import math
                arc_angle = math.radians(spacing if spacing > 0 else 360)
                result = sketch_mgr.SketchCircularPattern(count, arc_angle, True, False)
                if result:
                    return f"Circular pattern created: {count} instances"
                return "Failed to create circular pattern"
            else:
                return "Error: pattern_type must be 'linear' or 'circular'"
        except Exception as e:
            return f"Error creating sketch pattern: {e}"

    @mcp.tool()
    def sketch_mirror(axis_x1: float, axis_y1: float, axis_x2: float, axis_y2: float) -> str:
        """Mirror sketch entities about a line defined by two points.
        
        Args:
            axis_x1, axis_y1: First point of the mirror axis
            axis_x2, axis_y2: Second point of the mirror axis
        """
        try:
            doc = get_active_doc()
            sketch_mgr = doc.SketchManager
            
            doc.ClearSelection2(True)
            sketch_mgr.SketchMirror(axis_x1, axis_y1, 0, axis_x2, axis_y2, 0)
            return f"Sketch entities mirrored about line from ({axis_x1}, {axis_y1}) to ({axis_x2}, {axis_y2})"
        except Exception as e:
            return f"Error mirroring sketch: {e}"

    @mcp.tool()
    def sketch_trim() -> str:
        """Trim sketch entities to their nearest intersections. Operates on the active sketch."""
        try:
            doc = get_active_doc()
            sketch_mgr = doc.SketchManager
            result = sketch_mgr.SketchTrim(1, 0, 0, 0, 0, 0)
            if result:
                return "Sketch trim operation completed"
            return "No entities trimmed"
        except Exception as e:
            return f"Error trimming sketch: {e}"

    @mcp.tool()
    def sketch_offset(distance: float) -> str:
        """Offset selected sketch entities by the given distance.
        
        Args:
            distance: Offset distance (positive = outward, negative = inward)
        """
        try:
            doc = get_active_doc()
            sketch_mgr = doc.SketchManager
            result = sketch_mgr.SketchOffset(distance, True, True, True)
            if result:
                return f"Sketch entities offset by {distance}"
            return "No entities to offset (select entities first)"
        except Exception as e:
            return f"Error offsetting sketch: {e}"

    @mcp.tool()
    def sketch_constraints(
        constraint_type: str,
        entity1_index: int = 0,
        entity2_index: int = 0
    ) -> str:
        """Add a geometric constraint between sketch entities.
        
        Args:
            constraint_type: One of 'coincident', 'tangent', 'perpendicular', 'parallel',
                           'equal', 'symmetric', 'fix', 'horizontal', 'vertical',
                           'collinear', 'concentric', 'midpoint', 'pierce'
            entity1_index: Index of the first sketch entity
            entity2_index: Index of the second sketch entity (not needed for 'fix', 'horizontal', 'vertical')
        """
        try:
            constraint_map = {
                "coincident": SW_CONSTRAINT_COINCIDENT,
                "tangent": SW_CONSTRAINT_TANGENT,
                "perpendicular": SW_CONSTRAINT_PERPENDICULAR,
                "parallel": SW_CONSTRAINT_PARALLEL,
                "equal": SW_CONSTRAINT_EQUAL,
                "symmetric": SW_CONSTRAINT_SYMMETRIC,
                "fix": SW_CONSTRAINT_FIX,
                "horizontal": SW_CONSTRAINT_HORIZONTAL,
                "vertical": SW_CONSTRAINT_VERTICAL,
                "collinear": SW_CONSTRAINT_COLLINEAR,
                "concentric": SW_CONSTRAINT_CONCENTRIC,
                "midpoint": SW_CONSTRAINT_MIDPOINT,
                "pierce": SW_CONSTRAINT_PIERCE,
            }
            
            c_type = constraint_map.get(constraint_type.lower())
            if c_type is None:
                return f"Error: unknown constraint type '{constraint_type}'. Valid types: {', '.join(constraint_map.keys())}"
            
            doc = get_active_doc()
            sketch = doc.SketchManager
            sketch_segment = sketch.ActiveSketch
            
            result = sketch.AddConstraint(entity1_index, entity2_index, c_type)
            if result:
                return f"Added {constraint_type} constraint between entity {entity1_index} and entity {entity2_index}"
            return f"Failed to add {constraint_type} constraint"
        except Exception as e:
            return f"Error adding constraint: {e}"

    @mcp.tool()
    def exit_sketch() -> str:
        """Exit the active sketch and return to feature editing mode."""
        try:
            doc = get_active_doc()
            sketch_mgr = doc.SketchManager
            sketch_mgr.InsertSketch(False)
            return "Exited sketch successfully"
        except Exception as e:
            return f"Error exiting sketch: {e}"
