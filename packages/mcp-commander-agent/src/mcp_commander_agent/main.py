"""CLI entry point for MCP Commander Agent."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from rich.console import Console

from .agent.orchestrator import MCPCommanderOrchestrator
from .config import MCPCommanderConfig, load_config, setup_logging

console = Console()
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-commander",
        description="MCP Commander — AI Agent for CAD Automation via MCP",
    )
    parser.add_argument(
        "--config", "-c",
        default=None,
        help="Path to the YAML configuration file (default: config/mcp_commander_config.yaml)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--voice", "-v",
        action="store_true",
        default=None,
        help="Enable voice mode (microphone input + TTS output)",
    )
    group.add_argument(
        "--text", "-t",
        action="store_true",
        default=None,
        help="Enable text mode (interactive terminal input)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug-level logging",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List all available MCP tools and exit",
    )
    return parser


async def _run(config: MCPCommanderConfig, list_tools: bool = False) -> None:
    orchestrator = MCPCommanderOrchestrator(config)
    try:
        await orchestrator.startup()
        if list_tools:
            from .mcp.router import ToolRouter
            router = ToolRouter(orchestrator.mcp_client)
            console.print("[bold]Available MCP Tools:[/bold]\n")
            for srv in orchestrator.mcp_client.list_servers():
                tools = router.get_tools_for_server(srv)
                console.print(f"[cyan]{srv}[/cyan]")
                for t in tools:
                    console.print(f"  \u2022 {t.name}: {t.description}")
                console.print()
            return
        await orchestrator.interactive_loop()
    finally:
        await orchestrator.shutdown()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = load_config(args.config)

    if args.debug:
        config.logging.level = "DEBUG"
    if args.voice is True:
        config.voice.enabled = True
        config.voice.tts_enabled = True
    elif args.text is True:
        config.voice.enabled = False
        config.voice.tts_enabled = False

    setup_logging(config.logging)

    banner = r"""[bold cyan]
  _    _                 _
 | |  | |               | |
 | |__| | ___  _ __   __| | _____      __
 |  __  |/ _ \| '_ \ / _` |/ _ \ \ /\ / /
 | |  | | (_) | | | | (_| | (_) \ V  V /
 |_|  |_|\___/|_| |_|\__,_|\___/ \_/\_/
[/bold cyan]"""
    console.print(banner)
    console.print("[dim]AI Agent for CAD Automation via MCP[/dim]")

    try:
        asyncio.run(_run(config, list_tools=args.list_tools))
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        sys.exit(0)


if __name__ == "__main__":
    main()
