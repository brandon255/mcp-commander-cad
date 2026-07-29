"""Drawing tools — MCP tool registrations for Onshape drawing operations.

Provides 5 tools covering drawing creation, view management, drawing listing,
and PDF export.  Each tool delegates to the ``OnshapeConnection`` REST client.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from onshape_mcp.api.connection import (
    OnshapeConnection,
    OnshapeConnectionError,
)

logger = logging.getLogger(__name__)


def register_drawing_tools(mcp: FastMCP) -> None:
    """Register all drawing-related tools on the given MCP server."""

    # ------------------------------------------------------------------
    # Create Drawing
    # ------------------------------------------------------------------

    @mcp.tool()
    async def create_drawing(
        doc_id: str,
        workspace_id: str,
        drawing_name: str,
        sheet_size: str = "A",
    ) -> str:
        """Create a new drawing in an Onshape document.

        Args:
            doc_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            drawing_name: Name for the new drawing.
            sheet_size: Sheet size — 'A', 'B', 'C', 'D', or 'E'.

        Returns:
            A confirmation message with the new drawing element ID.
        """
        try:
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            result = await conn.create_drawing(
                doc_id, workspace_id, drawing_name, sheet_size
            )
            element_id = result.get("id", "")
            name = result.get("name", drawing_name)
            return (
                f"Created drawing '{name}' (element_id={element_id}) "
                f"with sheet size '{sheet_size}' in document {doc_id}."
            )
        except OnshapeConnectionError as exc:
            return f"Error creating drawing: {exc}"

    # ------------------------------------------------------------------
    # Get Drawing Views
    # ------------------------------------------------------------------

    @mcp.tool()
    async def get_drawing_views(
        doc_id: str,
        workspace_id: str,
        element_id: str,
    ) -> str:
        """List all views in a drawing.

        Args:
            doc_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            element_id: The Drawing element ID.

        Returns:
            A formatted list of drawing views with their IDs and types.
        """
        try:
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            result = await conn.get_drawing(doc_id, workspace_id, element_id)
            sheets = result.get("sheets", [])
            views_list: list[str] = []
            for idx, sheet in enumerate(sheets):
                sheet_name = sheet.get("name", f"Sheet {idx + 1}")
                views = sheet.get("views", [])
                for view in views:
                    view_id = view.get("id", "?")
                    view_type = view.get("type", "unknown")
                    views_list.append(
                        f"  View: '{view.get('name', 'unnamed')}' "
                        f"(id={view_id}, type={view_type}, sheet='{sheet_name}')"
                    )
            if not views_list:
                return f"No views found in drawing {element_id}."
            header = f"Drawing views ({len(views_list)} total):\n"
            return header + "\n".join(views_list)
        except OnshapeConnectionError as exc:
            return f"Error getting drawing views: {exc}"

    # ------------------------------------------------------------------
    # Add Drawing View
    # ------------------------------------------------------------------

    @mcp.tool()
    async def add_drawing_view(
        doc_id: str,
        workspace_id: str,
        drawing_id: str,
        view_type: str = "front",
    ) -> str:
        """Add a standard view to a drawing.

        Args:
            doc_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            drawing_id: The Drawing element ID.
            view_type: Standard view type — 'front', 'back', 'top', 'bottom',
                'left', 'right', 'isometric', or 'trimetric'.

        Returns:
            A confirmation message with the new view details.
        """
        try:
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            view_data = {
                "viewType": view_type.lower(),
                "drawingId": drawing_id,
            }
            result = await conn._request(
                "POST",
                f"/documents/{doc_id}/workspaces/{workspace_id}"
                f"/drawings/{drawing_id}/views",
                json=view_data,
            )
            view_id = result.get("id", "")
            return (
                f"Added {view_type} view (view_id={view_id}) "
                f"to drawing {drawing_id}."
            )
        except OnshapeConnectionError as exc:
            return f"Error adding drawing view: {exc}"

    # ------------------------------------------------------------------
    # Export Drawing as PDF
    # ------------------------------------------------------------------

    @mcp.tool()
    async def export_drawing_pdf(
        doc_id: str,
        workspace_id: str,
        drawing_id: str,
        output_path: str = "",
    ) -> str:
        """Export a drawing to PDF format.

        Args:
            doc_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            drawing_id: The Drawing element ID to export.
            output_path: Optional local file path to save the PDF.
                If empty, returns the download URL.

        Returns:
            A confirmation with the export translation ID or download URL.
        """
        try:
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            result = await conn.export_pdf(doc_id, workspace_id, drawing_id)
            translation_id = result.get("id", "")
            return (
                f"Drawing PDF export started (translation_id={translation_id}). "
                f"Use get_export_status to check progress."
            )
        except OnshapeConnectionError as exc:
            return f"Error exporting drawing PDF: {exc}"

    # ------------------------------------------------------------------
    # List Drawings
    # ------------------------------------------------------------------

    @mcp.tool()
    async def list_drawings(
        doc_id: str,
        workspace_id: str,
    ) -> str:
        """List all drawings in an Onshape document.

        Args:
            doc_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.

        Returns:
            A formatted list of drawing elements with their IDs and names.
        """
        try:
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            elements = await conn.get_document_elements(doc_id, workspace_id)
            drawings = [e for e in elements if e.get("type") == "Drawing"]
            if not drawings:
                return "No drawings found in the document."
            drawing_list: list[str] = []
            for dwg in drawings:
                drawing_list.append(
                    f"  Drawing: '{dwg.get('name', 'unnamed')}' "
                    f"(id={dwg.get('id', '?')})"
                )
            header = f"Drawings in document ({len(drawings)} total):\n"
            return header + "\n".join(drawing_list)
        except OnshapeConnectionError as exc:
            return f"Error listing drawings: {exc}"
