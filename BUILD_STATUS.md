# MCP Commander — Build Status (audited 2026-08-01)

> Ground-truth audit of what's actually built vs. what only looks built.
> Based on reading the real source (line counts, stub markers, connection
> code), not just file/tool counts from cartridge.json. Update this doc
> when the picture materially changes rather than trusting it forever.

---

## What's fully built (real, substantive code)

| Component | Tools | Lines | Notes |
|---|---|---|---|
| `solidworks-mcp` | 82 | 5,263 | Real COM automation. `api/connection.py` documents a workaround for an actual SolidWorks COM bug (`GetTypeInfo()` failing on `SldWorks.Application`) — evidence of real debugging against live SolidWorks, not generated boilerplate. |
| `fusion360-mcp` | 78 | 4,434 | REST-based, cross-platform (Mac + Windows) |
| `onshape-mcp` | 33 | 2,694 | Real REST client against Onshape's actual API v6 |
| `rhino-mcp` | 4 | 301 | In-process plugin + local HTTP relay -- deliberately *not* COM, per the "why not COM (the SolidWorks lesson)" note in its own README |
| `file-translator-mcp` | 20 | 3,021 | STL/STEP/IGES/OBJ/PLY/3MF/DXF conversion + mesh repair |
| `mcp-commander-analysis` | 11 | 3,131 | Vision/OCR/DFM/RAG. Falls back to a mock when no VLM API key is set -- that's a deliberate degradation path, not a broken stub |
| `mcp-commander-cognitive` | 9 | 2,681 | Background design-reasoning ops (divergent/convergent thinking, cross-domain transfer, pattern recognition, spatial reasoning, etc.) |
| `mcp-commander-materials` | 7 | 903 | Material search/comparison/substitution/cost |
| `mcp-commander-quoting` | 6 | 328 | Cost/lead-time estimation, quote generation |
| `mcp-commander-ideas` | 5 | 326 | Ideation/brainstorming, idea capture/search |
| `mcp-commander-scorecard` | 4 | 235 | Weighted design-alternative scoring |
| `mcp-commander-agent` | orchestrator | 1,111 | Real OpenAI/Anthropic intent parsing (`agent/intent_parser.py`), MCP client + router (`mcp/client.py`, `mcp/router.py`), Whisper STT + TTS (`voice/`) |
| `core/` (Node.js) | -- | 3,439 | Cartridge mounting, gates, WORM ledger, redaction -- zero runtime dependencies (pure Node stdlib) |

**~28,300 lines total, 226 tools, 11 cartridge symlinks, all resolving.**
This is genuine engineering effort, not scaffolding.

---

## What's actually missing or broken

1. **Zero automated tests exist anywhere.** `Makefile` has `test`,
   `test-sw`, `test-f360`, `test-mcp-commander` targets calling
   `pytest packages/...`, but there is not a single test file in any
   package. Nothing here has been verified by anything other than manual
   runs -- there's no way to know from the repo alone what actually works
   end to end.
2. **`Makefile` is incomplete.** `install` only installs `solidworks-mcp`,
   `fusion360-mcp`, and `mcp-commander-agent` -- it never references
   `onshape-mcp`, `rhino-mcp`, or any of the 6 supporting cartridges. Same
   class of gap already fixed in `CLAUDE-CODE-INSTALL-PROMPT.md` (see that
   file's Step 3/4) -- the Makefile still has it.
3. **FreeCAD, Bambu Studio, Excel -- no packages exist at all.** These are
   real, currently-running tools on the Dell with zero code here. New
   packages, not fixes, following the existing cartridge pattern
   (`cartridge.json` + `src/<name>/server.py` + `api/` + `tools/`).
4. **Install-prompt/README fixes not yet merged to `main`** -- sitting on
   branch `claude/fix-install-prompts-and-readme` (also has this doc).
5. **Rhino's bridge doesn't persist across restarts.** Has to be manually
   reloaded as a Rhino startup script every session unless auto-load is
   configured in Rhino's own settings -- a real daily-use gap, not just a
   documentation note.

---

## Open question this audit can't answer

Whether the full pipeline -- voice in -> intent parse -> tool call -> live
CAD app -> result back -- has ever actually been run end to end. The core
CAD drivers and the orchestrator are individually substantial and real,
but with no test suite and no smoke-log evidence checked into the repo,
there's no ground truth on integration, only on each piece in isolation.

---

## Recommended next work, in priority order

1. Merge/review `claude/fix-install-prompts-and-readme`, then actually run
   `CLAUDE-CODE-INSTALL-PROMPT.md` against the live Dell setup and record
   what breaks.
2. Fix `Makefile` the same way the install prompt was fixed: add
   `onshape-mcp`, `rhino-mcp`, and the 6 supporting cartridges to `install`
   and `test`.
3. Write real tests -- even smoke tests that just confirm each server
   starts and responds to `list_tools` would be a large improvement over
   zero.
4. Decide whether to build `freecad-mcp` / a Bambu Studio cartridge / an
   Excel cartridge as new packages, following the existing pattern.
5. Fix Rhino's bridge persistence.
