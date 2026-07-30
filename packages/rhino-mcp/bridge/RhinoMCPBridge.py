"""
RhinoMCPBridge - runs INSIDE Rhino's own Python 3 engine.

Starts a local HTTP server that accepts JSON commands from the external
rhino-mcp cartridge and dispatches them against the live active document.

Communication:
    External MCP server  ->  POST http://127.0.0.1:8765/{diagnostics,read,execute,update}
                              {...}
    This bridge           ->  {"status": "ok|error", "result": ..., "message": "..."}

Thread safety:
    The HTTP listener runs on a background thread. Every request that touches
    the document or UI is marshaled onto Rhino's main thread via
    Rhino.RhinoApp.InvokeOnUiThread before doing anything with scriptcontext.doc
    or RhinoCommon. Skipping this causes intermittent crashes or corrupted
    document state, not a clean error - so it is handled once, centrally, here
    in the dispatcher rather than per-operation.

Loading:
    1. In Rhino 8, open the Script Editor (Tools > ScriptEditor, or the
       `ScriptEditor` command).
    2. Open this file and click Run - or use `-RunPythonScript` pointing at
       this file's path from the command line.
    3. It prints a confirmation once the listener is up on 127.0.0.1:8765.
    4. Leave it running; start the external `rhino-mcp` server separately.

NOTE: this file has not yet been run against a live Rhino instance - it is
built directly from RhinoCommon/rhinoscriptsyntax documentation and the same
patterns already verified working in the fusion360-mcp and solidworks-mcp
bridges in this repo, but the threading marshal and HTTP layer should be
smoke-tested against a real Rhino session before being relied on.
"""
import json
import threading
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

try:
    import Rhino
    import Rhino.Geometry as rg
    import scriptcontext as sc
    import rhinoscriptsyntax as rs
    import System

    HAS_RHINO = True
except ImportError:
    HAS_RHINO = False


# ---------------------------------------------------------------------------
# Main-thread marshaling
# ---------------------------------------------------------------------------

def run_on_main_thread(func, timeout=120.0):
    """Run func() on Rhino's UI/main thread and block until it completes.

    Returns func()'s return value, or re-raises any exception it raised.
    Required for every call that touches scriptcontext.doc or RhinoCommon,
    since this function itself runs on the HTTP listener's background thread.
    """
    if not HAS_RHINO:
        raise RuntimeError("Not running inside Rhino's Python engine (Rhino module unavailable).")

    done = threading.Event()
    box = {}

    def wrapper():
        try:
            box["result"] = func()
        except Exception as e:
            box["error"] = e
            box["traceback"] = traceback.format_exc()
        finally:
            done.set()

    Rhino.RhinoApp.InvokeOnUiThread(System.Action(wrapper))

    if not done.wait(timeout):
        raise TimeoutError(f"Operation did not complete on Rhino's main thread within {timeout}s")

    if "error" in box:
        raise box["error"]
    return box.get("result")


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def _diagnostics():
    def work():
        doc = sc.doc
        return {
            "connected": True,
            "pid": __import__("os").getpid(),
            "rhino_version": str(Rhino.RhinoApp.Version),
            "document_name": doc.Name if doc else None,
            "document_path": doc.Path if doc else None,
            "document_modified": doc.Modified if doc else None,
            "open_document_count": Rhino.RhinoDoc.OpenDocuments().Length,
            "listener_port": DEFAULT_PORT,
        }
    return run_on_main_thread(work)


# ---------------------------------------------------------------------------
# Read (query-only)
# ---------------------------------------------------------------------------

def _read_document(params):
    def work():
        doc = sc.doc
        return {
            "name": doc.Name,
            "path": doc.Path,
            "modified": doc.Modified,
            "units": str(doc.ModelUnitSystem),
            "active_layer": doc.Layers.CurrentLayer.FullPath,
        }
    return run_on_main_thread(work)


def _read_objects(params):
    layer = params.get("layer") or None
    object_type = params.get("object_type") or None

    def work():
        doc = sc.doc
        objs = []
        for obj in doc.Objects:
            if layer and obj.Attributes.LayerIndex != doc.Layers.FindName(layer).Index:
                continue
            geo = obj.Geometry
            type_name = type(geo).__name__
            if object_type and object_type.lower() not in type_name.lower():
                continue
            bbox = geo.GetBoundingBox(True)
            objs.append({
                "id": str(obj.Id),
                "type": type_name,
                "layer": doc.Layers[obj.Attributes.LayerIndex].FullPath,
                "bounding_box": {
                    "min": [bbox.Min.X, bbox.Min.Y, bbox.Min.Z],
                    "max": [bbox.Max.X, bbox.Max.Y, bbox.Max.Z],
                },
            })
        return {"objects": objs, "count": len(objs)}
    return run_on_main_thread(work)


def _read_geometry(params):
    object_id = params.get("object_id")

    def work():
        doc = sc.doc
        if object_id:
            obj = doc.Objects.FindId(System.Guid(object_id))
            if obj is None:
                return {"error": f"No object with id {object_id}"}
            geo = obj.Geometry
        else:
            sel = list(doc.Objects.GetSelectedObjects(False, False))
            if not sel:
                return {"error": "No object_id given and no current selection"}
            geo = sel[0].Geometry
        bbox = geo.GetBoundingBox(True)
        return {
            "bounding_box": {
                "min": [bbox.Min.X, bbox.Min.Y, bbox.Min.Z],
                "max": [bbox.Max.X, bbox.Max.Y, bbox.Max.Z],
            },
            "dimensions": {
                "x": bbox.Max.X - bbox.Min.X,
                "y": bbox.Max.Y - bbox.Min.Y,
                "z": bbox.Max.Z - bbox.Min.Z,
            },
        }
    return run_on_main_thread(work)


def _read_screenshot(params):
    def work():
        view = sc.doc.Views.ActiveView
        bmp = view.CaptureToBitmap()
        import io
        stream = System.IO.MemoryStream()
        bmp.Save(stream, System.Drawing.Imaging.ImageFormat.Png)
        import base64
        data = base64.b64encode(bytes(stream.ToArray())).decode("ascii")
        return {"format": "png", "data_base64": data}
    return run_on_main_thread(work)


_READ_HANDLERS = {
    "document": _read_document,
    "objects": _read_objects,
    "geometry": _read_geometry,
    "screenshot": _read_screenshot,
}


def dispatch_read(query, params):
    handler = _READ_HANDLERS.get(query)
    if handler is None:
        return {"status": "error", "message": f"Unknown read query: {query}"}
    try:
        return {"status": "ok", "result": handler(params)}
    except Exception as e:
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


# ---------------------------------------------------------------------------
# Execute (arbitrary code escape hatch)
# ---------------------------------------------------------------------------

def dispatch_execute(code):
    def work():
        import io
        import contextlib

        local_ns = {
            "rs": rs,
            "sc": sc,
            "Rhino": Rhino,
            "rg": rg,
        }
        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            exec(code, local_ns)
        return {
            "stdout": stdout_capture.getvalue(),
            "result": local_ns.get("result"),
        }

    try:
        result = run_on_main_thread(work)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


# ---------------------------------------------------------------------------
# Update (curated named operations)
# ---------------------------------------------------------------------------

def _op_import_mesh(params):
    # Rhino's command-line macro parser for the Import/Export file-path prompt
    # requires native Windows backslash separators - a forward-slash path
    # silently fails with "Directory "" does not exist" even though the path
    # is otherwise valid and exists on disk. Normalize defensively so callers
    # don't have to know this.
    path = params["path"].replace("/", "\\")

    def work():
        doc = sc.doc
        before = set(o.Id for o in doc.Objects)
        rs.Command(f'-_Import "{path}" _Enter', True)
        # rs.Command's synchronous return does not guarantee the imported
        # object has actually been added to doc.Objects yet on this build -
        # give it a brief chance to land before concluding nothing imported.
        import time
        after = [o for o in doc.Objects if o.Id not in before]
        attempts = 0
        while not after and attempts < 20:
            time.sleep(0.25)
            after = [o for o in doc.Objects if o.Id not in before]
            attempts += 1
        return {"imported_ids": [str(o.Id) for o in after], "count": len(after)}
    return run_on_main_thread(work)


def _op_export(params):
    path = params["path"].replace("/", "\\")
    fmt = (params.get("format") or "step").lower()
    ext_map = {"step": "stp", "3dm": "3dm", "stl": "stl"}
    if fmt not in ext_map:
        raise ValueError(f"Unsupported export format: {fmt}")

    def work():
        rs.Command(f'-_Export "{path}" _Enter', True)
        return {"exported_path": path, "format": fmt}
    return run_on_main_thread(work)


def _op_mesh_to_subd(params):
    object_id = params["object_id"]
    target_quad_count = params.get("target_quad_count", 1500)

    def work():
        doc = sc.doc
        obj = doc.Objects.FindId(System.Guid(object_id))
        if obj is None:
            return {"error": f"No object with id {object_id}"}

        mesh = obj.Geometry.Duplicate()

        # Repair first: meshes from external tools (Blender etc.) commonly
        # have naked edges/small gaps and non-welded duplicate vertices. Left
        # unrepaired, these make SubD/NURBS conversion unstable or extremely
        # slow (observed: one degenerate mesh drove ToBrep() to run
        # indefinitely and consume 11GB+ RAM). Healing/filling/welding before
        # any conversion step fixes this at the source.
        try:
            mesh.HealNakedEdges(doc.ModelAbsoluteTolerance * 10)
        except Exception:
            pass
        try:
            mesh.FillHoles()
        except Exception:
            pass
        mesh.Weld(3.15159)

        # Retopologize into a small number of clean quads rather than leaving
        # one NURBS patch per original triangle. Without this, SubD.CreateFromMesh
        # + ToBrep() produce one trimmed surface per source face - thousands of
        # tiny patches that look like dense line-work instead of a smooth solid,
        # and bloat the exported STEP file (abracastle hit 124MB uncorrected).
        quad_mesh = mesh
        try:
            qr_params = rg.QuadRemeshParameters()
            qr_params.TargetQuadCount = target_quad_count
            qr_params.AdaptiveSize = 50
            result_mesh = mesh.QuadRemesh(qr_params)
            if result_mesh is not None:
                quad_mesh = result_mesh
        except Exception:
            pass  # fall back to the repaired (non-retopologized) mesh

        subd = rg.SubD.CreateFromMesh(quad_mesh)
        if subd is None:
            return {"error": "CreateFromMesh failed - mesh may not be manifold/watertight"}
        new_id = doc.Objects.AddSubD(subd)
        doc.Views.Redraw()
        return {"subd_id": str(new_id), "quad_count": quad_mesh.Faces.Count}
    return run_on_main_thread(work)


def _op_convert_to_nurbs(params):
    object_id = params["object_id"]

    def work():
        doc = sc.doc
        obj = doc.Objects.FindId(System.Guid(object_id))
        if obj is None:
            return {"error": f"No object with id {object_id}"}
        geo = obj.Geometry
        nurbs_brep = geo.ToBrep() if hasattr(geo, "ToBrep") else None
        if nurbs_brep is None:
            return {"error": f"Object type {type(geo).__name__} has no ToBrep() conversion"}
        new_id = doc.Objects.AddBrep(nurbs_brep)
        doc.Views.Redraw()
        return {"brep_id": str(new_id)}
    return run_on_main_thread(work)


def _op_silhouette_to_curve(params):
    object_id = params["object_id"]
    direction = params.get("direction") or [0, 0, 1]

    def work():
        doc = sc.doc
        obj = doc.Objects.FindId(System.Guid(object_id))
        if obj is None:
            return {"error": f"No object with id {object_id}"}
        view_dir = rg.Vector3d(direction[0], direction[1], direction[2])
        curves = rg.Silhouette.Compute(
            obj.Geometry, rg.SilhouetteType.SectionCut, view_dir,
            sc.doc.ModelAbsoluteTolerance, sc.doc.ModelAngleToleranceRadians,
        )
        if not curves:
            return {"error": "No silhouette curves computed"}
        new_ids = [str(doc.Objects.AddCurve(c.Curve)) for c in curves if c.Curve is not None]
        doc.Views.Redraw()
        return {"curve_ids": new_ids, "count": len(new_ids)}
    return run_on_main_thread(work)


def _op_extrude_curve(params):
    object_id = params["object_id"]
    distance = params.get("distance", 1.0)

    def work():
        doc = sc.doc
        obj = doc.Objects.FindId(System.Guid(object_id))
        if obj is None:
            return {"error": f"No object with id {object_id}"}
        curve = obj.Geometry
        path = rg.Line(rg.Point3d(0, 0, 0), rg.Point3d(0, 0, distance))
        extrusion = rg.Surface.CreateExtrusion(curve, path.Direction)
        if extrusion is None:
            return {"error": "CreateExtrusion failed - curve may not be closed/planar"}
        brep = extrusion.ToBrep()
        new_id = doc.Objects.AddBrep(brep)
        doc.Views.Redraw()
        return {"brep_id": str(new_id), "distance": distance}
    return run_on_main_thread(work)


def _op_scale(params):
    object_id = params["object_id"]
    factor = params.get("factor", 1.0)
    base_point = params.get("base_point")

    def work():
        doc = sc.doc
        obj = doc.Objects.FindId(System.Guid(object_id))
        if obj is None:
            return {"error": f"No object with id {object_id}"}
        if base_point:
            origin = rg.Point3d(base_point[0], base_point[1], base_point[2])
        else:
            bbox = obj.Geometry.GetBoundingBox(True)
            origin = bbox.Center
        xform = rg.Transform.Scale(origin, factor)
        doc.Objects.Transform(obj, xform, True)
        doc.Views.Redraw()
        return {"object_id": object_id, "factor": factor}
    return run_on_main_thread(work)


def _op_boolean_union(params):
    object_ids = params["object_ids"]

    def work():
        doc = sc.doc
        breps = []
        for oid in object_ids:
            obj = doc.Objects.FindId(System.Guid(oid))
            if obj is None:
                return {"error": f"No object with id {oid}"}
            breps.append(obj.Geometry)
        result = rg.Brep.CreateBooleanUnion(breps, doc.ModelAbsoluteTolerance)
        if not result:
            return {"error": "Boolean union produced no result"}
        new_ids = [str(doc.Objects.AddBrep(b)) for b in result]
        doc.Views.Redraw()
        return {"result_ids": new_ids}
    return run_on_main_thread(work)


def _op_boolean_diff(params):
    object_ids = params["object_ids"]
    if len(object_ids) < 2:
        raise ValueError("boolean_diff needs at least 2 object_ids (first minus the rest)")

    def work():
        doc = sc.doc
        objs = []
        for oid in object_ids:
            obj = doc.Objects.FindId(System.Guid(oid))
            if obj is None:
                return {"error": f"No object with id {oid}"}
            objs.append(obj.Geometry)
        result = rg.Brep.CreateBooleanDifference(
            [objs[0]], objs[1:], doc.ModelAbsoluteTolerance
        )
        if not result:
            return {"error": "Boolean difference produced no result"}
        new_ids = [str(doc.Objects.AddBrep(b)) for b in result]
        doc.Views.Redraw()
        return {"result_ids": new_ids}
    return run_on_main_thread(work)


_UPDATE_HANDLERS = {
    "import_mesh": _op_import_mesh,
    "export": _op_export,
    "mesh_to_subd": _op_mesh_to_subd,
    "convert_to_nurbs": _op_convert_to_nurbs,
    "silhouette_to_curve": _op_silhouette_to_curve,
    "extrude_curve": _op_extrude_curve,
    "scale": _op_scale,
    "boolean_union": _op_boolean_union,
    "boolean_diff": _op_boolean_diff,
}


def dispatch_update(operation, params):
    handler = _UPDATE_HANDLERS.get(operation)
    if handler is None:
        return {"status": "error", "message": f"Unknown update operation: {operation}"}
    try:
        result = handler(params)
        if isinstance(result, dict) and "error" in result:
            return {"status": "error", "message": result["error"]}
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

class BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # don't flood Rhino's console

    def _send_json(self, data, status_code=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        return json.loads(raw) if raw else {}

    def do_POST(self):
        try:
            data = self._read_body()
        except (json.JSONDecodeError, ValueError) as e:
            self._send_json({"status": "error", "message": f"Invalid JSON: {e}"}, 400)
            return

        if self.path == "/diagnostics":
            try:
                self._send_json({"status": "ok", "result": _diagnostics()})
            except Exception as e:
                self._send_json({"status": "error", "message": str(e), "traceback": traceback.format_exc()})
        elif self.path == "/read":
            self._send_json(dispatch_read(data.get("query", ""), data.get("params", {})))
        elif self.path == "/execute":
            self._send_json(dispatch_execute(data.get("code", "")))
        elif self.path == "/update":
            self._send_json(dispatch_update(data.get("operation", ""), data.get("params", {})))
        else:
            self._send_json({"status": "error", "message": f"Unknown endpoint: {self.path}"}, 404)


class ThreadedHTTPServer(HTTPServer):
    allow_reuse_address = True

    def process_request(self, request, client_address):
        thread = threading.Thread(target=self._process_request_thread, args=(request, client_address))
        thread.daemon = True
        thread.start()

    def _process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)


_server = None
_server_thread = None


def start_server(host=DEFAULT_HOST, port=DEFAULT_PORT):
    global _server, _server_thread
    if _server is not None:
        print(f"RhinoMCPBridge already running on {host}:{port}")
        return _server
    _server = ThreadedHTTPServer((host, port), BridgeHandler)
    _server_thread = threading.Thread(target=_server.serve_forever)
    _server_thread.daemon = True
    _server_thread.start()
    print(f"RhinoMCPBridge listening on http://{host}:{port}")
    return _server


if __name__ == "__main__":
    if not HAS_RHINO:
        raise RuntimeError(
            "This script must be run inside Rhino's Python engine "
            "(Tools > ScriptEditor > Run), not a standalone interpreter."
        )
    start_server()
