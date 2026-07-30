"""Query-only Rhino tools. No document mutation."""
import json

from rhino_mcp.api.connection import get_connection, RhinoConnectionError


def register_read_tools(mcp):
    @mcp.tool()
    def rhino_read(query: str, object_id: str = "", layer: str = "", object_type: str = "") -> str:
        """Query-only read from the active Rhino document. No mutation.

        Args:
            query: One of:
                - "document": name, path, modified/saved state, units, active layer
                - "objects": list objects, optionally filtered by layer/object_type,
                  each with id, type, bounding box, layer
                - "geometry": bounding box/dimensions for object_id (or current
                  selection if object_id is empty)
                - "screenshot": capture the active viewport
            object_id: Object id for the "geometry" query (empty = current selection)
            layer: Optional layer name filter for the "objects" query
            object_type: Optional type filter for the "objects" query (e.g. "mesh", "brep", "curve")
        """
        valid_queries = {"document", "objects", "geometry", "screenshot"}
        if query not in valid_queries:
            return f"Error: unknown query '{query}'. Must be one of {sorted(valid_queries)}"

        try:
            conn = get_connection()
            params = {}
            if query == "geometry":
                params["object_id"] = object_id
            elif query == "objects":
                if layer:
                    params["layer"] = layer
                if object_type:
                    params["object_type"] = object_type

            result = conn.read(query, params)
            return json.dumps(result, indent=2)
        except RhinoConnectionError as e:
            return f"Error: {e}"
