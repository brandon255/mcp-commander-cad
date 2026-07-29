"""Tool routing and discovery across multiple MCP servers."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from .client import MCPClientManager, ToolInfo

logger = logging.getLogger(__name__)


@dataclass
class ToolMatch:
    tool: ToolInfo
    score: float


class ToolRouter:
    """Routes natural-language intents to the correct MCP server + tool."""

    def __init__(self, mcp_client: MCPClientManager) -> None:
        self._mcp_client = mcp_client
        self._registry: dict[str, ToolInfo] = {}
        self._server_tools: dict[str, list[ToolInfo]] = {}
        self._build_registry()

    def _build_registry(self) -> None:
        self._registry.clear()
        self._server_tools.clear()
        for tool in self._mcp_client.get_tools():
            self._registry[tool.name] = tool
            self._server_tools.setdefault(tool.server, []).append(tool)
        logger.info(
            "Tool registry built: %d tools from %d servers.",
            len(self._registry), len(self._server_tools),
        )

    def find_tool(self, tool_name: str) -> ToolInfo | None:
        if tool_name in self._registry:
            return self._registry[tool_name]
        for name, tool in self._registry.items():
            if name.lower() == tool_name.lower():
                return tool
        return None

    def search_tools(self, query: str, top_k: int = 5) -> list[ToolMatch]:
        q = query.lower()
        scored: list[ToolMatch] = []
        for tool in self._registry.values():
            name_score = SequenceMatcher(None, q, tool.name.lower()).ratio()
            desc_score = SequenceMatcher(None, q, tool.description.lower()).ratio()
            combined = max(name_score, desc_score)
            combined += self._keyword_bonus(q, tool.name + " " + tool.description)
            if combined > 0.0:
                scored.append(ToolMatch(tool=tool, score=combined))
        scored.sort(key=lambda m: m.score, reverse=True)
        return scored[:top_k]

    def get_tools_for_server(self, server: str) -> list[ToolInfo]:
        return list(self._server_tools.get(server, []))

    def list_all_tools(self) -> list[ToolInfo]:
        return list(self._registry.values())

    def server_for_tool(self, tool_name: str) -> str | None:
        tool = self.find_tool(tool_name)
        return tool.server if tool else None

    @staticmethod
    def _keyword_bonus(query: str, text: str, bonus: float = 0.1) -> float:
        score = 0.0
        query_words = set(re.findall(r"\w+", query))
        text_words = set(re.findall(r"\w+", text.lower()))
        for qw in query_words:
            if len(qw) < 3:
                continue
            for tw in text_words:
                if qw in tw or tw in qw:
                    score += bonus
        return score
