"""Pydantic data models for Fusion 360 entities and API parameters.

These models serve dual purposes:
1. Type-safe parameter descriptors for MCP tool signatures.
2. Serialization helpers for constructing REST API JSON payloads.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Union

from pydantic import BaseModel, Field


# ======================================================================
# Geometry primitives
# ======================================================================


class Point2D(BaseModel):
    """A 2D point in sketch space."""

    x: float = Field(description="X coordinate in cm")
    y: float = Field(description="Y coordinate in cm")


class Point3D(BaseModel):
    """A 3D point in model space."""

    x: float = Field(description="X coordinate in cm")
    y: float = Field(description="Y coordinate in cm")
    z: float = Field(description="Z coordinate in cm")


class Vector3D(BaseModel):
    """A 3D direction vector."""

    x: float = Field(description="X component", default=0.0)
    y: float = Field(description="Y component", default=0.0)
    z: float = Field(description="Z component", default=1.0)


# ======================================================================
# Enumerations
# ======================================================================


class SketchPlane(str, Enum):
    """Standard construction planes available for sketch creation."""

    XY = "XY"
    XZ = "XZ"
    YZ = "YZ"
    CUSTOM = "custom"


class ExtrudeOperation(str, Enum):
    """Types of extrude feature operations."""

    NEW_BODY = "new_body"
    JOIN = "join"
    CUT = "cut"
    INTERSECT = "intersect"


class BooleanOperation(str, Enum):
    """Boolean combine operations."""

    JOIN = "join"
    CUT = "cut"
    INTERSECT = "intersect"


class ExtrudeExtentType(str, Enum):
    """Ways to define an extrude's distance."""

    DISTANCE = "distance"
    THROUGH_ALL = "through_all"
    TO_OBJECT = "to_object"
    SYMMETRIC = "symmetric"


class ViewOrientation(str, Enum):
    """Standard orthographic view orientations for drawings."""

    FRONT = "front"
    BACK = "back"
    TOP = "top"
    BOTTOM = "bottom"
    RIGHT = "right"
    LEFT = "left"
    ISOMETRIC_RIGHT = "isometric_right"
    ISOMETRIC_LEFT = "isometric_left"
    ISOMETRIC_TOP = "isometric_top"
    ISOMETRIC_BOTTOM = "isometric_bottom"


class ToleranceType(str, Enum):
    """Dimension tolerance class."""

    BILATERAL = "bilateral"
    UNILATERAL = "unilateral"
    LIMITS = "limits"
    FIT = "fit"


class HoleType(str, Enum):
    """Hole feature types."""

    SIMPLE = "simple"
    COUNTERBORE = "counterbore"
    COUNTERSINK = "countersink"


class DimensionDisplayType(str, Enum):
    """Drawing dimension display styles."""

    DECIMAL = "decimal"
    FRACTIONAL = "fractional"
    DEGREES_MIN_SEC = "degrees_min_sec"


class GeometricToleranceType(str, Enum):
    """GD&T geometric tolerance symbols."""

    POSITION = "position"
    PERPENDICULARITY = "perpendicularity"
    PARALLELISM = "parallelism"
    ANGULARITY = "angularity"
    CONCENTRICITY = "concentricity"
    CYLINDRICITY = "cylindricity"
    CIRCULARITY = "circularity"
    FLATNESS = "flatness"
    STRAIGHTNESS = "straightness"
    SYMMETRY = "symmetry"
    PROFILE_OF_A_LINE = "profile_of_a_line"
    PROFILE_OF_A_SURFACE = "profile_of_a_surface"
    RUNOUT_CIRCULAR = "runout_circular"
    RUNOUT_TOTAL = "runout_total"


class SheetSize(str, Enum):
    """Drawing sheet sizes."""

    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class ChamferType(str, Enum):
    """Chamfer definition types."""

    EQUAL_DISTANCE = "equal_distance"
    TWO_DISTANCES = "two_distances"
    DISTANCE_ANGLE = "distance_angle"


class SplineFitType(str, Enum):
    """Spline fit methods."""

    CONTROL_POINTS = "control_points"
    FIT_POINTS = "fit_points"


class ArcType(str, Enum):
    """Arc construction methods."""

    CENTER_POINT = "center_point"
    THREE_POINT = "three_point"


class RectangleType(str, Enum):
    """Rectangle construction methods."""

    TWO_POINT = "two_point"
    THREE_POINT = "three_point"


class SlotType(str, Enum):
    """Slot construction methods."""

    CENTER_TO_CENTER = "center_to_center"
    OVERALL = "overall"


class PatternComputeType(str, Enum):
    """Pattern computation methods."""

    OPTIMIZED = "optimized"
    IDENTICAL = "identical"
    ADJUSTABLE = "adjustable"


# ======================================================================
# Sketch entities
# ======================================================================


class SketchEntity(BaseModel):
    """Base model for all sketch geometry entities."""

    entity_type: str = Field(description="Discriminator: line, circle, arc, rectangle, ellipse, spline, polygon, slot")
    sketch_name: str = Field(default="", description="Name of the containing sketch")
    is_construction: bool = Field(default=False, description="Whether this is a construction (reference) entity")
    color: str | None = Field(default=None, description="Optional hex color override, e.g. '#FF0000'")


class SketchLine(SketchEntity):
    """Line segment between two points."""

    entity_type: Literal["line"] = "line"
    start: Point2D = Field(description="Start point")
    end: Point2D = Field(description="End point")


class SketchCircle(SketchEntity):
    """Circle defined by center and radius."""

    entity_type: Literal["circle"] = "circle"
    center: Point2D = Field(description="Center point")
    radius: float = Field(gt=0, description="Radius in cm")


class SketchArc(SketchEntity):
    """Arc defined by center, radius, and sweep angles."""

    entity_type: Literal["arc"] = "arc"
    arc_type: ArcType = Field(default=ArcType.CENTER_POINT, description="Arc construction method")
    center: Point2D | None = Field(default=None, description="Center point (for center-point arc)")
    radius: float | None = Field(default=None, gt=0, description="Radius in cm")
    start_angle: float | None = Field(default=None, description="Start angle in degrees")
    end_angle: float | None = Field(default=None, description="End angle in degrees")
    start_point: Point2D | None = Field(default=None, description="Start point (for 3-point arc)")
    through_point: Point2D | None = Field(default=None, description="Intermediate point (for 3-point arc)")
    end_point: Point2D | None = Field(default=None, description="End point (for 3-point arc)")


class SketchRectangle(SketchEntity):
    """Rectangle defined by corner points."""

    entity_type: Literal["rectangle"] = "rectangle"
    rect_type: RectangleType = Field(default=RectangleType.TWO_POINT, description="Rectangle construction method")
    corner1: Point2D = Field(description="First corner")
    corner2: Point2D = Field(description="Diagonally opposite corner")
    corner3: Point2D | None = Field(default=None, description="Third corner for 3-point rectangle")
    corner4: Point2D | None = Field(default=None, description="Fourth corner (computed) for 3-point rectangle")


class SketchEllipse(SketchEntity):
    """Ellipse defined by center, major/minor radii, and rotation."""

    entity_type: Literal["ellipse"] = "ellipse"
    center: Point2D = Field(description="Center point")
    major_radius: float = Field(gt=0, description="Major semi-axis in cm")
    minor_radius: float = Field(gt=0, description="Minor semi-axis in cm")
    rotation: float = Field(default=0.0, description="Rotation angle in degrees from X axis")


class SketchSpline(SketchEntity):
    """Spline curve through a series of points."""

    entity_type: Literal["spline"] = "spline"
    fit_type: SplineFitType = Field(default=SplineFitType.FIT_POINTS, description="Spline fit method")
    points: list[Point2D] = Field(min_length=2, description="Ordered list of defining points")


# ======================================================================
# Profiles and components
# ======================================================================


class Profile(BaseModel):
    """A closed region in a sketch that can be used for feature creation."""

    sketch_name: str = Field(description="Name of the containing sketch")
    profile_id: str | None = Field(default=None, description="API profile identifier")


class Component(BaseModel):
    """A component (body or sub-assembly occurrence) in the design."""

    name: str = Field(description="Component name")
    component_id: str | None = Field(default=None, description="API component identifier")
    is_active: bool = Field(default=False, description="Whether this is the active component")
    parent_component: str | None = Field(default=None, description="Parent component name")


class Occurrence(BaseModel):
    """An occurrence of a component in the assembly tree."""

    occurrence_name: str = Field(description="Full occurrence path, e.g. 'ComponentA:1'")
    component_name: str = Field(description="Referenced component name")
    transform: dict[str, Any] | None = Field(default=None, description="3x4 affine transform matrix")


# ======================================================================
# Feature parameter models
# ======================================================================


class ExtrudeParams(BaseModel):
    """Parameters for creating an extrude feature."""

    profile: Profile | None = Field(default=None, description="Profile to extrude")
    operation: ExtrudeOperation = Field(default=ExtrudeOperation.NEW_BODY, description="Boolean operation type")
    extent_type: ExtrudeExtentType = Field(default=ExtrudeExtentType.DISTANCE, description="How the depth is specified")
    distance: float = Field(default=1.0, gt=0, description="Extrude distance in cm (for distance extent)")
    direction: Vector3D | None = Field(default=None, description="Custom direction vector")
    symmetric: bool = Field(default=False, description="Extrude symmetrically in both directions")
    taper_angle: float = Field(default=0.0, description="Taper/draft angle in degrees")
    to_object_id: str | None = Field(default=None, description="Target entity ID for ToObject extent")


class RevolveParams(BaseModel):
    """Parameters for creating a revolve feature."""

    profile: Profile | None = Field(default=None, description="Profile to revolve")
    axis: Vector3D = Field(description="Axis direction vector")
    axis_origin: Point3D | None = Field(default=None, description="Point on the revolution axis")
    angle: float = Field(default=360.0, description="Revolution angle in degrees")
    operation: ExtrudeOperation = Field(default=ExtrudeOperation.NEW_BODY, description="Boolean operation")


class FilletParams(BaseModel):
    """Parameters for creating a constant-radius fillet."""

    radius: float = Field(gt=0, description="Fillet radius in cm")
    edge_ids: list[str] = Field(min_length=1, description="IDs of edges to fillet")


class ChamferParams(BaseModel):
    """Parameters for creating a chamfer."""

    chamfer_type: ChamferType = Field(default=ChamferType.EQUAL_DISTANCE, description="Chamfer definition type")
    edge_ids: list[str] = Field(min_length=1, description="IDs of edges to chamfer")
    distance1: float = Field(gt=0, description="First chamfer distance in cm")
    distance2: float | None = Field(default=None, gt=0, description="Second distance for two-distance chamfer")
    angle: float | None = Field(default=None, ge=0, le=90, description="Angle for distance-angle chamfer")


class ShellParams(BaseModel):
    """Parameters for creating a shell feature."""

    thickness: float = Field(gt=0, description="Wall thickness in cm")
    remove_faces: list[str] = Field(default_factory=list, description="Face IDs to remove")


# ======================================================================
# Drawing parameter models
# ======================================================================


class DrawingSheetParams(BaseModel):
    """Parameters for creating or modifying a drawing sheet."""

    sheet_size: SheetSize = Field(default=SheetSize.A3, description="Sheet size")
    sheet_name: str = Field(default="Sheet1", description="Sheet name")


class DrawingViewParams(BaseModel):
    """Parameters for adding a drawing view."""

    sheet_name: str = Field(default="Sheet1", description="Target sheet name")
    orientation: ViewOrientation = Field(default=ViewOrientation.FRONT, description="View direction")
    scale: float = Field(default=1.0, gt=0, description="View scale")
    position: Point2D = Field(default_factory=lambda: Point2D(x=10.0, y=15.0), description="View placement position")
    style: str = Field(default="hidden", description="Line style: visible, hidden, shaded")


# ======================================================================
# Sheet metal parameter models
# ======================================================================


class SheetMetalFlangeParams(BaseModel):
    """Parameters for creating an edge flange."""

    edge_id: str = Field(description="Edge to attach the flange")
    height: float = Field(gt=0, description="Flange height in cm")
    angle: float = Field(default=90.0, description="Bend angle in degrees")
    bend_radius: float | None = Field(default=None, gt=0, description="Override bend radius in cm")
    offset: float = Field(default=0.0, description="Flange offset from edge in cm")
    position: Literal["inner", "outer", "bend_center"] = Field(default="bend_center", description="Flange position relative to edge")


class SheetMetalBendParams(BaseModel):
    """Parameters for creating a bend between two faces."""

    face1_id: str = Field(description="First face")
    face2_id: str = Field(description="Second face")
    bend_radius: float = Field(gt=0, description="Inner bend radius in cm")
    bend_angle: float = Field(default=90.0, description="Bend angle in degrees")


class BendAllowanceParams(BaseModel):
    """Parameters for configuring bend allowance."""

    allowance_type: Literal["k_factor", "bend_table", "bend_allowance"] = Field(
        default="k_factor",
        description="Bend allowance calculation method",
    )
    k_factor: float | None = Field(default=0.44, ge=0, le=1, description="K-factor value (0–1)")
    bend_table_path: str | None = Field(default=None, description="Path to custom bend table CSV")
    bend_allowance_value: float | None = Field(default=None, gt=0, description="Direct bend allowance value in cm")
