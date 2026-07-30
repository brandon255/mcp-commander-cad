"""Arbitrary-code escape hatch for Rhino - the most important tool in this cartridge.

This exists precisely because the SolidWorks connector didn't have one: when a
named operation turns out to call a nonexistent or wrong-interface COM/API
method, there was no way to inspect or work around it without editing source
and restarting the whole MCP server. Here, the same class of problem can be
diagnosed and patched around live, from the calling side.
"""
import json

from rhino_mcp.api.connection import get_connection, RhinoConnectionError


def register_execute_tools(mcp):
    @mcp.tool()
    def rhino_execute(code: str) -> str:
        """Run a Python snippet inside the Rhino plugin's main-thread context.

        The snippet runs with `rhinoscriptsyntax as rs`, `scriptcontext as sc`,
        and `Rhino` already imported, and `sc.doc` set to the active document.
        Assign a JSON-serializable value to a variable named `result` to return
        it; otherwise only captured stdout is returned.

        Use this for one-off geometry math, custom conversions, or anything not
        yet wrapped as a named rhino_update operation - and to diagnose a named
        operation that's failing, by trying the underlying calls directly.

        Args:
            code: Python source to execute inside the bridge plugin.
        """
        try:
            conn = get_connection()
            result = conn.execute(code)
            return json.dumps(result, indent=2)
        except RhinoConnectionError as e:
            return f"Error: {e}"
