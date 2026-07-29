# MCP Commander -- AI Agent for CAD Automation

MCP Commander is the AI agent orchestrator that coordinates voice input, intent parsing,
and MCP tool calls to both Solidworks and Fusion 360.

## Architecture

```
User Voice --> Whisper STT --> Text --> LLM Intent Parser --> MCP Client --> [Solidworks MCP | Fusion 360 MCP] --> CAD Action
                                                                        |
                                                                Status/Result --> TTS --> User Audio Feedback
```

### How It Works

1. **Listen** -- MCP Commander records your voice (microphone) or accepts typed commands.
2. **Transcribe** -- Speech is converted to text using OpenAI Whisper (via `faster-whisper`).
3. **Parse Intent** -- An LLM (OpenAI GPT-4o or Anthropic Claude) analyzes the text and selects
   the right MCP tool calls using function/tool-calling APIs.
4. **Execute** -- The selected tools are called on the appropriate CAD MCP server
   (Solidworks or Fusion 360) via the MCP stdio protocol.
5. **Respond** -- Results are summarized by the LLM and optionally spoken back via TTS.

## Features

- **Voice Control** -- Speak natural-language commands; MCP Commander listens, transcribes, and acts.
- **Multi-CAD Support** -- Routes commands to Solidworks or Fusion 360 based on context.
- **Intent Parsing** -- LLM-powered function calling selects and chains MCP tools.
- **MCP Protocol** -- Uses the official MCP Python SDK with stdio transport.
- **Pluggable TTS** -- Offline (pyttsx3), OpenAI, or Edge TTS backends.
- **Confirmation Prompt** -- Destructive operations require user confirmation.
- **Execution Logging** -- Every tool-call plan and result is logged to JSON-lines.

## Prerequisites

- **Python 3.10+**
- **OpenAI or Anthropic API key** -- set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in your environment.
- **Solidworks MCP server** (`solidworks-mcp`) on `PATH`.
- **Fusion 360 MCP server** (`fusion360-mcp`) on `PATH`.
- **Microphone** (for voice mode).

## Quick Start

```bash
cd packages/mcp-commander-agent
pip install -e .
```

### Run

```bash
# Voice mode
mcp-commander --voice

# Text mode
mcp-commander --text

# Debug logging
mcp-commander --text --debug

# Custom config
mcp-commander --config /path/to/config.yaml --text

# List available MCP tools
mcp-commander --list-tools
```

## Voice Command Examples

| Natural Language | Parsed Intent | Tool Calls |
|---|---|---|
| "Create a new sketch on the top plane" | New sketch on top plane | `create_sketch(plane="Top")` |
| "Draw a 50mm circle centered at the origin" | Add circle | `add_circle(center=[0,0], radius=25)` |
| "Extrude the sketch 20 millimeters" | Boss extrude | `extrude_sketch(depth=20, unit="mm")` |
| "Fillet all edges with a 3mm radius" | Apply fillet | `add_fillet(radius=3, edges="all")` |
| "Save as bracket_v2" | Save as | `save_as(name="bracket_v2")` |
| "What dimensions does this part have?" | Query | `get_part_dimensions()` |

## Configuration Reference

### mcp_servers

Each key is a server name.

| Field | Type | Default | Description |
|---|---|---|---|
| `command` | string | *(required)* | Executable name or path |
| `transport` | string | `"stdio"` | Transport type |
| `args` | list | `[]` | Additional arguments |
| `env` | dict | `{}` | Extra environment variables |

### voice

| Field | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `true` | Enable microphone input |
| `model` | string | `"base"` | Whisper model size |
| `language` | string | `"en"` | Language code or "auto" |
| `tts_enabled` | bool | `true` | Enable text-to-speech |
| `tts_backend` | string | `"pyttsx3"` | pyttsx3, openai, or edge |
| `vad_threshold` | float | `0.5` | VAD sensitivity |
| `silence_timeout` | float | `2.0` | Seconds of silence to stop |

### llm

| Field | Type | Default | Description |
|---|---|---|---|
| `provider` | string | `"openai"` | openai or anthropic |
| `model` | string | `"gpt-4o"` | Model name |
| `api_key_env` | string | `"OPENAI_API_KEY"` | Env var for API key |
| `base_url` | string/null | `null` | Custom API endpoint |
| `temperature` | float | `0.1` | Sampling temperature |
| `max_tokens` | int | `4096` | Max response tokens |

## Development

```bash
pip install -e .
mcp-commander --text --debug
mcp-commander --list-tools
```

### Project Structure

```
mcp-commander-agent/
  pyproject.toml
  README.md
  config/mcp_commander_config.yaml
  src/mcp_commander_agent/
    __init__.py
    main.py
    config.py
    utils.py
    agent/
      orchestrator.py
      intent_parser.py
    mcp/
      client.py
      router.py
    voice/
      stt.py
      tts.py
```

## License

MIT
