"""Main MCP server entry point for MCP Commander Analysis.

Provides AI-powered tools for engineering drawing understanding:
vision analysis, OCR dimension extraction, feature recognition,
design validation, and CAD knowledge search.
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "mcp-commander-analysis",
    instructions=(
        "AI-powered analysis tools for engineering drawings. Analyzes drawing "
        "images via VLM vision, extracts dimensions via OCR, recognizes geometric "
        "features, validates designs for manufacturability, and searches CAD "
        "knowledge bases. Works with Solidworks and Fusion 360 workflows."
    ),
)

from mcp_commander_analysis.tools.vision import register_vision_tools  # noqa: E402
from mcp_commander_analysis.tools.ocr import register_ocr_tools  # noqa: E402
from mcp_commander_analysis.tools.validation import register_validation_tools  # noqa: E402
from mcp_commander_analysis.tools.knowledge import register_knowledge_tools  # noqa: E402

register_vision_tools(mcp)
register_ocr_tools(mcp)
register_validation_tools(mcp)
register_knowledge_tools(mcp)


def main() -> None:
    """Run the MCP analysis server on stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
