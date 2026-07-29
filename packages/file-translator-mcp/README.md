# file-translator-mcp

**Model Context Protocol (MCP) server for CAD file format translation and conversion.**

This server handles conversions between common CAD file formats — STL, STEP, IGES, OBJ, PLY, 3MF, and DXF — with automatic format detection, mesh analysis, and mesh repair tools. The primary pain point it solves is **STL → STEP conversion** (mesh to B-rep surface reconstruction), which is essential for moving geometry from 3D scanning/3D printing workflows into parametric CAD environments.

---

## How It Works — Architecture

file-translator-mcp is a standalone Python MCP server that uses **trimesh** and **cadquery** to perform file format conversions entirely locally. No cloud services or external CAD applications are required.

```
┌─────────────────┐    Voice/AI    ┌──────────────────────┐    stdio     ┌───────────────┐
│  MCP Commander  │◄──────────────►│  file-translator-mcp │◄────────────►│  LLM (Hermes) │
│  Core OS        │                │  (MCP cartridge)     │              │  / Claude     │
└─────────────────┘                └──────────┬───────────┘              └───────────────┘
                                             │
                                    ┌────────┴──────────┐
                                    │  Conversion Engine │
                                    │  ┌──────────────┐ │
                                    │  │ Format Detect │ │
                                    │  ├──────────────┤ │
                                    │  │ Mesh Analysis │ │
                                    │  ├──────────────┤ │
                                    │  │ Mesh Repair   │ │
                                    │  ├──────────────┤ │
                                    │  │ STL→STEP      │ │
                                    │  │  Strategy 1:  │ │
                                    │  │  Trimesh/OCCT │ │
                                    │  │  Strategy 2:  │ │
                                    │  │  CadQuery M2S │ │
                                    │  │  Strategy 3:  │ │
                                    │  │  Convex Hull  │ │
                                    │  │  Strategy 4:  │ │
                                    │  │  Voxelized    │ │
                                    │  └──────────────┘ │
                                    └───────────────────┘
                                             │
                              ┌──────────────┼──────────────┐
                              │              │              │
                        ┌─────┴─────┐ ┌────┴────┐ ┌──────┴──────┐
                        │  trimesh  │ │ cadquery│ │   numpy     │
                        │  (mesh I/O│ │ (solid  │ │  (geometry │
                        │  + repair)│ │  recon) │ │  + math)   │
                        └───────────┘ └─────────┘ └────────────┘
```

**Communication flow:**
1. You speak or type: *"Convert bracket.stl to STEP format"*
2. LLM generates MCP tool call: `analyze_mesh("bracket.stl")` to check quality
3. If mesh has issues, LLM calls: `repair_mesh("bracket.stl", "bracket_fixed.stl")`
4. LLM calls: `stl_to_step("bracket_fixed.stl", "bracket.step")`
5. Conversion engine tries trimesh→cadquery→convex_hull strategies
6. Result JSON with quality assessment flows back through the chain

---

## STL → STEP Conversion: The Hard Problem

STL files contain raw triangle meshes — they have **no topology, no curves, no surfaces**. Converting to STEP (B-rep) requires *surface reconstruction*, which is fundamentally an ill-posed problem.

**What this cartridge does:**
1. **Trimesh + OpenCASCADE** (best quality): Uses trimesh's native STEP export which calls OpenCASCADE to build B-rep surfaces from the mesh. Works well for watertight, manifold meshes.
2. **CadQuery mesh-to-solid**: Uses CadQuery's `Mesh.makeMesh()` to build a proper solid from the triangle data. Better for complex but well-formed meshes.
3. **Convex hull fallback**: For non-watertight or badly broken meshes, creates a convex approximation. The shape changes but you get a valid STEP file.
4. **Voxelized fallback**: Converts to voxels then back to mesh, creating a blocky but watertight result.

**Important limitations:**
- The STEP output will **never** have the smooth curves and exact dimensions of a native CAD model
- Non-watertight meshes produce approximate results
- Large meshes (>1M triangles) may need simplification first
- Organic/scan meshes convert with lower quality than mechanical parts

---

## Prerequisites

- **Python 3.10+** (3.11 or 3.12 recommended)
- **pip** for package installation
- **OpenCASCADE** (installed automatically with `cadquery` or via system packages)
- Optional: **ezdxf** for DXF support

---

## Setup — Step by Step

### Step 1: Install the MCP Cartridge

```bash
cd /path/to/mcp-commander-cad

# Install the file-translator MCP cartridge
pip install -e packages/file-translator-mcp
```

Dependencies installed automatically:
- `mcp>=1.0.0` — Model Context Protocol Python SDK (FastMCP)
- `trimesh>=4.0.0` — Mesh I/O, analysis, and repair library
- `numpy>=1.24.0` — Numerical computing (geometry operations)
- `cadquery>=2.0.0` — CAD kernel for B-rep operations
- `pydantic>=2.0.0` — Data validation and serialization

**For DXF support (optional):**
```bash
pip install ezdxf
```

**For OpenCASCADE (if not installed via cadquery):**

| OS | Install Command |
|---|---|
| **macOS** | `brew install opencascade` |
| **Ubuntu/Debian** | `sudo apt install liboce-*-dev` |
| **Windows** | Install via conda: `conda install -c conda-forge cadquery-oocc` |

### Step 2: Mount the Cartridge in MCP Commander

```bash
# From the mcp-commander-cad root
node core/src/cli.js mount file-translator-mcp
```

### Step 3: Verify Everything Works

```bash
# Test format detection
python -c "
from file_translator_mcp.api.converter import detect_format, get_file_info
d = detect_format('test.stl')
print(f'Format: {d.format}, Confidence: {d.confidence}, Encoding: {d.encoding}')

info = get_file_info('test.stl')
print(f'Size: {info.size_human}, Triangles: {info.triangle_count}')
"

# Test mesh analysis
python -c "
from file_translator_mcp.api.converter import analyze_mesh
a = analyze_mesh('test.stl')
print(f'Triangles: {a.triangle_count}, Watertight: {a.watertight}')
print(f'Volume: {a.volume}, Surface Area: {a.surface_area}')
"
```

### Step 4: Use It

Run MCP Commander in voice or text mode:

```bash
# Voice mode (with microphone)
node core/src/cli.js run --voice

# Text mode (stdin)
node core/src/cli.js run --text
```

Or run the MCP cartridge standalone (for Claude Desktop, Cursor, etc.):

```bash
file-translator-mcp
```

**Claude Desktop config** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "file-translator": {
      "command": "file-translator-mcp",
      "args": []
    }
  }
}
```

---

## Supported Conversions

### Conversion Matrix

| From → To | STL | STEP | IGES | OBJ | PLY | 3MF | DXF |
|---|---|---|---|---|---|---|---|
| **STL** | — | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| **STEP** | ✅ | — | ✅ | — | — | — | — |
| **IGES** | ✅ | ✅ | — | — | — | — | — |
| **OBJ** | ✅ | ✅ | — | — | — | — | — |
| **PLY** | ✅ | — | — | — | — | — | — |
| **3MF** | — | — | — | — | — | — | — |
| **DXF** | ✅ | — | — | — | — | — | — |

---

## Available Tools — 20 Total

### Conversion Tools (12 tools)

| Tool | Description |
|---|---|
| `convert_file` | Convert between CAD file formats (STL, STEP, IGES, OBJ, PLY, 3MF, DXF) |
| `stl_to_step` | Convert STL mesh to STEP B-rep with multi-strategy surface reconstruction |
| `stl_to_iges` | Convert STL mesh to IGES format |
| `stl_to_obj` | Convert STL to OBJ with computed normals |
| `step_to_stl` | Convert STEP B-rep to STL mesh with tessellation control |
| `step_to_iges` | Convert STEP to IGES (B-rep to B-rep) |
| `iges_to_step` | Convert IGES to STEP (B-rep to B-rep) |
| `iges_to_stl` | Convert IGES B-rep to STL mesh |
| `obj_to_stl` | Convert OBJ to STL |
| `obj_to_step` | Convert OBJ mesh to STEP B-rep |
| `ply_to_stl` | Convert PLY (mesh or point cloud) to STL |
| `batch_convert` | Convert multiple files to a target format in batch |

### Analysis Tools (3 tools)

| Tool | Description |
|---|---|
| `analyze_mesh` | Analyze mesh: triangles, volume, surface area, watertight status, bounding box |
| `detect_format` | Auto-detect file format from header bytes (magic byte detection) |
| `get_file_info` | Get file size, format, encoding, triangle count |

### Repair Tools (6 tools)

| Tool | Description |
|---|---|
| `repair_mesh` | Full repair: degenerate removal, duplicate removal, hole filling, normals, vertex merge |
| `simplify_mesh` | Reduce triangle count via quadric decimation while preserving shape |
| `fill_holes` | Fill holes in non-watertight meshes |
| `make_watertight` | Ensure mesh is watertight (fill, crumble, or wrap strategies) |
| `remove_degenerate` | Remove degenerate/zero-area triangles |
| `merge_vertices` | Merge duplicate vertices to clean topology |

---

## Typical Workflow: STL to STEP

The recommended workflow for converting STL files to STEP:

```
1. analyze_mesh("part.stl")           → Check watertight, triangle count
2. get_file_info("part.stl")         → Check file size and encoding
3. repair_mesh("part.stl",           → Fix degeneracies and holes
              "part_repaired.stl")
4. simplify_mesh("part_repaired.stl",→ Reduce if >500K triangles
                "part_simple.stl",
                target_faces=50000)
5. make_watertight("part_simple.stl",→ Ensure closed mesh
                  "part_closed.stl")
6. stl_to_step("part_closed.stl",    → Convert with multi-strategy
              "part.step")
```

---

## Voice Command Examples

Once running, you can say things like:

- **"Convert bracket.stl to STEP format"**
- **"Convert all the STL files in the models folder to OBJ"**
- **"Analyze the mesh quality of scan_data.stl"**
- **"What format is this file? Check models/unknown_part.igs"**
- **"Repair the mesh in broken_part.stl and save as fixed_part.stl"**
- **"Simplify this mesh to 20,000 triangles before converting"**
- **"Make this scan mesh watertight for STEP conversion"**
- **"Convert engine.step to STL for 3D printing"**
- **"Check if the mesh is watertight before converting to IGES"**
- **"Batch convert all PLY files in the scan_data folder to STL"**

---

## Troubleshooting

### "OpenCASCADE not available" when converting STL to STEP
- Install OpenCASCADE: `brew install opencascade` (macOS) or `conda install -c conda-forge opencascade`
- Or install cadquery which bundles OpenCASCADE: `pip install cadquery`
- The convex_hull method will work without OpenCASCADE as a fallback

### "Cannot detect input format"
- Ensure the file has the correct extension (.stl, .step, .iges, .obj, .ply)
- For ambiguous files, try renaming with the correct extension

### STL to STEP produces poor quality
- Run `analyze_mesh` first to check if the mesh is watertight
- Non-watertight meshes produce approximate results — this is a fundamental limitation
- Try `repair_mesh` → `make_watertight` before conversion
- For organic/scan data, consider simplifying to reduce noise

### Memory errors with large meshes
- Use `simplify_mesh` to reduce triangle count before conversion
- Target 50,000–100,000 faces for most conversion operations
- Very large files (>100MB) may need to be split

### DXF conversion fails
- Install ezdxf: `pip install ezdxf`
- Only 3D mesh DXF entities (MESH, POLYFACE) are supported
- 2D DXF drawings cannot be converted to STL

---

## Project Structure

```
file-translator-mcp/
├── pyproject.toml                      # Package configuration (hatchling)
├── cartridge.json                      # MCP Commander cartridge manifest
├── README.md                           # This file
└── src/
    └── file_translator_mcp/
        ├── __init__.py                 # Package version
        ├── server.py                   # FastMCP server entry point
        ├── api/
        │   ├── __init__.py
        │   ├── models.py              # Pydantic data models
        │   └── converter.py            # Core conversion engine (the heavy lifter)
        └── tools/
            ├── __init__.py
            ├── convert.py              # 12 conversion tools
            ├── analyze.py              # 3 analysis tools
            └── repair.py               # 6 repair tools
```

---

## License

MIT
