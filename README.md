# MCP Commander CAD MCP — Voice-Controlled CAD Automation

MCP Commander is a monorepo containing **four packages** that work together to provide **voice-controlled CAD automation with vision and analysis** for Solidworks and Fusion 360 using the Model Context Protocol (MCP).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         MCP COMMANDER AGENT                        │
│  ┌──────────┐   ┌──────────────┐   ┌──────────────────┐   │
│  │  Microphone  │→│  Whisper STT │→│  LLM Intent Parse │   │
│  └──────────┘   └──────────────┘   └────────┬─────────┘   │
│                                              │             │
│  ┌──────────┐   ┌──────────────┐   ┌────────▼─────────┐   │
│  │  Speaker    │←│  TTS Engine  │←│  MCP Client       │   │
│  └──────────┘   └──────────────┘   └────┬────────┬────┘   │
│                                        │        │         │
└────────────────────────────────────────┼────────┼─────────┘
                                         │        │
                  ┌──────────────────────┼────────┼──────────┐
                  │                      │        │          │
       ┌──────────▼──────────┐  ┌────────▼──┐  ┌─▼──────────────┐
       │  SOLIDWORKS MCP      │  │ FUSION360  │  │ MCP-COMMANDER-ANALYSIS │
       │  (COM / pywin32)     │  │ (REST)     │  │ (Vision/OCR/RAG) │
       │  82 creation tools   │  │ 78 tools   │  │ 11 analysis tools│
       └──────────┬──────────┘  └────────┬──┘  └─┬──────────────┘
                  │                      │        │
       ┌──────────▼──────────┐  ┌────────▼─┐    │ VLM (GPT-4o/Claude)
       │    Solidworks        │  │ Fusion 360│   │ Tesseract + EasyOCR
       │    (Windows)         │  │ (cross)   │   │ OpenCV (geometry)
       └──────────────────────┘  └──────────┘    │ FAISS + sentence-T
                                                  │ DFM rules + standards
                                                  └──────────────────
```

## Packages

| Package | Description | Tools | Language |
|---------|-------------|-------|----------|
| [solidworks-mcp](packages/solidworks-mcp/) | MCP server for Solidworks via COM API | 82 creation tools | Python |
| [fusion360-mcp](packages/fusion360-mcp/) | MCP server for Fusion 360 via REST API | 78 creation tools | Python |
| [mcp-commander-analysis](packages/mcp-commander-analysis/) | **NEW** — Vision, OCR, geometry, DFM, RAG tutorial search | 11 analysis tools | Python |
| [mcp-commander-agent](packages/mcp-commander-agent/) | AI orchestrator with voice, LLM, MCP client | N/A (client) | Python |

## What's New: The Analysis Layer

The original two CAD servers (`solidworks-mcp` + `fusion360-mcp`) provide **160 creation tools** for sketching, featuring, dimensioning, drawing, assembly, and sheet metal work. But they are **one-way remote controls** — you tell them what to make, they make it.

The new `mcp-commander-analysis` package adds the **eyes and brain**:

| Tool | Capability |
|---|---|
| `analyze_drawing_image` | VLM (GPT-4o / Claude Vision) sees a drawing, returns views/title-block/annotations/features/recommendations |
| `extract_dimensions_from_image` | Tesseract + EasyOCR pulls dims, tolerances, GD&T, surface finishes, weld symbols off a drawing |
| `recognize_features_in_sketch` | OpenCV detects lines, circles, arcs, rectangles, slots, patterns, symmetry |
| `validate_sketch_design` | Checks open profiles, over-constraints, duplicates, tiny edges, self-intersections |
| `check_manufacturability` | DFM rule engine for 6 processes (CNC mill/turn, injection molding, sheet metal, FDM/SLA 3D printing) |
| `search_cad_tutorials` | RAG over 25 seeded CAD tutorials with FAISS + sentence-transformers |
| `capture_screenshot` | Grabs a screenshot from Solidworks (COM) / Fusion 360 (REST) / desktop |

This enables a **two-way conversation**: the agent can *see* your drawing, *understand* it, *recommend* improvements, and *execute* changes — all through voice or text.

## How It Works

1. **Voice Input** — You speak a command like *"Create a 2-inch bore on the front face and add a counterbore hole wizard"* (requires: "Create a 2-inch bore on the front face and add a counterbore hole wizard"* via `faster-whisper` + `sounddevice`)
2. **Intent Parsing** — An LLM (OpenAI GPT-4o or Anthropic Claude) parses the transcription, selects the right MCP tools, and builds an execution plan
3. **Tool Execution** — The MCP client routes tool calls to the correct CAD server (Solidworks or Fusion 360)
4. **Result Feedback** — Results are summarized in natural language and optionally spoken back via TTS

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Solidworks** (for solidworks-mcp) — Windows only
- **Fusion 360** (for fusion360-mcp) — with API access enabled
- **OpenAI or Anthropic API key** (for the LLM intent parser)

### Installation

```bash
# Clone the monorepo
git clone <repo-url> mcp-commander-cad
cd mcp-commander-cad

# Install all packages in development mode
pip install -e packages/solidworks-mcp
pip install -e packages/fusion360-mcp
pip install -e packages/mcp-commander-agent
```

### Configuration

Edit `packages/mcp-commander-agent/config/mcp_commander_config.yaml`:

```yaml
llm:
  provider: "openai"        # or "anthropic"
  model: "gpt-4o"           # or "claude-3-5-sonnet-20241022"
  api_key_env: "OPENAI_API_KEY"  # set this environment variable

mcp_servers:
  solidworks:
    command: "solidworks-mcp"
    transport: "stdio"
  fusion360:
    command: "fusion360-mcp"
    transport: "stdio"

voice:
  enabled: true
  model: "base"             # whisper model size
  tts_enabled: true
```

### Running

```bash
# Voice mode (speak commands)
mcp-commander --voice

# Text mode (type commands)
mcp-commander --text

# Debug mode with verbose logging
mcp-commander --voice --debug
```

### Example Commands

| Voice Command | What MCP Commander Does |
|---------------|------------------|
| "Open bracket.sldprt" | Opens the Solidworks part file |
| "Extrude the sketch 25 millimeters" | Calls `extrude_boss` with 25mm depth |
| "Create a drawing with three standard views" | Creates drawing + front/top/right views |
| "Auto-dimension everything with bilateral ±0.05 tolerance" | Calls `auto_dim_sketch` + `set_dim_tolerance` |
| "Add a fillet to all edges, 3 millimeter radius" | Calls `fillet` with radius=3mm |
| "Create a section view through the center" | Calls `add_section_view` |

## MCP Tool Reference

### Solidworks MCP (60+ tools)

| Category | Tools | Examples |
|----------|-------|---------|
| Sketch | 14 | `create_sketch`, `sketch_line`, `sketch_circle`, `sketch_rectangle`, `sketch_arc`, `sketch_spline`, `sketch_slot`, `sketch_text`, `sketch_pattern`, `sketch_mirror`, `sketch_trim`, `sketch_offset`, `sketch_constraints`, `exit_sketch` |
| Features | 15 | `extrude_boss`, `extrude_cut`, `revolve_boss`, `revolve_cut`, `fillet`, `chamfer`, `hole_wizard`, `shell`, `draft`, `sweep`, `loft`, `mirror_feature`, `pattern_linear`, `pattern_circular`, `scale` |
| Drawing | 14 | `create_drawing`, `add_standard_views`, `add_isometric_view`, `add_section_view`, `add_detail_view`, `add_broken_view`, `set_sheet_format`, `add_weld_symbol`, `add_surface_finish`, `create_bom`, `add_balloon`, `add_centerline`, `export_drawing_pdf`, `export_drawing_dxf` |
| Dimensions | 10 | `auto_dim_sketch`, `add_smart_dim`, `add_ordinate_dim`, `add_baseline_dim`, `add_chain_dim`, `set_dim_tolerance`, `add_gdt`, `add_datum`, `set_dim_precision` |
| Assembly | 12 | `create_assembly`, `insert_component`, `add_mate_coincident`, `add_mate_concentric`, `add_mate_distance`, `add_mate_angle`, `add_mate_tangent`, `add_mate_lock`, `add_mate_advanced`, `explode_assembly`, `assembly_bom`, `check_interference` |
| Sheet Metal | 17 | `create_base_flange`, `add_edge_flange`, `add_miter_flange`, `add_tab`, `add_lofted_bend`, `add_hem`, `add_jog`, `add_fold`, `add_rip`, `add_gusset`, `flatten`, `fold_flat`, `set_bend_allowance`, `set_gauge_table`, `convert_to_sheet_metal`, `insert_dies` |

### Fusion 360 MCP (50+ tools)

| Category | Tools | Examples |
|----------|-------|---------|
| Sketch | 27 | `create_sketch`, `sketch_line`, `sketch_circle`, `sketch_arc`, `sketch_rectangle`, `sketch_polygon`, `sketch_ellipse`, `sketch_spline`, `sketch_slot`, `sketch_text`, `sketch_offset`, `sketch_project`, `sketch_trim`, `sketch_extend`, `sketch_mirror`, pattern tools, 9 constraint tools, `add_dimension` |
| Features | 19 | `extrude`, `revolve`, `loft`, `sweep`, `thicken`, `fillet`, `chamfer`, `shell`, `hole`, `thread`, `draft`, `pattern_rectangular`, `pattern_circular`, `mirror`, `combine`, `split_body`, `scale`, `create_component`, `create_joint_origin` |
| Drawing | 13 | `create_drawing`, `add_base_view`, `add_projected_view`, `add_section_view`, `add_detail_view`, `add_isometric_view`, `set_sheet_size`, `add_bom`, `add_balloon`, `add_centerline`, `export_pdf`, `export_dxf`, `add_title_block` |
| Dimensions | 9 | `add_linear_dim`, `add_angular_dim`, `add_radial_dim`, `add_diametric_dim`, `add_ordinate_dim`, `set_tolerance`, `set_precision`, `add_gdt`, `add_datum_feature` |
| Sheet Metal | 13 | `create_sheet_metal_component`, `create_base_flange`, `add_flange`, `add_contour_flange`, `add_hem`, `add_fold`, `add_bend`, `add_rip`, `add_relief`, `create_flat_pattern`, `set_bend_allowance`, `punch_tool`, `convert_to_sheet_metal` |

## Development

### Project Structure

```
mcp-commander-cad/
├── packages/
│   ├── solidworks-mcp/          # Solidworks MCP server
│   │   ├── src/solidworks_mcp/
│   │   │   ├── server.py        # FastMCP server entry point
│   │   │   ├── api/             # COM connection manager + models
│   │   │   └── tools/           # 6 tool modules (sketch, features, drawing, etc.)
│   │   └── pyproject.toml
│   ├── fusion360-mcp/           # Fusion 360 MCP server
│   │   ├── src/fusion360_mcp/
│   │   │   ├── server.py        # FastMCP server entry point
│   │   │   ├── api/             # REST connection manager + models
│   │   │   └── tools/           # 5 tool modules (sketch, features, drawing, etc.)
│   │   └── pyproject.toml
│   └── mcp-commander-agent/            # AI orchestrator
│       ├── src/mcp_commander_agent/
│       │   ├── main.py          # CLI entry point
│       │   ├── config.py        # YAML config loader
│       │   ├── voice/           # STT (Whisper) + TTS (pyttsx3/OpenAI/Edge)
│       │   ├── agent/           # Intent parser + orchestrator
│       │   ├── mcp/             # MCP client manager + tool router
│       │   └── utils.py         # Shared utilities
│       ├── config/
│       │   └── mcp_commander_config.yaml
│       └── pyproject.toml
├── README.md                     # This file
└── LICENSE                       # MIT
```

### Running Tests

```bash
# Run all tests
make test

# Run specific package tests
python -m pytest packages/solidworks-mcp/tests/
python -m pytest packages/fusion360-mcp/tests/
python -m pytest packages/mcp-commander-agent/tests/
```

### Adding New Tools

To add a new MCP tool to Solidworks:

1. Open `packages/solidworks-mcp/src/solidworks_mcp/tools/<category>.py`
2. Create a new async function decorated via the registration pattern
3. Add it to the `register_*_tools(mcp)` function
4. The tool will automatically appear in MCP Commander's tool registry

To add a new MCP tool to Fusion 360, follow the same pattern in `packages/fusion360-mcp/`.

## License

MIT — See [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-tool`)
3. Commit your changes
4. Push to the branch (`git push origin feature/my-tool`)
5. Open a Pull Request
