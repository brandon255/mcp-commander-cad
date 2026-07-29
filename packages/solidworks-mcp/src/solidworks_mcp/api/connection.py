"""
Solidworks COM connection manager.
Singleton pattern for managing the Solidworks application instance.
"""
import win32com.client

_sw_app = None

def get_sw_app():
    """Get or create the Solidworks application COM object."""
    global _sw_app
    if _sw_app is None:
        try:
            _sw_app = win32com.client.Dispatch("SldWorks.Application")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Solidworks via COM: {e}. Ensure Solidworks is installed and running.")
    return _sw_app

def get_active_doc():
    """Return the active model document."""
    app = get_sw_app()
    doc = app.ActiveDoc
    if doc is None:
        raise RuntimeError("No active document in Solidworks. Open or create a document first.")
    return doc

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

def open_document(filepath):
    """Open a Solidworks document at the given file path."""
    app = get_sw_app()
    try:
        doc = app.OpenDoc6(filepath, 1, 0, "", None, None)
        if doc is None:
            raise RuntimeError(f"Failed to open document: {filepath}")
        app.ActivateDoc3(filepath, False, 0, None)
        return f"Opened document: {filepath}"
    except Exception as e:
        return f"Error opening document {filepath}: {e}"

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
