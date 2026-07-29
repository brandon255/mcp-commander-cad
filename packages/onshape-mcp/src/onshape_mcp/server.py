"""Onshape MCP server entry point.

Creates a ``FastMCP`` server named ``onshape-mcp``, registers all tool
modules (sketch, features, …), and starts the stdio transport so the
cartridge can be driven by any MCP-compatible host (Claude Desktop,
mcp-commander, etc.).

Usage::

    python -m onshape_mcp.server
    # or via the console_scripts entry point:
    onshape-mcp
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from onshape_mcp.tools.assembly import register_assembly_tools
from onshape_mcp.tools.drawing import register_drawing_tools
from onshape_mcp.tools.features import register_feature_tools
from onshape_mcp.tools.import_export import register_import_export_tools
from onshape_mcp.tools.sketch import register_sketch_tools

mcp = FastMCP("onshape-mcp")

# Register all tool groups ------------------------------------------------
register_sketch_tools(mcp)
register_feature_tools(mcp)
register_import_export_tools(mcp)
register_drawing_tools(mcp)
register_assembly_tools(mcp)


def main() -> None:
    """Run the Onshape MCP server on the default stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
