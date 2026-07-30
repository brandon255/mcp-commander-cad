"""Connection diagnostics for the Rhino MCP bridge.

Built first, deliberately - this is the tool that would have saved the
SolidWorks connector debugging session if it had existed from day one.
"""
import json

from rhino_mcp.api.connection import get_connection, RhinoConnectionError


def register_diagnostics_tools(mcp):
    @mcp.tool()
    def rhino_connection_diagnostics() -> str:
        """Report the Rhino bridge connection state for debugging.

        Returns the plugin host process PID, Rhino version, listener status,
        active document name/path, and open document count. Use this to
        distinguish "Rhino not running" / "plugin not loaded" from "attached
        but no active document" before assuming any other tool works.
        """
        try:
            conn = get_connection()
            result = conn.diagnostics()
            return json.dumps(result, indent=2)
        except RhinoConnectionError as e:
            return json.dumps({"connected": False, "error": str(e)}, indent=2)
