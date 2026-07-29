"""
Pydantic models and enums for Solidworks data types.
"""
from enum import Enum
from pydantic import BaseModel, Field


class SketchPlane(str, Enum):
    TOP = "top"
    FRONT = "front"
    RIGHT = "right"
    CUSTOM = "custom"


class EndCondition(str, Enum):
    BLIND = "blind"
    THROUGH_ALL = "through_all"
    MID_PLANE = "mid_plane"
    UP_TO_SURFACE = "up_to_surface"
    UP_TO_VERTEX = "up_to_vertex"
    UP_TO_BODY = "up_to_body"
    OFFSET_FROM_SURFACE = "offset_from_surface"


class Direction(str, Enum):
    NORMAL = "normal"
    REVERSED = "reversed"
    MID_PLANE = "mid_plane"
    TWO_SIDED = "two_sided"


class ViewType(str, Enum):
    FRONT = "front_view"
    TOP = "top_view"
    RIGHT = "right_view"
    LEFT = "left_view"
    BOTTOM = "bottom_view"
    BACK = "back_view"
    ISOMETRIC = "isometric"
    TRIMETRIC = "trimetric"
    DIMETRIC = "dimetric"


class Point2D(BaseModel):
    x: float = Field(description="X coordinate")
    y: float = Field(description="Y coordinate")


class Point3D(BaseModel):
    x: float = Field(description="X coordinate")
    y: float = Field(description="Y coordinate")
    z: float = Field(description="Z coordinate")


class Vector3D(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class SketchLine(BaseModel):
    start: Point2D
    end: Point2D


class SketchArc(BaseModel):
    center: Point2D
    start_point: Point2D
    end_point: Point2D


class SketchCircle(BaseModel):
    center: Point2D
    radius: float = Field(gt=0)


class SketchRectangle(BaseModel):
    corner1: Point2D
    corner2: Point2D


class SketchSpline(BaseModel):
    points: list[Point2D] = Field(min_length=2)


class ExtrudeParams(BaseModel):
    depth: float = Field(default=10.0, ge=0)
    end_condition: EndCondition = EndCondition.BLIND
    direction: Direction = Direction.NORMAL
    draft_angle: float = 0.0
    merge_result: bool = True


class RevolveParams(BaseModel):
    angle: float = Field(default=360.0, ge=0, le=360)
    direction: Direction = Direction.NORMAL
    merge_result: bool = True


class FilletParams(BaseModel):
    radius: float = Field(default=1.0, gt=0)
    variable_radius: bool = False
    radius_values: list[dict] = Field(default_factory=list)


class ChamferParams(BaseModel):
    distance: float = Field(default=1.0, gt=0)
    angle: float = Field(default=45.0, gt=0, le=90)
    chamfer_type: str = Field(default="angle_distance", description="angle_distance, distance_distance, or vertex_chamfer")
    distance2: float = Field(default=1.0, gt=0)


class DrawingViewParams(BaseModel):
    view_type: ViewType = ViewType.FRONT
    scale: float = 1.0
    position_x: float = 0.0
    position_y: float = 0.0


class DimensionParams(BaseModel):
    value: float
    tolerance_plus: float = 0.0
    tolerance_minus: float = 0.0
    precision: int = Field(default=2, ge=0, le=8)


class SheetMetalParams(BaseModel):
    thickness: float = Field(default=1.0, gt=0)
    bend_radius: float = Field(default=1.0, ge=0)
    k_factor: float = Field(default=0.5, ge=0, le=1)
    relief_type: str = "rectangular"
