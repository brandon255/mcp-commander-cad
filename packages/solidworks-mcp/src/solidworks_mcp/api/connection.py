"""
Solidworks COM connection manager.
Singleton pattern for managing the Solidworks application instance.

This build's live SldWorks.Application COM object fails GetTypeInfo() when
obtained via GetActiveObject/ROT (TypeInfoCount reports 1, but GetTypeInfo(0)
raises "Element not found"). That breaks win32com's plain dynamic dispatch:
without working type info it can't tell a zero-arg property from a method
that needs arguments, so real, documented members (FirstFeature, Extension,
etc.) intermittently fail with AttributeError.

The fix is early (type-library) binding, built directly from the .tlb file
registered on disk rather than from the live object's (broken) GetTypeInfo.
Wrapper objects are constructed via a plain QueryInterface (DispatchBaseClass
already does this internally when given a raw PyIDispatch), which sidesteps
GetTypeInfo entirely. Once the top-level app/doc object is early-bound,
nested property access (doc.SketchManager, doc.FeatureManager, doc.Extension,
...) auto-wraps to the correct generated class too, so tool code elsewhere in
this package doesn't need to change.
"""
import os
import subprocess
import winreg

import pythoncom
import pywintypes
import win32com.client
import win32com.client.gencache
import win32com.client.makepy

_PROG_ID = "SldWorks.Application"

_sw_app = None
_gen_mod = None


def _find_typelib_path():
    """Locate the registered .tlb file path for SldWorks.Application on disk."""
    clsid_key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{_PROG_ID}\\CLSID")
    clsid, _ = winreg.QueryValueEx(clsid_key, "")
    typelib_key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"CLSID\\{clsid}\\TypeLib")
    typelib_guid, _ = winreg.QueryValueEx(typelib_key, "")

    tl_key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"TypeLib\\{typelib_guid}")
    i = 0
    while True:
        try:
            version = winreg.EnumKey(tl_key, i)
        except OSError:
            break
        i += 1
        for lcid_variant in ("0", "9"):
            for arch_key in ("win64", "win32"):
                try:
                    path_key = winreg.OpenKey(
                        winreg.HKEY_CLASSES_ROOT,
                        f"TypeLib\\{typelib_guid}\\{version}\\{lcid_variant}\\{arch_key}",
                    )
                    path, _ = winreg.QueryValueEx(path_key, "")
                    if os.path.exists(path):
                        return path
                except FileNotFoundError:
                    continue
    raise RuntimeError(
        "Could not locate SldWorks.Application's registered type library (.tlb) on disk."
    )


def _ensure_gen_module():
    """Ensure the early-bound wrapper module for the Solidworks type library is generated
    and cached (once per machine, under the standard win32com gen_py cache directory)."""
    global _gen_mod
    if _gen_mod is not None:
        return _gen_mod

    tlb_path = _find_typelib_path()
    tlb = pythoncom.LoadTypeLib(tlb_path)
    guid, lcid, _syskind, major, minor, _flags = tlb.GetLibAttr()

    try:
        _gen_mod = win32com.client.gencache.GetModuleForTypelib(guid, lcid, major, minor)
    except ImportError:
        win32com.client.makepy.GenerateFromTypeLibSpec(tlb)
        _gen_mod = win32com.client.gencache.GetModuleForTypelib(guid, lcid, major, minor)
    return _gen_mod


def _wrap(raw):
    """Wrap a raw/dynamically-dispatched COM object as its early-bound IModelDoc2 equivalent.

    Used for members whose declared type is a generic IDispatch (e.g. ActiveDoc,
    which can be a part/assembly/drawing) and so don't auto-wrap the way
    statically-typed members (SketchManager, FeatureManager, Extension, ...) do.
    """
    return wrap_as(raw, "IModelDoc2")


def wrap_as(raw, interface_name):
    """Wrap a raw/dynamically-dispatched COM object as a named early-bound interface.

    Several members return a generic IDispatch rather than a statically-typed
    interface (ActiveDoc, FirstFeature/GetNextFeature, ...), so win32com can't
    auto-wrap them the way it does for e.g. doc.SketchManager. Call this on
    such return values with the real interface name (e.g. "IFeature") to get
    a properly early-bound object whose methods resolve correctly.
    """
    if raw is None:
        return None
    gen_mod = _ensure_gen_module()
    oleobj = raw._oleobj_ if hasattr(raw, "_oleobj_") else raw
    cls = getattr(gen_mod, interface_name)
    return cls(oleobj)


def _is_alive(app):
    """Check whether a cached SldWorks.Application COM reference still resolves.

    A stale reference (e.g. left over from a Solidworks process that has since
    been closed/restarted) raises pywintypes.com_error on any property access,
    even for something as cheap as .Visible.
    """
    try:
        _ = app.Visible
        return True
    except pywintypes.com_error:
        return False


def get_sw_app():
    """Attach to the already-running Solidworks application COM object, early-bound.

    Uses GetActiveObject (the Running Object Table) rather than Dispatch, so
    this binds to the visible instance the user already has open instead of
    silently spinning up a new hidden one. Re-validates the cached reference
    on every call so a Solidworks restart is detected instead of reusing a
    dead COM pointer.
    """
    global _sw_app
    if _sw_app is not None and _is_alive(_sw_app):
        return _sw_app

    try:
        raw = win32com.client.GetActiveObject(_PROG_ID)
    except pywintypes.com_error as e:
        _sw_app = None
        raise RuntimeError(
            f"No running Solidworks instance found via COM (GetActiveObject failed: {e}). "
            "Open Solidworks first, then retry."
        )

    gen_mod = _ensure_gen_module()
    _sw_app = gen_mod.ISldWorks(raw._oleobj_)
    return _sw_app


def get_active_doc():
    """Return the active model document, early-bound, reconnecting once if the cached app went stale."""
    app = get_sw_app()
    try:
        doc = app.ActiveDoc
    except (pywintypes.com_error, AttributeError):
        global _sw_app
        _sw_app = None
        app = get_sw_app()
        doc = app.ActiveDoc
    if doc is None:
        raise RuntimeError("No active document in Solidworks. Open or create a document first.")
    return _wrap(doc)


def get_diagnostics():
    """Report the attached Solidworks process(es) and currently open documents.

    Useful for debugging COM connection issues: distinguishes "no Solidworks
    running", "attached but no active doc", and "attached with N docs open".
    """
    pids = []
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq SLDWORKS.EXE", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.strip().splitlines():
            parts = [p.strip('"') for p in line.split('","')]
            if len(parts) >= 2:
                pids.append(parts[1])
    except Exception:
        pass

    try:
        app = get_sw_app()
    except RuntimeError as e:
        return {
            "sldworks_pids": pids,
            "com_attached": False,
            "error": str(e),
        }

    visible = None
    try:
        visible = app.Visible
    except pywintypes.com_error:
        pass

    # ISldWorks has no .Documents collection property, and GetFirstDocument()/
    # GetNext() don't resolve on this build either - only the active document
    # is reliably readable, so that's all we report.
    active_doc_title = None
    try:
        active = app.ActiveDoc
        if active is not None:
            active_doc_title = _wrap(active).GetTitle()
    except Exception:
        pass

    return {
        "sldworks_pids": pids,
        "com_attached": True,
        "visible": visible,
        "active_document": active_doc_title,
    }


def get_modeler():
    """Return the modeler object from the active document."""
    doc = get_active_doc()
    modeler = doc.GetModeler()
    if modeler is None:
        raise RuntimeError("Failed to get modeler from active document.")
    return modeler


def ensure_visible():
    """Make the Solidworks application window visible."""
    app = get_sw_app()
    app.Visible = True
    return "Solidworks is now visible."


# swDocumentTypes_e: the document-type argument OpenDoc6 requires must match
# the file being opened, or SolidWorks silently fails to load it correctly.
_DOC_TYPE_BY_EXT = {
    ".sldprt": 1,   # swDocPART
    ".sldasm": 2,   # swDocASSEMBLY
    ".slddrw": 3,   # swDocDRAWING
}


def open_document(filepath):
    """Open a Solidworks document at the given file path.

    Returns the opened IModelDoc2 object (not a string), so callers can chain
    further operations (e.g. building a drawing from it) without needing a
    separate get_active_doc() round trip.
    """
    app = get_sw_app()
    ext = os.path.splitext(filepath)[1].lower()
    doc_type = _DOC_TYPE_BY_EXT.get(ext, 1)
    doc = app.OpenDoc6(filepath, doc_type, 0, "", None, None)
    if doc is None:
        raise RuntimeError(f"Failed to open document: {filepath}")
    return doc


def save_document(filepath=None):
    """Save the current active document. If filepath is None, saves in place."""
    doc = get_active_doc()
    try:
        if filepath:
            errors = doc.SaveAs(filepath)
        else:
            errors = doc.Save3(0, None, None)
        if errors != 0:
            return f"Document saved with warnings (error code: {errors})"
        return f"Document saved successfully: {filepath or 'in place'}"
    except Exception as e:
        return f"Error saving document: {e}"


def close_document():
    """Close the current active document."""
    app = get_sw_app()
    doc = get_active_doc()
    try:
        title = doc.GetTitle()
        app.CloseDoc(title)
        return f"Closed document: {title}"
    except Exception as e:
        return f"Error closing document: {e}"
