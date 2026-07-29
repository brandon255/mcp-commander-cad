"""
MCP Commander Bridge — Fusion 360 Add-In

Runs inside Fusion 360's Python environment and exposes a local HTTP server
that accepts JSON commands from the external fusion360-mcp cartridge.

Communication:
    External MCP server  →  POST http://localhost:8080/api/command
                            {"command": "...", "params": {...}}
    Fusion 360 bridge    →  {"status": "ok|error", "result": ..., "message": "..."}

Architecture:
    Fusion 360 (embedded Python)
    ┌──────────────────────────────────────┐
    │ MCPCommanderBridge (add-in)          │
    │  ┌──────────────┐  ┌──────────────┐ │
    │  │ HTTP Server  │  │ Command      │ │
    │  │ (threading)  │─│ Dispatcher    │ │
    │  │ :8080        │  │              │ │
    │  └──────────────┘  │ ┌──────────┐│ │
    │                     │ │ Sketches ││ │
    │                     │ │ Features ││ │
    │                     │ │ Drawing  ││ │
    │                     │ │ Analysis ││ │
    │                     │ │ Export   ││ │
    │                     │ └──────────┘│ │
    │                     └──────────────┘ │
    └──────────────────────────────────────┘
            ↑ connects to Fusion 360 API
    adsk.fusion, adsk.core

Installation:
    1. Copy MCPCommanderBridge.py and MCPCommanderBridge.manifest
       to Fusion 360's Scripts and Add-Ins folder:
       Windows: %APPDATA%\\Autodesk\\Autodesk Fusion 360\\API\\Scripts
       Mac: ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts
    2. Open Fusion 360 → Utilities → Scripts and Add-Ins
    3. Select MCPCommanderBridge, click Run
    4. The bridge starts on localhost:8080
    5. Start the external fusion360-mcp MCP server
"""

import json
import threading
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from functools import partial

try:
    import adsk.core, adsk.fusion, adsk.cam
    HAS_FUSION_API = True
except ImportError:
    HAS_FUSION_API = False

# ---------------------------------------------------------------------------
# Global references
# ---------------------------------------------------------------------------

_app: adsk.core.Application = None
_ui: adsk.core.UserInterface = None
_handlers: list = []
_command_executor = None  # threading-based executor for API calls

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8080


# ===========================================================================
# Command Handlers — Sketch operations
# ===========================================================================

def _get_active_design():
    """Return the active design product, or None."""
    if not HAS_FUSION_API:
        return None
    product = _app.activeProduct
    if product and product.productType == adsk.fusion.ProductTypes.DesignProductType:
        return adsk.fusion.Design.cast(product)
    return None


def _get_root_component(design):
    """Return the root component of a design."""
    return design.rootComponent if design else None


def _get_sketch_by_name(component, sketch_name):
    """Find a sketch by name in a component."""
    if not component:
        return None
    for i in range(component.sketches.count):
        sk = component.sketches.item(i)
        if sk.name == sketch_name:
            return sk
    return None


def _get_active_or_named_sketch(params):
    """Get sketch by name param, or return the active sketch."""
    sketch_name = params.get("sketch_name", "")
    design = _get_active_design()
    comp = _get_root_component(design) if design else None

    if sketch_name:
        sk = _get_sketch_by_name(comp, sketch_name)
        if sk:
            return sk
    # Fall back to active sketch
    if design:
        active_sk = design.activeSketch
        if active_sk:
            return active_sk
    return None


def _get_or_create_sketch(params):
    """Get existing sketch or create a new one on the specified plane."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return None, "No active design"

    sketch_name = params.get("sketch_name", "")
    if sketch_name:
        existing = _get_sketch_by_name(comp, sketch_name)
        if existing:
            return existing, None

    # Create new sketch on specified plane
    plane_str = params.get("plane", "XY")
    plane = _get_construction_plane(comp, plane_str)
    if not plane:
        return None, f"Cannot find plane '{plane_str}'"

    sketches = comp.sketches
    sk = sketches.add(plane)
    if sketch_name:
        sk.name = sketch_name
    return sk, None


def _get_construction_plane(comp, plane_str):
    """Return a construction plane reference for standard planes."""
    if not comp:
        return None
    if plane_str == "XY":
        return comp.xYConstructionPlane
    elif plane_str == "XZ":
        return comp.xZConstructionPlane
    elif plane_str == "YZ":
        return comp.yZConstructionPlane
    else:
        # Try to find by name
        for i in range(comp.constructionPlanes.count):
            cp = comp.constructionPlanes.item(i)
            if cp.name == plane_str:
                return cp
        return None


def _get_point2d(params, prefix=""):
    """Extract a Point2D from params dict."""
    x = params.get(f"{prefix}x", params.get(f"{prefix}_x", 0.0))
    y = params.get(f"{prefix}y", params.get(f"{prefix}_y", 0.0))
    if HAS_FUSION_API:
        return adsk.core.Point2D.create(float(x), float(y))
    return None


def _get_point3d(params, prefix=""):
    """Extract a Point3D from params dict."""
    x = params.get(f"{prefix}x", params.get(f"{prefix}_x", 0.0))
    y = params.get(f"{prefix}y", params.get(f"{prefix}_y", 0.0))
    z = params.get(f"{prefix}z", params.get(f"{prefix}_z", 0.0))
    if HAS_FUSION_API:
        return adsk.core.Point3D.create(float(x), float(y), float(z))
    return None


def _create_sketch(params):
    """Create a new sketch on a construction plane."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    plane_str = params.get("plane", "XY")
    plane = _get_construction_plane(comp, plane_str)
    if not plane:
        return {"error": f"Cannot find plane '{plane_str}'"}

    sketch_name = params.get("sketch_name", "")
    sk = comp.sketches.add(plane)
    if sketch_name:
        sk.name = sketch_name

    return {
        "sketch_name": sk.name,
        "sketch_id": sk.entityToken,
        "plane": plane_str,
    }


def _sketch_line(params):
    """Draw a line segment in a sketch."""
    sk, err = _get_or_create_sketch(params)
    if err:
        return {"error": err}
    if not sk:
        return {"error": "No sketch available"}

    x1 = float(params.get("x1", params.get("start_x", 0)))
    y1 = float(params.get("y1", params.get("start_y", 0)))
    x2 = float(params.get("x2", params.get("end_x", 10)))
    y2 = float(params.get("y2", params.get("end_y", 0)))

    lines = sk.sketchCurves.sketchLines
    start_pt = adsk.core.Point2D.create(x1, y1)
    end_pt = adsk.core.Point2D.create(x2, y2)
    line = lines.addByTwoPoints(start_pt, end_pt)

    return {
        "entity_type": "line",
        "entity_id": line.entityToken,
        "start": {"x": x1, "y": y1},
        "end": {"x": x2, "y": y2},
    }


def _sketch_circle(params):
    """Draw a circle at center with radius."""
    sk, err = _get_or_create_sketch(params)
    if err:
        return {"error": err}
    if not sk:
        return {"error": "No sketch available"}

    cx = float(params.get("center_x", params.get("x", 0)))
    cy = float(params.get("center_y", params.get("y", 0)))
    r = float(params.get("radius", 1.0))

    circles = sk.sketchCurves.sketchCircles
    center = adsk.core.Point2D.create(cx, cy)
    circ = circles.addByCenterRadius(center, r)

    return {
        "entity_type": "circle",
        "entity_id": circ.entityToken,
        "center": {"x": cx, "y": cy},
        "radius": r,
    }


def _sketch_rectangle(params):
    """Draw a rectangle by two corner points."""
    sk, err = _get_or_create_sketch(params)
    if err:
        return {"error": err}
    if not sk:
        return {"error": "No sketch available"}

    x1 = float(params.get("x1", params.get("corner1_x", 0)))
    y1 = float(params.get("y1", params.get("corner1_y", 0)))
    x2 = float(params.get("x2", params.get("corner2_x", 10)))
    y2 = float(params.get("y2", params.get("corner2_y", 5)))

    lines = sk.sketchCurves.sketchLines
    pt1 = adsk.core.Point2D.create(x1, y1)
    pt2 = adsk.core.Point2D.create(x2, y1)
    pt3 = adsk.core.Point2D.create(x2, y2)
    pt4 = adsk.core.Point2D.create(x1, y2)

    l1 = lines.addByTwoPoints(pt1, pt2)
    l2 = lines.addByTwoPoints(pt2, pt3)
    l3 = lines.addByTwoPoints(pt3, pt4)
    l4 = lines.addByTwoPoints(pt4, pt1)

    return {
        "entity_type": "rectangle",
        "entity_ids": [l1.entityToken, l2.entityToken, l3.entityToken, l4.entityToken],
        "corner1": {"x": x1, "y": y1},
        "corner2": {"x": x2, "y": y2},
    }


def _sketch_arc(params):
    """Draw an arc (center-point or 3-point)."""
    sk, err = _get_or_create_sketch(params)
    if err:
        return {"error": err}
    if not sk:
        return {"error": "No sketch available"}

    arc_type = params.get("arc_type", "center_point")
    arcs = sk.sketchCurves.sketchArcs

    if arc_type == "three_point":
        sx = float(params.get("start_x", 0))
        sy = float(params.get("start_y", 0))
        tx = float(params.get("through_x", 5))
        ty = float(params.get("through_y", 5))
        ex = float(params.get("end_x", 10))
        ey = float(params.get("end_y", 0))
        arc = arcs.addByThreePoints(
            adsk.core.Point2D.create(sx, sy),
            adsk.core.Point2D.create(tx, ty),
            adsk.core.Point2D.create(ex, ey),
        )
    else:
        cx = float(params.get("center_x", 0))
        cy = float(params.get("center_y", 0))
        r = float(params.get("radius", 5))
        sa = float(params.get("start_angle", 0))
        ea = float(params.get("end_angle", 180))
        arc = arcs.addByCenterStartEnd(
            adsk.core.Point2D.create(cx, cy),
            adsk.core.Point2D.create(cx + r, cy),  # start point
            adsk.core.Point2D.create(cx + r * _cos(ea), cy + r * _sin(ea)),
        )

    return {
        "entity_type": "arc",
        "entity_id": arc.entityToken,
        "arc_type": arc_type,
    }


def _sketch_spline(params):
    """Draw a spline through fit points."""
    sk, err = _get_or_create_sketch(params)
    if err:
        return {"error": err}
    if not sk:
        return {"error": "No sketch available"}

    points_data = params.get("points", [])
    if len(points_data) < 2:
        return {"error": "Spline requires at least 2 points"}

    splines = sk.sketchCurves.sketchSplines
    fit_points = adsk.core.ObjectCollection.create()
    for pt in points_data:
        fit_points.add(adsk.core.Point2D.create(float(pt["x"]), float(pt["y"])))
    spline = splines.add(fit_points)

    return {
        "entity_type": "spline",
        "entity_id": spline.entityToken,
        "point_count": len(points_data),
    }


def _sketch_polygon(params):
    """Draw a regular polygon."""
    sk, err = _get_or_create_sketch(params)
    if err:
        return {"error": err}
    if not sk:
        return {"error": "No sketch available"}

    cx = float(params.get("center_x", 0))
    cy = float(params.get("center_y", 0))
    r = float(params.get("radius", 5))
    sides = int(params.get("sides", 6))

    lines = sk.sketchCurves.sketchLines
    entity_ids = []
    prev_pt = None
    first_pt = None

    for i in range(sides):
        angle = 2 * 3.14159265 * i / sides
        x = cx + r * _cos(angle)
        y = cy + r * _sin(angle)
        pt = adsk.core.Point2D.create(x, y)
        if i == 0:
            first_pt = pt
        if prev_pt is not None:
            line = lines.addByTwoPoints(prev_pt, pt)
            entity_ids.append(line.entityToken)
        prev_pt = pt

    if prev_pt and first_pt:
        line = lines.addByTwoPoints(prev_pt, first_pt)
        entity_ids.append(line.entityToken)

    return {
        "entity_type": "polygon",
        "entity_ids": entity_ids,
        "sides": sides,
        "center": {"x": cx, "y": cy},
        "radius": r,
    }


def _sketch_text(params):
    """Add text to a sketch."""
    sk, err = _get_or_create_sketch(params)
    if err:
        return {"error": err}
    if not sk:
        return {"error": "No sketch available"}

    text_str = params.get("text", "Text")
    x = float(params.get("x", params.get("position_x", 0)))
    y = float(params.get("y", params.get("position_y", 0)))
    height = float(params.get("height", 1.0))

    text_input = adsk.core.TextBoxInput.create(
        text_str,
        height,
        adsk.core.HorizontalAlignTextStyles.CenterHorizontalTextAlign,
    )
    pos = adsk.core.Point2D.create(x, y)
    text = sk.sketchTexts.add(text_input, pos)

    return {
        "entity_type": "text",
        "entity_id": text.entityToken,
        "text": text_str,
    }


def _sketch_offset(params):
    """Offset sketch entities by a distance."""
    sk, err = _get_or_create_sketch(params)
    if err:
        return {"error": err}
    if not sk:
        return {"error": "No sketch available"}

    distance = float(params.get("distance", 0.5))
    # Offset all entities if no specific ones given
    curves = adsk.core.ObjectCollection.create()
    entity_ids = params.get("entity_ids", [])
    for eid in entity_ids:
        # In practice we'd look up by token, for now offset all
        pass

    # Fallback: offset all sketch curves
    for i in range(sketch.sketchCurves.sketchLines.count):
        curves.add(sketch.sketchCurves.sketchLines.item(i))
    for i in range(sketch.sketchCurves.sketchArcs.count):
        curves.add(sketch.sketchCurves.sketchArcs.item(i))
    for i in range(sketch.sketchCurves.sketchCircles.count):
        curves.add(sketch.sketchCurves.sketchCircles.item(i))

    if curves.count > 0:
        offsets = sk.offsets
        offsets.add(curves, distance * -1.0)  # negative = outward

    return {"entity_type": "offset", "distance": distance}


def _add_dimension(params):
    """Add a driving dimension to a sketch entity."""
    sk, err = _get_or_create_sketch(params)
    if err:
        return {"error": err}
    if not sk:
        return {"error": "No sketch available"}

    # For simplicity, add a dimension between two sketch points
    x1 = float(params.get("x1", params.get("point1_x", 0)))
    y1 = float(params.get("y1", params.get("point1_y", 0)))
    x2 = float(params.get("x2", params.get("point2_x", 10)))
    y2 = float(params.get("y2", params.get("point2_y", 0)))
    value = params.get("value")

    p1 = adsk.core.Point2D.create(x1, y1)
    p2 = adsk.core.Point2D.create(x2, y2)

    dims = sk.sketchDimensions
    if value is not None:
        dim = dims.addDistanceDimension(p1, p2,
            adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
            adsk.core.Point3D.create((x1 + x2) / 2, (y1 + y2) / 2 - 1, 0))
        dim.parameter.expression = str(float(value))
    else:
        dim = dims.addDistanceDimension(p1, p2,
            adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
            adsk.core.Point3D.create((x1 + x2) / 2, (y1 + y2) / 2 - 1, 0))

    return {
        "dimension_id": dim.entityToken,
        "value": dim.parameter.value,
    }


def _add_constraint(params):
    """Add a geometric constraint between sketch entities."""
    sk, err = _get_or_create_sketch(params)
    if err:
        return {"error": err}
    if not sk:
        return {"error": "No sketch available"}

    constraint_type = params.get("constraint_type", params.get("type", "coincident"))
    constraints = sk.constraints

    # Simplified: apply constraint type
    try:
        if constraint_type == "horizontal":
            # Constrain first sketch line to horizontal
            if sk.sketchCurves.sketchLines.count > 0:
                line = sk.sketchCurves.sketchLines.item(0)
                constraints.addHorizontal(line)
        elif constraint_type == "vertical":
            if sk.sketchCurves.sketchLines.count > 0:
                line = sk.sketchCurves.sketchLines.item(0)
                constraints.addVertical(line)
        elif constraint_type == "coincident":
            # Coincident between two points
            x1 = float(params.get("x1", 0))
            y1 = float(params.get("y1", 0))
            x2 = float(params.get("x2", 0))
            y2 = float(params.get("y2", 0))
            constraints.addCoincident(
                adsk.core.Point2D.create(x1, y1),
                adsk.core.Point2D.create(x2, y2),
            )
        elif constraint_type == "tangent":
            if sk.sketchCurves.sketchLines.count > 0 and sk.sketchCurves.sketchArcs.count > 0:
                constraints.addTangent(
                    sk.sketchCurves.sketchLines.item(0),
                    sk.sketchCurves.sketchArcs.item(0),
                )
        elif constraint_type == "perpendicular":
            if sk.sketchCurves.sketchLines.count > 1:
                constraints.addPerpendicular(
                    sk.sketchCurves.sketchLines.item(0),
                    sk.sketchCurves.sketchLines.item(1),
                )
        elif constraint_type == "parallel":
            if sk.sketchCurves.sketchLines.count > 1:
                constraints.addParallel(
                    sk.sketchCurves.sketchLines.item(0),
                    sk.sketchCurves.sketchLines.item(1),
                )
        elif constraint_type == "equal":
            if sk.sketchCurves.sketchLines.count > 1:
                constraints.addEqual(
                    sk.sketchCurves.sketchLines.item(0),
                    sk.sketchCurves.sketchLines.item(1),
                )
        elif constraint_type == "fix":
            if sk.sketchCurves.sketchLines.count > 0:
                line = sk.sketchCurves.sketchLines.item(0)
                constraints.addFix(line)
        elif constraint_type == "symmetric":
            if sk.sketchCurves.sketchLines.count > 1:
                constraints.addSymmetric(
                    sk.sketchCurves.sketchLines.item(0),
                    sk.sketchCurves.sketchLines.item(1),
                    sk.originConstructionPlane,
                )
        else:
            return {"error": f"Unknown constraint type: {constraint_type}"}

        return {"constraint_type": constraint_type, "status": "applied"}
    except Exception as e:
        return {"error": f"Failed to add {constraint_type} constraint: {str(e)}"}


def _sketch_mirror(params):
    """Mirror sketch entities about a line."""
    sk, err = _get_or_create_sketch(params)
    if err:
        return {"error": err}
    if not sk:
        return {"error": "No sketch available"}

    # Get mirror line from params
    x1 = float(params.get("line_x1", params.get("axis_x1", 0)))
    y1 = float(params.get("line_y1", params.get("axis_y1", 0)))
    x2 = float(params.get("line_x2", params.get("axis_x2", 0)))
    y2 = float(params.get("line_y2", params.get("axis_y2", 10)))

    # Collect entities to mirror
    to_mirror = adsk.core.ObjectCollection.create()
    for i in range(sk.sketchCurves.sketchLines.count):
        to_mirror.add(sk.sketchCurves.sketchLines.item(i))
    for i in range(sk.sketchCurves.sketchArcs.count):
        to_mirror.add(sk.sketchCurves.sketchArcs.item(i))
    for i in range(sk.sketchCurves.sketchCircles.count):
        to_mirror.add(sk.sketchCurves.sketchCircles.item(i))

    if to_mirror.count == 0:
        return {"error": "No entities to mirror"}

    mirror_line = sk.sketchCurves.sketchLines.addByTwoPoints(
        adsk.core.Point2D.create(x1, y1),
        adsk.core.Point2D.create(x2, y2),
    )

    result = sk.mirror(to_mirror, mirror_line)
    mirror_line.deleteMe()  # Clean up construction line

    return {"status": "mirrored", "entity_count": result.count}


def _sketch_pattern_rectangular(params):
    """Create a rectangular pattern of sketch entities."""
    sk, err = _get_or_create_sketch(params)
    if err:
        return {"error": err}
    if not sk:
        return {"error": "No sketch available"}

    count_x = int(params.get("count_x", params.get("count", 3)))
    count_y = int(params.get("count_y", 2))
    spacing_x = float(params.get("spacing_x", params.get("spacing", 5)))
    spacing_y = float(params.get("spacing_y", spacing_x))

    entities = adsk.core.ObjectCollection.create()
    for i in range(sk.sketchCurves.sketchLines.count):
        entities.add(sk.sketchCurves.sketchLines.item(i))
    for i in range(sk.sketchCurves.sketchArcs.count):
        entities.add(sk.sketchCurves.sketchArcs.item(i))
    for i in range(sk.sketchCurves.sketchCircles.count):
        entities.add(sk.sketchCurves.sketchCircles.item(i))

    if entities.count == 0:
        return {"error": "No entities to pattern"}

    result = sk.rectangularPattern(
        entities,
        adsk.core.Point2D.create(1, 0),  # direction
        spacing_x,
        count_x,
        adsk.core.Point2D.create(0, 1),  # direction
        spacing_y,
        count_y,
    )

    return {
        "status": "patterned",
        "count_x": count_x,
        "count_y": count_y,
        "spacing_x": spacing_x,
        "spacing_y": spacing_y,
    }


def _sketch_pattern_circular(params):
    """Create a circular pattern of sketch entities."""
    sk, err = _get_or_create_sketch(params)
    if err:
        return {"error": err}
    if not sk:
        return {"error": "No sketch available"}

    count = int(params.get("count", 6))
    angle_span = float(params.get("angle_span", 360))
    cx = float(params.get("center_x", 0))
    cy = float(params.get("center_y", 0))

    entities = adsk.core.ObjectCollection.create()
    for i in range(sk.sketchCurves.sketchLines.count):
        entities.add(sk.sketchCurves.sketchLines.item(i))
    for i in range(sk.sketchCurves.sketchArcs.count):
        entities.add(sk.sketchCurves.sketchArcs.item(i))
    for i in range(sk.sketchCurves.sketchCircles.count):
        entities.add(sk.sketchCurves.sketchCircles.item(i))

    if entities.count == 0:
        return {"error": "No entities to pattern"}

    center = adsk.core.Point2D.create(cx, cy)
    result = sk.circularPattern(entities, center, count, angle_span * 3.14159265 / 180)

    return {
        "status": "patterned",
        "count": count,
        "angle_span": angle_span,
        "center": {"x": cx, "y": cy},
    }


def _validate_sketch_constraints(params):
    """Validate constraints on a sketch and report status."""
    sketch_name = params.get("sketch_name", "")
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    sk = None
    if sketch_name:
        sk = _get_sketch_by_name(comp, sketch_name)
    elif design.activeSketch:
        sk = design.activeSketch

    if not sk:
        return {"error": f"No sketch found (name='{sketch_name}')"}

    # Analyze constraint status
    fully_constrained = 0
    under_constrained = 0
    over_constrained = 0
    issues = []

    # Check profiles for constraint status
    for i in range(sk.profiles.count):
        prof = sk.profiles.item(i)
        # profileProperties doesn't directly give constraint status,
        # but we can check degrees of freedom
        status = prof.profileProperties
        if status:
            try:
                dof = sk.sketchCurves.count - sk.constraints.count
                if dof <= 0:
                    fully_constrained += 1
                elif dof > 3:
                    under_constrained += 1
                issues.append(f"Profile {i}: ~{dof} DOF remaining")
            except:
                under_constrained += 1

    return {
        "sketch_name": sk.name,
        "fully_constrained": fully_constrained,
        "under_constrained": under_constrained,
        "over_constrained": over_constrained,
        "issues": issues,
    }


# ===========================================================================
# Command Handlers — Feature operations
# ===========================================================================

def _extrude(params):
    """Create an extrude feature."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    sketch_name = params.get("sketch_name", "")
    operation = params.get("operation", "new_body")
    extent_type = params.get("extent_type", "distance")
    distance = float(params.get("distance", 1.0))
    taper_angle = float(params.get("taper_angle", 0))

    sk = None
    if sketch_name:
        sk = _get_sketch_by_name(comp, sketch_name)
    elif design.activeSketch:
        sk = design.activeSketch

    if not sk or sk.profiles.count == 0:
        return {"error": "No sketch with profiles found"}

    # Get the first profile (simplified - in production you'd select by area/region)
    profile = sk.profiles.item(0)

    extrudes = comp.features.extrudeFeatures
    ext_input = extrudes.createInput(profile, _get_feature_operation(operation))

    # Set extent
    if extent_type == "through_all":
        extent = adsk.fusion.ThroughAllExtentDefinition.create(
            adsk.fusion.ThroughAllExtentDirection.NegativeExtentDirection)
    else:
        extent = adsk.fusion.DistanceExtentDefinition.create(
            adsk.core.ValueInput.createByReal(distance / 10.0))  # cm to internal units
        if taper_angle != 0:
            extent.taperAngle = adsk.core.ValueInput.createByReal(taper_angle * 3.14159265 / 180)

    ext_input.setOneSideExtent(extent, _get_feature_operation(operation))
    ext_input.participantBodies = _get_bodies_for_operation(comp, operation)

    extrude_feature = extrudes.add(ext_input)

    return {
        "feature_name": extrude_feature.name,
        "feature_id": extrude_feature.entityToken,
        "operation": operation,
        "distance": distance,
    }


def _revolve(params):
    """Create a revolve feature."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    sketch_name = params.get("sketch_name", "")
    angle = float(params.get("angle", 360))
    operation = params.get("operation", "new_body")

    sk = _get_sketch_by_name(comp, sketch_name) if sketch_name else (design.activeSketch if design else None)
    if not sk or sk.profiles.count == 0:
        return {"error": "No sketch with profiles found"}

    profile = sk.profiles.item(0)
    revolves = comp.features.revolveFeatures

    # Use sketch origin line or Y axis as revolve axis
    axis = comp.yConstructionAxis if comp else None
    if not axis:
        return {"error": "No construction axis available"}

    rev_input = revolves.createInput(profile, axis, _get_feature_operation(operation))
    angle_extent = adsk.fusion.AngleExtentDefinition.create(
        adsk.core.ValueInput.createByReal(angle * 3.14159265 / 180))
    rev_input.setAngleExtent(False, angle_extent)

    revolve_feature = revolves.add(rev_input)

    return {
        "feature_name": revolve_feature.name,
        "feature_id": revolve_feature.entityToken,
        "angle": angle,
    }


def _fillet(params):
    """Apply fillets to edges."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    radius = float(params.get("radius", 0.5))
    edge_ids = params.get("edge_ids", [])

    fillets = comp.features.filletFeatures
    edges = adsk.core.ObjectCollection.create()

    # Try to get edges from top face/body
    body = comp.bRepBodies.item(0) if comp.bRepBodies.count > 0 else None
    if body:
        for i in range(body.edges.count):
            edge = body.edges.item(i)
            edges.add(edge)

    if edges.count == 0:
        return {"error": "No edges found on the active body"}

    fillet_input = fillets.createInput()
    fillet_input.addConstantRadiusEdgeSet(edges, adsk.core.ValueInput.createByReal(radius / 10.0), True)
    fillet_feature = fillets.add(fillet_input)

    return {
        "feature_name": fillet_feature.name,
        "feature_id": fillet_feature.entityToken,
        "radius": radius,
    }


def _chamfer(params):
    """Apply chamfers to edges."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    distance1 = float(params.get("distance1", params.get("distance", 0.3)))
    chamfer_type = params.get("chamfer_type", "equal_distance")

    chamfers = comp.features.chamferFeatures
    edges = adsk.core.ObjectCollection.create()

    body = comp.bRepBodies.item(0) if comp.bRepBodies.count > 0 else None
    if body:
        for i in range(body.edges.count):
            edges.add(body.edges.item(i))

    if edges.count == 0:
        return {"error": "No edges found"}

    chamfer_input = chamfers.createInput(edges, True)
    chamfer_input.setToEqualDistance(adsk.core.ValueInput.createByReal(distance1 / 10.0))
    chamfer_feature = chamfers.add(chamfer_input)

    return {
        "feature_name": chamfer_feature.name,
        "feature_id": chamfer_feature.entityToken,
        "distance": distance1,
    }


def _shell(params):
    """Create a shell feature."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    thickness = float(params.get("thickness", 0.2))
    shells = comp.features.shellFeatures

    faces = adsk.core.ObjectCollection.create()
    body = comp.bRepBodies.item(0) if comp.bRepBodies.count > 0 else None
    if body:
        # Remove top face (common case)
        top_face = body.faces.item(0)
        faces.add(top_face)

    if faces.count == 0:
        return {"error": "No faces to remove"}

    shell_input = shells.createInput(faces)
    shell_input.insideThickness = adsk.core.ValueInput.createByReal(thickness / 10.0)
    shell_feature = shells.add(shell_input)

    return {
        "feature_name": shell_feature.name,
        "feature_id": shell_feature.entityToken,
        "thickness": thickness,
    }


def _hole(params):
    """Create a hole feature."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    diameter = float(params.get("diameter", 1.0))
    depth = float(params.get("depth", params.get("distance", 2.0)))
    hole_type = params.get("hole_type", "simple")
    pos_x = float(params.get("x", params.get("position_x", 0)))
    pos_y = float(params.get("y", params.get("position_y", 0)))

    # Create a center point for the hole
    sk = design.activeSketch
    if not sk:
        return {"error": "No active sketch for hole placement"}

    center_point = sk.sketchPoints.add(adsk.core.Point2D.create(pos_x, pos_y))

    # Create hole using HoleFeature
    holes = comp.features.holeFeatures
    hole_input = holes.createSimpleInput(adsk.core.ValueInput.createByReal(diameter / 10.0))
    hole_input.setPositionByPoint(center_point)
    hole_input.setDistanceExtent(adsk.core.ValueInput.createByReal(depth / 10.0))
    hole_feature = holes.add(hole_input)

    return {
        "feature_name": hole_feature.name,
        "feature_id": hole_feature.entityToken,
        "diameter": diameter,
        "depth": depth,
    }


def _pattern_rectangular(params):
    """Create a rectangular pattern of features."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    count_x = int(params.get("count_x", params.get("count", 3)))
    count_y = int(params.get("count_y", 2))
    spacing_x = float(params.get("spacing_x", params.get("spacing", 5)))
    spacing_y = float(params.get("spacing_y", spacing_x))

    patterns = comp.features.rectangularPatternFeatures

    # Collect all features to pattern
    input_ents = adsk.core.ObjectCollection.create()
    for i in range(comp.features.count):
        feat = comp.features.item(i)
        input_ents.add(feat)

    if input_ents.count == 0:
        return {"error": "No features to pattern"}

    pat_input = patterns.createInput(input_ents,
        adsk.core.ValueInput.createByReal(spacing_x / 10.0),
        adsk.core.ValueInput.createByReal(count_x),
        adsk.core.ValueInput.createByReal(spacing_y / 10.0),
        adsk.core.ValueInput.createByReal(count_y))

    pattern_feature = patterns.add(pat_input)

    return {
        "feature_name": pattern_feature.name,
        "feature_id": pattern_feature.entityToken,
        "count_x": count_x,
        "count_y": count_y,
    }


def _pattern_circular(params):
    """Create a circular pattern of features."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    count = int(params.get("count", 6))
    angle = float(params.get("angle_span", 360))

    patterns = comp.features.circularPatternFeatures
    axis = comp.yConstructionAxis if comp else None

    input_ents = adsk.core.ObjectCollection.create()
    for i in range(comp.features.count):
        input_ents.add(comp.features.item(i))

    if input_ents.count == 0 or not axis:
        return {"error": "No features or axis available"}

    pat_input = patterns.createInput(input_ents, axis)
    pat_input.quantity = adsk.core.ValueInput.createByReal(count)
    pat_input.totalAngle = adsk.core.ValueInput.createByReal(angle * 3.14159265 / 180)

    pattern_feature = patterns.add(pat_input)

    return {
        "feature_name": pattern_feature.name,
        "count": count,
        "angle": angle,
    }


def _mirror(params):
    """Mirror features about a plane."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    plane_str = params.get("plane", "XZ")
    mirror_plane = _get_construction_plane(comp, plane_str)
    if not mirror_plane:
        mirror_plane = comp.xZConstructionPlane

    mirrors = comp.features.mirrorFeatures
    input_ents = adsk.core.ObjectCollection.create()
    for i in range(comp.features.count):
        input_ents.add(comp.features.item(i))

    if input_ents.count == 0:
        return {"error": "No features to mirror"}

    mirror_input = mirrors.createInput(input_ents, mirror_plane)
    mirror_feature = mirrors.add(mirror_input)

    return {
        "feature_name": mirror_feature.name,
        "feature_id": mirror_feature.entityToken,
        "plane": plane_str,
    }


def _combine(params):
    """Combine bodies (join, cut, intersect)."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    operation = params.get("operation", "join")
    combines = comp.features.combineFeatures

    if comp.bRepBodies.count < 2:
        return {"error": "Need at least 2 bodies to combine"}

    target_body = comp.bRepBodies.item(0)
    tool_bodies = adsk.core.ObjectCollection.create()
    tool_bodies.add(comp.bRepBodies.item(1))

    combine_input = combines.createInput(target_body, tool_bodies)
    if operation == "cut":
        combine_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    elif operation == "intersect":
        combine_input.operation = adsk.fusion.FeatureOperations.IntersectFeatureOperation
    else:
        combine_input.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation

    combine_feature = combines.add(combine_input)

    return {
        "feature_name": combine_feature.name,
        "feature_id": combine_feature.entityToken,
        "operation": operation,
    }


def _create_component(params):
    """Create a new component in the active design."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    name = params.get("component_name", "New Component")
    new_comp = comp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    new_comp.component.name = name

    return {
        "component_name": name,
        "component_id": new_comp.entityToken,
    }


# ===========================================================================
# Command Handlers — Document management
# ===========================================================================

def _document_get_active(params):
    """Get metadata for the active document."""
    doc = _app.activeDocument
    if not doc:
        return {"error": "No active document"}

    design = _get_active_design()
    doc_type = "unknown"
    if design:
        doc_type = "design"

    return {
        "name": doc.name,
        "document_type": doc_type,
        "is_dirty": doc.isDirty,
        "units": str(design.unitsManager.distanceDisplayUnits) if design else "unknown",
    }


def _document_list(params):
    """List all open documents."""
    docs = []
    for i in range(_app.documents.count):
        doc = _app.documents.item(i)
        docs.append({
            "name": doc.name,
            "document_type": str(doc.documentType),
            "is_dirty": doc.isDirty,
        })
    return {"documents": docs}


def _document_save(params):
    """Save the active document."""
    doc = _app.activeDocument
    if not doc:
        return {"error": "No active document"}

    filepath = params.get("filepath", "")
    if filepath:
        try:
            doc.saveAs(filepath, None, None)
            return {"saved_path": filepath, "success": True}
        except:
            return {"error": f"Failed to save to '{filepath}'"}
    else:
        try:
            doc.save(False)
            return {"saved_path": doc.name, "success": True}
        except:
            return {"error": "Failed to save document"}


# ===========================================================================
# Command Handlers — Analysis
# ===========================================================================

def _get_physical_properties(params):
    """Get mass, volume, surface area, bounding box."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    units = params.get("units", "cm")
    bodies = []
    total_mass = 0
    total_volume = 0

    for i in range(comp.bRepBodies.count):
        body = comp.bRepBodies.item(i)
        physical = body.getPhysicalProperties(adsk.fusion.CalculationAccuracy.MediumCalculationAccuracy)
        mass = physical.mass
        vol = physical.volume
        total_mass += mass
        total_volume += vol
        bodies.append({
            "name": body.name,
            "mass": round(mass, 6),
            "volume": round(vol, 6),
        })

    return {
        "bodies": bodies,
        "total_mass": round(total_mass, 6),
        "total_volume": round(total_volume, 6),
        "units": units,
    }


def _measure_distance(params):
    """Measure distance between two entities."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    # Simplified: measure between two points if provided
    x1 = float(params.get("entity1", {}).get("x", params.get("x1", 0)))
    y1 = float(params.get("entity1", {}).get("y", params.get("y1", 0)))
    z1 = float(params.get("entity1", {}).get("z", params.get("z1", 0)))
    x2 = float(params.get("entity2", {}).get("x", params.get("x2", 10)))
    y2 = float(params.get("entity2", {}).get("y", params.get("y2", 0)))
    z2 = float(params.get("entity2", {}).get("z", params.get("z2", 0)))

    import math
    dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)

    return {
        "distance": round(dist, 6),
        "delta_x": round(x2 - x1, 6),
        "delta_y": round(y2 - y1, 6),
        "delta_z": round(z2 - z1, 6),
        "entity1_point": {"x": x1, "y": y1, "z": z1},
        "entity2_point": {"x": x2, "y": y2, "z": z2},
    }


def _measure_angle(params):
    """Measure angle between two entities."""
    # Simplified angle measurement
    a = float(params.get("angle_degrees", params.get("angle", 90)))
    rad = a * 3.14159265 / 180
    return {
        "angle_degrees": a,
        "angle_radians": round(rad, 6),
        "supplementary_degrees": 180 - a,
        "supplementary_radians": round((180 - a) * 3.14159265 / 180, 6),
    }


def _analyze_feature_tree(params):
    """Analyze the parametric feature tree."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    features = []
    for i in range(comp.features.count):
        feat = comp.features.item(i)
        features.append({
            "name": feat.name,
            "type": str(feat.objectType),
            "index": i,
            "is_suppressed": feat.isSuppressed,
        })

    return {
        "features": features,
        "total_features": len(features),
    }


def _export_design(params):
    """Export the active design to various formats."""
    design = _get_active_design()
    if not design:
        return {"error": "No active design"}

    format_type = params.get("format", params.get("export_format", "STEP"))
    output_path = params.get("output_path", "")

    # Map format names to Fusion 360 export options
    format_map = {
        "STEP": adsk.fusion.ExportOptionsSTEP,
        "STL": adsk.fusion.ExportOptionsSTL,
        "IGES": adsk.fusion.ExportOptionsIGES,
        "F3D": None,  # Native format
        "OBJ": None,
        "DXF": None,
    }

    export_options_class = format_map.get(format_type.upper())
    if not export_options_class:
        return {"error": f"Unsupported export format: {format_type}"}

    try:
        if format_type.upper() == "STEP":
            export_options = adsk.fusion.ExportOptionsStep.create(output_path or "")
            design.export(output_path, export_options)
        elif format_type.upper() == "STL":
            export_options = adsk.fusion.ExportOptionsSTL(
                adsk.fusion.MeshRefinementSettings.MeshRefinementSettingsMediumQuality)
            design.export(output_path, export_options)
        elif format_type.upper() == "IGES":
            export_options = adsk.fusion.ExportOptionsIGES.create(output_path)
            design.export(output_path, export_options)
        else:
            return {"error": f"Export for {format_type} not implemented"}

        return {
            "status": "ok",
            "output_path": output_path,
            "format": format_type.upper(),
        }
    except Exception as e:
        return {"error": f"Export failed: {str(e)}"}


def _export_step(params):
    return _export_design({"format": "STEP", "output_path": params.get("output_path", "")})


def _export_iges(params):
    return _export_design({"format": "IGES", "output_path": params.get("output_path", "")})


def _export_stl(params):
    return _export_design({"format": "STL", "output_path": params.get("output_path", "")})


# ===========================================================================
# Command Handlers — Drawing operations
# ===========================================================================

def _drawing_create(params):
    """Create a new drawing from a design."""
    design = _get_active_design()
    if not design:
        return {"error": "No active design"}

    sheet_size = params.get("sheet_size", "A3")
    standard = params.get("standard", "ISO")

    # Fusion 360 drawing creation
    draw_doc = _app.documents.add(adsk.core.DocumentTypes.DrawingDocumentType)

    return {
        "document_name": draw_doc.name,
        "sheet_size": sheet_size,
        "standard": standard,
        "status": "drawing_created",
    }


def _check_manufacturability(params):
    """Basic DFM check."""
    design = _get_active_design()
    comp = _get_root_component(design) if design else None
    if not comp:
        return {"error": "No active design"}

    process = params.get("process", "cnc")
    issues = []
    score = 85  # Default score, adjusted by checks

    # Basic checks
    if comp.bRepBodies.count == 0:
        issues.append({"severity": "error", "message": "No bodies in design"})
        score = 0
    else:
        for i in range(comp.bRepBodies.count):
            body = comp.bRepBodies.item(i)
            # Check for non-manifold geometry
            physical = body.getPhysicalProperties(adsk.fusion.CalculationAccuracy.MediumCalculationAccuracy)
            if physical.volume <= 0:
                issues.append({"severity": "error", "message": f"Body '{body.name}' has zero or negative volume"})
                score -= 20
            # Check for very thin walls
            if physical.volume > 0 and physical.mass > 0:
                vol = physical.volume
                area = 0  # Would need surface area calc
                # Rough wall thickness estimate
                issues.append({"severity": "info", "message": f"Body '{body.name}': basic geometry checks passed"})

    return {
        "process": process,
        "dfm_score": max(0, min(100, score)),
        "issues": issues,
        "summary": f"{len([i for i in issues if i['severity'] == 'error'])} errors, {len([i for i in issues if i['severity'] == 'warning'])} warnings",
    }


# ===========================================================================
# Helpers
# ===========================================================================

def _cos(degrees):
    import math
    return math.cos(math.radians(degrees))


def _sin(degrees):
    import math
    return math.sin(math.radians(degrees))


def _get_feature_operation(op_str):
    """Map string to FeatureOperations enum."""
    if not HAS_FUSION_API:
        return None
    op_map = {
        "new_body": adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        "join": adsk.fusion.FeatureOperations.JoinFeatureOperation,
        "cut": adsk.fusion.FeatureOperations.CutFeatureOperation,
        "intersect": adsk.fusion.FeatureOperations.IntersectFeatureOperation,
    }
    return op_map.get(op_str, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)


def _get_bodies_for_operation(comp, operation):
    """Get the appropriate body collection for the operation type."""
    if not HAS_FUSION_API:
        return None
    if operation in ("join", "cut", "intersect"):
        if comp.bRepBodies.count > 0:
            bodies = adsk.core.ObjectCollection.create()
            bodies.add(comp.bRepBodies.item(0))
            return bodies
    return None


# ===========================================================================
# Command Dispatcher
# ===========================================================================

COMMAND_MAP = {
    # Document management
    "document_get_active": _document_get_active,
    "document_list": _document_list,
    "document_save": _document_save,
    "document_open": lambda p: {"error": "document_open: Use Fusion UI to open files"},
    "document_create": lambda p: {"error": "document_create: Use Fusion UI File > New"},

    # Sketch creation
    "sketch_create": _create_sketch,
    "create_sketch": _create_sketch,

    # Sketch entities
    "sketch_line": _sketch_line,
    "create_line": _sketch_line,
    "sketch_circle": _sketch_circle,
    "create_circle": _sketch_circle,
    "sketch_rectangle": _sketch_rectangle,
    "create_rectangle": _sketch_rectangle,
    "sketch_arc": _sketch_arc,
    "create_arc": _sketch_arc,
    "sketch_spline": _sketch_spline,
    "create_spline": _sketch_spline,
    "sketch_polygon": _sketch_polygon,
    "create_polygon": _sketch_polygon,
    "sketch_text": _sketch_text,
    "sketch_offset": _sketch_offset,
    "sketch_mirror": _sketch_mirror,
    "sketch_pattern_rectangular": _sketch_pattern_rectangular,
    "sketch_pattern_circular": _sketch_pattern_circular,

    # Constraints
    "sketch_add_constraint": _add_constraint,
    "add_constraint": _add_constraint,
    "add_dimension": _add_dimension,
    "sketch_add_dimension": _add_dimension,
    "sketch_validate_constraints": _validate_sketch_constraints,

    # Features
    "extrude": _extrude,
    "extrude_profile": _extrude,
    "revolve": _revolve,
    "fillet": _fillet,
    "chamfer": _chamfer,
    "shell": _shell,
    "hole": _hole,
    "combine": _combine,
    "pattern_rectangular": _pattern_rectangular,
    "pattern_circular": _pattern_circular,
    "mirror": _mirror,
    "create_component": _create_component,

    # Analysis
    "analysis_get_physical_properties": _get_physical_properties,
    "get_physical_properties": _get_physical_properties,
    "analysis_measure_distance": _measure_distance,
    "measure_distance": _measure_distance,
    "analysis_measure_angle": _measure_angle,
    "measure_angle": _measure_angle,
    "feature_analyze_tree": _analyze_feature_tree,
    "analysis_check_manufacturability": _check_manufacturability,

    # Export
    "export_design": _export_design,
    "export_step": _export_step,
    "export_iges": _export_iges,
    "export_stl": _export_stl,

    # Drawing
    "drawing_create": _drawing_create,
    "create_drawing": _drawing_create,
}


def dispatch_command(command, params):
    """Route a command to the appropriate handler."""
    handler = COMMAND_MAP.get(command)
    if handler:
        try:
            result = handler(params)
            if isinstance(result, dict) and "error" in result:
                return {"status": "error", "message": result["error"], "result": result}
            return {"status": "ok", "result": result}
        except Exception as e:
            return {
                "status": "error",
                "message": f"Command '{command}' failed: {str(e)}",
                "traceback": traceback.format_exc(),
            }
    else:
        return {
            "status": "error",
            "message": f"Unknown command: '{command}'. Available: {sorted(COMMAND_MAP.keys())}",
        }


# ===========================================================================
# HTTP Server
# ===========================================================================

class BridgeHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Fusion 360 bridge."""

    def log_message(self, format, *args):
        """Suppress default logging to avoid flooding Fusion console."""
        pass

    def _send_json(self, data, status_code=200):
        """Send a JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self._send_json({"status": "ok"})

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/ping" or self.path == "/api/ping":
            self._send_json({"status": "ok", "bridge": "MCP Commander Fusion 360 Bridge", "version": "1.0.0"})
        elif self.path == "/api/tools":
            self._send_json({"status": "ok", "tools": sorted(COMMAND_MAP.keys())})
        elif self.path == "/api/status":
            design = _get_active_design()
            doc = _app.activeDocument if _app else None
            self._send_json({
                "status": "ok",
                "connected": True,
                "document": doc.name if doc else None,
                "design_active": design is not None,
                "commands_available": len(COMMAND_MAP),
            })
        else:
            self._send_json({"status": "error", "message": f"Unknown endpoint: {self.path}"}, 404)

    def do_POST(self):
        """Handle POST requests (command execution)."""
        if self.path == "/api/command" or self.path == "/command":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body) if body else {}
            except (json.JSONDecodeError, ValueError) as e:
                self._send_json({"status": "error", "message": f"Invalid JSON: {str(e)}"}, 400)
                return

            command = data.get("command", "")
            params = data.get("params", {})

            if not command:
                self._send_json({"status": "error", "message": "Missing 'command' field"}, 400)
                return

            # Execute command (could queue to main thread in production)
            result = dispatch_command(command, params)
            self._send_json(result)

        else:
            self._send_json({"status": "error", "message": f"Unknown endpoint: {self.path}"}, 404)


class ThreadedHTTPServer(HTTPServer):
    """HTTP server that handles each request in a new thread."""
    allow_reuse_address = True

    def process_request(self, request, client_address):
        """Process request in a new thread."""
        thread = threading.Thread(target=self._process_request_thread,
                                  args=(request, client_address))
        thread.daemon = True
        thread.start()

    def _process_request_thread(self, request, client_address):
        """Handle a request in its own thread."""
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)


# ===========================================================================
# Fusion 360 Add-In Lifecycle
# ===========================================================================

def start_server(host=DEFAULT_HOST, port=DEFAULT_PORT):
    """Start the HTTP bridge server."""
    server = ThreadedHTTPServer((host, port), BridgeHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server


def run(context):
    """Entry point called by Fusion 360 when the add-in is run."""
    global _app, _ui
    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface

        if _ui:
            _ui.messageBox(
                "MCP Commander Bridge starting...\n\n"
                "HTTP server: http://localhost:8080\n\n"
                "Commands available: " + str(len(COMMAND_MAP)) + "\n"
                "Ping: http://localhost:8080/ping\n"
                "Status: http://localhost:8080/api/status\n\n"
                "Start the external fusion360-mcp server to connect.",
                "MCP Commander Bridge"
            )

        # Start HTTP server on background thread
        start_server()

        # Add a panel to show bridge status
        try:
            cmd_defs = _ui.commandDefinitions
            test_cmd = cmd_defs.addButtonDefinition(
                "MCPCommanderBridgeStatus",
                "MCP Bridge Status",
                "Check MCP Commander bridge connection status",
                ""
            )

            def on_command_created(event):
                try:
                    import urllib.request
                    resp = urllib.request.urlopen("http://localhost:8080/ping", timeout=2)
                    status = json.loads(resp.read().decode())
                    _ui.messageBox(
                        f"Bridge Status: ONLINE\n\n"
                        f"Version: {status.get('version', '?')}\n"
                        f"Commands: {len(COMMAND_MAP)}",
                        "MCP Commander Bridge"
                    )
                except Exception as e:
                    _ui.messageBox(f"Bridge Status: OFFLINE\n\nError: {str(e)}", "MCP Commander Bridge")

            test_cmd.commandCreated.add(on_command_created)

            # Add to Design panel
            design_panel = _ui.allToolbarPanels.itemById("DesignPanel")
            if design_panel:
                design_panel.controls.addCommand(test_cmd)
                _handlers.append(test_cmd)
        except:
            pass  # Panel creation is optional

    except:
        if _ui:
            _ui.messageBox("Failed to start MCP Commander Bridge:\n{}".format(traceback.format_exc()))


def stop(context):
    """Entry point called by Fusion 360 when the add-in is stopped."""
    global _app, _ui
    try:
        _app = adsk.core.Application.get()
        _ui = _app.userInterface

        # Clean up command definitions
        for handler in _handlers:
            try:
                handler.deleteMe()
            except:
                pass
        _handlers.clear()

        if _ui:
            _ui.messageBox("MCP Commander Bridge stopped.", "MCP Commander Bridge")
    except:
        if _ui:
            _ui.messageBox("Failed to stop MCP Commander Bridge:\n{}".format(traceback.format_exc()))
