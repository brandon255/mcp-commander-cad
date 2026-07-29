# MCP Commander — Full Installation Prompt for Claude Code

> **Copy everything below this line and paste it as the prompt for Claude Code (or any code agent with shell/file access).**

---

## Context

You are installing **MCP Commander** — a voice-AI agent framework for CAD software built by Doctrine Labs. The repo is at a known location. This is a monorepo with a Node.js Core OS and multiple Python MCP cartridge packages. Your job is to get everything installed, linked, configured, and verified so the user can run it.

**The project has:**
- 1 Node.js Core OS (CLI + runtime)
- 10 Python MCP cartridge packages (each is an installable pip package)
- 1 Fusion 360 bridge add-in (Python script that runs INSIDE Fusion 360)
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

# Core CAD platform cartridges (the 3 you'll use with actual CAD software)
pip install -e packages/fusion360-mcp
pip install -e packages/onshape-mcp
pip install -e packages/solidworks-mcp

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

You should see 10 symlinks. If `file-translator-mcp` is missing:

```bash
cd <REPO_ROOT>/cartridges
ln -sf ../packages/file-translator-mcp/ file-translator-mcp
```

If any OTHER symlinks are missing, create them:

```bash
ln -sf ../packages/fusion360-mcp/ fusion360-mcp
ln -sf ../packages/onshape-mcp/ onshape-mcp
ln -sf ../packages/solidworks-mcp/ solidworks-mcp
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

Should list 10 cartridge.json files.

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
which file-translator-mcp
which mcp-commander 2>/dev/null || echo "mcp-commander entry point not found (OK if not configured)"

echo ""
echo "=== 3. Cartridge symlinks ==="
ls cartridges/*/cartridge.json | wc -l
echo "Expected: 10"

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
- **10 MCP cartridges** (190+ CAD tools across Fusion 360, SolidWorks, Onshape, file translation, analysis, cognitive, ideas, materials, quoting, scorecard)
- **Fusion 360 bridge add-in** deployed to Fusion's Scripts folder
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
| Node.js CLI errors | Run `npm install` in `core/` directory |

---

**END OF INSTALLATION PROMPT**
