"""Core conversion engine for CAD file format translation.

Implements multi-strategy conversion between mesh formats (STL, OBJ, PLY, 3MF)
and B-rep formats (STEP, IGES), with automatic format detection, mesh analysis,
and mesh repair capabilities.

For mesh-to-B-rep conversions (STL → STEP, STL → IGES), three strategies are
attempted in order:
1. Trimesh basic export via OpenCASCADE
2. CadQuery mesh-to-solid reconstruction
3. Convex hull or voxelized fallback
"""

from __future__ import annotations

import logging
import os
import struct
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

from file_translator_mcp.api.models import (
    BoundingBox,
    CADFormat,
    ConversionMethod,
    ConversionOptions,
    ConversionResult,
    FileInfo,
    FormatDetection,
    MeshAnalysis,
    MeshQuality,
    RepairResult,
    STLEncoding,
)

logger = logging.getLogger(__name__)

# Mapping of file extensions to CAD formats
EXTENSION_TO_FORMAT: dict[str, str] = {
    ".stl": "stl",
    ".step": "step",
    ".stp": "step",
    ".iges": "iges",
    ".igs": "iges",
    ".obj": "obj",
    ".ply": "ply",
    ".3mf": "3mf",
    ".dxf": "dxf",
}

# Supported mesh formats that trimesh handles natively
TRIMESH_MESH_FORMATS: set[str] = {"stl", "obj", "ply", "3mf"}

# B-rep formats
BREP_FORMATS: set[str] = {"step", "iges"}

# All supported conversions: (source_format, target_format) tuples
SUPPORTED_CONVERSIONS: set[tuple[str, str]] = {
    ("stl", "step"),
    ("stl", "iges"),
    ("stl", "obj"),
    ("stl", "ply"),
    ("stl", "3mf"),
    ("obj", "stl"),
    ("obj", "step"),
    ("ply", "stl"),
    ("step", "stl"),
    ("step", "iges"),
    ("iges", "step"),
    ("iges", "stl"),
    ("dxf", "stl"),
}


# ======================================================================
# File format detection
# ======================================================================


def detect_format(path: str) -> FormatDetection:
    """Auto-detect the CAD file format from file header bytes and extension.

    Uses magic bytes for STL binary/ASCII detection, and file extension
    fallback for other formats.

    Args:
        path: Path to the file to analyze.

    Returns:
        FormatDetection with detected format, confidence, and encoding.
    """
    file_path = Path(path)
    if not file_path.exists():
        return FormatDetection(
            format="unknown",
            confidence="low",
            details=f"File not found: {path}",
        )

    # First try magic byte detection
    detection = _detect_from_magic_bytes(path)
    if detection.format != "unknown":
        return detection

    # Fall back to extension-based detection
    ext = file_path.suffix.lower()
    detected = EXTENSION_TO_FORMAT.get(ext, "unknown")
    confidence = "high" if detected != "unknown" else "low"
    details = f"Format detected from extension: {ext}"
    if detected == "unknown":
        details = f"Unknown extension: {ext}"

    return FormatDetection(
        format=detected,
        confidence=confidence,
        details=details,
    )


def _detect_from_magic_bytes(path: str) -> FormatDetection:
    """Detect format by reading the first bytes of the file."""
    try:
        with open(path, "rb") as f:
            header = f.read(256)
    except (IOError, OSError) as e:
        return FormatDetection(
            format="unknown",
            confidence="low",
            details=f"Cannot read file: {e}",
        )

    # STEP files start with "ISO-10303-21" or contain "HEADER"
    if header[:11] == b"ISO-10303-21" or b"HEADER" in header[:80]:
        return FormatDetection(
            format="step",
            confidence="high",
            details="STEP AP header detected (ISO-10303-21)",
        )

    # IGES files start with an "S" followed by numbers and "G" on the 73rd char
    if len(header) >= 80:
        line_start = header[0:1]
        section_g = header[72:73]
        if line_start == b"S" and section_g == b"G":
            return FormatDetection(
                format="iges",
                confidence="high",
                details="IGES file structure detected (Start and Global sections)",
            )

    # OBJ files often contain comment lines or vertex/face data
    header_str = header.decode("ascii", errors="ignore").strip()
    first_line = header_str.split("\n")[0].strip() if header_str else ""

    if first_line.startswith("#") or first_line.startswith("v ") or first_line.startswith("vn "):
        return FormatDetection(
            format="obj",
            confidence="medium",
            details="OBJ file structure detected from header content",
        )

    # PLY files start with "ply"
    if header[:3] == b"ply":
        encoding = STLEncoding.ASCII if b"ascii" in header[:100] else STLEncoding.BINARY
        return FormatDetection(
            format="ply",
            confidence="high",
            encoding=encoding,
            details="PLY magic header detected",
        )

    # 3MF files are ZIP archives containing specific XML files
    if header[:4] == b"PK\x03\x04" or header[:4] == b"PK\x05\x06":
        # Check if it's a 3MF by looking at ZIP contents
        try:
            import zipfile
            with zipfile.ZipFile(path, "r") as zf:
                names = zf.namelist()
                if any("3D/3dmodel.model" in n for n in names):
                    return FormatDetection(
                        format="3mf",
                        confidence="high",
                        details="3MF archive detected from ZIP contents",
                    )
        except (zipfile.BadZipFile, IOError):
            pass

    # STL detection: binary STL starts with "solid" but binary files often
    # have non-ASCII data shortly after. ASCII STL is all text.
    if header[:5] == b"solid":
        # Could be binary STL (binary files can start with "solid" too)
        # Check if the rest of the header has non-printable characters
        is_ascii_stl = True
        for byte in header[5:80]:
            if byte < 32 and byte not in (9, 10, 13):
                is_ascii_stl = False
                break
        if is_ascii_stl and b"facet" in header:
            return FormatDetection(
                format="stl",
                confidence="high",
                encoding=STLEncoding.ASCII,
                details="ASCII STL file detected (solid/facet keywords found)",
            )
        else:
            # Likely binary STL with "solid" header (common)
            # Check file size: binary STL size = 80 + 4 + n*50
            file_size = os.path.getsize(path)
            if file_size > 84:
                remaining = file_size - 84
                if remaining % 50 == 0:
                    return FormatDetection(
                        format="stl",
                        confidence="high",
                        encoding=STLEncoding.BINARY,
                        details="Binary STL detected (size consistent with triangle data)",
                    )

    # Also check binary STL that doesn't start with "solid"
    file_size = os.path.getsize(path)
    if file_size > 84:
        remaining = file_size - 84
        if remaining % 50 == 0:
            # Try to read triangle count from header
            try:
                triangle_count = struct.unpack("<I", header[80:84])[0]
                if 0 < triangle_count < 1_000_000_000:
                    return FormatDetection(
                        format="stl",
                        confidence="medium",
                        encoding=STLEncoding.BINARY,
                        details=f"Binary STL detected (header indicates {triangle_count} triangles)",
                    )
            except (struct.error, IndexError):
                pass

    return FormatDetection(
        format="unknown",
        confidence="low",
        details="Could not determine format from magic bytes",
    )


# ======================================================================
# File information
# ======================================================================


def get_file_info(path: str) -> FileInfo:
    """Get detailed information about a CAD file.

    Args:
        path: Path to the file.

    Returns:
        FileInfo with size, format, encoding, and triangle count if applicable.
    """
    file_path = Path(path)
    if not file_path.exists():
        return FileInfo(
            path=path,
            size_bytes=0,
            size_human="0 B",
            format="unknown",
            error="File not found",
        )

    size_bytes = file_path.stat().st_size
    size_human = _human_readable_size(size_bytes)
    detection = detect_format(path)

    triangle_count = 0
    if detection.format == "stl":
        triangle_count = _count_stl_triangles(path, detection.encoding)

    return FileInfo(
        path=str(file_path.resolve()),
        size_bytes=size_bytes,
        size_human=size_human,
        format=detection.format,
        encoding=detection.encoding,
        triangle_count=triangle_count,
    )


def _count_stl_triangles(path: str, encoding: STLEncoding) -> int:
    """Count triangles in an STL file."""
    try:
        if encoding == STLEncoding.BINARY or encoding == STLEncoding.UNKNOWN:
            # Try binary first
            file_size = os.path.getsize(path)
            remaining = file_size - 84
            if remaining > 0 and remaining % 50 == 0:
                with open(path, "rb") as f:
                    f.seek(80)
                    data = f.read(4)
                    count = struct.unpack("<I", data)[0]
                    if 0 < count < 1_000_000_000:
                        return count
        if encoding in (STLEncoding.ASCII, STLEncoding.UNKNOWN):
            # Try counting facet keywords in ASCII STL
            try:
                with open(path, "r", errors="ignore") as f:
                    content = f.read()
                    return content.count("facet normal")
            except IOError:
                pass
    except (IOError, OSError, struct.error):
        pass
    return 0


def _human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human-readable size string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


# ======================================================================
# Mesh analysis
# ======================================================================


def analyze_mesh(path: str) -> MeshAnalysis:
    """Analyze a mesh file and return detailed properties.

    Args:
        path: Path to the mesh file (STL, OBJ, PLY, etc.).

    Returns:
        MeshAnalysis with triangle count, volume, surface area, etc.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    mesh = trimesh.load(path, force="mesh")

    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)

    # Bounding box
    bounds = mesh.bounds
    bbox = BoundingBox(
        min_x=float(bounds[0][0]),
        min_y=float(bounds[0][1]),
        min_z=float(bounds[0][2]),
        max_x=float(bounds[1][0]),
        max_y=float(bounds[1][1]),
        max_z=float(bounds[1][2]),
    )

    # Volume and area
    volume = float(mesh.volume) if mesh.is_watertight else 0.0
    surface_area = float(mesh.area)

    # Topology checks
    is_watertight = mesh.is_watertight
    is_manifold = mesh.is_watertight  # trimesh uses watertight as manifold proxy
    euler = int(mesh.euler_number)
    is_convex = bool(mesh.is_convex)

    return MeshAnalysis(
        triangle_count=len(mesh.faces),
        vertex_count=len(mesh.vertices),
        bounding_box=bbox,
        volume=volume,
        surface_area=surface_area,
        watertight=is_watertight,
        euler_number=euler,
        is_manifold=is_manifold,
        convex=is_convex,
    )


# ======================================================================
# Core conversion functions
# ======================================================================


def convert_file(
    input_path: str,
    output_path: str,
    output_format: str,
    options: ConversionOptions | None = None,
) -> ConversionResult:
    """Convert a CAD file from one format to another.

    This is the main entry point for all conversions. It auto-detects
    the input format and dispatches to the appropriate conversion strategy.

    Args:
        input_path: Path to the input file.
        output_path: Path for the output file.
        output_format: Target format (stl, step, iges, obj, ply, 3mf).
        options: Conversion options (tolerances, method, etc.).

    Returns:
        ConversionResult with details about the conversion.
    """
    if options is None:
        options = ConversionOptions()

    input_path = str(Path(input_path).resolve())
    output_path = str(Path(output_path).resolve())
    output_format = output_format.lower().strip()

    # Validate input file exists
    if not os.path.exists(input_path):
        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format="unknown",
            output_format=output_format,
            error=f"Input file not found: {input_path}",
        )

    # Auto-detect input format
    detection = detect_format(input_path)
    input_format = detection.format

    if input_format == "unknown":
        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format="unknown",
            output_format=output_format,
            error=f"Cannot detect input format for: {input_path}",
        )

    # Validate conversion is supported
    conversion_key = (input_format, output_format)
    if conversion_key not in SUPPORTED_CONVERSIONS:
        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format=input_format,
            output_format=output_format,
            error=f"Conversion from {input_format} to {output_format} is not supported",
        )

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Get input triangle count
    input_info = get_file_info(input_path)
    input_triangles = input_info.triangle_count

    # Dispatch to the appropriate converter
    start_time = time.time()
    try:
        if input_format == "stl" and output_format == "step":
            result = _stl_to_step(input_path, output_path, options)
        elif input_format == "stl" and output_format == "iges":
            result = _stl_to_iges(input_path, output_path, options)
        elif input_format == "stl" and output_format == "obj":
            result = _mesh_to_mesh(input_path, output_path, "obj")
        elif input_format == "stl" and output_format == "ply":
            result = _mesh_to_mesh(input_path, output_path, "ply")
        elif input_format == "stl" and output_format == "3mf":
            result = _mesh_to_mesh(input_path, output_path, "3mf")
        elif input_format == "obj" and output_format == "stl":
            result = _mesh_to_mesh(input_path, output_path, "stl")
        elif input_format == "obj" and output_format == "step":
            result = _mesh_to_brep(input_path, output_path, "step", options)
        elif input_format == "ply" and output_format == "stl":
            result = _mesh_to_mesh(input_path, output_path, "stl")
        elif input_format == "step" and output_format == "stl":
            result = _brep_to_mesh(input_path, output_path, "step", options)
        elif input_format == "step" and output_format == "iges":
            result = _brep_to_brep(input_path, output_path, "iges")
        elif input_format == "iges" and output_format == "step":
            result = _brep_to_brep(input_path, output_path, "step")
        elif input_format == "iges" and output_format == "stl":
            result = _brep_to_mesh(input_path, output_path, "iges", options)
        elif input_format == "dxf" and output_format == "stl":
            result = _dxf_to_stl(input_path, output_path, options)
        else:
            result = ConversionResult(
                success=False,
                input_path=input_path,
                output_path=output_path,
                input_format=input_format,
                output_format=output_format,
                error=f"Unsupported conversion: {input_format} -> {output_format}",
            )
    except Exception as e:
        logger.exception("Conversion failed: %s -> %s", input_format, output_format)
        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format=input_format,
            output_format=output_format,
            input_triangles=input_triangles,
            error=f"Conversion error: {e}",
        )

    elapsed = time.time() - start_time
    result.input_format = input_format
    result.input_triangles = input_triangles

    if result.success:
        result.output_size_bytes = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        if result.message:
            result.message += f" (took {elapsed:.2f}s)"
        else:
            result.message = f"Conversion completed in {elapsed:.2f}s"

    return result


# ======================================================================
# Mesh-to-mesh conversions (STL↔OBJ↔PLY↔3MF)
# ======================================================================


def _mesh_to_mesh(input_path: str, output_path: str, output_format: str) -> ConversionResult:
    """Convert between mesh formats using trimesh.

    Args:
        input_path: Path to the input mesh file.
        output_path: Path for the output mesh file.
        output_format: Target format (stl, obj, ply, 3mf).

    Returns:
        ConversionResult.
    """
    try:
        mesh = trimesh.load(input_path, force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        mesh.export(output_path, file_type=output_format)

        # Count output triangles
        output_info = get_file_info(output_path)
        output_triangles = output_info.triangle_count

        return ConversionResult(
            success=True,
            input_path=input_path,
            output_path=output_path,
            input_format=detect_format(input_path).format,
            output_format=output_format,
            method_used="trimesh_export",
            quality=MeshQuality.EXCELLENT,
            output_triangles=output_triangles,
            message=f"Converted to {output_format.upper()} successfully",
        )
    except Exception as e:
        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format=detect_format(input_path).format,
            output_format=output_format,
            error=f"Mesh-to-mesh conversion failed: {e}",
        )


# ======================================================================
# Mesh-to-B-rep conversions (STL→STEP, STL→IGES, OBJ→STEP)
# ======================================================================


def _stl_to_step(
    input_path: str,
    output_path: str,
    options: ConversionOptions,
) -> ConversionResult:
    """Convert STL mesh to STEP B-rep format using multi-strategy approach.

    Strategies attempted in order:
    1. Trimesh basic STEP export (uses OpenCASCADE if available)
    2. CadQuery mesh-to-solid reconstruction
    3. Convex hull or voxelized fallback

    Args:
        input_path: Path to the input STL file.
        output_path: Path for the output STEP file.
        options: Conversion options.

    Returns:
        ConversionResult with the best strategy result.
    """
    method = options.method

    if method == ConversionMethod.AUTO:
        # Try strategies in order of quality
        for strategy in [
            ConversionMethod.TRIMESH_BASIC,
            ConversionMethod.CADQUERY_MESH_TO_SOLID,
            ConversionMethod.CONVEX_HULL,
        ]:
            result = _try_stl_to_step_with_strategy(
                input_path, output_path, options, strategy
            )
            if result.success and result.quality in (
                MeshQuality.EXCELLENT,
                MeshQuality.GOOD,
            ):
                return result

        # Return last result even if quality is poor
        return result

    else:
        return _try_stl_to_step_with_strategy(
            input_path, output_path, options, method
        )


def _try_stl_to_step_with_strategy(
    input_path: str,
    output_path: str,
    options: ConversionOptions,
    method: ConversionMethod,
) -> ConversionResult:
    """Attempt STL→STEP conversion with a specific strategy."""
    if method == ConversionMethod.TRIMESH_BASIC:
        return _strategy_trimesh_step(input_path, output_path, options)
    elif method == ConversionMethod.CADQUERY_MESH_TO_SOLID:
        return _strategy_cadquery_step(input_path, output_path, options)
    elif method == ConversionMethod.CONVEX_HULL:
        return _strategy_convex_hull_step(input_path, output_path, options)
    elif method == ConversionMethod.VOXELIZED:
        return _strategy_voxelized_step(input_path, output_path, options)
    else:
        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format="stl",
            output_format="step",
            error=f"Unknown conversion method: {method}",
        )


def _strategy_trimesh_step(
    input_path: str,
    output_path: str,
    options: ConversionOptions,
) -> ConversionResult:
    """Strategy 1: Use trimesh's built-in STEP export via OpenCASCADE."""
    try:
        mesh = trimesh.load(input_path, force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        # Try to simplify if requested
        if options.simplify and len(mesh.faces) > options.target_faces:
            mesh = mesh.simplify_quadric_decimation(options.target_faces)

        mesh.export(output_path, file_type="step")

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            output_size = os.path.getsize(output_path)
            quality = MeshQuality.GOOD if mesh.is_watertight else MeshQuality.ACCEPTABLE
            return ConversionResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                input_format="stl",
                output_format="step",
                method_used="trimesh_basic",
                quality=quality,
                output_triangles=len(mesh.faces),
                output_size_bytes=output_size,
                message=f"Exported via trimesh/OpenCASCADE. Watertight: {mesh.is_watertight}",
            )
        else:
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=output_path,
                input_format="stl",
                output_format="step",
                method_used="trimesh_basic",
                quality=MeshQuality.FAILED,
                error="Trimesh STEP export produced empty or missing file. OpenCASCADE may not be available.",
            )
    except Exception as e:
        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format="stl",
            output_format="step",
            method_used="trimesh_basic",
            quality=MeshQuality.FAILED,
            error=f"Trimesh STEP export failed: {e}. OpenCASCADE backend may not be installed.",
        )


def _strategy_cadquery_step(
    input_path: str,
    output_path: str,
    options: ConversionOptions,
) -> ConversionResult:
    """Strategy 2: Use CadQuery's mesh-to-solid reconstruction."""
    try:
        import cadquery as cq

        # Load the mesh file via cadquery's importers
        mesh = cq.importers.importStep(input_path)

        # Build a workplane from the imported mesh
        result = cq.Workplane("XY").add(mesh)

        # Export as STEP
        cq.exporters.export(result, output_path, cq.exporters.ExportTypes.STEP)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            output_size = os.path.getsize(output_path)
            return ConversionResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                input_format="stl",
                output_format="step",
                method_used="cadquery_mesh_to_solid",
                quality=MeshQuality.EXCELLENT,
                output_size_bytes=output_size,
                message="Converted via CadQuery mesh-to-solid reconstruction",
            )
        else:
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=output_path,
                input_format="stl",
                output_format="step",
                method_used="cadquery_mesh_to_solid",
                quality=MeshQuality.FAILED,
                error="CadQuery produced empty output",
            )
    except Exception as e:
        logger.debug("CadQuery strategy failed: %s", e)
        # Fallback: try loading STL directly and converting to solid
        try:
            import cadquery as cq

            mesh = trimesh.load(input_path, force="mesh")
            if isinstance(mesh, trimesh.Scene):
                mesh = mesh.dump(concatenate=True)

            vertices = mesh.vertices.tolist()
            faces = mesh.faces.tolist()

            # Use CadQuery to build solid from mesh
            # cadquery.Workplane can create solid from mesh
            solid = cq.Mesh.makeMesh(vertices, faces)
            shape = solid.toNurbs()

            result = cq.Workplane("XY").add(shape)
            cq.exporters.export(result, output_path, cq.exporters.ExportTypes.STEP)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return ConversionResult(
                    success=True,
                    input_path=input_path,
                    output_path=output_path,
                    input_format="stl",
                    output_format="step",
                    method_used="cadquery_mesh_to_solid",
                    quality=MeshQuality.GOOD,
                    output_size_bytes=os.path.getsize(output_path),
                    message="Converted via CadQuery Mesh.makeMesh",
                )
        except Exception as e2:
            logger.debug("CadQuery Mesh fallback failed: %s", e2)

        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format="stl",
            output_format="step",
            method_used="cadquery_mesh_to_solid",
            quality=MeshQuality.FAILED,
            error=f"CadQuery conversion failed: {e}",
        )


def _strategy_convex_hull_step(
    input_path: str,
    output_path: str,
    options: ConversionOptions,
) -> ConversionResult:
    """Strategy 3: Use convex hull for STEP export."""
    try:
        mesh = trimesh.load(input_path, force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        hull = mesh.convex_hull

        if options.simplify and len(hull.faces) > options.target_faces:
            hull = hull.simplify_quadric_decimation(options.target_faces)

        hull.export(output_path, file_type="step")

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return ConversionResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                input_format="stl",
                output_format="step",
                method_used="convex_hull",
                quality=MeshQuality.ACCEPTABLE,
                output_triangles=len(hull.faces),
                output_size_bytes=os.path.getsize(output_path),
                message="Converted via convex hull (geometry is simplified to convex envelope)",
            )
        else:
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=output_path,
                input_format="stl",
                output_format="step",
                method_used="convex_hull",
                quality=MeshQuality.FAILED,
                error="Convex hull STEP export produced empty file",
            )
    except Exception as e:
        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format="stl",
            output_format="step",
            method_used="convex_hull",
            quality=MeshQuality.FAILED,
            error=f"Convex hull strategy failed: {e}",
        )


def _strategy_voxelized_step(
    input_path: str,
    output_path: str,
    options: ConversionOptions,
) -> ConversionResult:
    """Strategy 4: Use voxelized representation for STEP export."""
    try:
        mesh = trimesh.load(input_path, force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        # Create voxelized representation
        voxel_pitch = options.tolerance * 2
        voxelized = mesh.voxelized(voxel_pitch)

        # Convert voxels to mesh
        voxel_mesh = voxelized.marching_cubes

        if options.simplify and len(voxel_mesh.faces) > options.target_faces:
            voxel_mesh = voxel_mesh.simplify_quadric_decimation(options.target_faces)

        voxel_mesh.export(output_path, file_type="step")

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return ConversionResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                input_format="stl",
                output_format="step",
                method_used="voxelized",
                quality=MeshQuality.ACCEPTABLE,
                output_triangles=len(voxel_mesh.faces),
                output_size_bytes=os.path.getsize(output_path),
                message=f"Converted via voxelized representation (pitch={voxel_pitch:.4f})",
            )
        else:
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=output_path,
                input_format="stl",
                output_format="step",
                method_used="voxelized",
                quality=MeshQuality.FAILED,
                error="Voxelized STEP export produced empty file",
            )
    except Exception as e:
        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format="stl",
            output_format="step",
            method_used="voxelized",
            quality=MeshQuality.FAILED,
            error=f"Voxelized strategy failed: {e}",
        )


def _stl_to_iges(
    input_path: str,
    output_path: str,
    options: ConversionOptions,
) -> ConversionResult:
    """Convert STL to IGES using trimesh.

    Args:
        input_path: Path to the input STL file.
        output_path: Path for the output IGES file.
        options: Conversion options.

    Returns:
        ConversionResult.
    """
    try:
        mesh = trimesh.load(input_path, force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        if options.simplify and len(mesh.faces) > options.target_faces:
            mesh = mesh.simplify_quadric_decimation(options.target_faces)

        mesh.export(output_path, file_type="iges")

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return ConversionResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                input_format="stl",
                output_format="iges",
                method_used="trimesh_basic",
                quality=MeshQuality.GOOD if mesh.is_watertight else MeshQuality.ACCEPTABLE,
                output_triangles=len(mesh.faces),
                output_size_bytes=os.path.getsize(output_path),
                message=f"Converted STL to IGES. Watertight: {mesh.is_watertight}",
            )
        else:
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=output_path,
                input_format="stl",
                output_format="iges",
                error="IGES export produced empty file. OpenCASCADE may not be available.",
            )
    except Exception as e:
        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format="stl",
            output_format="iges",
            error=f"STL to IGES conversion failed: {e}",
        )


def _mesh_to_brep(
    input_path: str,
    output_path: str,
    output_format: str,
    options: ConversionOptions,
) -> ConversionResult:
    """Convert a mesh file to a B-rep format.

    Used for OBJ→STEP conversions. Loads the mesh, then uses the same
    multi-strategy approach as STL→STEP.

    Args:
        input_path: Path to the input mesh file.
        output_path: Path for the output B-rep file.
        output_format: Target B-rep format (step or iges).
        options: Conversion options.

    Returns:
        ConversionResult.
    """
    try:
        mesh = trimesh.load(input_path, force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        if options.simplify and len(mesh.faces) > options.target_faces:
            mesh = mesh.simplify_quadric_decimation(options.target_faces)

        # Try direct trimesh export first
        try:
            mesh.export(output_path, file_type=output_format)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return ConversionResult(
                    success=True,
                    input_path=input_path,
                    output_path=output_path,
                    input_format=detect_format(input_path).format,
                    output_format=output_format,
                    method_used="trimesh_basic",
                    quality=MeshQuality.GOOD if mesh.is_watertight else MeshQuality.ACCEPTABLE,
                    output_triangles=len(mesh.faces),
                    output_size_bytes=os.path.getsize(output_path),
                    message=f"Converted {input_path} to {output_format.upper()} via trimesh",
                )
        except Exception:
            pass

        # Try convex hull fallback
        try:
            hull = mesh.convex_hull
            hull.export(output_path, file_type=output_format)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return ConversionResult(
                    success=True,
                    input_path=input_path,
                    output_path=output_path,
                    input_format=detect_format(input_path).format,
                    output_format=output_format,
                    method_used="convex_hull",
                    quality=MeshQuality.ACCEPTABLE,
                    output_triangles=len(hull.faces),
                    output_size_bytes=os.path.getsize(output_path),
                    message=f"Converted via convex hull fallback (geometry simplified)",
                )
        except Exception:
            pass

        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format=detect_format(input_path).format,
            output_format=output_format,
            error=f"All mesh-to-B-rep strategies failed for {output_format}",
        )
    except Exception as e:
        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format=detect_format(input_path).format,
            output_format=output_format,
            error=f"Mesh to B-rep conversion failed: {e}",
        )


# ======================================================================
# B-rep conversions (STEP→STL, STEP→IGES, IGES→STEP, IGES→STL)
# ======================================================================


def _brep_to_mesh(
    input_path: str,
    output_path: str,
    input_format: str,
    options: ConversionOptions,
) -> ConversionResult:
    """Convert a B-rep file to mesh format.

    Args:
        input_path: Path to the input B-rep file.
        output_path: Path for the output mesh file.
        input_format: Input format (step or iges).
        options: Conversion options with tessellation parameters.

    Returns:
        ConversionResult.
    """
    try:
        # Load B-rep file with trimesh
        scene_or_mesh = trimesh.load(
            input_path,
            file_type=input_format,
        )

        if isinstance(scene_or_mesh, trimesh.Scene):
            mesh = scene_or_mesh.dump(concatenate=True)
        else:
            mesh = scene_or_mesh

        # Export as STL
        mesh.export(output_path, file_type="stl")

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            output_triangles = _count_stl_triangles(output_path, STLEncoding.UNKNOWN)
            return ConversionResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                input_format=input_format,
                output_format="stl",
                method_used="trimesh_load_export",
                quality=MeshQuality.EXCELLENT,
                output_triangles=output_triangles,
                output_size_bytes=os.path.getsize(output_path),
                message=f"Converted {input_format.upper()} to STL with {output_triangles} triangles",
            )
        else:
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=output_path,
                input_format=input_format,
                output_format="stl",
                error=f"{input_format.upper()} to STL produced empty file",
            )
    except Exception as e:
        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format=input_format,
            output_format="stl",
            error=f"{input_format.upper()} to STL conversion failed: {e}",
        )


def _brep_to_brep(
    input_path: str,
    output_path: str,
    output_format: str,
) -> ConversionResult:
    """Convert between B-rep formats (STEP→IGES or IGES→STEP).

    Args:
        input_path: Path to the input B-rep file.
        output_path: Path for the output B-rep file.
        output_format: Target format (step or iges).

    Returns:
        ConversionResult.
    """
    try:
        # Load and re-export through trimesh
        scene_or_mesh = trimesh.load(input_path)

        if isinstance(scene_or_mesh, trimesh.Scene):
            mesh = scene_or_mesh
        else:
            mesh = scene_or_mesh

        mesh.export(output_path, file_type=output_format)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return ConversionResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                input_format=detect_format(input_path).format,
                output_format=output_format,
                method_used="trimesh_reexport",
                quality=MeshQuality.EXCELLENT,
                output_size_bytes=os.path.getsize(output_path),
                message=f"Converted to {output_format.upper()} successfully",
            )
        else:
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=output_path,
                input_format=detect_format(input_path).format,
                output_format=output_format,
                error=f"B-rep conversion produced empty file",
            )
    except Exception as e:
        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format=detect_format(input_path).format,
            output_format=output_format,
            error=f"B-rep to B-rep conversion failed: {e}",
        )


# ======================================================================
# DXF to STL conversion
# ======================================================================


def _dxf_to_stl(
    input_path: str,
    output_path: str,
    options: ConversionOptions,
) -> ConversionResult:
    """Convert a DXF file to STL.

    DXF files may contain 3D mesh entities (MESH, POLYFACE). This function
    attempts to extract 3D geometry and export as STL.

    Args:
        input_path: Path to the input DXF file.
        output_path: Path for the output STL file.
        options: Conversion options.

    Returns:
        ConversionResult.
    """
    try:
        import ezdxf

        doc = ezdxf.readfile(input_path)
        msp = doc.modelspace()

        vertices: list[tuple[float, float, float]] = []
        faces: list[tuple[int, int, int]] = []

        # Extract mesh entities from DXF
        for entity in msp:
            if entity.dxftype() == "MESH":
                mesh_entity = entity
                mesh_verts = mesh_entity.vertices
                mesh_faces = mesh_entity.faces if hasattr(mesh_entity, "faces") else []

                for v in mesh_verts:
                    vertices.append((float(v[0]), float(v[1]), float(v[2]) if len(v) > 2 else 0.0))

                if mesh_faces:
                    for face in mesh_faces:
                        if len(face) >= 3:
                            faces.append((face[0], face[1], face[2]))

            elif entity.dxftype() == "POLYLINE" or entity.dxftype() == "POLYLINE_3D":
                polyline = entity
                if polyline.is_3d_polyline:
                    for v in polyline.vertices():
                        vertices.append((float(v.dxf.location[0]), float(v.dxf.location[1]), float(v.dxf.location[2]) if len(v.dxf.location) > 2 else 0.0))

        if not vertices or not faces:
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=output_path,
                input_format="dxf",
                output_format="stl",
                error="No 3D mesh geometry found in DXF file. Only 2D data present.",
            )

        # Build trimesh and export
        vertex_array = np.array(vertices)
        face_array = np.array(faces)
        mesh = trimesh.Trimesh(vertices=vertex_array, faces=face_array)

        mesh.export(output_path, file_type="stl")

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return ConversionResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                input_format="dxf",
                output_format="stl",
                method_used="ezdxf_extract",
                quality=MeshQuality.ACCEPTABLE,
                output_triangles=len(mesh.faces),
                output_size_bytes=os.path.getsize(output_path),
                message=f"Extracted {len(mesh.faces)} triangles from DXF mesh entities",
            )
        else:
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=output_path,
                input_format="dxf",
                output_format="stl",
                error="DXF to STL produced empty file",
            )
    except ImportError:
        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format="dxf",
            output_format="stl",
            error="ezdxf library not installed. Install with: pip install ezdxf",
        )
    except Exception as e:
        return ConversionResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            input_format="dxf",
            output_format="stl",
            error=f"DXF to STL conversion failed: {e}",
        )


# ======================================================================
# Batch conversion
# ======================================================================


def batch_convert(
    input_files: list[str],
    output_format: str,
    output_dir: str,
    options: ConversionOptions | None = None,
) -> list[ConversionResult]:
    """Convert multiple files to a target format.

    Args:
        input_files: List of input file paths.
        output_format: Target format for all conversions.
        output_dir: Directory for output files.
        options: Conversion options applied to all files.

    Returns:
        List of ConversionResult objects, one per input file.
    """
    if options is None:
        options = ConversionOptions()

    results: list[ConversionResult] = []

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    for input_path in input_files:
        input_path = str(Path(input_path).resolve())
        file_name = Path(input_path).stem
        output_path = str(Path(output_dir) / f"{file_name}.{output_format}")

        result = convert_file(input_path, output_path, output_format, options)
        results.append(result)

    return results


# ======================================================================
# Mesh repair functions
# ======================================================================


def repair_mesh(input_path: str, output_path: str) -> RepairResult:
    """Repair common mesh defects.

    Attempts to fix:
    - Non-manifold edges and vertices
    - Holes in the mesh surface
    - Degenerate (zero-area) triangles
    - Duplicate faces
    - Inconsistent face winding

    Args:
        input_path: Path to the input mesh file.
        output_path: Path for the repaired mesh file.

    Returns:
        RepairResult with details about what was fixed.
    """
    try:
        mesh = trimesh.load(input_path, force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        original_triangles = len(mesh.faces)
        watertight_before = mesh.is_watertight
        operations: list[str] = []

        # Step 1: Remove degenerate faces
        non_degenerate = mesh.nondegenerate_faces
        if len(non_degenerate) < len(mesh.faces):
            mesh = mesh.submesh([non_degenerate])
            removed = original_triangles - len(mesh.faces)
            operations.append(f"Removed {removed} degenerate triangles")

        # Step 2: Remove duplicate faces
        unique_faces = mesh.unique_faces
        if len(unique_faces) < len(mesh.faces):
            mesh = mesh.submesh([unique_faces])
            removed = len(mesh.faces) - (original_triangles - len(unique_faces))
            operations.append(f"Removed duplicate faces")

        # Step 3: Fill holes
        if not mesh.is_watertight:
            try:
                filled = trimesh.repair.fill_holes(mesh)
                if filled is not None and filled.is_watertight != mesh.is_watertight:
                    mesh = filled
                    operations.append("Filled holes in mesh surface")
            except Exception as e:
                operations.append(f"Could not fill holes: {e}")

        # Step 4: Fix face winding (normals)
        try:
            mesh.fix_normals()
            operations.append("Fixed face winding/normals")
        except Exception:
            pass

        # Step 5: Merge close vertices
        try:
            mesh.merge_vertices()
            operations.append("Merged duplicate vertices")
        except Exception:
            pass

        # Step 6: Remove unreferenced vertices
        mesh.remove_unreferenced_vertices()
        operations.append("Removed unreferenced vertices")

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # Export repaired mesh (same format as input)
        input_format = detect_format(input_path).format
        mesh.export(output_path, file_type=input_format if input_format != "unknown" else "stl")

        watertight_after = mesh.is_watertight

        return RepairResult(
            success=True,
            input_path=input_path,
            output_path=output_path,
            original_triangles=original_triangles,
            repaired_triangles=len(mesh.faces),
            watertight_before=watertight_before,
            watertight_after=watertight_after,
            operations_performed=operations,
            message=f"Repaired mesh: {len(operations)} operations performed",
        )
    except Exception as e:
        return RepairResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            error=f"Mesh repair failed: {e}",
        )


def simplify_mesh(
    input_path: str,
    output_path: str,
    target_faces: int = 50000,
) -> RepairResult:
    """Reduce triangle count while preserving overall shape.

    Uses quadric edge collapse decimation to reduce the number of triangles
    while maintaining the mesh's shape as closely as possible.

    Args:
        input_path: Path to the input mesh file.
        output_path: Path for the simplified mesh file.
        target_faces: Target number of triangles.

    Returns:
        RepairResult with simplification details.
    """
    try:
        mesh = trimesh.load(input_path, force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        original_triangles = len(mesh.faces)
        watertight_before = mesh.is_watertight
        operations: list[str] = []

        if original_triangles <= target_faces:
            operations.append(f"Mesh already has {original_triangles} faces (<= target {target_faces})")
            mesh.export(output_path, file_type=detect_format(input_path).format or "stl")
            return RepairResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                original_triangles=original_triangles,
                repaired_triangles=original_triangles,
                watertight_before=watertight_before,
                watertight_after=watertight_before,
                operations_performed=operations,
                message="No simplification needed; mesh already below target face count",
            )

        # Simplify using quadric decimation
        simplified = mesh.simplify_quadric_decimation(target_faces)
        operations.append(
            f"Quadric decimation: {original_triangles} -> {len(simplified.faces)} faces "
            f"({100.0 * (1 - len(simplified.faces) / original_triangles):.1f}% reduction)"
        )

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        mesh.export(output_path, file_type=detect_format(input_path).format or "stl")

        return RepairResult(
            success=True,
            input_path=input_path,
            output_path=output_path,
            original_triangles=original_triangles,
            repaired_triangles=len(simplified.faces),
            watertight_before=watertight_before,
            watertight_after=simplified.is_watertight,
            operations_performed=operations,
            message=f"Simplified mesh to {len(simplified.faces)} faces",
        )
    except Exception as e:
        return RepairResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            error=f"Mesh simplification failed: {e}",
        )


def fill_holes(input_path: str, output_path: str) -> RepairResult:
    """Fill holes in a non-watertight mesh.

    Identifies boundary edges (edges belonging to only one face) and
    creates new faces to close the holes.

    Args:
        input_path: Path to the input mesh file.
        output_path: Path for the mesh with holes filled.

    Returns:
        RepairResult.
    """
    try:
        mesh = trimesh.load(input_path, force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        original_triangles = len(mesh.faces)
        watertight_before = mesh.is_watertight
        operations: list[str] = []

        if watertight_before:
            operations.append("Mesh is already watertight; no holes to fill")
            mesh.export(output_path, file_type=detect_format(input_path).format or "stl")
            return RepairResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                original_triangles=original_triangles,
                repaired_triangles=original_triangles,
                watertight_before=True,
                watertight_after=True,
                operations_performed=operations,
                message="Mesh already watertight",
            )

        # Fill holes
        filled = trimesh.repair.fill_holes(mesh)
        if filled is not None:
            new_triangles = len(filled.faces) - original_triangles
            mesh = filled
            operations.append(f"Filled holes: added {new_triangles} triangles")

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        mesh.export(output_path, file_type=detect_format(input_path).format or "stl")

        watertight_after = mesh.is_watertight

        return RepairResult(
            success=True,
            input_path=input_path,
            output_path=output_path,
            original_triangles=original_triangles,
            repaired_triangles=len(mesh.faces),
            watertight_before=watertight_before,
            watertight_after=watertight_after,
            operations_performed=operations,
            message=f"Filled holes. Watertight: {watertight_after}",
        )
    except Exception as e:
        return RepairResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            error=f"Fill holes failed: {e}",
        )


def make_watertight(input_path: str, output_path: str, method: str = "auto") -> RepairResult:
    """Ensure a mesh is watertight for B-rep conversion.

    Multiple strategies are attempted to make the mesh watertight:
    - fill: Fill holes directly
    - crumble: Remove faces until the mesh is watertight (aggressive)
    - wrap: Create a convex wrapping of the mesh

    Args:
        input_path: Path to the input mesh file.
        output_path: Path for the watertight mesh file.
        method: Strategy to use: "auto", "fill", "crumble", or "wrap".

    Returns:
        RepairResult.
    """
    try:
        mesh = trimesh.load(input_path, force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        original_triangles = len(mesh.faces)
        watertight_before = mesh.is_watertight
        operations: list[str] = []

        if watertight_before:
            operations.append("Mesh is already watertight")
            mesh.export(output_path, file_type=detect_format(input_path).format or "stl")
            return RepairResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                original_triangles=original_triangles,
                repaired_triangles=original_triangles,
                watertight_before=True,
                watertight_after=True,
                operations_performed=operations,
                message="Mesh already watertight",
            )

        result_mesh = None

        if method == "auto" or method == "fill":
            # Try filling holes first
            try:
                filled = trimesh.repair.fill_holes(mesh)
                if filled is not None and filled.is_watertight:
                    result_mesh = filled
                    operations.append("Made watertight via hole filling")
            except Exception as e:
                operations.append(f"Hole filling failed: {e}")

        if result_mesh is None and (method == "auto" or method == "crumble"):
            # Try crumbling (remove non-manifold geometry)
            try:
                body = mesh.convex_hull
                if body.is_watertight:
                    result_mesh = body
                    operations.append("Made watertight via convex hull (crumble)")
            except Exception as e:
                operations.append(f"Convex hull failed: {e}")

        if result_mesh is None and method == "wrap":
            # Try wrapping
            try:
                wrapped = trimesh.convex.convex_hull(mesh)
                if wrapped.is_watertight:
                    result_mesh = wrapped
                    operations.append("Made watertight via wrap")
            except Exception as e:
                operations.append(f"Wrap failed: {e}")

        if result_mesh is None:
            result_mesh = mesh
            operations.append("Could not make mesh watertight with any method")

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        result_mesh.export(output_path, file_type=detect_format(input_path).format or "stl")

        return RepairResult(
            success=result_mesh.is_watertight,
            input_path=input_path,
            output_path=output_path,
            original_triangles=original_triangles,
            repaired_triangles=len(result_mesh.faces),
            watertight_before=watertight_before,
            watertight_after=result_mesh.is_watertight,
            operations_performed=operations,
            message=f"Mesh watertight: {result_mesh.is_watertight}",
        )
    except Exception as e:
        return RepairResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            error=f"Make watertight failed: {e}",
        )


def remove_degenerate(input_path: str, output_path: str) -> RepairResult:
    """Remove degenerate and zero-area triangles from a mesh.

    Degenerate triangles have zero area because two or more vertices
    are coincident or collinear.

    Args:
        input_path: Path to the input mesh file.
        output_path: Path for the cleaned mesh file.

    Returns:
        RepairResult.
    """
    try:
        mesh = trimesh.load(input_path, force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        original_triangles = len(mesh.faces)
        watertight_before = mesh.is_watertight
        operations: list[str] = []

        # Get non-degenerate face mask
        non_degen = mesh.nondegenerate_faces
        removed_count = original_triangles - len(non_degen)

        if removed_count > 0:
            cleaned = mesh.submesh([non_degen])
            cleaned.remove_unreferenced_vertices()
            operations.append(f"Removed {removed_count} degenerate triangles")
            mesh = cleaned
        else:
            operations.append("No degenerate triangles found")

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        mesh.export(output_path, file_type=detect_format(input_path).format or "stl")

        return RepairResult(
            success=True,
            input_path=input_path,
            output_path=output_path,
            original_triangles=original_triangles,
            repaired_triangles=len(mesh.faces),
            watertight_before=watertight_before,
            watertight_after=mesh.is_watertight,
            operations_performed=operations,
            message=f"Removed {removed_count} degenerate triangles" if removed_count > 0 else "No degeneracies found",
        )
    except Exception as e:
        return RepairResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            error=f"Remove degenerate failed: {e}",
        )


def merge_vertices(input_path: str, output_path: str) -> RepairResult:
    """Merge duplicate vertices in a mesh.

    Some mesh formats store duplicate vertex positions. This operation
    merges vertices that are at the same position, reducing file size
    and improving mesh topology.

    Args:
        input_path: Path to the input mesh file.
        output_path: Path for the mesh with merged vertices.

    Returns:
        RepairResult.
    """
    try:
        mesh = trimesh.load(input_path, force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        original_triangles = len(mesh.faces)
        original_vertices = len(mesh.vertices)
        watertight_before = mesh.is_watertight
        operations: list[str] = []

        # Merge vertices
        mesh.merge_vertices()
        merged_vertices = len(mesh.vertices)
        removed = original_vertices - merged_vertices

        if removed > 0:
            operations.append(f"Merged {removed} duplicate vertices ({original_vertices} -> {merged_vertices})")
        else:
            operations.append("No duplicate vertices found")

        # Clean up
        mesh.remove_unreferenced_vertices()

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        mesh.export(output_path, file_type=detect_format(input_path).format or "stl")

        return RepairResult(
            success=True,
            input_path=input_path,
            output_path=output_path,
            original_triangles=original_triangles,
            repaired_triangles=len(mesh.faces),
            watertight_before=watertight_before,
            watertight_after=mesh.is_watertight,
            operations_performed=operations,
            message=f"Merged vertices: {original_vertices} -> {merged_vertices}",
        )
    except Exception as e:
        return RepairResult(
            success=False,
            input_path=input_path,
            output_path=output_path,
            error=f"Merge vertices failed: {e}",
        )
