from mcp.server.fastmcp import FastMCP

mcp = FastMCP("solidworks", instructions="MCP server for Solidworks automation via COM API.")

from solidworks_mcp.tools.sketch import register_sketch_tools
from solidworks_mcp.tools.features import register_feature_tools
from solidworks_mcp.tools.drawing import register_drawing_tools
from solidworks_mcp.tools.assembly import register_assembly_tools
from solidworks_mcp.tools.dimensions import register_dimension_tools
from solidworks_mcp.tools.sheet_metal import register_sheet_metal_tools
from solidworks_mcp.tools.analysis import register_analysis_tools  # noqa: E402
from solidworks_mcp.tools.surfacing import register_surfacing_tools  # noqa: E402
from solidworks_mcp.tools.materials_export import register_materials_export_tools  # noqa: E402
from solidworks_mcp.tools.configurations import register_configuration_tools  # noqa: E402

register_sketch_tools(mcp)
register_feature_tools(mcp)
register_drawing_tools(mcp)
register_assembly_tools(mcp)
register_dimension_tools(mcp)
register_sheet_metal_tools(mcp)
register_analysis_tools(mcp)
register_surfacing_tools(mcp)
register_materials_export_tools(mcp)
register_configuration_tools(mcp)

def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
