"""Main MCP server entry point for Fusion 360 automation.

Creates a ``FastMCP`` instance and registers all tool groups (sketch,
features, drawing, dimensions, sheet_metal).  The server communicates
with Fusion 360 over its local REST API via ``httpx``.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "fusion360",
    instructions=(
        "MCP server for Fusion 360 automation. Controls Fusion 360 via its "
        "Python REST API for sketching, features, drawings, and assembly "
        "operations. All dimensions are in centimeters unless otherwise noted."
    ),
)

from fusion360_mcp.tools.sketch import register_sketch_tools  # noqa: E402
from fusion360_mcp.tools.features import register_feature_tools  # noqa: E402
from fusion360_mcp.tools.drawing import register_drawing_tools  # noqa: E402
from fusion360_mcp.tools.dimensions import register_dimension_tools  # noqa: E402
from fusion360_mcp.tools.sheet_metal import register_sheet_metal_tools  # noqa: E402
from fusion360_mcp.tools.analysis import register_analysis_tools  # noqa: E402

register_sketch_tools(mcp)
register_feature_tools(mcp)
register_drawing_tools(mcp)
register_dimension_tools(mcp)
register_sheet_metal_tools(mcp)
register_analysis_tools(mcp)


def main() -> None:
    """Run the MCP server on stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
