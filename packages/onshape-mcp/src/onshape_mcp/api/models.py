"""Pydantic data models for Onshape entities and API parameters.

These models serve dual purposes:
1. Type-safe parameter descriptors for MCP tool signatures.
2. Serialization helpers for constructing REST API JSON payloads.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ======================================================================
# Resource identification
# ======================================================================


class OnshapeResourceId(BaseModel):
    """Identifies a resource in Onshape by its hierarchical IDs.

    All fields are optional so the model can represent partial references
    (e.g., document-only, or document+workspace+element).
    """

    document_id: str | None = Field(default=None, description="Onshape document ID")
    workspace_id: str | None = Field(default=None, description="Workspace ID within a document")
    element_id: str | None = Field(default=None, description="Element ID (Part Studio, Assembly, Drawing, etc.)")
    part_id: str | None = Field(default=None, description="Part ID within a Part Studio")


# ======================================================================
# Geometry primitives — Sketch entities
# ======================================================================


class SketchPoint(BaseModel):
    """A 2D point in sketch space (meters)."""

    x: float = Field(description="X coordinate in meters")
    y: float = Field(description="Y coordinate in meters")


class SketchLine(BaseModel):
    """A line segment between two sketch points."""

    start: SketchPoint = Field(description="Line start point")
    end: SketchPoint = Field(description="Line end point")
    is_construction: bool = Field(default=False, description="Whether this is a construction line")


class SketchArc(BaseModel):
    """An arc defined by center, angles, and radius."""

    center: SketchPoint = Field(description="Arc center point")
    start_angle: float = Field(description="Start angle in degrees")
    end_angle: float = Field(description="End angle in degrees")
    radius: float = Field(description="Arc radius in meters")


class SketchCircle(BaseModel):
    """A circle defined by center and radius."""

    center: SketchPoint = Field(description="Circle center point")
    radius: float = Field(description="Circle radius in meters")


class SketchEllipse(BaseModel):
    """An ellipse defined by center and two radii."""

    center: SketchPoint = Field(description="Ellipse center point")
    major_radius: float = Field(description="Major radius (X) in meters")
    minor_radius: float = Field(description="Minor radius (Y) in meters")


class SketchRectangle(BaseModel):
    """An axis-aligned rectangle defined by corner and dimensions."""

    x: float = Field(description="Bottom-left X coordinate in meters")
    y: float = Field(description="Bottom-left Y coordinate in meters")
    width: float = Field(description="Rectangle width in meters")
    height: float = Field(description="Rectangle height in meters")


class SketchSpline(BaseModel):
    """A spline curve through a series of control points."""

    points: list[SketchPoint] = Field(description="Ordered list of spline control points")


# ======================================================================
# Constraint types
# ======================================================================


class ConstraintType(str, Enum):
    """Types of sketch constraints."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    COINCIDENT = "coincident"
    COLLINEAR = "collinear"
    TANGENT = "tangent"
    PERPENDICULAR = "perpendicular"
    PARALLEL = "parallel"
    EQUAL = "equal"
    SYMMETRIC = "symmetric"
    MIDPOINT = "midpoint"
    FIXED = "fixed"
    concentric = "concentric"


# ======================================================================
# Feature parameter models
# ======================================================================


class FeatureParams(BaseModel):
    """Base model for feature parameters."""

    feature_type: str = Field(description="Feature type identifier")


class ExtrudeParams(FeatureParams):
    """Parameters for an extrude feature."""

    feature_type: str = "extrude"
    operation: Literal["new", "add", "remove", "intersect"] = Field(
        default="new", description="Boolean operation type"
    )
    distance: float = Field(default=0.01, description="Extrude distance in meters")
    direction: str = Field(default="normal", description="Extrude direction: 'normal' or 'reverse'")
    symmetric: bool = Field(default=False, description="Extrude symmetrically in both directions")


class RevolveParams(FeatureParams):
    """Parameters for a revolve feature."""

    feature_type: str = "revolve"
    axis: str = Field(default="Y", description="Revolution axis: 'X', 'Y', 'Z', or custom axis ID")
    angle: float = Field(default=360.0, description="Revolution angle in degrees")


class FilletParams(FeatureParams):
    """Parameters for a fillet feature."""

    feature_type: str = "fillet"
    radius: float = Field(default=0.005, description="Fillet radius in meters")
    edges: str = Field(default="all", description="Edge IDs or 'all' for all edges")


class ChamferParams(FeatureParams):
    """Parameters for a chamfer feature."""

    feature_type: str = "chamfer"
    distance: float = Field(default=0.005, description="Chamfer distance in meters")
    edges: str = Field(default="all", description="Edge IDs or 'all' for all edges")


class ShellParams(FeatureParams):
    """Parameters for a shell feature."""

    feature_type: str = "shell"
    thickness: float = Field(default=0.002, description="Shell wall thickness in meters")
    faces: str = Field(default="", description="Face IDs to remove (comma-separated)")


class PatternParams(FeatureParams):
    """Parameters for a pattern feature."""

    feature_type: str = "pattern"
    count: int = Field(default=2, description="Number of pattern instances")
    spacing: float = Field(default=0.05, description="Pattern spacing in meters")
    direction: str = Field(default="X", description="Pattern direction")


# ======================================================================
# Error model
# ======================================================================


class OnshapeError(BaseModel):
    """Structured error response from the Onshape API."""

    status: int = Field(description="HTTP status code")
    error_code: str = Field(default="", description="Onshape-specific error code")
    message: str = Field(description="Human-readable error message")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional error details")
