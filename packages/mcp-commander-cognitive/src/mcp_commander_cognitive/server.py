"""
MCP Commander Cognitive Server.

FastMCP server providing 9 cognitive operations for engineering design
intelligence. Each operation is registered as an MCP tool and runs as a
background cognitive cartridge within the MCP Commander ecosystem.

Operations:
    1. divergent_thinking   - Generate alternative design approaches
    2. convergent_thinking   - Evaluate and rank design alternatives
    3. cross_domain_transfer - Transfer solutions across industry domains
    4. uncommon_methods      - Suggest non-traditional manufacturing methods
    5. pattern_recognition   - Identify recurring design inefficiencies
    6. compression_thinking  - Simplify over-engineered assemblies
    7. spatial_reasoning     - Infer 3D spatial relationships from text
    8. context_diagnostics   - Identify missing constraints and gaps
    9. design_rationale      - Capture and retrieve design rationale
"""

from mcp.server.fastmcp import FastMCP

from mcp_commander_cognitive.operations.divergent import divergent_thinking
from mcp_commander_cognitive.operations.convergent import convergent_thinking
from mcp_commander_cognitive.operations.cross_domain import cross_domain_transfer
from mcp_commander_cognitive.operations.uncommon import uncommon_methods
from mcp_commander_cognitive.operations.pattern import pattern_recognition
from mcp_commander_cognitive.operations.compression import compression_thinking
from mcp_commander_cognitive.operations.spatial import spatial_reasoning
from mcp_commander_cognitive.operations.diagnostics import context_diagnostics
from mcp_commander_cognitive.operations.rationale import design_rationale

# ---------------------------------------------------------------------------
# FastMCP Server Instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="mcp-commander-cognitive",
    instructions=(
        "Cognitive architecture cartridge for engineering design intelligence. "
        "Provides 9 background operations covering divergent/convergent thinking, "
        "cross-domain transfer, uncommon manufacturing methods, pattern recognition, "
        "compression thinking, spatial reasoning, context diagnostics, and "
        "design rationale capture. Each tool operates independently and returns "
        "structured results suitable for downstream CAD/CAE integration."
    ),
)

# ---------------------------------------------------------------------------
# Register all cognitive operations as MCP tools
# ---------------------------------------------------------------------------
mcp.tool()(divergent_thinking)
mcp.tool()(convergent_thinking)
mcp.tool()(cross_domain_transfer)
mcp.tool()(uncommon_methods)
mcp.tool()(pattern_recognition)
mcp.tool()(compression_thinking)
mcp.tool()(spatial_reasoning)
mcp.tool()(context_diagnostics)
mcp.tool()(design_rationale)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    """Run the cognitive cartridge MCP server with stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
