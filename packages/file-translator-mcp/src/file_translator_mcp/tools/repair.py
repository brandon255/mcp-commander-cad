"""Repair tools — MCP tool registrations for mesh repair and cleanup.

Provides 6 tools for fixing common mesh defects, simplifying meshes,
making meshes watertight for B-rep conversion, and removing degeneracies.
"""

from __future__ import annotations

import json
import logging

from mcp.server.fastmcp import FastMCP

from file_translator_mcp.api.converter import (
    fill_holes,
    make_watertight,
    merge_vertices,
    remove_degenerate,
    repair_mesh,
    simplify_mesh,
)

logger = logging.getLogger(__name__)


def register_repair_tools(mcp: FastMCP) -> None:
    """Register all repair-related tools on the given MCP server."""

    @mcp.tool()
    async def repair_mesh_tool(input_path: str, output_path: str) -> str:
        """Repair common mesh defects in a CAD file.

        Attempts to fix multiple issues in sequence:
        - Removes degenerate (zero-area) triangles
        - Removes duplicate faces
        - Fills holes in the mesh surface
        - Fixes face winding and normals
        - Merges duplicate vertices
        - Removes unreferenced vertices

        Use this tool before STL-to-STEP conversion to improve conversion quality.

        Args:
            input_path: Path to the input mesh file to repair.
            output_path: Path for the repaired output file.

        Returns:
            JSON string with repair results including operations performed,
            triangle counts before and after, and watertight status changes.
        """
        try:
            result = repair_mesh(input_path, output_path)
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "original_triangles": result.original_triangles,
                "repaired_triangles": result.repaired_triangles,
                "watertight_before": result.watertight_before,
                "watertight_after": result.watertight_after,
                "operations_performed": result.operations_performed,
                "message": result.message,
                "error": result.error,
            }, indent=2)
        except Exception as e:
            logger.exception("repair_mesh failed")
            return json.dumps({"success": False, "error": f"Mesh repair error: {e}"})

    @mcp.tool()
    async def simplify_mesh_tool(
        input_path: str,
        output_path: str,
        target_faces: int = 50000,
    ) -> str:
        """Reduce triangle count while preserving overall shape.

        Uses quadric edge collapse decimation to reduce the number of
        triangles while maintaining the mesh's shape as closely as possible.
        Useful for reducing very large meshes before conversion.

        Args:
            input_path: Path to the input mesh file.
            output_path: Path for the simplified output file.
            target_faces: Target number of triangles (default 50000).
                Must be at least 10.

        Returns:
            JSON string with simplification results including face counts,
            reduction percentage, and watertight status.
        """
        try:
            if target_faces < 10:
                return json.dumps({
                    "success": False,
                    "error": "target_faces must be at least 10",
                })

            result = simplify_mesh(input_path, output_path, target_faces)
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "original_triangles": result.original_triangles,
                "repaired_triangles": result.repaired_triangles,
                "watertight_before": result.watertight_before,
                "watertight_after": result.watertight_after,
                "operations_performed": result.operations_performed,
                "message": result.message,
                "error": result.error,
            }, indent=2)
        except Exception as e:
            logger.exception("simplify_mesh failed")
            return json.dumps({"success": False, "error": f"Mesh simplification error: {e}"})

    @mcp.tool()
    async def fill_holes_tool(input_path: str, output_path: str) -> str:
        """Fill holes in a non-watertight mesh.

        Identifies boundary edges (edges belonging to only one face) and
        creates new triangular faces to close the holes. Essential for
        preparing meshes for STL-to-STEP conversion.

        Args:
            input_path: Path to the input mesh file with holes.
            output_path: Path for the mesh with holes filled.

        Returns:
            JSON string with fill results including new triangle count
            and watertight status before/after.
        """
        try:
            result = fill_holes(input_path, output_path)
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "original_triangles": result.original_triangles,
                "repaired_triangles": result.repaired_triangles,
                "watertight_before": result.watertight_before,
                "watertight_after": result.watertight_after,
                "operations_performed": result.operations_performed,
                "message": result.message,
                "error": result.error,
            }, indent=2)
        except Exception as e:
            logger.exception("fill_holes failed")
            return json.dumps({"success": False, "error": f"Fill holes error: {e}"})

    @mcp.tool()
    async def make_watertight_tool(
        input_path: str,
        output_path: str,
        method: str = "auto",
    ) -> str:
        """Ensure a mesh is watertight for B-rep conversion.

        Watertight meshes are required for high-quality STL-to-STEP conversion.
        Multiple strategies are attempted:
        - 'fill': Fill holes directly (best for small holes)
        - 'crumble': Remove non-manifold geometry (aggressive)
        - 'wrap': Create convex wrapping (most aggressive, changes shape)
        - 'auto': Try fill first, then crumble, then wrap

        Args:
            input_path: Path to the input mesh file.
            output_path: Path for the watertight output file.
            method: Strategy: auto, fill, crumble, or wrap.

        Returns:
            JSON string with results including watertight status before/after
            and which strategy succeeded.
        """
        try:
            if method not in ("auto", "fill", "crumble", "wrap"):
                return json.dumps({
                    "success": False,
                    "error": "method must be one of: auto, fill, crumble, wrap",
                })

            result = make_watertight(input_path, output_path, method)
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "original_triangles": result.original_triangles,
                "repaired_triangles": result.repaired_triangles,
                "watertight_before": result.watertight_before,
                "watertight_after": result.watertight_after,
                "operations_performed": result.operations_performed,
                "message": result.message,
                "error": result.error,
            }, indent=2)
        except Exception as e:
            logger.exception("make_watertight failed")
            return json.dumps({"success": False, "error": f"Make watertight error: {e}"})

    @mcp.tool()
    async def remove_degenerate_tool(input_path: str, output_path: str) -> str:
        """Remove degenerate and zero-area triangles from a mesh.

        Degenerate triangles have zero area because two or more vertices
        are coincident or all three vertices are collinear. These can cause
        errors during conversion and should be removed.

        Args:
            input_path: Path to the input mesh file.
            output_path: Path for the cleaned output file.

        Returns:
            JSON string with removal results including count of removed
            triangles and remaining triangle count.
        """
        try:
            result = remove_degenerate(input_path, output_path)
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "original_triangles": result.original_triangles,
                "repaired_triangles": result.repaired_triangles,
                "watertight_before": result.watertight_before,
                "watertight_after": result.watertight_after,
                "operations_performed": result.operations_performed,
                "message": result.message,
                "error": result.error,
            }, indent=2)
        except Exception as e:
            logger.exception("remove_degenerate failed")
            return json.dumps({"success": False, "error": f"Remove degenerate error: {e}"})

    @mcp.tool()
    async def merge_vertices_tool(input_path: str, output_path: str) -> str:
        """Merge duplicate vertices to clean mesh topology.

        Some mesh formats (especially OBJ) may store duplicate vertex positions.
        This operation merges vertices at the same position, which reduces
        file size and improves mesh topology for downstream operations.

        Args:
            input_path: Path to the input mesh file.
            output_path: Path for the mesh with merged vertices.

        Returns:
            JSON string with merge results including vertex counts before/after
            and number of duplicates removed.
        """
        try:
            result = merge_vertices(input_path, output_path)
            return json.dumps({
                "success": result.success,
                "input_path": result.input_path,
                "output_path": result.output_path,
                "original_triangles": result.original_triangles,
                "repaired_triangles": result.repaired_triangles,
                "watertight_before": result.watertight_before,
                "watertight_after": result.watertight_after,
                "operations_performed": result.operations_performed,
                "message": result.message,
                "error": result.error,
            }, indent=2)
        except Exception as e:
            logger.exception("merge_vertices failed")
            return json.dumps({"success": False, "error": f"Merge vertices error: {e}"})
