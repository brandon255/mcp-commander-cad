# fusion360-mcp

**Model Context Protocol (MCP) server for Autodesk Fusion 360 automation.**

This server wraps the Fusion 360 bridge add-in to let AI agents create sketches, build features, manage drawings, apply dimensions and tolerances, and design sheet metal parts — all through standardized MCP tool calls.

---

## How It Works — The Two-Piece Architecture

MCP Commander talks to Fusion 360 through a **bridge add-in** that runs *inside* Fusion 360's embedded Python environment. The bridge exposes a local HTTP server that the external MCP cartridge communicates with.

```
┌─────────────────┐    Voice/AI    ┌──────────────────┐    stdio     ┌───────────────┐
│  MCP Commander  │◄──────────────►│  fusion360-mcp   │◄────────────►│  LLM (Hermes) │
│  Core OS        │                │  (MCP cartridge) │              │  / Claude     │
└─────────────────┘                └────────┬─────────┘              └───────────────┘
                                             │
                                    HTTP POST :8080
                                    localhost only
                                             │
                                  ┌──────────┴──────────┐
                                  │  Fusion 360         │
                                  │  MCP Commander      │
                                  │  Bridge Add-In      │
                                  │  (embedded Python)  │
                                  └──────────┬──────────┘
                                             │
                                  Fusion 360 API
                                  (adsk.fusion, adsk.core)
```

**Communication flow:**
1. You speak or type a command: *"Create a 10x5cm rectangle and extrude it 3cm"*
2. LLM generates MCP tool calls (e.g. `create_sketch`, `sketch_rectangle`, `extrude`)
3. MCP cartridge sends HTTP POST to `localhost:8080/api/command`
4. Bridge add-in executes the command via Fusion 360's Python API
5. Fusion 360 updates the model in real-time
6. Result JSON flows back through the chain

---

## Prerequisites

- **Fusion 360** (desktop application, current version)
- **Python 3.10+** (on your system, for the external MCP cartridge)
- **pip** for package installation

---

## Setup — Step by Step

### Step 1: Install the Bridge Add-In in Fusion 360

Copy these two files into Fusion 360's Scripts and Add-Ins folder:

```
packages/fusion360-mcp/bridge/
├── MCPCommanderBridge.py        ← Main add-in code
└── MCPCommanderBridge.manifest ← Fusion 360 add-in metadata
```

**Destination paths:**

| OS | Path |
|---|---|
| **Windows** | `%APPDATA%\Autodesk\Autodesk Fusion 360\API\Scripts\MCPCommanderBridge\` |
| **macOS** | `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/MCPCommanderBridge/` |

**Quick copy (Windows PowerShell):**
```powershell
Copy-Item -Recurse packages\fusion360-mcp\bridge\* "$env:APPDATA\Autodesk\Autodesk Fusion 360\API\Scripts\MCPCommanderBridge\"
```

**Quick copy (macOS / Linux):**
```bash
cp -r packages/fusion360-mcp/bridge/* ~/Library/Application\ Support/Autodesk/Autodesk\ Fusion\ 360/API/Scripts/MCPCommanderBridge/
```

### Step 2: Run the Bridge in Fusion 360

1. Open **Fusion 360**
2. Go to **Utilities → Scripts and Add-Ins** (or press **Shift + S**)
3. In the Scripts panel, find **"MCP Commander Bridge"**
4. Click **Run**
5. You'll see a confirmation dialog: *"MCP Commander Bridge starting... HTTP server: http://localhost:8080"*

The bridge is now running and listening for commands. You'll also see a **"MCP Bridge Status"** button in the Design panel you can click anytime to verify the connection.

### Step 3: Install the External MCP Cartridge

```bash
cd /path/to/mcp-commander-cad

# Install the Fusion 360 MCP cartridge
pip install -e packages/fusion360-mcp
```

Dependencies installed automatically:
- `mcp>=1.0.0` — Model Context Protocol Python SDK (FastMCP)
- `httpx>=0.25.0` — Async HTTP client for bridge communication

### Step 4: Mount the Cartridge in MCP Commander

```bash
# From the mcp-commander-cad root
node core/src/cli.js mount fusion360-mcp
```

### Step 5: Verify Everything Works

```bash
# Test that the bridge is running
curl http://localhost:8080/ping
# Expected: {"status": "ok", "bridge": "MCP Commander Fusion 360 Bridge", "version": "1.0.0"}

# Test status endpoint
curl http://localhost:8080/api/status
# Expected: {"status": "ok", "connected": true, "commands_available": 50, ...}

# Test a command through the MCP cartridge
python -c "
import asyncio
from fusion360_mcp.api.connection import FusionConnection
async def test():
    conn = FusionConnection()
    await conn.connect()
    print('Connected to Fusion 360!')
    doc = await conn.get_active_document()
    print(f'Active document: {doc}')
    await conn.disconnect()
asyncio.run(test())
"
```

### Step 6: Use It

Run MCP Commander in voice or text mode:

```bash
# Voice mode (with microphone)
node core/src/cli.js run --voice

# Text mode (stdin)
node core/src/cli.js run --text
```

Or run the MCP cartridge standalone (for Claude Desktop, Cursor, etc.):

```bash
fusion360-mcp
```

**Claude Desktop config** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "fusion360": {
      "command": "fusion360-mcp",
      "args": []
    }
  }
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `FUSION_HOST` | `localhost` | Bridge HTTP hostname (always localhost for security) |
| `FUSION_PORT` | `8080` | Bridge HTTP port |
| `FUSION_API_KEY` | _(none)_ | API key if authentication is configured |
| `FUSION_TIMEOUT` | `30` | Request timeout in seconds |

### Changing the Bridge Port

If port 8080 is busy, edit the bridge add-in:

1. Open `MCPCommanderBridge.py` in the Scripts folder
2. Change `DEFAULT_PORT = 8080` to your preferred port
3. Set `FUSION_PORT` env var when running the MCP cartridge:
   ```bash
   FUSION_PORT=9090 fusion360-mcp
   ```

---

## Available Tools — 89 Total

### Sketch Tools (24 tools)

| Tool | Description |
|---|---|
| `create_sketch` | Create a new sketch on a plane or face |
| `sketch_line` | Draw a line between two points |
| `sketch_circle` | Draw a circle at center with radius |
| `sketch_arc` | Draw a center-point or 3-point arc |
| `sketch_rectangle` | Draw a 2-point or 3-point rectangle |
| `sketch_polygon` | Draw a regular polygon (N sides) |
| `sketch_ellipse` | Draw an ellipse with major/minor radii |
| `sketch_spline` | Draw a spline through control/fit points |
| `sketch_slot` | Draw a center-to-center or overall slot |
| `sketch_text` | Add text to a sketch |
| `sketch_offset` | Offset entities by distance |
| `sketch_project` | Project geometry onto sketch plane |
| `sketch_trim` | Trim entities at an intersection |
| `sketch_extend` | Extend entities to boundary or distance |
| `sketch_mirror` | Mirror entities about a line |
| `sketch_pattern_circular` | Circular pattern of entities |
| `sketch_pattern_rectangular` | Rectangular pattern of entities |
| `add_constraint_coincident` | Coincident constraint |
| `add_constraint_horizontal` | Horizontal constraint |
| `add_constraint_vertical` | Vertical constraint |
| `add_constraint_tangent` | Tangent constraint |
| `add_constraint_perpendicular` | Perpendicular constraint |
| `add_constraint_parallel` | Parallel constraint |
| `add_constraint_equal` | Equal-length constraint |
| `add_constraint_symmetric` | Symmetric constraint |
| `add_constraint_fix` | Fix entity position |
| `add_dimension` | Add driving dimension |

### Feature Tools (19 tools)

| Tool | Description |
|---|---|
| `extrude` | Extrude a profile (new body, join, cut, intersect) |
| `revolve` | Revolve a profile about an axis |
| `loft` | Loft between two or more profiles |
| `sweep` | Sweep a profile along a path |
| `thicken` | Thicken a surface body |
| `fillet` | Constant-radius fillet on edges |
| `chamfer` | Chamfer edges (equal, two-distance, distance-angle) |
| `shell` | Shell a body with face removal |
| `hole` | Create hole (simple, counterbore, countersink) |
| `thread` | Add thread to cylindrical face |
| `draft` | Apply draft angle to faces |
| `pattern_rectangular` | Rectangular pattern of features/bodies |
| `pattern_circular` | Circular pattern of features/bodies |
| `mirror` | Mirror features/bodies about a plane |
| `combine` | Combine bodies (join, cut, intersect) |
| `split_body` | Split a body with a tool |
| `scale` | Uniform or non-uniform scaling |
| `create_component` | Create/activate new component |
| `create_joint_origin` | Create joint origin for assembly |

### Drawing Tools (13 tools)

| Tool | Description |
|---|---|
| `create_drawing` | Create a new drawing from a design |
| `add_base_view` | Add base drawing view with orientation |
| `add_projected_view` | Add projected orthographic view |
| `add_section_view` | Add section view with cutting line |
| `add_detail_view` | Add detail/circular magnified view |
| `add_isometric_view` | Add isometric/perspective view |
| `set_sheet_size` | Set drawing sheet size (A0-E) |
| `add_bom` | Add bill of materials for assembly |
| `add_balloon` | Add balloons with leader lines |
| `add_centerline` | Add centerlines and center marks |
| `export_pdf` | Export drawing to PDF |
| `export_dxf` | Export to DXF |
| `add_title_block` | Insert or edit title block |

### Dimension & Annotation Tools (9 tools)

| Tool | Description |
|---|---|
| `add_linear_dim` | Add linear dimension |
| `add_angular_dim` | Add angular dimension |
| `add_radial_dim` | Add radial dimension |
| `add_diametric_dim` | Add diametric dimension |
| `add_ordinate_dim` | Add ordinate dimension set |
| `set_tolerance` | Set tolerance (bilateral, unilateral, limits, fit) |
| `set_precision` | Set decimal precision |
| `add_gdt` | Add geometric tolerance (GD&T) |
| `add_datum_feature` | Add datum feature symbol |

### Sheet Metal Tools (13 tools)

| Tool | Description |
|---|---|
| `create_sheet_metal_component` | Create a new sheet metal component |
| `create_base_flange` | Create base flange from sketch profile |
| `add_flange` | Add edge flange |
| `add_contour_flange` | Add contour flange |
| `add_hem` | Add hem fold |
| `add_fold` | Add fold along a sketch line |
| `add_bend` | Add bend between two faces |
| `add_rip` | Rip a sheet metal body |
| `add_relief` | Add corner relief |
| `create_flat_pattern` | Create and show flat pattern |
| `set_bend_allowance` | Configure K-factor or bend table |
| `punch_tool` | Apply punch/press tool |
| `convert_to_sheet_metal` | Convert imported geometry |

### Analysis Tools (11 tools)

| Tool | Description |
|---|---|
| `validate_sketch_constraints` | Validate sketch constraint status |
| `analyze_feature_tree` | Analyze the parametric feature tree |
| `get_physical_properties` | Get mass, volume, surface area, CoG |
| `measure_distance` | Measure distance between entities |
| `measure_angle` | Measure angle between entities |
| `check_manufacturability` | DFM analysis for CNC, turning, 3D print, etc. |
| `analyze_section_properties` | Area, centroid, moments of inertia |
| `detect_interference_detailed` | Interference detection between bodies |
| `analyze_curvature` | Surface curvature analysis |
| `export_screenshot` | Capture viewport to image file |
| `analyze_wall_thickness` | Wall thickness analysis |

---

## Voice Command Examples

Once running, you can say things like:

- **"Create a 10 by 5 centimeter rectangle on the XY plane"**
- **"Extrude that 3 centimeters"**
- **"Add a 1 centimeter fillet to all edges"**
- **"Create a 2 millimeter hole at the center"**
- **"Pattern that hole 6 times in a circle, 3 centimeter radius"**
- **"Show me the mass and volume"**
- **"Export to STEP"**
- **"Create a sheet metal bracket, 2mm steel, with a 90 degree flange"**

---

## Troubleshooting

### "Cannot connect to Fusion 360"
- Ensure Fusion 360 is open with a document loaded
- Ensure the bridge add-in is running (check Scripts and Add-Ins panel)
- Click the **MCP Bridge Status** button in the Design panel
- Verify with: `curl http://localhost:8080/ping`

### "No active document" errors
- Open or create a document in Fusion 360 before sending commands
- The bridge needs an active design to operate on

### "No sketch with profiles found" when extruding
- Make sure you created sketch geometry first (lines, rectangles, circles)
- Sketch entities need to form a closed profile for extrusion
- Verify the sketch has profiles: switch to Sketch mode and check

### Port 8080 already in use
- Change `DEFAULT_PORT` in the bridge add-in script
- Set matching `FUSION_PORT` env var for the MCP cartridge
- Or close whatever else is using port 8080

### Commands return "Unknown command"
- The bridge supports 50+ commands — check the available list:
  `curl http://localhost:8080/api/tools`
- Some advanced drawing/sheet metal commands may need bridge updates

---

## Project Structure

```
fusion360-mcp/
├── pyproject.toml
├── cartridge.json                      # MCP Commander cartridge manifest
├── README.md
├── bridge/                             # ← Fusion 360 add-in (runs INSIDE Fusion)
│   ├── MCPCommanderBridge.py           #    HTTP server + command dispatcher
│   └── MCPCommanderBridge.manifest     #    Fusion 360 add-in metadata
└── src/
    └── fusion360_mcp/                  # ← External MCP cartridge (runs OUTSIDE)
        ├── __init__.py
        ├── server.py                   #    FastMCP server entry point
        ├── api/
        │   ├── __init__.py
        │   ├── connection.py           #    HTTP client to bridge (httpx)
        │   └── models.py              #    Pydantic data models
        └── tools/
            ├── __init__.py
            ├── sketch.py               #    24 sketch tools
            ├── features.py             #    19 feature tools
            ├── drawing.py              #    13 drawing tools
            ├── dimensions.py           #    9 dimension tools
            ├── sheet_metal.py          #    13 sheet metal tools
            └── analysis.py            #    11 analysis tools
```

---

## License

MIT
