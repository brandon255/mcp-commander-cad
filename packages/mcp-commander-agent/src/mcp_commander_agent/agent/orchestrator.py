"""Main orchestrator: voice/text -> intent -> MCP tool calls -> response."""

from __future__ import annotations

import asyncio
import logging
import sys

from rich.console import Console

from ..config import MCPCommanderConfig
from ..mcp.client import MCPClientManager
from ..mcp.router import ToolRouter
from ..utils import confirm_action, log_execution
from .intent_parser import ExecutionPlan, IntentParser
from ..voice.stt import SpeechToText, TranscriptionResult
from ..voice.tts import TextToSpeech

logger = logging.getLogger(__name__)
console = Console()


class MCPCommanderOrchestrator:
    """Coordinates voice input, intent parsing, and MCP tool execution."""

    def __init__(self, config: MCPCommanderConfig) -> None:
        self.config = config
        self.mcp_client = MCPClientManager(config.mcp_servers)
        self.intent_parser = IntentParser(config.llm)
        self.router: ToolRouter | None = None
        self.stt: SpeechToText | None = None
        self.tts: TextToSpeech | None = None

        if config.voice.enabled:
            self.stt = SpeechToText(
                model_size=config.voice.model,
                language=config.voice.language,
                vad_threshold=config.voice.vad_threshold,
                silence_timeout=config.voice.silence_timeout,
                sample_rate=config.voice.sample_rate,
                max_record_seconds=config.voice.max_record_seconds,
            )

        if config.voice.tts_enabled:
            self.tts = TextToSpeech(
                backend=config.voice.tts_backend,
                voice=config.voice.tts_voice,
            )

    async def startup(self) -> None:
        """Connect to all MCP servers and build the tool registry."""
        console.print("[bold cyan]MCP Commander[/bold cyan] \u2014 Starting MCP connections...")
        await self.mcp_client.connect_all()
        self.router = ToolRouter(self.mcp_client)
        tool_count = len(self.router.list_all_tools())
        server_count = len(self.mcp_client.list_servers())
        console.print(
            f"[green]Connected to {server_count} server(s) "
            f"with {tool_count} tool(s) available.[/green]"
        )
        for srv in self.mcp_client.list_servers():
            tools = self.router.get_tools_for_server(srv)
            console.print(f"  [dim]{srv}: {', '.join(t.name for t in tools)}[/dim]")

    async def shutdown(self) -> None:
        console.print("[yellow]Shutting down MCP Commander...[/yellow]")
        if self.tts:
            self.tts.cleanup()
        await self.mcp_client.shutdown()
        console.print("[green]Goodbye.[/green]")

    async def process_voice(self) -> str:
        """Record audio -> transcribe -> parse -> execute -> respond."""
        if self.stt is None:
            raise RuntimeError("Voice mode is not enabled.")
        console.print("[dim]Listening...[/dim]")
        audio = self.stt.listen()
        result: TranscriptionResult = self.stt.transcribe(audio)
        if not result.text:
            console.print("[yellow]No speech detected. Try again.[/yellow]")
            return ""
        console.print(f"[bold]{result.text}[/bold]")
        if result.confidence < 0.5:
            console.print(f"[dim]Confidence: {result.confidence:.0%} \u2014 may be inaccurate[/dim]")
        response = await self.process_text(result.text)
        if self.tts:
            self.tts.speak_async(response)
        return response

    async def process_text(self, user_input: str) -> str:
        """Parse text intent and execute MCP tool calls."""
        user_input = user_input.strip()
        if not user_input:
            return ""

        tools = self.mcp_client.get_tools()
        if not tools:
            return "No MCP tools are available. Check server connections."

        console.print("[dim]Parsing intent...[/dim]")
        plan: ExecutionPlan = await self.intent_parser.parse(user_input, tools)

        if not plan.steps:
            return plan.reasoning or "I understood but no matching tool was found."

        console.print(f"[dim]Execution plan: {len(plan.steps)} step(s)[/dim]")
        for i, step in enumerate(plan.steps, 1):
            console.print(f"  {i}. [{step.server}] {step.tool}({step.arguments})")

        if plan.needs_confirmation:
            desc = "; ".join(s.description for s in plan.steps)
            if not confirm_action(desc):
                return "Action cancelled by user."

        results: list[str] = []
        for step in plan.steps:
            try:
                res = await self.mcp_client.call_tool(step.server, step.tool, step.arguments)
                results.append(res)
            except Exception as exc:
                logger.error("Tool call failed: %s", exc)
                results.append(f"ERROR: {exc}")

        log_execution(plan, results)
        response = await self.intent_parser.summarize(user_input, plan, results)
        return response

    async def interactive_loop(self) -> None:
        """Main interactive voice/text loop."""
        voice_mode = self.config.voice.enabled
        mode_label = "voice" if voice_mode else "text"
        console.print(
            f"\n[bold green]MCP Commander ready ({mode_label} mode). "
            "Ctrl+C to quit.[/bold green]\n"
        )

        while True:
            try:
                if voice_mode:
                    result = await self.process_voice()
                else:
                    user_input = input("MCP Commander > ")
                    result = await self.process_text(user_input)

                if result:
                    console.print(f"[bold cyan]MCP Commander:[/bold cyan] {result}")

            except KeyboardInterrupt:
                console.print()
                break
            except Exception as exc:
                logger.exception("Error in interactive loop")
                console.print(f"[red]Error: {exc}[/red]")
