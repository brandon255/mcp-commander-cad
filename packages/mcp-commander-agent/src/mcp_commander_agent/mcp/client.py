"""MCP client manager and individual server client using the official MCP SDK."""

from __future__ import annotations

import asyncio
import logging
import shutil
from dataclasses import dataclass, field
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..config import MCPServerConfig

logger = logging.getLogger(__name__)


@dataclass
class ToolInfo:
    """Schema of an MCP tool, enriched with its server name."""
    name: str
    description: str
    server: str
    input_schema: dict[str, Any] = field(default_factory=dict)

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }

    def to_anthropic_tool(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class MCPClient:
    """Client for a single MCP server process (stdio transport)."""

    def __init__(self, server_name: str, config: MCPServerConfig) -> None:
        self.server_name = server_name
        self._config = config
        self._session: ClientSession | None = None
        self._stdio_context: Any = None
        self._session_context: Any = None
        self._connected = False
        self._tools: list[ToolInfo] = []

    async def connect(self) -> None:
        """Spawn the server process and initialize the MCP session."""
        executable = self._resolve_command(self._config.command)
        logger.info(
            "Connecting to MCP server '%s' via %s: %s",
            self.server_name, self._config.transport, executable,
        )
        server_params = StdioServerParameters(
            command=executable,
            args=self._config.args,
            env={**self._config.env},
        )
        self._stdio_context = stdio_client(server_params)
        read_stream, write_stream = await self._stdio_context.__aenter__()
        self._session_context = ClientSession(read_stream, write_stream)
        self._session = await self._session_context.__aenter__()
        await self._session.initialize()
        self._connected = True
        self._tools = await self.list_tools()
        logger.info(
            "'%s' connected -- %d tools available.",
            self.server_name, len(self._tools),
        )

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> str:
        if not self._connected or self._session is None:
            raise RuntimeError(f"Not connected to server '{self.server_name}'.")
        logger.info("Calling %s.%s(%s)", self.server_name, tool_name, arguments)
        result = await self._session.call_tool(tool_name, arguments or {})
        text_parts: list[str] = []
        if hasattr(result, "content") and result.content:
            for item in result.content:
                if hasattr(item, "text"):
                    text_parts.append(item.text)
        output = "\n".join(text_parts) if text_parts else str(result)
        logger.info("Result from %s.%s: %s", self.server_name, tool_name, output[:200])
        return output

    async def list_tools(self) -> list[ToolInfo]:
        if not self._connected or self._session is None:
            return []
        result = await self._session.list_tools()
        tools: list[ToolInfo] = []
        for t in result.tools:
            tools.append(ToolInfo(
                name=t.name,
                description=t.description or "",
                server=self.server_name,
                input_schema=t.inputSchema if hasattr(t, "inputSchema") else {},
            ))
        return tools

    async def disconnect(self) -> None:
        logger.info("Disconnecting from '%s'...", self.server_name)
        try:
            if self._session_context is not None:
                await self._session_context.__aexit__(None, None, None)
            if self._stdio_context is not None:
                await self._stdio_context.__aexit__(None, None, None)
        except Exception as exc:
            logger.warning("Error disconnecting from '%s': %s", self.server_name, exc)
        finally:
            self._session = None
            self._session_context = None
            self._stdio_context = None
            self._connected = False
            self._tools = []

    @staticmethod
    def _resolve_command(cmd: str) -> str:
        resolved = shutil.which(cmd)
        if resolved:
            return resolved
        return cmd

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def tools(self) -> list[ToolInfo]:
        return list(self._tools)


class MCPClientManager:
    """Manages connections to multiple MCP server processes."""

    def __init__(self, servers_config: dict[str, MCPServerConfig]) -> None:
        self._servers_config = servers_config
        self._clients: dict[str, MCPClient] = {}

    async def connect_all(self) -> None:
        """Spawn and connect to every configured MCP server."""
        for name, cfg in self._servers_config.items():
            try:
                client = MCPClient(name, cfg)
                await client.connect()
                self._clients[name] = client
            except Exception as exc:
                logger.error(
                    "Failed to connect to MCP server '%s': %s", name, exc
                )

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> str:
        if server_name not in self._clients:
            raise KeyError(f"Unknown MCP server: {server_name!r}")
        return await self._clients[server_name].call_tool(tool_name, arguments)

    def get_tools(self) -> list[ToolInfo]:
        tools: list[ToolInfo] = []
        for client in self._clients.values():
            tools.extend(client.tools)
        return tools

    def get_client(self, server_name: str) -> MCPClient:
        if server_name not in self._clients:
            raise KeyError(f"Unknown MCP server: {server_name!r}")
        return self._clients[server_name]

    def list_servers(self) -> list[str]:
        return list(self._clients.keys())

    async def shutdown(self) -> None:
        tasks = [client.disconnect() for client in self._clients.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
        self._clients.clear()
        logger.info("All MCP servers disconnected.")
