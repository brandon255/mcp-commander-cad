# mcp-commander-analysis

Vision-powered analysis layer for the MCP Commander CAD MCP monorepo.

Adds **11 MCP tools** that give the MCP Commander agent the ability to *see* drawings,
*understand* dimensions, *recognize* features, *validate* designs, *check*
manufacturability, and *search* tutorials — turning the existing Solidworks
and Fusion 360 servers into a two-way conversational system.

## Tools at a Glance

| Tool | Purpose |
|---|---|
| `analyze_drawing_image` | VLM (GPT-4o / Claude Vision) describes a drawing image — views, title block, features, recommendations |
| `describe_image` | Lightweight image description |
| `extract_dimensions_from_image` | Tesseract + EasyOCR extracts dims, tolerances, GD&T, surface finishes, weld symbols |
| `ocr_raw_text` | Low-level OCR — returns raw text blocks with positions |
| `recognize_features_in_sketch` | OpenCV detects lines, circles, arcs, rectangles, slots, patterns, symmetry |
| `detect_circles_in_image` | Focused circle/hole detection |
| `validate_sketch_design` | Checks open profiles, over-constraints, duplicates, tiny edges, self-intersections |
| `check_manufacturability` | DFM rule engine for CNC milling, turning, injection molding, sheet metal, 3D printing |
| `list_dfm_processes` | Lists available manufacturing processes and their rules |
| `search_cad_tutorials` | RAG (FAISS + sentence-transformers) over CAD tutorials |
| `add_tutorial_chunk` | Add new tutorial chunks at runtime |
| `get_tutorial_stats` | Knowledge base statistics |
| `capture_screenshot` | Grabs a screenshot from Solidworks (COM), Fusion 360 (REST), or desktop |
| `capture_solidworks_view` | Capture a specific named view from Solidworks |

## Architecture

```
                  ┌──────────────────────────────────────┐
                  │       mcp-commander-analysis MCP server      │
                  │        (FastMCP / stdio transport)    │
                  └──────────────────────────────────────┘
                                    │
       ┌───────────────┬────────────┼────────────┬──────────────────┐
       ▼               ▼            ▼            ▼                  ▼
 ┌──────────┐   ┌──────────┐  ┌──────────┐  ┌──────────┐    ┌────────────┐
 │  vision  │   │   ocr    │  │ geometry │  │ knowledge│    │ screenshot │
 │ GPT-4o / │   │Tesseract │  │ OpenCV   │  │ FAISS +  │    │ COM / REST │
 │ Claude   │   │ EasyOCR  │  │ Hough    │  │ sentence-│    │ / Pillow   │
 └──────────┘   └──────────┘  └──────────┘  │transform │    └────────────┘
                                             └──────────┘
                                                   │
                                            ┌─────────────┐
                                            │ knowledge/  │
                                            │  dfm_rules  │
                                            │  standards  │
                                            │  tutorials  │
                                            └─────────────┘
```

## Quick Start

```bash
# From the package directory
pip install -e .

# Run the MCP server (stdio transport)
mcp-commander-analysis

# Or via Python module
python -m mcp_commander_analysis.server
```

### Environment Variables

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Enable GPT-4o vision analysis |
| `ANTHROPIC_API_KEY` | Enable Claude 3.5 Sonnet vision analysis |
| `MCP_COMMANDER_EMBEDDING_MODEL` | Override sentence-transformer model (default `all-MiniLM-L6-v2`) |
| `MCP_COMMANDER_MODEL_CACHE_DIR` | Cache dir for embedding model |
| `FUSION_API_URL` | Fusion 360 REST API base URL (default `http://localhost:8080`) |
| `FUSION_API_TIMEOUT` | Fusion 360 API timeout seconds (default `10`) |

If neither `OPENAI_API_KEY` nor `ANTHROPIC_API_KEY` is set, vision tools
return a mock response — useful for development and testing.

## Tool Examples

### Analyze a Drawing Image

```python
# Via MCP client (or mcp-commander-agent voice command)
result = await client.call_tool("analyze_drawing_image", {
    "image_path": "/tmp/bracket_drawing.png"
})
# Returns: {summary, views, title_block, annotations, key_features, recommendations, confidence}
```

### Ask a Specific Question

```python
result = await client.call_tool("analyze_drawing_image", {
    "image_path": "/tmp/bracket_drawing.png",
    "question": "What is the tolerance on the mounting holes?"
})
# Returns: {answer: "M6 tapped hole, H7 tolerance, depth 15mm", ...}
```

### Extract Dimensions from a Scanned Drawing

```python
result = await client.call_tool("extract_dimensions_from_image", {
    "image_path": "/tmp/scan.png",
    "engine": "tesseract"
})
# Returns: {dimensions: [{value, unit, dimension_type, tolerance, ...}], gdt_symbols, ...}
```

### Check Manufacturability

```python
result = await client.call_tool("check_manufacturability", {
    "design_data": {
        "features": [
            {"type": "wall", "thickness": 0.3},  # Too thin!
            {"type": "hole", "diameter": 2.0, "depth": 10.0},
            {"type": "fillet", "radius": 0.5}
        ],
        "material": "aluminum_6061"
    },
    "process": "cnc_milling"
})
# Returns: {overall_score: 75, rule_results: [...], critical_issues: [...], recommendations: [...]}
```

### Search CAD Tutorials

```python
result = await client.call_tool("search_cad_tutorials", {
    "query": "how to create a lofted bend in sheet metal",
    "top_k": 3
})
# Returns: {results: [{title, content, score, related_tools}], suggested_tools: [...], summary}
```

### Capture + Analyze Workflow

```python
# 1. Capture a screenshot from Solidworks
screenshot = await client.call_tool("capture_screenshot", {"source": "solidworks"})

# 2. Analyze the screenshot
analysis = await client.call_tool("analyze_drawing_image", {
    "image_path": screenshot["image_path"]
})

# 3. Extract dimensions
dims = await client.call_tool("extract_dimensions_from_image", {
    "image_path": screenshot["image_path"]
})
```

## Knowledge Base

The package ships with three knowledge files in `src/mcp_commander_analysis/knowledge/`:

- **`dfm_rules.yaml`** — DFM rules for 6 manufacturing processes
  (CNC milling, CNC turning, injection molding, sheet metal, FDM 3D printing,
  SLA 3D printing). Each rule has a severity, threshold, and recommendation.
- **`standards.yaml`** — ASME Y14.5 and ISO 1101 GD&T symbols, sheet sizes,
  default tolerances, surface finish values, ISO fit classes.
- **`tutorials_index.json`** — Seeded CAD tutorial chunks (~24 tutorials)
  covering Solidworks and Fusion 360 features. Extend at runtime via
  `add_tutorial_chunk`.

## Dependencies

Heavy dependencies (installed via `pip install -e .`):

- `mcp` — Model Context Protocol SDK
- `openai` — GPT-4o vision API
- `anthropic` — Claude 3.5 Sonnet vision API
- `pytesseract` + `easyocr` — OCR engines
- `opencv-python-headless` — Geometric feature recognition
- `sentence-transformers` — Embedding model for RAG
- `faiss-cpu` — Vector similarity search
- `Pillow` — Image I/O
- `httpx` — HTTP client for Fusion 360 API
- `pywin32` — Windows COM API (for Solidworks screenshot; Windows only)

## License

MIT
