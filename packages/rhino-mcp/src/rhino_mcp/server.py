"""Main MCP server entry point for Rhino automation.

Creates a FastMCP instance and registers the four tools (diagnostics, read,
execute, update). The server itself does nothing to Rhino directly - it's a
thin stdio-to-HTTP relay to the RhinoMCPBridge plugin running inside Rhino
(see api/connection.py and ../bridge/RhinoMCPBridge.py).
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "rhino",
    instructions=(
        "MCP server for Rhino automation. Relays tool calls over local HTTP to "
        "a plugin (RhinoMCPBridge.py) running inside Rhino - call "
        "rhino_connection_diagnostics first if anything else fails, to check "
        "whether Rhino is running and the bridge plugin has been loaded."
    ),
)

from rhino_mcp.tools.diagnostics import register_diagnostics_tools  # noqa: E402
from rhino_mcp.tools.read import register_read_tools  # noqa: E402
from rhino_mcp.tools.execute import register_execute_tools  # noqa: E402
from rhino_mcp.tools.update import register_update_tools  # noqa: E402

register_diagnostics_tools(mcp)
register_read_tools(mcp)
register_execute_tools(mcp)
register_update_tools(mcp)


def main() -> None:
    """Run the MCP server on stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
