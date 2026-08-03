# MCP Commander — Full Installation Prompt for Claude Code

> **Copy everything below this line and paste it as the prompt for Claude Code (or any code agent with shell/file access).**

---

## Context

You are installing **MCP Commander** — a voice-AI agent framework for CAD software built by Doctrine Labs. The repo is at a known location. This is a monorepo with a Node.js Core OS and multiple Python MCP cartridge packages. Your job is to get everything installed, linked, configured, and verified so the user can run it.

**The project has:**
- 1 Node.js Core OS (CLI + runtime)
- 11 Python MCP cartridge packages (each is an installable pip package),
  226 tools total. The 4 CAD platform cartridges are fusion360-mcp (78
  tools), solidworks-mcp (82 tools), onshape-mcp (33 tools), and
  rhino-mcp (4 tools) -- rhino-mcp was previously missing from this
  install flow (real code, never wired in); fixed below.
- 1 Fusion 360 bridge add-in (Python script that runs INSIDE Fusion 360,
  copied into Fusion's Scripts folder)
- 1 Rhino bridge plugin (Python script that runs INSIDE Rhino, loaded as
  a startup script -- different mechanism than Fusion's, see Step 6b)
- Symlinks from `cartridges/` → `packages/` for Core OS discovery
- A Makefile with shortcuts

**CRITICAL**: The repo root is wherever the files already are. Use `pwd` to confirm. All commands below are relative to the repo root.

---

## STEP 1 — Environment Check

Run these and report results before proceeding:

```bash
node --version          # Need v18+
python3 --version       # Need 3.10+
pip --version || pip3 --version
which python3
```

If any are missing, install them first (use brew on macOS, winget/chocolatey on Windows, apt on Linux).

---

## STEP 2 — Python Environment (Recommended: venv)

Create a virtual environment in the repo root to keep dependencies isolated:

```bash
cd <REPO_ROOT>
python3 -m venv .venv
source .venv/bin/activate    # macOS/Linux
# OR on Windows PowerShell:
# .\.venv\Scripts\Activate.ps1
```

All `pip install` commands below assume the venv is active.

---

## STEP 3 — Install All Python Cartridge Packages

Install every package in editable mode (`-e`) so changes to source are reflected immediately:

```bash
cd <REPO_ROOT>

# Core CAD platform cartridges (the 4 you'll use with actual CAD software)
pip install -e packages/fusion360-mcp
pip install -e packages/onshape-mcp
pip install -e packages/solidworks-mcp
pip install -e packages/rhino-mcp

# File format translator (STL↔STEP↔IGES↔OBJ etc)
pip install -e packages/file-translator-mcp

# MCP Commander agent (the orchestrator)
pip install -e packages/mcp-commander-agent

# Supporting cartridges
pip install -e packages/mcp-commander-analysis
pip install -e packages/mcp-commander-cognitive
pip install -e packages/mcp-commander-ideas
pip install -e packages/mcp-commander-materials
pip install -e packages/mcp-commander-quoting
pip install -e packages/mcp-commander-scorecard
```

**Expected output**: Each should complete with `Successfully installed ...`

**If you get errors**:
- `pywin32` failing on macOS/Linux → **NORMAL**. Only needed on Windows for SolidWorks. Skip that one error and continue.
- `cadquery` failing → Run `pip install cadquery==2.3.1 --break-system-packages` or install Conda first: `conda install -c conda-forge cadquery`
- `trimesh` missing → `pip install trimesh numpy`

---

## STEP 4 — Verify Cartridge Symlinks

The Core OS discovers cartridges via `cartridges/` directory. These should be symlinks pointing to `packages/`. Verify:

```bash
cd <REPO_ROOT>
ls -la cartridges/
```

You should see 11 symlinks. If any are missing, create them:

```bash
cd <REPO_ROOT>/cartridges
ln -sf ../packages/fusion360-mcp/ fusion360-mcp
ln -sf ../packages/onshape-mcp/ onshape-mcp
ln -sf ../packages/solidworks-mcp/ solidworks-mcp
ln -sf ../packages/rhino-mcp/ rhino-mcp
ln -sf ../packages/file-translator-mcp/ file-translator-mcp
ln -sf ../packages/mcp-commander-agent/ mcp-commander-agent
ln -sf ../packages/mcp-commander-analysis/ mcp-commander-analysis
ln -sf ../packages/mcp-commander-cognitive/ mcp-commander-cognitive
ln -sf ../packages/mcp-commander-ideas/ mcp-commander-ideas
ln -sf ../packages/mcp-commander-materials/ mcp-commander-materials
ln -sf ../packages/mcp-commander-quoting/ mcp-commander-quoting
ln -sf ../packages/mcp-commander-scorecard/ mcp-commander-scorecard
```

Verify all links resolve:
```bash
ls cartridges/*/cartridge.json
```

Should list 11 cartridge.json files.

---

## STEP 5 — Node.js Core OS

```bash
cd <REPO_ROOT>/core
npm install
```

Verify the CLI works:
```bash
cd <REPO_ROOT>
node core/src/cli.js --help
node core/src/cli.js status
```

---

## STEP 6 — Fusion 360 Bridge Add-In Deployment

The bridge add-in needs to be copied into Fusion 360's Scripts and Add-Ins folder so Fusion can discover and run it.

**Find the Fusion 360 scripts folder:**

| OS | Path |
|---|---|
| **Windows** | `%APPDATA%\Autodesk\Autodesk Fusion 360\API\Scripts` |
| **macOS** | `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts` |

**Copy the bridge files:**

```bash
# macOS
mkdir -p ~/Library/Application\ Support/Autodesk/Autodesk\ Fusion\ 360/API/Scripts/MCPCommanderBridge
cp packages/fusion360-mcp/bridge/MCPCommanderBridge.py ~/Library/Application\ Support/Autodesk/Autodesk\ Fusion\ 360/API/Scripts/MCPCommanderBridge/
cp packages/fusion360-mcp/bridge/MCPCommanderBridge.manifest ~/Library/Application\ Support/Autodesk/Autodesk\ Fusion\ 360/API/Scripts/MCPCommanderBridge/

# Windows PowerShell
# mkdir "$env:APPDATA\Autodesk\Autodesk Fusion 360\API\Scripts\MCPCommanderBridge"
# Copy-Item packages\fusion360-mcp\bridge\* "$env:APPDATA\Autodesk\Autodesk Fusion 360\API\Scripts\MCPCommanderBridge\"
```

**Verify** the files exist in the Fusion scripts folder after copying.

---

## STEP 6b — Rhino Bridge Plugin (Different Mechanism Than Fusion)

Unlike Fusion's bridge, this is not a file-copy step -- it's loaded manually
inside Rhino itself, once:

1. Open Rhino 8.
2. Open the Script Editor (or use `-RunPythonScript`).
3. Run `packages/rhino-mcp/bridge/RhinoMCPBridge.py` as a startup script.
4. It starts a local HTTP listener on `127.0.0.1:8765` and holds a live
   reference to the active document -- no external COM-style attach step,
   unlike SolidWorks.
5. Tell the user this step must be repeated each time they restart Rhino,
   unless they set it up as an auto-loading startup script in Rhino's own
   settings (their choice, not something to do without asking).

**Verify**: with the bridge running, `rhino-mcp`'s
`rhino_connection_diagnostics` tool should report the plugin's host PID,
Rhino version, active document, and listener status -- check this first
before assuming any other Rhino tool works.

---

## STEP 7 — Claude Desktop Configuration (Optional but Recommended)

If the user wants to use any cartridge standalone with Claude Desktop, create/update the config file:

**Config file locations:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

**Create this config** (only include the cartridges the user actually uses):

```json
{
  "mcpServers": {
    "fusion360": {
      "command": "fusion360-mcp",
      "args": []
    },
    "onshape": {
      "command": "onshape-mcp",
      "args": [],
      "env": {
        "ONSHAPE_ACCESS_KEY": "<USER NEEDS TO FILL THIS IN>",
        "ONSHAPE_SECRET_KEY": "<USER NEEDS TO FILL THIS IN>"
      }
    },
    "rhino": {
      "command": "rhino-mcp",
      "args": []
    },
    "file-translator": {
      "command": "file-translator-mcp",
      "args": []
    }
  }
}
```

**NOTE**: Do NOT hardcode API keys. Leave the placeholder strings. Tell the user they need to fill in their Onshape keys.

---

## STEP 8 — Environment Variables (Onshape Only)

Onshape requires API keys. Set them in the user's shell profile:

```bash
# macOS/Linux — add to ~/.zshrc or ~/.bashrc
echo 'export ONSHAPE_ACCESS_KEY="your-access-key-here"' >> ~/.zshrc
echo 'export ONSHAPE_SECRET_KEY="your-secret-key-here"' >> ~/.zshrc

# Windows PowerShell — tell the user to run:
# $env:ONSHAPE_ACCESS_KEY = "your-access-key-here"
# $env:ONSHAPE_SECRET_KEY = "your-secret-key-here"
```

**IMPORTANT**: Tell the user they need to get their keys from https://cad.onshape.com → Account → API Keys.

---

## STEP 9 — Verify Everything Works

Run this full verification script and report ALL results:

```bash
cd <REPO_ROOT>

echo "=== 1. Python packages ==="
pip list | grep -E "mcp|trimesh|cadquery|httpx|pywin32|pydantic|numpy"

echo ""
echo "=== 2. Console script entry points ==="
which fusion360-mcp
which onshape-mcp
which rhino-mcp
which file-translator-mcp
which mcp-commander 2>/dev/null || echo "mcp-commander entry point not found (OK if not configured)"

echo ""
echo "=== 3. Cartridge symlinks ==="
ls cartridges/*/cartridge.json | wc -l
echo "Expected: 11"

echo ""
echo "=== 4. Node.js Core OS ==="
node core/src/cli.js status

echo ""
echo "=== 5. Python import test ==="
python3 -c "
from fusion360_mcp.api.connection import FusionConnection
print('fusion360-mcp: OK')
"
python3 -c "
from onshape_mcp.api.connection import OnshapeConnection
print('onshape-mcp: OK')
"
python3 -c "
from rhino_mcp.api.connection import RhinoConnection
print('rhino-mcp: OK')
"
python3 -c "
from file_translator_mcp.api.converter import get_file_info
print('file-translator-mcp: OK')
"

echo ""
echo "=== 6. Fusion bridge files ==="
# Check the bridge was copied to Fusion scripts folder
FUSION_DIR=""
if [[ "$OSTYPE" == "darwin"* ]]; then
  FUSION_DIR="$HOME/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/MCPCommanderBridge"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  FUSION_DIR="$APPDATA/Autodesk/Autodesk Fusion 360/API/Scripts/MCPCommanderBridge"
fi
if [ -n "$FUSION_DIR" ] && [ -d "$FUSION_DIR" ]; then
  echo "Bridge directory: $FUSION_DIR"
  ls -la "$FUSION_DIR"
else
  echo "Fusion 360 scripts directory not found (OK if Fusion is not installed)"
fi

echo ""
echo "=== DONE ==="
```

---

## STEP 10 — What to Tell the User After Installation

Tell the user this summary:

### What's Installed
- **11 MCP cartridges, 226 tools total**: fusion360-mcp (78), solidworks-mcp (82),
  onshape-mcp (33), rhino-mcp (4), file-translator-mcp (20), mcp-commander-analysis (11),
  mcp-commander-cognitive (9), mcp-commander-materials (7), mcp-commander-quoting (6),
  mcp-commander-ideas (5), mcp-commander-scorecard (4)
- **Fusion 360 bridge add-in** deployed to Fusion's Scripts folder
- **Rhino bridge plugin** loaded as a Rhino startup script (manual, repeats each Rhino restart unless the user sets up auto-load themselves)
- **Claude Desktop config** ready (needs Onshape API keys filled in)
- **Node.js Core OS** ready to run

### To Start Using It

**Fusion 360:**
1. Open Fusion 360
2. Go to Utilities → Scripts and Add-Ins
3. Select MCPCommanderBridge → click **Run**
4. You should see "MCP Bridge Status" button appear in the Design panel — click it to verify status shows "Connected"
5. In a terminal: `fusion360-mcp` (starts the MCP server that talks to the bridge)

**Onshape:**
1. Get API keys from https://cad.onshape.com → Account → API Keys
2. Set environment variables (see Step 8)
3. Run: `onshape-mcp`

**Rhino:**
1. Open Rhino 8
2. Load `packages/rhino-mcp/bridge/RhinoMCPBridge.py` as a startup script (Step 6b) -- do this every session unless auto-load is configured
3. In a terminal: `rhino-mcp`
4. Ask for `rhino_connection_diagnostics` first to confirm the bridge is actually connected before trying anything else

**File Translator (STL → STEP):**
1. Run: `file-translator-mcp`
2. Use `stl_to_step` tool to convert mesh files

**SolidWorks (Windows only):**
1. Launch SolidWorks
2. Run: `solidworks-mcp`

### Quick Test for the STL Problem
```bash
# Activate venv first
source .venv/bin/activate

# Analyze the STL file
python3 -c "
from file_translator_mcp.api.converter import get_file_info, analyze_mesh

info = get_file_info('path/to/sitemap.stl')
print(info)

mesh_info = analyze_mesh('path/to/sitemap.stl')
print(mesh_info)
"
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `pip install` fails with "externally-managed-environment" | Use the venv (Step 2), or add `--break-system-packages` |
| `cadquery` won't install | Install via Conda: `conda install -c conda-forge cadquery` |
| `pywin32` fails on macOS/Linux | **Expected** — only needed for SolidWorks on Windows |
| Fusion 360 bridge doesn't appear in Scripts | Verify files are in the correct Scripts folder (Step 6). Restart Fusion. |
| `fusion360-mcp` command not found | Ensure venv is active and `pip install -e packages/fusion360-mcp` succeeded |
| Onshape returns 401 | Check API keys are set correctly (no extra whitespace) |
| Rhino tools time out / `rhino_connection_diagnostics` fails | The bridge plugin (Step 6b) isn't loaded, or was unloaded after a Rhino restart -- it does not persist automatically |
| Node.js CLI errors | Run `npm install` in `core/` directory |

---

**END OF INSTALLATION PROMPT**
