"""Configuration loading, validation, and defaults for MCP Commander Agent."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server connection."""

    command: str
    transport: str = "stdio"
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class VoiceConfig:
    """Voice input / output settings."""

    enabled: bool = True
    model: str = "base"
    language: str = "en"
    tts_enabled: bool = True
    tts_voice: str = "default"
    tts_backend: str = "pyttsx3"  # pyttsx3 | openai | edge
    sample_rate: int = 16000
    vad_threshold: float = 0.5
    silence_timeout: float = 2.0
    max_record_seconds: float = 30.0


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: str = "openai"  # openai | anthropic | local
    model: str = "gpt-4o"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str | None = None
    system_prompt: str = "You are MCP Commander, a CAD automation assistant."
    temperature: float = 0.1
    max_tokens: int = 4096

    @property
    def api_key(self) -> str:
        """Resolve the API key from the environment variable."""
        key = os.environ.get(self.api_key_env, "")
        if not key:
            raise ValueError(
                f"API key environment variable '{self.api_key_env}' is not set. "
                f"Please export {self.api_key_env}=your-key-here"
            )
        return key


@dataclass
class LoggingConfig:
    """Logging settings."""

    level: str = "INFO"
    file: str | None = None
    console: bool = True


@dataclass
class MCPCommanderConfig:
    """Top-level MCP Commander configuration."""

    mcp_servers: dict[str, MCPServerConfig] = field(default_factory=dict)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_SYSTEM_PROMPT = """You are MCP Commander, an AI assistant that controls CAD software (Solidworks and Fusion 360) via MCP tools.
The user gives you voice/text commands for engineering tasks. Parse their intent and call the appropriate MCP tools.
Always confirm what you're about to do before executing destructive operations.
Respond concisely with status updates."""

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "mcp_commander_config.yaml"


# ── Loaders ───────────────────────────────────────────────────────────────────


def _parse_mcp_servers(raw: dict[str, Any]) -> dict[str, MCPServerConfig]:
    """Parse the mcp_servers section of the YAML config."""
    servers: dict[str, MCPServerConfig] = {}
    for name, cfg in raw.items():
        if not isinstance(cfg, dict):
            logger.warning("Skipping invalid MCP server config for '%s'", name)
            continue
        servers[name] = MCPServerConfig(
            command=str(cfg.get("command", name)),
            transport=str(cfg.get("transport", "stdio")),
            args=[str(a) for a in cfg.get("args", [])],
            env={str(k): str(v) for k, v in cfg.get("env", {}).items()},
        )
    return servers


def _parse_voice(raw: dict[str, Any] | None) -> VoiceConfig:
    """Parse the voice section."""
    if raw is None:
        return VoiceConfig()
    return VoiceConfig(
        enabled=bool(raw.get("enabled", True)),
        model=str(raw.get("model", "base")),
        language=str(raw.get("language", "en")),
        tts_enabled=bool(raw.get("tts_enabled", True)),
        tts_voice=str(raw.get("tts_voice", "default")),
        tts_backend=str(raw.get("tts_backend", "pyttsx3")),
        sample_rate=int(raw.get("sample_rate", 16000)),
        vad_threshold=float(raw.get("vad_threshold", 0.5)),
        silence_timeout=float(raw.get("silence_timeout", 2.0)),
        max_record_seconds=float(raw.get("max_record_seconds", 30.0)),
    )


def _parse_llm(raw: dict[str, Any] | None) -> LLMConfig:
    """Parse the llm section."""
    if raw is None:
        return LLMConfig(system_prompt=DEFAULT_SYSTEM_PROMPT)
    return LLMConfig(
        provider=str(raw.get("provider", "openai")),
        model=str(raw.get("model", "gpt-4o")),
        api_key_env=str(raw.get("api_key_env", "OPENAI_API_KEY")),
        base_url=raw.get("base_url") if raw.get("base_url") is not None else None,
        system_prompt=str(raw.get("system_prompt", DEFAULT_SYSTEM_PROMPT)),
        temperature=float(raw.get("temperature", 0.1)),
        max_tokens=int(raw.get("max_tokens", 4096)),
    )


def _parse_logging(raw: dict[str, Any] | None) -> LoggingConfig:
    """Parse the logging section."""
    if raw is None:
        return LoggingConfig()
    return LoggingConfig(
        level=str(raw.get("level", "INFO")).upper(),
        file=raw.get("file") if raw.get("file") is not None else None,
        console=bool(raw.get("console", True)),
    )


def load_config(path: str | Path | None = None) -> MCPCommanderConfig:
    """Load and validate MCP Commander configuration from a YAML file.

    Args:
        path: Path to the YAML config file. If *None*, attempts to load
              from the default location (``config/mcp_commander_config.yaml``
              relative to the package root).

    Returns:
        A fully-populated :class:`MCPCommanderConfig` instance.
    """
    if path is None:
        path = DEFAULT_CONFIG_PATH
    path = Path(path).resolve()

    if path.is_file():
        logger.info("Loading configuration from %s", path)
        with open(path, "r", encoding="utf-8") as fh:
            raw: dict[str, Any] = yaml.safe_load(fh) or {}
    else:
        logger.warning(
            "Config file not found at %s — using defaults.", path
        )
        raw = {}

    return MCPCommanderConfig(
        mcp_servers=_parse_mcp_servers(raw.get("mcp_servers", {})),
        voice=_parse_voice(raw.get("voice")),
        llm=_parse_llm(raw.get("llm")),
        logging=_parse_logging(raw.get("logging")),
    )


def setup_logging(config: LoggingConfig) -> None:
    """Configure Python logging from a :class:`LoggingConfig`."""
    handlers: list[logging.Handler] = []

    if config.console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        handlers.append(console_handler)

    if config.file:
        log_path = Path(config.file).resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=getattr(logging, config.level, logging.INFO),
        handlers=handlers,
        force=True,
    )
