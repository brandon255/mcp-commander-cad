# rhino-mcp

MCP server for Rhino automation. Talks to a Rhino plugin (`bridge/RhinoMCPBridge.py`) running
*inside* Rhino over a local HTTP relay, rather than attaching to Rhino from outside via COM.

## Why not COM (the SolidWorks lesson)

The `solidworks-mcp` cartridge originally attached to SolidWorks from an external process via
`win32com.client`. That has two structural problems that cost a full debugging session to work
through:

- An external COM client can't reliably tell "which running instance has the user's visible
  document open" — it can end up creating or attaching to the wrong instance, or holding a
  stale reference across an app restart.
- COM automation doesn't exist on macOS, and Rhino needs to work cross-platform.

Instead, `rhino-mcp` follows the same shape as `fusion360-mcp`: a plugin loaded *inside* Rhino
opens a local HTTP listener (`127.0.0.1:8765` by default) and always has direct, live access to
`scriptcontext.doc` (the actual active document) and `Rhino.RhinoApp` — no external attach step,
no stale-handle risk. The external `rhino-mcp` process is a thin relay that forwards MCP tool
calls to that local port.

```
Claude  <--MCP-->  rhino-mcp (this package, external process)  <--HTTP-->  RhinoMCPBridge.py (in-process plugin)
                                                                                  |
                                                                            RhinoCommon API
                                                                            scriptcontext.doc,
                                                                            active view, selection
```

## Tool shape

Four tools, matching the Fusion 360 connector rather than SolidWorks' ~90 narrow per-feature
tools (which had no generic escape hatch to debug/patch around a failure):

- **`rhino_connection_diagnostics`** — plugin host PID, Rhino version, active document, listener
  status. Build and check this first, always, before assuming anything else works.
- **`rhino_read`** — query-only: `document`, `objects`, `geometry`, `screenshot`.
- **`rhino_execute`** — run an arbitrary `rhinoscriptsyntax`/RhinoCommon Python snippet inside
  the plugin's main-thread context. The escape hatch for anything not yet wrapped as a named
  operation.
- **`rhino_update`** — curated, parameter-validated operations: `import_mesh`, `export`,
  `mesh_to_subd`, `convert_to_nurbs`, `silhouette_to_curve`, `extrude_curve`, `scale`,
  `boolean_union`, `boolean_diff`.

## Installation

```bash
pip install -e packages/rhino-mcp
```

### Loading the bridge plugin into Rhino

1. Open Rhino 8.
2. Tools → Options → (or the Script Editor) → run `bridge/RhinoMCPBridge.py` as a startup script,
   or load it via `-RunPythonScript` pointing at this file.
3. It starts an HTTP listener on `127.0.0.1:8765` and marshals every request onto Rhino's main
   thread via `Rhino.RhinoApp.InvokeOnUiThread` before touching the document.
4. Start the external server: `rhino-mcp` (stdio transport, same as the other cartridges).

## Thread safety

Every RhinoCommon call that touches the document or UI runs via
`Rhino.RhinoApp.InvokeOnUiThread(...)`, never directly on the HTTP listener's background thread.
Skipping this causes intermittent crashes or corrupted document state rather than a clean error,
so it's handled once, centrally, in the bridge's request dispatcher rather than per-tool.
