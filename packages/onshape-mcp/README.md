# onshape-mcp

**Model Context Protocol (MCP) server for Onshape cloud CAD automation.**

This cartridge connects directly to the Onshape REST API over HTTPS — no local bridge needed. Provide your API key pair and you're controlling Onshape documents, sketches, features, assemblies, and drawings through voice or text commands.

---

## Architecture — Direct Cloud Connection

```
┌─────────────────┐    Voice/AI    ┌──────────────────┐    stdio     ┌───────────────┐
│  MCP Commander  │◄──────────────►│  onshape-mcp     │◄────────────►│  LLM (Hermes) │
│  Core OS        │                │  (MCP cartridge) │              │  / Claude     │
└─────────────────┘                └────────┬─────────┘              └───────────────┘
                                             │
                                   HTTPS (httpx async)
                                   Basic Auth (API key pair)
                                   cad.onshape.com/api/v6/
                                             │
                                  ┌──────────┴──────────┐
                                  │  Onshape Cloud      │
                                  │  REST API            │
                                  │  - Documents         │
                                  │  - Part Studios      │
                                  │  - Assemblies        │
                                  │  - Drawings          │
                                  │  - Features          │
                                  └─────────────────────┘
```

**No bridge required.** Onshape exposes a full REST API, so the MCP cartridge connects directly over HTTPS.

---

## Prerequisites

- **Onshape account** (Free tier works; Professional/Education for advanced features)
- **Onshape API key pair** (access key + secret key)
- **Python 3.10+**
- `pip` for package installation

---

## Setup — Step by Step

### Step 1: Get Your Onshape API Keys

1. Log in to [onshape.com](https://cad.onshape.com)
2. Click your **avatar** (top-right) → **Account**
3. Go to **API Keys** (or [onshape.com/api-keys](https://cad.onshape.com/api-keys))
4. Click **Create API Key**
5. Give it a name (e.g. "MCP Commander")
6. Copy the **Access Key** and **Secret Key** — you only see the secret once

### Step 2: Set Environment Variables

**Windows (PowerShell):**
```powershell
$env:ONSHAPE_ACCESS_KEY = "your-access-key-here"
$env:ONSHAPE_SECRET_KEY = "your-secret-key-here"
```

**Windows (Command Prompt):**
```cmd
set ONSHAPE_ACCESS_KEY=your-access-key-here
set ONSHAPE_SECRET_KEY=your-secret-key-here
```

**macOS / Linux:**
```bash
export ONSHAPE_ACCESS_KEY="your-access-key-here"
export ONSHAPE_SECRET_KEY="your-secret-key-here"
```

**Persistent (add to your shell profile):**
```bash
# ~/.bashrc, ~/.zshrc, or ~/.profile
export ONSHAPE_ACCESS_KEY="your-access-key-here"
export ONSHAPE_SECRET_KEY="your-secret-key-here"
```

### Step 3: Install the Cartridge

```bash
cd /path/to/mcp-commander-cad
pip install -e packages/onshape-mcp
```

Dependencies installed automatically:
- `mcp>=1.0.0` — Model Context Protocol Python SDK (FastMCP)
- `httpx>=0.25.0` — Async HTTP client for Onshape REST API

### Step 4: Mount in MCP Commander

```bash
node core/src/cli.js mount onshape-mcp
```

### Step 5: Verify the Connection

```bash
python -c "
import asyncio
from onshape_mcp.api.connection import OnshapeConnection

async def test():
    conn = OnshapeConnection()
    await conn.connect()
    print('Connected to Onshape!')
    docs = await conn.list_documents()
    for doc in docs[:5]:
        print(f'  - {doc.get(\"name\", \"?\")}')
    await conn.disconnect()

asyncio.run(test())
"
```

### Step 6: Use It

**Through MCP Commander:**
```bash
node core/src/cli.js run --voice
# or
node core/src/cli.js run --text
```

**Standalone (Claude Desktop, Cursor, etc.):**
```bash
onshape-mcp
```

**Claude Desktop config:**
```json
{
  "mcpServers": {
    "onshape": {
      "command": "onshape-mcp",
      "args": [],
      "env": {
        "ONSHAPE_ACCESS_KEY": "your-access-key",
        "ONSHAPE_SECRET_KEY": "your-secret-key"
      }
    }
  }
}
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ONSHAPE_ACCESS_KEY` | **Yes** | _(none)_ | Onshape API access key |
| `ONSHAPE_SECRET_KEY` | **Yes** | _(none)_ | Onshape API secret key |
| `ONSHAPE_BASE_URL` | No | `https://cad.onshape.com/api/v6` | Override for enterprise/region-specific instances |

### Units

Onshape's API uses **meters** internally. The MCP cartridge exposes tools in meters by default. The voice/text layer in MCP Commander can handle unit conversions ("3 centimeters" → 0.03 meters).

---

## Available Tools — 34 Total

### Sketch Tools (7 tools)

| Tool | Description |
|---|---|
| `create_line` | Create a line segment in a sketch |
| `create_circle` | Create a circle in a sketch |
| `create_arc` | Create an arc in a sketch |
| `create_rectangle` | Create a rectangle in a sketch |
| `create_point` | Create a reference point in a sketch |
| `add_constraint` | Add a constraint to sketch entities |
| *(implied: dimension, trim, extend, etc. via constraint tool)* | |

### Feature Tools (8 tools)

| Tool | Description |
|---|---|
| `extrude_feature` | Create an extrude feature from a sketch profile |
| `revolve_feature` | Create a revolve feature from a sketch profile |
| `fillet_feature` | Apply fillets to edges in a part |
| `chamfer_feature` | Apply chamfers to edges in a part |
| `pattern_feature` | Create a linear or circular pattern of features |
| `mirror_feature` | Mirror features about a plane |
| `shell_feature` | Create a shell by removing faces from a part |
| `boolean_feature` | Perform boolean operations between parts |

### Document Management (3 tools)

| Tool | Description |
|---|---|
| `get_part_info` | Get metadata and properties of a part |
| `list_documents` | List accessible Onshape documents |
| `create_document` | Create a new Onshape document |

### Import/Export Tools (6 tools)

| Tool | Description |
|---|---|
| `import_file` | Upload an STL, STEP, IGES, or OBJ file to an Onshape document |
| `export_stl` | Export a Part Studio as STL |
| `export_step` | Export a Part Studio as STEP |
| `export_iges` | Export a Part Studio as IGES |
| `export_pdf` | Export a Drawing as PDF |
| `get_export_status` | Check the status of an export or import translation job |

### Drawing Tools (5 tools)

| Tool | Description |
|---|---|
| `create_drawing` | Create a new drawing in an Onshape document |
| `get_drawing_views` | List all views in a drawing |
| `add_drawing_view` | Add a standard view to a drawing |
| `export_drawing_pdf` | Export a drawing to PDF format |
| `list_drawings` | List all drawings in an Onshape document |

### Assembly Tools (5 tools)

| Tool | Description |
|---|---|
| `get_assembly_structure` | Get the full assembly tree structure |
| `list_assembly_instances` | List all instances in an assembly |
| `add_mate` | Insert a mate constraint into an assembly |
| `create_assembly` | Create a new empty assembly element |
| `list_assemblies` | List all assemblies in an Onshape document |

---

## Voice Command Examples

Once connected, you can say things like:

- **"List my Onshape documents"**
- **"Create a new document called Bracket Design"**
- **"Create a rectangle 100mm by 60mm"**
- **"Extrude that 20mm"**
- **"Add a 5mm fillet to all edges"**
- **"Export to STEP"**
- **"Show me the part properties"**
- **"Import an STL file called bracket.stl"**
- **"Upload this STEP file to my document"**
- **"Export as IGES"**
- **"Create a drawing from this part"**
- **"Add a front view to the drawing"**
- **"Export the drawing as PDF"**
- **"Create a new assembly called Motor Assembly"**
- **"Add a fastened mate between these two parts"**

---

## Onshape API Reference

The connection layer (`api/connection.py`) maps to these Onshape REST endpoints:

| Method | API Endpoint | Purpose |
|---|---|---|
| `GET` | `/users/me` | Verify credentials |
| `GET` | `/documents` | List documents |
| `POST` | `/documents` | Create document |
| `GET` | `/documents/{did}/workspaces` | List workspaces |
| `GET` | `/documents/{did}/workspaces/{wid}/elements` | List elements |
| `GET` | `/documents/{did}/workspaces/{wid}/parts/{eid}` | List parts |
| `GET` | `/documents/{did}/workspaces/{wid}/parts/{eid}/{pid}` | Get part |
| `GET` | `/documents/{did}/workspaces/{wid}/parts/{eid}/{pid}/properties` | Get properties |
| `GET/POST` | `/documents/{did}/workspaces/{wid}/features/{eid}` | List/create features |
| `DELETE` | `/documents/{did}/workspaces/{wid}/features/{eid}/feature/{fid}` | Delete feature |
| `GET` | `/documents/{did}/workspaces/{wid}/assemblies/{eid}` | Get assembly |
| `GET` | `/documents/{did}/workspaces/{wid}/assemblies/{eid}/instances` | List instances |
| `POST` | `/documents/{did}/workspaces/{wid}/assemblies/{eid}/mates` | Insert mate |
| `GET/POST` | `/documents/{did}/workspaces/{wid}/drawings` | Get/create drawings |
| `POST` | `/documents/{did}/workspaces/{wid}/stl/export` | Export STL |
| `POST` | `/documents/{did}/workspaces/{wid}/step/export` | Export STEP |
| `POST` | `/documents/{did}/workspaces/{wid}/iges/export` | Export IGES |
| `POST` | `/documents/{did}/workspaces/{wid}/pdf/export` | Export PDF |
| `POST` | `/documents/{did}/workspaces/{wid}/elements` | Import file (multipart) |
| `GET` | `/translations/{tid}` | Translation status |
| `POST` | `/documents/{did}/workspaces/{wid}/assemblies` | Create assembly |

---

## Troubleshooting

### "Onshape API key not configured"
- Set both `ONSHAPE_ACCESS_KEY` and `ONSHAPE_SECRET_KEY` env vars
- Verify the keys work by logging into onshape.com with your account
- Keys are case-sensitive

### "Cannot connect to Onshape API"
- Check internet connectivity
- If behind a corporate proxy, set `HTTPS_PROXY` env var
- Verify your Onshape account is active (free accounts can go dormant)

### "HTTP 401 Unauthorized"
- Your API keys may have been rotated or revoked
- Regenerate keys at onshape.com → Account → API Keys
- Ensure no extra whitespace in env var values

### "Request timed out"
- Default timeout is 60 seconds (large assemblies can take longer)
- Increase timeout: set `ONSHAPE_TIMEOUT=120` (seconds)

### Rate limiting
- Onshape API has rate limits depending on your plan
- Free tier: ~60 requests/minute
- Professional: ~300 requests/minute
- If hitting limits, add small delays between rapid tool calls

---

## Project Structure

```
onshape-mcp/
├── pyproject.toml
├── cartridge.json                          # MCP Commander cartridge manifest
├── README.md
└── src/
    └── onshape_mcp/
        ├── __init__.py
        ├── server.py                       # FastMCP server entry point
        ├── api/
        │   ├── __init__.py
        │   ├── connection.py               # Onshape REST API client (592 lines)
        │   └── models.py                   # Pydantic data models
        └── tools/
            ├── __init__.py
            ├── sketch.py                   # 12 sketch tools
            ├── features.py                 # 8 feature tools
            ├── import_export.py            # 6 import/export tools
            ├── drawing.py                  # 5 drawing tools
            └── assembly.py                 # 5 assembly tools
```

---

## License

MIT
