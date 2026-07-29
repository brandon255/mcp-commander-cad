"""Main MCP server entry point for CAD file format translation.

Creates a ``FastMCP`` instance and registers all tool groups (convert,
analyze, repair). This server handles CAD file format conversions between
STL, STEP, IGES, OBJ, PLY, 3MF, and DXF using trimesh and cadquery.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "file-translator",
    instructions=(
        "MCP server for CAD file format translation. Converts between STL, STEP, "
        "IGES, OBJ, PLY, 3MF, and DXF formats. Provides mesh analysis and repair "
        "tools. Supports both mesh-to-mesh and mesh-to-B-rep conversions. "
        "For STL to STEP conversion, multiple reconstruction strategies are attempted "
        "automatically. All file paths are resolved relative to the server's working "
        "directory or accepted as absolute paths."
    ),
)

from file_translator_mcp.tools.convert import register_convert_tools  # noqa: E402
from file_translator_mcp.tools.analyze import register_analyze_tools  # noqa: E402
from file_translator_mcp.tools.repair import register_repair_tools  # noqa: E402

register_convert_tools(mcp)
register_analyze_tools(mcp)
register_repair_tools(mcp)


def main() -> None:
    """Run the MCP server on stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
