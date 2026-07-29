"""LLM-powered intent parser that selects MCP tools via function calling."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from ..config import LLMConfig
from ..mcp.client import ToolInfo

logger = logging.getLogger(__name__)


@dataclass
class ExecutionStep:
    server: str
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class ExecutionPlan:
    steps: list[ExecutionStep] = field(default_factory=list)
    reasoning: str = ""
    needs_confirmation: bool = False


def _build_system_prompt(base: str, tools: list[ToolInfo]) -> str:
    tools_desc = ""
    for t in tools:
        tools_desc += f"- {t.name} (server: {t.server}): {t.description}\n"
        if t.input_schema:
            tools_desc += f"  Parameters: {json.dumps(t.input_schema)}\n"
    return f"""{base}

Available MCP tools:
{tools_desc}

Rules:
1. Select the appropriate tool(s) based on the user request.
2. For multi-step tasks, chain tool calls in the correct order.
3. Include clear, concise arguments.
4. If the intent is ambiguous, explain what you need clarified.
5. Flag destructive operations with needs_confirmation=true."""


class IntentParser:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._client: Any = None
        self._init_client()

    def _init_client(self) -> None:
        if self.config.provider == "openai":
            from openai import OpenAI
            self._client = OpenAI(
                api_key=os.environ.get(self.config.api_key_env, ""),
                base_url=self.config.base_url,
            )
        elif self.config.provider == "anthropic":
            from anthropic import Anthropic
            self._client = Anthropic(
                api_key=os.environ.get(self.config.api_key_env, ""),
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.provider!r}")
        logger.info("LLM client initialised (%s / %s)", self.config.provider, self.config.model)

    async def parse(self, user_input: str, available_tools: list[ToolInfo]) -> ExecutionPlan:
        system_prompt = _build_system_prompt(self.config.system_prompt, available_tools)
        if self.config.provider == "openai":
            openai_tools = [t.to_openai_tool() for t in available_tools]
            return await self._parse_openai(user_input, system_prompt, openai_tools)
        else:
            return await self._parse_anthropic(user_input, system_prompt, available_tools)

    async def _parse_openai(self, user_input: str, system_prompt: str, tools: list[dict]) -> ExecutionPlan:
        import asyncio
        response = await asyncio.to_thread(
            self._client.chat.completions.create,
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            tools=tools if tools else None,
            tool_choice="auto",
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        msg = response.choices[0].message
        return self._extract_plan(msg, tools)

    async def _parse_anthropic(self, user_input: str, system_prompt: str, tools: list[ToolInfo]) -> ExecutionPlan:
        import asyncio
        anth_tools = [t.to_anthropic_tool() for t in tools]
        response = await asyncio.to_thread(
            self._client.messages.create,
            model=self.config.model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_input}],
            tools=anth_tools if anth_tools else None,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        return self._extract_plan_anthropic(response, tools)

    def _extract_plan(self, message: Any, tools: list[dict]) -> ExecutionPlan:
        steps: list[ExecutionStep] = []
        needs_confirm = False
        reasoning = ""
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                fn = tc.function
                try:
                    args = json.loads(fn.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}
                server = self._resolve_server(fn.name, tools)
                steps.append(ExecutionStep(
                    server=server, tool=fn.name, arguments=args,
                    description=f"Call {fn.name} with {args}",
                ))
                if any(kw in fn.name.lower() for kw in ("delete", "remove", "clear", "close")):
                    needs_confirm = True
        text = getattr(message, "content", "") or ""
        if text and not steps:
            reasoning = text
        return ExecutionPlan(steps=steps, reasoning=reasoning, needs_confirmation=needs_confirm)

    def _extract_plan_anthropic(self, response: Any, tools: list[ToolInfo]) -> ExecutionPlan:
        steps: list[ExecutionStep] = []
        needs_confirm = False
        reasoning = ""
        for block in response.content:
            if block.type == "tool_use":
                try:
                    args = json.loads(json.dumps(block.input))
                except (json.JSONDecodeError, TypeError):
                    args = {}
                server = self._resolve_server_from_tools(block.name, tools)
                steps.append(ExecutionStep(
                    server=server, tool=block.name, arguments=args,
                    description=f"Call {block.name} with {args}",
                ))
                if any(kw in block.name.lower() for kw in ("delete", "remove", "clear", "close")):
                    needs_confirm = True
            elif block.type == "text":
                if not steps:
                    reasoning = block.text
        return ExecutionPlan(steps=steps, reasoning=reasoning, needs_confirmation=needs_confirm)

    @staticmethod
    def _resolve_server(tool_name: str, tools: list[dict]) -> str:
        for t in tools:
            fn = t.get("function", {})
            if fn.get("name") == tool_name:
                desc = fn.get("description", "")
                if "solidworks" in desc.lower() or "solidworks" in tool_name.lower():
                    return "solidworks"
                if "fusion" in desc.lower() or "fusion" in tool_name.lower():
                    return "fusion360"
                break
        return "solidworks"

    @staticmethod
    def _resolve_server_from_tools(tool_name: str, tools: list[ToolInfo]) -> str:
        for t in tools:
            if t.name == tool_name:
                return t.server
        return "solidworks"

    async def summarize(self, user_input: str, plan: ExecutionPlan, results: list[str]) -> str:
        if not plan.steps:
            return plan.reasoning or "I understood but could not determine a specific action."
        steps_text = ""
        for i, step in enumerate(plan.steps, 1):
            res = results[i - 1] if i - 1 < len(results) else "(no result)"
            steps_text += f"Step {i}: {step.tool}({step.arguments}) -> {res}\n"
        prompt = f"User asked: {user_input}\n\nActions taken:\n{steps_text}\n\nSummarize concisely what was done."
        import asyncio
        if self.config.provider == "openai":
            response = await asyncio.to_thread(
                self._client.chat.completions.create,
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self.config.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.config.temperature, max_tokens=512,
            )
            return response.choices[0].message.content or "Done."
        else:
            response = await asyncio.to_thread(
                self._client.messages.create,
                model=self.config.model,
                system=self.config.system_prompt,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512, temperature=self.config.temperature,
            )
            for block in response.content:
                if block.type == "text":
                    return block.text
            return "Done."
