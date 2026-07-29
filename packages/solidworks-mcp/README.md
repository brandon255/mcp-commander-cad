# solidworks-mcp

**Model Context Protocol (MCP) server for SolidWorks automation via COM API.**

This cartridge connects directly to SolidWorks through Windows COM automation (pywin32). No bridge add-in needed — the MCP cartridge talks straight to the SolidWorks application instance. Just have SolidWorks running and fire up the server.

---

## ⚠️ Windows Only

SolidWorks COM automation requires **Windows**. This cartridge will not work on macOS or Linux.

---

## Architecture — Direct COM Connection

```
┌─────────────────┐    Voice/AI    ┌──────────────────┐    stdio     ┌───────────────┐
│  MCP Commander  │◄──────────────►│  solidworks-mcp  │◄────────────►│  LLM (Hermes) │
│  Core OS        │                │  (MCP cartridge) │              │  / Claude     │
└─────────────────┘                └────────┬─────────┘              └───────────────┘
                                             │
                                   COM Automation (pywin32)
                                   win32com.client.Dispatch
                                   "SldWorks.Application"
                                             │
                                  ┌──────────┴──────────┐
                                  │  SolidWorks          │
                                  │  (Desktop App)       │
                                  │  - Part documents    │
                                  │  - Assembly docs     │
                                  │  - Drawing docs      │
                                  │  - Sheet metal       │
                                  └─────────────────────┘
```

**No bridge required.** SolidWorks exposes a full COM API, so pywin32 connects directly to the running application.

---

## Prerequisites

- **Windows 10/11** (required for COM automation)
- **SolidWorks 2018** or later (installed and licensed)
- **Python 3.10+**
- **pywin32** (installed automatically as a dependency)
- SolidWorks must be **running** before using tools

---

## Setup — Step by Step

### Step 1: Install SolidWorks

Ensure SolidWorks is installed and activated. The COM API works with:
- SolidWorks 2018+
- Any license type (Premium, Professional, Standard)

### Step 2: Install the Cartridge

```powershell
# From the monorepo root
cd C:\path\to\mcp-commander-cad
pip install -e packages\solidworks-mcp
```

Dependencies installed automatically:
- `mcp>=1.0.0` — Model Context Protocol Python SDK (FastMCP)
- `pywin32>=306` — Windows COM automation library

### Step 3: Run SolidWorks

Launch SolidWorks and open or create a document. The COM API requires a running instance.

> **Tip:** Keep SolidWorks in the background. The MCP server will interact with it programmatically.

### Step 4: Mount in MCP Commander

```powershell
node core\src\cli.js mount solidworks-mcp
```

### Step 5: Verify the Connection

```powershell
python -c "
from solidworks_mcp.api.connection import get_sw_app, ensure_visible
app = get_sw_app()
print(f'Connected to SolidWorks {app.RevisionNumber()}')
ensure_visible()
"
```

### Step 6: Use It

**Through MCP Commander:**
```powershell
node core\src\cli.js run --voice
# or
node core\src\cli.js run --text
```

**Standalone (Claude Desktop, Cursor, etc.):**
```powershell
solidworks-mcp
```

**Claude Desktop config** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "solidworks": {
      "command": "solidworks-mcp",
      "args": []
    }
  }
}
```

---

## Configuration

No environment variables needed. The COM API connects to whatever SolidWorks instance is running.

**Requirements:**
1. SolidWorks must be **running** (the COM dispatcher will start it if possible, but an open document is preferred)
2. Only **one** MCP server instance should connect at a time (COM singleton)
3. Don't run other COM automation tools simultaneously (exclusive lock)

---

## Available Tools — 91 Total

### Sketch Tools (14 tools)

| Tool | Description |
|---|---|
| `create_sketch` | Create a new 2D sketch on Top/Front/Right or custom plane |
| `sketch_line` | Draw a line between two points |
| `sketch_circle` | Draw a circle at center with radius |
| `sketch_rectangle` | Draw a rectangle from corner to corner |
| `sketch_arc` | Draw a 3-point arc |
| `sketch_spline` | Draw a spline through control points |
| `sketch_slot` | Draw a straight or angular slot |
| `sketch_text` | Add text annotation to sketch |
| `sketch_pattern` | Linear or circular pattern of sketch entities |
| `sketch_mirror` | Mirror sketch entities about a line |
| `sketch_trim` | Trim sketch entities to intersections |
| `sketch_offset` | Offset sketch entities by distance |
| `sketch_constraints` | Add geometric constraints (coincident, tangent, perpendicular, etc.) |
| `exit_sketch` | Exit the active sketch |

### Feature Tools (15 tools)

| Tool | Description |
|---|---|
| `extrude_boss` | Extrude a sketch as a boss (blind, through all, mid-plane) |
| `extrude_cut` | Extrude cut from a sketch |
| `revolve_boss` | Revolve a sketch profile about an axis |
| `revolve_cut` | Revolve cut |
| `fillet` | Add constant or variable radius fillets |
| `chamfer` | Add chamfers (angle-distance, distance-distance) |
| `hole_wizard` | Create standard holes (counterbore, countersink, tapped) |
| `shell` | Shell a solid body to wall thickness |
| `draft` | Apply draft to faces |
| `sweep` | Sweep a profile along a path |
| `loft` | Loft between multiple profiles |
| `mirror_feature` | Mirror features about a plane |
| `pattern_linear` | Linear pattern of features |
| `pattern_circular` | Circular pattern of features |
| `scale` | Scale a part about a point |

### Drawing Tools (14 tools)

| Tool | Description |
|---|---|
| `create_drawing` | Create a new drawing document |
| `add_standard_views` | Add standard 3 views (front, top, right) |
| `add_isometric_view` | Add isometric view |
| `add_section_view` | Create section view |
| `add_detail_view` | Create detail/circle view |
| `add_broken_view` | Create broken-out section view |
| `set_sheet_format` | Set sheet size (A/B/C/D/E) and format |
| `add_weld_symbol` | Add weld symbol annotation |
| `add_surface_finish` | Add surface finish symbol |
| `create_bom` | Insert bill of materials table |
| `add_balloon` | Auto-ballooning or manual balloons |
| `add_centerline` | Add centerlines and center marks |
| `export_drawing_pdf` | Export drawing to PDF |
| `export_drawing_dxf` | Export drawing to DXF |

### Dimension Tools (10 tools)

| Tool | Description |
|---|---|
| `auto_dim_sketch` | Auto-dimension all sketch entities |
| `add_smart_dim` | Add a smart dimension between two points/edges |
| `add_ordinate_dim` | Add ordinate dimension set |
| `add_baseline_dim` | Add baseline dimensions |
| `add_chain_dim` | Add chain dimensions |
| `set_dim_tolerance` | Set tolerance class (bilateral, unilateral, limits, fit) |
| `add_gdt` | Add GDT frames (position, perpendicularity, flatness, etc.) |
| `add_datum` | Add datum feature symbol |
| `set_dim_precision` | Set number of decimal places |

### Assembly Tools (12 tools)

| Tool | Description |
|---|---|
| `create_assembly` | Create a new assembly document |
| `insert_component` | Insert a part/assembly into the assembly |
| `add_mate_coincident` | Add coincident mate |
| `add_mate_concentric` | Add concentric mate |
| `add_mate_distance` | Add distance mate |
| `add_mate_angle` | Add angle mate |
| `add_mate_tangent` | Add tangent mate |
| `add_mate_lock` | Lock a component in place |
| `add_mate_advanced` | Width, cam, hinge, gear, rack-pinion mates |
| `explode_assembly` | Create or edit exploded view |
| `assembly_bom` | Generate BOM data from assembly |
| `check_interference` | Run interference detection |

### Sheet Metal Tools (17 tools)

| Tool | Description |
|---|---|
| `create_base_flange` | Create a base flange from a sketch |
| `add_edge_flange` | Add edge flange to an edge |
| `add_miter_flange` | Add miter flange |
| `add_tab` | Add sketch tab |
| `add_lofted_bend` | Lofted bend transition |
| `add_hem` | Add hem fold |
| `add_jog` | Add jog bend |
| `add_fold` | Sketch fold |
| `add_rip` | Rip a sheet metal edge |
| `add_gusset` | Add gusset |
| `flatten` | Flatten the sheet metal part |
| `fold_flat` | Show folded state |
| `set_bend_allowance` | Set bend allowance (K-factor, bend table, custom) |
| `set_gauge_table` | Set material gauge table |
| `convert_to_sheet_metal` | Convert imported solid to sheet metal |
| `insert_dies` | Insert forming tools |

---

## Usage Examples

### Create a Simple Bracket

```
# 1. Create a new part and sketch
create_sketch(plane_name="top")

# 2. Draw a rectangle
sketch_rectangle(x1=0, y1=0, x2=100, y2=60)

# 3. Exit sketch and extrude
exit_sketch()
extrude_boss(depth=20, end_condition="blind")

# 4. Add fillets to all edges
fillet(radius=5.0)

# 5. Create a mounting hole
create_sketch(plane_name="front")
sketch_circle(cx=50, cy=50, radius=5)
exit_sketch()
extrude_cut(depth=25, end_condition="through_all")
```

### Create a Drawing with Dimensions

```
create_drawing(sheet_size="A")
add_standard_views(pos_x=0.15, pos_y=0.15, scale=0.5)
add_isometric_view(pos_x=0.4, pos_y=0.15, scale=0.5)
add_smart_dim(x1=0, y1=0, x2=100, y2=0)
export_drawing_pdf(filepath="C:/Drawings/bracket.pdf")
```

### Sheet Metal Bracket

```
create_sketch(plane_name="top")
sketch_rectangle(x1=0, y1=0, x2=200, y2=100)
exit_sketch()
create_base_flange(thickness=2.0)
add_edge_flange(height=50, angle=90)
add_hem(hem_type="closed", length=5)
flatten()
```

### Assembly Mates

```
create_assembly()
insert_component(filepath="C:/Parts/bracket.sldprt")
insert_component(filepath="C:/Parts/mounting_plate.sldprt")
add_mate_coincident(face1="bracket_top", face2="plate_bottom")
add_mate_concentric(edge1="bracket_hole", edge2="plate_hole")
add_mate_distance(face1="bracket_front", face2="plate_back", distance=0)
```

---

## Voice Command Examples

Once SolidWorks is running and the cartridge is active, you can say:

- **"Create a new sketch on the top plane"**
- **"Draw a rectangle 100 by 60 millimeters"**
- **"Extrude that 20 millimeters"**
- **"Add a 5 millimeter fillet"**
- **"Create a through-all hole at the center"**
- **"Pattern that hole 6 times in a circle"**
- **"Create a drawing and add standard views"**
- **"Export the drawing to PDF"**
- **"Create a sheet metal flange, 2mm thick, 50mm tall"**

---

## Troubleshooting

### "Failed to connect to SolidWorks via COM"
- Ensure SolidWorks is installed and properly licensed
- SolidWorks must be running (check Task Manager)
- Try launching SolidWorks first, then start the MCP server
- COM automation requires a full Windows installation (not web/remote)

### "No active document in SolidWorks"
- Open or create a document in SolidWorks before sending commands
- Use `create_sketch` on an existing part, or `create_assembly` to start fresh

### "CoInitialize has not been called"
- This is a COM threading issue — rare with the singleton pattern
- Restart the MCP server (it reinitializes COM on startup)

### SolidWorks freezes or becomes unresponsive
- Large assemblies can lock the COM interface during rebuilds
- Wait for SolidWorks to finish processing before sending more commands
- Avoid sending rapid-fire commands on complex geometry

### COM singleton conflicts
- Only one MCP server instance should connect to SolidWorks at a time
- Close other COM automation tools (VBA macros, other scripts)
- If stuck, restart SolidWorks and reconnect

---

## Project Structure

```
solidworks-mcp/
├── pyproject.toml
├── cartridge.json                          # MCP Commander cartridge manifest
├── README.md
└── src/
    └── solidworks_mcp/
        ├── __init__.py
        ├── server.py                       # FastMCP server entry point
        ├── api/
        │   ├── __init__.py
        │   ├── connection.py               # SolidWorks COM singleton (77 lines)
        │   └── models.py                   # Pydantic data models
        └── tools/
            ├── __init__.py
            ├── sketch.py                   # 14 sketch tools
            ├── features.py                 # 15 feature tools
            ├── drawing.py                  # 14 drawing tools
            ├── dimensions.py              # 10 dimension tools
            ├── assembly.py                 # 12 assembly tools
            ├── sheet_metal.py              # 17 sheet metal tools
            └── analysis.py                 # Analysis tools
```

---

## License

MIT
