"""Analysis tools — MCP tool registrations for mesh and file analysis.

Provides 3 tools for analyzing mesh properties, detecting file formats,
and retrieving detailed file information before conversion.
"""

from __future__ import annotations

import json
import logging

from mcp.server.fastmcp import FastMCP

from file_translator_mcp.api.converter import analyze_mesh, detect_format, get_file_info

logger = logging.getLogger(__name__)


def register_analyze_tools(mcp: FastMCP) -> None:
    """Register all analysis-related tools on the given MCP server."""

    @mcp.tool()
    async def analyze_mesh_tool(input_path: str) -> str:
        """Analyze a mesh file and return detailed properties.

        Returns triangle count, vertex count, bounding box dimensions,
        enclosed volume, surface area, watertight status, Euler number,
        manifold status, and convexity.

        Use this tool before conversion to understand the input mesh quality
        and determine if STL-to-STEP conversion will produce good results.

        Args:
            input_path: Path to the mesh file (STL, OBJ, PLY, etc.).

        Returns:
            JSON string with mesh analysis results including quality assessment.
        """
        try:
            analysis = analyze_mesh(input_path)
            return json.dumps({
                "success": True,
                "input_path": input_path,
                "triangle_count": analysis.triangle_count,
                "vertex_count": analysis.vertex_count,
                "bounding_box": {
                    "min": {
                        "x": analysis.bounding_box.min_x,
                        "y": analysis.bounding_box.min_y,
                        "z": analysis.bounding_box.min_z,
                    },
                    "max": {
                        "x": analysis.bounding_box.max_x,
                        "y": analysis.bounding_box.max_y,
                        "z": analysis.bounding_box.max_z,
                    },
                    "size": {
                        "x": round(analysis.bounding_box.max_x - analysis.bounding_box.min_x, 6),
                        "y": round(analysis.bounding_box.max_y - analysis.bounding_box.min_y, 6),
                        "z": round(analysis.bounding_box.max_z - analysis.bounding_box.min_z, 6),
                    },
                },
                "volume": round(analysis.volume, 6),
                "surface_area": round(analysis.surface_area, 6),
                "watertight": analysis.watertight,
                "euler_number": analysis.euler_number,
                "is_manifold": analysis.is_manifold,
                "convex": analysis.convex,
                "step_conversion_advice": _get_step_conversion_advice(analysis),
            }, indent=2)
        except FileNotFoundError as e:
            return json.dumps({"success": False, "error": f"File not found: {e}"})
        except Exception as e:
            logger.exception("analyze_mesh failed")
            return json.dumps({"success": False, "error": f"Mesh analysis error: {e}"})

    @mcp.tool()
    async def detect_format(input_path: str) -> str:
        """Auto-detect the CAD file format from header bytes and extension.

        Reads the file's magic bytes to determine the format. Supports STL
        (binary and ASCII), STEP (AP214/AP242), IGES, OBJ, PLY, 3MF, and DXF.

        Args:
            input_path: Path to the file to analyze.

        Returns:
            JSON string with detected format, confidence level, encoding
            (binary/ascii for STL), and detection details.
        """
        try:
            detection = detect_format(input_path)
            return json.dumps({
                "success": True,
                "input_path": input_path,
                "format": detection.format,
                "confidence": detection.confidence,
                "encoding": detection.encoding.value,
                "details": detection.details,
            }, indent=2)
        except Exception as e:
            logger.exception("detect_format failed")
            return json.dumps({"success": False, "error": f"Format detection error: {e}"})

    @mcp.tool()
    async def get_file_info(input_path: str) -> str:
        """Get detailed information about a CAD file.

        Returns file size (human-readable and bytes), detected format,
        encoding type (binary/ASCII for STL), and triangle count for mesh files.

        Args:
            input_path: Path to the file to analyze.

        Returns:
            JSON string with file information including size, format, and mesh data.
        """
        try:
            info = get_file_info(input_path)
            return json.dumps({
                "success": True,
                "path": info.path,
                "size_bytes": info.size_bytes,
                "size_human": info.size_human,
                "format": info.format,
                "encoding": info.encoding.value,
                "triangle_count": info.triangle_count,
            }, indent=2)
        except Exception as e:
            logger.exception("get_file_info failed")
            return json.dumps({"success": False, "error": f"File info error: {e}"})


def _get_step_conversion_advice(analysis) -> dict:
    """Generate advice for STL-to-STEP conversion based on mesh analysis."""
    issues = []
    recommended_method = "trimesh_basic"
    expected_quality = "good"

    if not analysis.watertight:
        issues.append("Mesh is NOT watertight — STL-to-STEP conversion will produce approximate results")
        issues.append("Consider using make_watertight or repair_mesh before conversion")
        recommended_method = "convex_hull"
        expected_quality = "acceptable"

    if analysis.triangle_count > 1000000:
        issues.append(f"Very large mesh ({analysis.triangle_count} triangles) — consider simplifying first")
        issues.append("Use simplify_mesh to reduce triangle count before conversion")
    elif analysis.triangle_count > 100000:
        issues.append(f"Large mesh ({analysis.triangle_count} triangles) — conversion may take time")

    if not analysis.is_manifold:
        issues.append("Mesh contains non-manifold geometry — may cause conversion issues")
        issues.append("Use repair_mesh to fix non-manifold edges before conversion")

    if analysis.convex:
        issues.append("Mesh is convex — convex_hull method will produce exact results")

    if analysis.volume <= 0:
        issues.append("Mesh has zero or negative volume — likely degenerate or open")

    if not issues:
        issues.append("Mesh appears suitable for high-quality STL-to-STEP conversion")

    return {
        "issues": issues,
        "recommended_method": recommended_method,
        "expected_quality": expected_quality,
    }
