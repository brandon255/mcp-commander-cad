# SolidWorks MCP — Windows Installation Prompt for Claude Code

> **Copy everything below this line and paste it as the prompt for a fresh Claude Code session running ON the Windows machine that has SolidWorks installed.** This will not work from a session running on a different machine — Claude Code can only execute commands on the machine it's actually running on.

---

## Context

You are setting up **solidworks-mcp** — the SolidWorks cartridge from the MCP Commander CAD monorepo — on a Windows machine that has SolidWorks installed. This package lets an AI agent control SolidWorks via its COM API. The repo already exists on GitHub with this package fully working (verified on macOS for the non-Windows packages; `solidworks-mcp` itself could not be tested there since it requires Windows COM).

**CRITICAL**: Run `pwd` first to confirm your working directory. All commands below assume you start from wherever you want the repo cloned (e.g. `C:\Users\<you>\Projects\`).

---

## STEP 1 — Environment Check

```powershell
python --version          # Need 3.10+
pip --version
git --version
```

If Python is missing or below 3.10, install from python.org or via `winget install Python.Python.3.12`.

---

## STEP 2 — Clone the Repo

```powershell
git clone https://github.com/brandon255/mcp-commander-cad.git
cd mcp-commander-cad
```

---

## STEP 3 — Python Virtual Environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, run once as admin: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

---

## STEP 4 — Install solidworks-mcp

```powershell
pip install --upgrade pip
pip install -e packages\solidworks-mcp
```

**Expected**: This should succeed cleanly on Windows — `pywin32` (which failed on macOS, expected) should install fine here since it's a Windows-only package for COM automation.

The `mcp` dependency is already pinned to `>=1.0.0,<2.0.0` in this repo (a real bug was found and fixed for this exact reason on 2026-07-28 — `mcp==2.0.0` removed the `FastMCP` API this codebase depends on). If for any reason it installs `mcp==2.0.0` anyway, run:
```powershell
pip install "mcp<2.0.0" --force-reinstall
```

---

## STEP 5 — Verify the Entry Point Works

**SolidWorks must be running first** — this server talks to a live SolidWorks instance via COM, there is no separate bridge add-in to load (unlike the Fusion 360 cartridge).

1. Open SolidWorks.
2. In a terminal (venv active):
```powershell
solidworks-mcp
```
3. It should start without crashing and wait for MCP protocol messages on stdio (no visible output is normal/healthy for a stdio MCP server — that means it's working, not stuck).
4. Press Ctrl+C to stop the test.

If it crashes with an import error or COM connection error, report the full traceback — don't guess at a fix, diagnose the actual error first.

---

## STEP 6 — Wire It Into Whatever You're Chatting Through

**If using Claude Desktop:**

Edit `%APPDATA%\Claude\claude_desktop_config.json` (create if missing) and merge in (don't overwrite other keys if the file already has content):

```json
{
  "mcpServers": {
    "solidworks": {
      "command": "C:\\Users\\<you>\\Projects\\mcp-commander-cad\\.venv\\Scripts\\solidworks-mcp.exe",
      "args": []
    }
  }
}
```
Replace the path with the actual absolute path to `solidworks-mcp.exe` in this venv. Restart Claude Desktop after saving.

**If using Claude Code on this machine:**

```powershell
claude mcp add --scope user solidworks -- "C:\Users\<you>\Projects\mcp-commander-cad\.venv\Scripts\solidworks-mcp.exe"
claude mcp list
```
Confirm it shows as Connected. Note: any Claude Code session already running before this command won't see it — a new session is needed.

---

## STEP 7 — Real Test

With SolidWorks open and a part/assembly loaded, ask (through whichever app you wired it into) for something simple and observable, e.g. "list the available SolidWorks tools" or "what's the name of the currently open document in SolidWorks." Confirm you get a real, correct answer back — not just that the tool call didn't error.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `pip install` fails with "externally-managed-environment" | Use the venv (Step 3) |
| `pywin32` fails to install | Should not happen on real Windows — if it does, run `pip install pywin32` separately and check the Python architecture (32 vs 64-bit) matches your Python install |
| COM connection errors | SolidWorks must already be running before starting `solidworks-mcp` |
| `mcp.server.fastmcp` import error | You got `mcp==2.0.0` — run `pip install "mcp<2.0.0" --force-reinstall` |
| Claude Desktop doesn't see the tool | Check the JSON path uses `\\` (escaped backslashes) and restart the app |

---

**END OF INSTALLATION PROMPT**
