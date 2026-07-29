"""
Operations package for MCP Commander Cognitive Cartridge.

Each module implements one cognitive operation as an MCP tool.
"""

from mcp_commander_cognitive.operations.divergent import divergent_thinking
from mcp_commander_cognitive.operations.convergent import convergent_thinking
from mcp_commander_cognitive.operations.cross_domain import cross_domain_transfer
from mcp_commander_cognitive.operations.uncommon import uncommon_methods
from mcp_commander_cognitive.operations.pattern import pattern_recognition
from mcp_commander_cognitive.operations.compression import compression_thinking
from mcp_commander_cognitive.operations.spatial import spatial_reasoning
from mcp_commander_cognitive.operations.diagnostics import context_diagnostics
from mcp_commander_cognitive.operations.rationale import design_rationale

__all__ = [
    "divergent_thinking",
    "convergent_thinking",
    "cross_domain_transfer",
    "uncommon_methods",
    "pattern_recognition",
    "compression_thinking",
    "spatial_reasoning",
    "context_diagnostics",
    "design_rationale",
]
