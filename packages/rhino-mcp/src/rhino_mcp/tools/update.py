"""Curated, parameter-validated Rhino operations.

Thin named wrappers around common rhino_execute snippets, for the recipes
expected to get reused constantly (the STL-cleanup pipeline in particular),
so they don't need to be hand-written from scratch each time.
"""
import json

from rhino_mcp.api.connection import get_connection, RhinoConnectionError

_OPERATIONS = {
    "import_mesh",
    "export",
    "mesh_to_subd",
    "convert_to_nurbs",
    "silhouette_to_curve",
    "extrude_curve",
    "scale",
    "boolean_union",
    "boolean_diff",
}


def register_update_tools(mcp):
    @mcp.tool()
    def rhino_update(
        operation: str,
        path: str = "",
        format: str = "step",
        object_id: str = "",
        object_ids: list[str] | None = None,
        distance: float = 0.0,
        factor: float = 1.0,
        base_point: list[float] | None = None,
        direction: list[float] | None = None,
    ) -> str:
        """Run a curated, named Rhino operation.

        Args:
            operation: One of:
                - "import_mesh" (path) - import a mesh file (stl/obj/etc.)
                - "export" (path, format: step/3dm/stl) - export the active document
                - "mesh_to_subd" (object_id) - convert a mesh to a SubD
                - "convert_to_nurbs" (object_id) - convert a SubD/mesh to NURBS
                - "silhouette_to_curve" (object_id, direction) - extract an outline
                  curve from a flat/prismatic piece, viewed along direction
                - "extrude_curve" (object_id, distance) - extrude a curve into a solid
                - "scale" (object_id, factor, base_point) - uniform scale about base_point
                - "boolean_union" (object_ids) - union multiple solids
                - "boolean_diff" (object_ids) - subtract object_ids[1:] from object_ids[0]
            path: File path for import_mesh/export
            format: Export format for "export" - "step", "3dm", or "stl"
            object_id: Target object id for single-object operations
            object_ids: Target object ids for boolean operations
            distance: Extrusion distance for "extrude_curve"
            factor: Scale factor for "scale"
            base_point: [x, y, z] scale origin for "scale" (default: object's bounding box center)
            direction: [x, y, z] projection direction for "silhouette_to_curve" (default: world Z)
        """
        if operation not in _OPERATIONS:
            return f"Error: unknown operation '{operation}'. Must be one of {sorted(_OPERATIONS)}"

        params = {
            "path": path,
            "format": format,
            "object_id": object_id,
            "object_ids": object_ids or [],
            "distance": distance,
            "factor": factor,
            "base_point": base_point,
            "direction": direction,
        }

        try:
            conn = get_connection()
            result = conn.update(operation, params)
            return json.dumps(result, indent=2)
        except RhinoConnectionError as e:
            return f"Error: {e}"
