"""Pydantic data models for file translation requests and responses.

These models provide type-safe parameter descriptors for MCP tool signatures
and serialization helpers for structured JSON responses.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ======================================================================
# Enumerations
# ======================================================================


class CADFormat(str, Enum):
    """Supported CAD file formats for conversion."""

    STL = "stl"
    STEP = "step"
    IGES = "iges"
    OBJ = "obj"
    PLY = "ply"
    THREE_MF = "3mf"
    DXF = "dxf"


class ConversionMethod(str, Enum):
    """Methods for mesh-to-B-rep conversion."""

    AUTO = "auto"
    TRIMESH_BASIC = "trimesh_basic"
    CADQUERY_MESH_TO_SOLID = "cadquery_mesh_to_solid"
    CONVEX_HULL = "convex_hull"
    VOXELIZED = "voxelized"


class STLEncoding(str, Enum):
    """STL file encoding types."""

    BINARY = "binary"
    ASCII = "ascii"
    UNKNOWN = "unknown"


class MeshQuality(str, Enum):
    """Quality assessment for mesh-to-B-rep conversion results."""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    FAILED = "failed"


# ======================================================================
# Request / Option models
# ======================================================================


class ConversionOptions(BaseModel):
    """Options for controlling conversion behavior."""

    method: ConversionMethod = Field(
        default=ConversionMethod.AUTO,
        description="Conversion method for mesh-to-B-rep conversions",
    )
    tolerance: float = Field(
        default=0.01,
        gt=0.0,
        description="Tolerance for B-rep reconstruction in model units",
    )
    linear_tolerance: float = Field(
        default=0.01,
        gt=0.0,
        description="Linear tolerance for B-rep to mesh tessellation",
    )
    angular_tolerance: float = Field(
        default=0.5,
        gt=0.0,
        description="Angular tolerance for B-rep to mesh tessellation in degrees",
    )
    simplify: bool = Field(
        default=True,
        description="Whether to simplify the mesh before conversion",
    )
    target_faces: int = Field(
        default=50000,
        gt=10,
        description="Target face count for mesh simplification",
    )
    watertight_method: str = Field(
        default="auto",
        description="Method for making mesh watertight: auto, fill, crumble, wrap",
    )


# ======================================================================
# Response models
# ======================================================================


class BoundingBox(BaseModel):
    """3D axis-aligned bounding box."""

    min_x: float = Field(description="Minimum X coordinate")
    min_y: float = Field(description="Minimum Y coordinate")
    min_z: float = Field(description="Minimum Z coordinate")
    max_x: float = Field(description="Maximum X coordinate")
    max_y: float = Field(description="Maximum Y coordinate")
    max_z: float = Field(description="Maximum Z coordinate")


class MeshAnalysis(BaseModel):
    """Analysis results for a 3D mesh."""

    triangle_count: int = Field(description="Number of triangles in the mesh")
    vertex_count: int = Field(description="Number of unique vertices")
    bounding_box: BoundingBox = Field(description="Axis-aligned bounding box")
    volume: float = Field(default=0.0, description="Enclosed volume in model units cubed")
    surface_area: float = Field(default=0.0, description="Total surface area in model units squared")
    watertight: bool = Field(description="Whether the mesh is watertight (closed)")
    euler_number: int = Field(default=0, description="Euler characteristic of the mesh")
    is_manifold: bool = Field(default=True, description="Whether the mesh is manifold")
    convex: bool = Field(default=False, description="Whether the mesh is convex")


class FormatDetection(BaseModel):
    """File format detection result."""

    format: str = Field(description="Detected file format (e.g. stl, step, iges)")
    confidence: str = Field(description="Detection confidence: high, medium, low")
    encoding: STLEncoding = Field(
        default=STLEncoding.UNKNOWN,
        description="Encoding type (binary/ascii) for formats that support both",
    )
    details: str = Field(default="", description="Additional detection details")


class FileInfo(BaseModel):
    """Detailed file information."""

    path: str = Field(description="File path")
    size_bytes: int = Field(description="File size in bytes")
    size_human: str = Field(description="Human-readable file size")
    format: str = Field(description="Detected file format")
    encoding: STLEncoding = Field(
        default=STLEncoding.UNKNOWN,
        description="File encoding (binary/ascii)",
    )
    triangle_count: int = Field(default=0, description="Triangle count if mesh file")


class ConversionResult(BaseModel):
    """Result of a file format conversion."""

    success: bool = Field(description="Whether the conversion succeeded")
    input_path: str = Field(description="Input file path")
    output_path: str = Field(description="Output file path")
    input_format: str = Field(description="Detected input format")
    output_format: str = Field(description="Output format")
    method_used: str = Field(default="", description="Conversion method that succeeded")
    quality: MeshQuality = Field(
        default=MeshQuality.FAILED,
        description="Quality assessment of the conversion result",
    )
    input_triangles: int = Field(default=0, description="Triangle count in input")
    output_triangles: int = Field(default=0, description="Triangle count in output (mesh formats)")
    output_size_bytes: int = Field(default=0, description="Output file size in bytes")
    message: str = Field(default="", description="Status message or warning")
    error: str = Field(default="", description="Error message if conversion failed")


class BatchConversionResult(BaseModel):
    """Result of a batch conversion operation."""

    total_files: int = Field(description="Total number of files to convert")
    succeeded: int = Field(description="Number of successful conversions")
    failed: int = Field(description="Number of failed conversions")
    results: list[ConversionResult] = Field(
        default_factory=list,
        description="Individual conversion results",
    )


class RepairResult(BaseModel):
    """Result of a mesh repair operation."""

    success: bool = Field(description="Whether the repair succeeded")
    input_path: str = Field(description="Input file path")
    output_path: str = Field(description="Output file path")
    original_triangles: int = Field(description="Triangle count before repair")
    repaired_triangles: int = Field(description="Triangle count after repair")
    watertight_before: bool = Field(description="Watertight status before repair")
    watertight_after: bool = Field(description="Watertight status after repair")
    operations_performed: list[str] = Field(
        default_factory=list,
        description="List of repair operations performed",
    )
    message: str = Field(default="", description="Status message or details")
    error: str = Field(default="", description="Error message if repair failed")
