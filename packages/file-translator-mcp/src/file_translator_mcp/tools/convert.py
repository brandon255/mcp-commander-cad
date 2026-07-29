"""Conversion tools — MCP tool registrations for CAD file format conversion.

Provides 11 tools covering general-purpose conversion, specific format-to-format
converters, and batch conversion capabilities.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from file_translator_mcp.api.converter import (
    SUPPORTED_CONVERSIONS,
    convert_file,
    batch_convert,
)

logger = logging.getLogger(__name__)


def register_convert_tools(mcp: FastMCP) -> None:
    """Register all conversion-related tools on the given MCP server."""

    @mcp.tool()
    async def convert_file_tool(
        input_path: str,
        output_path: str,
        output_format: str,
        method: str = "auto",
        tolerance: float = 0.01,
        simplify: bool = True,
        target_faces: int = 50000,
    ) -> str:
        """Convert a CAD file from one format to another.

        Supports conversions between STL, STEP, IGES, OBJ, PLY, 3MF, and DXF.
        For mesh-to-B-rep conversions (e.g., STL to STEP), multiple
        reconstruction strategies are attempted automatically.

        Args:
            input_path: Path to the input file (absolute or relative).
            output_path: Path for the output file.
            output_format: Target format: stl, step, iges, obj, ply, 3mf.
            method: Conversion method for mesh-to-B-rep: auto, trimesh_basic,
                cadquery_mesh_to_solid, convex_hull, voxelized.
            tolerance: Reconstruction tolerance for B-rep conversion (default 0.01).
            simplify: Whether to simplify mesh before conversion (default true).
            target_faces: Target face count for simplification (default 50000).

        Returns:
            JSON string with conversion result including success status,
            method used, quality assessment, and file sizes.
        """
        try:
            from file_translator_mcp.api.models import ConversionMethod, ConversionOptions

            options = ConversionOptions(
                method=ConversionMethod(method),
                tolerance=tolerance,
                simplify=simplify,
                target_faces=target_faces,
            )
            result = convert_file(input_path, output_path, output_format, options)
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "input_format": result.input_format,
                "output_format": result.output_format,
                "method_used": result.method_used,
                "quality": result.quality.value,
                "input_triangles": result.input_triangles,
                "output_triangles": result.output_triangles,
                "output_size_bytes": result.output_size_bytes,
                "message": result.message,
                "error": result.error,
            }, indent=2)
        except Exception as e:
            logger.exception("convert_file failed")
            return json.dumps({"success": False, "error": f"Conversion error: {e}"})

    @mcp.tool()
    async def stl_to_step(
        input_path: str,
        output_path: str,
        method: str = "auto",
        tolerance: float = 0.01,
        simplify: bool = True,
    ) -> str:
        """Convert an STL mesh file to STEP B-rep format.

        STL files contain raw triangle meshes with no topology information.
        Converting to STEP (B-rep) requires surface reconstruction. This tool
        uses multiple strategies automatically:
        1. Trimesh basic export via OpenCASCADE (best quality for watertight meshes)
        2. CadQuery mesh-to-solid reconstruction
        3. Convex hull or voxelized fallback

        The quality of the result depends heavily on whether the input STL is
        watertight. Non-watertight meshes will produce approximate results.

        Args:
            input_path: Path to the input STL file.
            output_path: Path for the output STEP file.
            method: Reconstruction method: auto, trimesh_basic,
                cadquery_mesh_to_solid, convex_hull, voxelized.
            tolerance: Reconstruction tolerance (default 0.01).
            simplify: Simplify mesh before conversion (default true).

        Returns:
            JSON string with conversion result, quality assessment, and warnings.
        """
        try:
            from file_translator_mcp.api.models import ConversionMethod, ConversionOptions

            options = ConversionOptions(
                method=ConversionMethod(method),
                tolerance=tolerance,
                simplify=simplify,
            )
            result = convert_file(input_path, output_path, "step", options)
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "method_used": result.method_used,
                "quality": result.quality.value,
                "input_triangles": result.input_triangles,
                "output_size_bytes": result.output_size_bytes,
                "message": result.message,
                "error": result.error,
                "note": "STL to STEP conversion quality depends on mesh watertight status. "
                        "Non-watertight meshes produce approximate B-rep geometry.",
            }, indent=2)
        except Exception as e:
            logger.exception("stl_to_step failed")
            return json.dumps({"success": False, "error": f"STL to STEP error: {e}"})

    @mcp.tool()
    async def stl_to_iges(
        input_path: str,
        output_path: str,
        tolerance: float = 0.01,
    ) -> str:
        """Convert an STL mesh file to IGES format.

        Uses trimesh's OpenCASCADE-based export to convert the STL mesh
        to IGES B-rep format. Quality depends on mesh watertight status.

        Args:
            input_path: Path to the input STL file.
            output_path: Path for the output IGES file.
            tolerance: Reconstruction tolerance (default 0.01).

        Returns:
            JSON string with conversion result and quality assessment.
        """
        try:
            from file_translator_mcp.api.models import ConversionOptions

            options = ConversionOptions(tolerance=tolerance)
            result = convert_file(input_path, output_path, "iges", options)
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "method_used": result.method_used,
                "quality": result.quality.value,
                "output_size_bytes": result.output_size_bytes,
                "message": result.message,
                "error": result.error,
            }, indent=2)
        except Exception as e:
            logger.exception("stl_to_iges failed")
            return json.dumps({"success": False, "error": f"STL to IGES error: {e}"})

    @mcp.tool()
    async def stl_to_obj(input_path: str, output_path: str) -> str:
        """Convert an STL mesh file to OBJ format.

        OBJ format supports vertex normals, materials, and multiple objects.
        This conversion preserves geometry and optionally computes normals.

        Args:
            input_path: Path to the input STL file.
            output_path: Path for the output OBJ file.

        Returns:
            JSON string with conversion result.
        """
        try:
            result = convert_file(input_path, output_path, "obj")
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "output_triangles": result.output_triangles,
                "output_size_bytes": result.output_size_bytes,
                "message": result.message,
                "error": result.error,
            }, indent=2)
        except Exception as e:
            logger.exception("stl_to_obj failed")
            return json.dumps({"success": False, "error": f"STL to OBJ error: {e}"})

    @mcp.tool()
    async def step_to_stl(
        input_path: str,
        output_path: str,
        linear_tolerance: float = 0.01,
        angular_tolerance: float = 0.5,
    ) -> str:
        """Convert a STEP B-rep file to STL mesh.

        Tessellates the STEP model's surfaces into triangles at the specified
        tolerances. Lower tolerances produce more accurate (but larger) meshes.

        Args:
            input_path: Path to the input STEP file.
            output_path: Path for the output STL file.
            linear_tolerance: Maximum deviation from true surface (default 0.01).
            angular_tolerance: Maximum angle between adjacent triangles in degrees (default 0.5).

        Returns:
            JSON string with conversion result and triangle count.
        """
        try:
            from file_translator_mcp.api.models import ConversionOptions

            options = ConversionOptions(
                linear_tolerance=linear_tolerance,
                angular_tolerance=angular_tolerance,
            )
            result = convert_file(input_path, output_path, "stl", options)
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "output_triangles": result.output_triangles,
                "output_size_bytes": result.output_size_bytes,
                "message": result.message,
                "error": result.error,
            }, indent=2)
        except Exception as e:
            logger.exception("step_to_stl failed")
            return json.dumps({"success": False, "error": f"STEP to STL error: {e}"})

    @mcp.tool()
    async def step_to_iges(input_path: str, output_path: str) -> str:
        """Convert a STEP file to IGES format.

        Preserves B-rep topology when converting between STEP and IGES.
        Some advanced STEP entities may not have direct IGES equivalents.

        Args:
            input_path: Path to the input STEP file.
            output_path: Path for the output IGES file.

        Returns:
            JSON string with conversion result.
        """
        try:
            result = convert_file(input_path, output_path, "iges")
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "output_size_bytes": result.output_size_bytes,
                "message": result.message,
                "error": result.error,
            }, indent=2)
        except Exception as e:
            logger.exception("step_to_iges failed")
            return json.dumps({"success": False, "error": f"STEP to IGES error: {e}"})

    @mcp.tool()
    async def iges_to_step(input_path: str, output_path: str) -> str:
        """Convert an IGES file to STEP format.

        Converts IGES B-rep data to the more modern STEP (AP214/AP242) format.
        STEP preserves more geometry and topology information than IGES.

        Args:
            input_path: Path to the input IGES file.
            output_path: Path for the output STEP file.

        Returns:
            JSON string with conversion result.
        """
        try:
            result = convert_file(input_path, output_path, "step")
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "output_size_bytes": result.output_size_bytes,
                "message": result.message,
                "error": result.error,
            }, indent=2)
        except Exception as e:
            logger.exception("iges_to_step failed")
            return json.dumps({"success": False, "error": f"IGES to STEP error: {e}"})

    @mcp.tool()
    async def iges_to_stl(
        input_path: str,
        output_path: str,
        linear_tolerance: float = 0.01,
        angular_tolerance: float = 0.5,
    ) -> str:
        """Convert an IGES B-rep file to STL mesh.

        Tessellates IGES model surfaces into triangles.

        Args:
            input_path: Path to the input IGES file.
            output_path: Path for the output STL file.
            linear_tolerance: Maximum deviation from true surface (default 0.01).
            angular_tolerance: Maximum angle between triangles in degrees (default 0.5).

        Returns:
            JSON string with conversion result and triangle count.
        """
        try:
            from file_translator_mcp.api.models import ConversionOptions

            options = ConversionOptions(
                linear_tolerance=linear_tolerance,
                angular_tolerance=angular_tolerance,
            )
            result = convert_file(input_path, output_path, "stl", options)
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "output_triangles": result.output_triangles,
                "output_size_bytes": result.output_size_bytes,
                "message": result.message,
                "error": result.error,
            }, indent=2)
        except Exception as e:
            logger.exception("iges_to_stl failed")
            return json.dumps({"success": False, "error": f"IGES to STL error: {e}"})

    @mcp.tool()
    async def obj_to_stl(input_path: str, output_path: str) -> str:
        """Convert an OBJ mesh file to STL format.

        Preserves geometry while converting from OBJ's vertex/face format
        to STL's triangle format. Normals are recomputed.

        Args:
            input_path: Path to the input OBJ file.
            output_path: Path for the output STL file.

        Returns:
            JSON string with conversion result.
        """
        try:
            result = convert_file(input_path, output_path, "stl")
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "output_triangles": result.output_triangles,
                "output_size_bytes": result.output_size_bytes,
                "message": result.message,
                "error": result.error,
            }, indent=2)
        except Exception as e:
            logger.exception("obj_to_stl failed")
            return json.dumps({"success": False, "error": f"OBJ to STL error: {e}"})

    @mcp.tool()
    async def obj_to_step(
        input_path: str,
        output_path: str,
        method: str = "auto",
        tolerance: float = 0.01,
        simplify: bool = True,
    ) -> str:
        """Convert an OBJ mesh file to STEP B-rep format.

        Uses the same multi-strategy approach as STL to STEP conversion.
        The quality of the result depends on the mesh being watertight.

        Args:
            input_path: Path to the input OBJ file.
            output_path: Path for the output STEP file.
            method: Reconstruction method: auto, trimesh_basic, convex_hull, voxelized.
            tolerance: Reconstruction tolerance (default 0.01).
            simplify: Simplify mesh before conversion (default true).

        Returns:
            JSON string with conversion result and quality assessment.
        """
        try:
            from file_translator_mcp.api.models import ConversionMethod, ConversionOptions

            options = ConversionOptions(
                method=ConversionMethod(method),
                tolerance=tolerance,
                simplify=simplify,
            )
            result = convert_file(input_path, output_path, "step", options)
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "method_used": result.method_used,
                "quality": result.quality.value,
                "input_triangles": result.input_triangles,
                "output_size_bytes": result.output_size_bytes,
                "message": result.message,
                "error": result.error,
            }, indent=2)
        except Exception as e:
            logger.exception("obj_to_step failed")
            return json.dumps({"success": False, "error": f"OBJ to STEP error: {e}"})

    @mcp.tool()
    async def ply_to_stl(input_path: str, output_path: str) -> str:
        """Convert a PLY (Polygon/Point Cloud) file to STL format.

        Handles both polygon mesh PLY files and point cloud PLY files.
        For point clouds, a mesh reconstruction is attempted if possible.

        Args:
            input_path: Path to the input PLY file.
            output_path: Path for the output STL file.

        Returns:
            JSON string with conversion result.
        """
        try:
            result = convert_file(input_path, output_path, "stl")
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "output_triangles": result.output_triangles,
                "output_size_bytes": result.output_size_bytes,
                "message": result.message,
                "error": result.error,
            }, indent=2)
        except Exception as e:
            logger.exception("ply_to_stl failed")
            return json.dumps({"success": False, "error": f"PLY to STL error: {e}"})

    @mcp.tool()
    async def batch_convert(
        input_files: str,
        output_format: str,
        output_dir: str,
        method: str = "auto",
        tolerance: float = 0.01,
        simplify: bool = True,
    ) -> str:
        """Convert multiple CAD files to a target format in batch.

        Processes a list of files (comma-separated or newline-separated paths),
        converting each to the specified output format. Output files are named
        after the input files with the new extension.

        Args:
            input_files: Comma-separated or newline-separated list of input file paths.
            output_format: Target format for all conversions: stl, step, iges, obj, ply, 3mf.
            output_dir: Directory for output files (created if needed).
            method: Conversion method for mesh-to-B-rep: auto, trimesh_basic, convex_hull.
            tolerance: Reconstruction tolerance (default 0.01).
            simplify: Simplify meshes before conversion (default true).

        Returns:
            JSON string with per-file results and summary counts.
        """
        try:
            from file_translator_mcp.api.models import ConversionMethod, ConversionOptions

            # Parse input file list (comma-separated, with optional newlines)
            files = [f.strip() for f in input_files.replace("\n", ",").split(",") if f.strip()]

            if not files:
                return json.dumps({
                    "success": False,
                    "error": "No input files provided",
                }, indent=2)

            options = ConversionOptions(
                method=ConversionMethod(method),
                tolerance=tolerance,
                simplify=simplify,
            )

            results = batch_convert(files, output_format, output_dir, options)

            succeeded = sum(1 for r in results if r.success)
            failed = len(results) - succeeded

            per_file = []
            for r in results:
                per_file.append({
                    "input": r.input_path,
                    "output": r.output_path,
                    "success": r.success,
                    "error": r.error,
                    "message": r.message,
                })

            return json.dumps({
                "success": failed == 0,
                "total_files": len(results),
                "succeeded": succeeded,
                "failed": failed,
                "output_format": output_format,
                "output_dir": output_dir,
                "results": per_file,
            }, indent=2)
        except Exception as e:
            logger.exception("batch_convert failed")
            return json.dumps({"success": False, "error": f"Batch conversion error: {e}"})
