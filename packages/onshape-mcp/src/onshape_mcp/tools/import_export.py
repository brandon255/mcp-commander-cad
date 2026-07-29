"""Import/Export tools — MCP tool registrations for Onshape file import and export.

Provides 6 tools covering file import (STL/STEP/IGES/OBJ upload), Part Studio
export (STL/STEP/IGES), drawing export (PDF), and translation job status
checking.  Each tool delegates to the ``OnshapeConnection`` REST client.
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


def register_import_export_tools(mcp: FastMCP) -> None:
    """Register all import/export-related tools on the given MCP server."""

    # ------------------------------------------------------------------
    # File Import
    # ------------------------------------------------------------------

    @mcp.tool()
    async def import_file(
        doc_id: str,
        workspace_id: str,
        element_name: str,
        file_path: str,
        format: str = "stl",
    ) -> str:
        """Upload an STL, STEP, IGES, or OBJ file to an Onshape document.

        Args:
            doc_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            element_name: Name for the imported element in Onshape.
            file_path: Local filesystem path to the file to upload.
            format: File format — 'stl', 'step', 'iges', or 'obj'.

        Returns:
            A confirmation message with the new element ID.
        """
        try:
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            result = await conn.import_file(
                doc_id=doc_id,
                wid=workspace_id,
                element_name=element_name,
                file_path=file_path,
                file_format=format,
            )
            element_id = result.get("id", "")
            name = result.get("name", element_name)
            return (
                f"Imported file '{file_path}' as '{name}' "
                f"(element_id={element_id}) in document {doc_id}."
            )
        except OnshapeConnectionError as exc:
            return f"Error importing file: {exc}"

    # ------------------------------------------------------------------
    # Part Studio Export — STL
    # ------------------------------------------------------------------

    @mcp.tool()
    async def export_stl(
        doc_id: str,
        workspace_id: str,
        element_id: str,
        output_path: str = "",
    ) -> str:
        """Export a Part Studio as STL.

        Args:
            doc_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            element_id: The Part Studio element ID to export.
            output_path: Optional local file path to save the export.
                If empty, returns the download URL.

        Returns:
            A confirmation with the export translation ID or download URL.
        """
        try:
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            result = await conn.export_stl(doc_id, workspace_id, element_id)
            translation_id = result.get("id", "")
            return (
                f"STL export started (translation_id={translation_id}). "
                f"Use get_export_status to check progress."
            )
        except OnshapeConnectionError as exc:
            return f"Error exporting STL: {exc}"

    # ------------------------------------------------------------------
    # Part Studio Export — STEP
    # ------------------------------------------------------------------

    @mcp.tool()
    async def export_step(
        doc_id: str,
        workspace_id: str,
        element_id: str,
        output_path: str = "",
    ) -> str:
        """Export a Part Studio as STEP.

        Args:
            doc_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            element_id: The Part Studio element ID to export.
            output_path: Optional local file path to save the export.
                If empty, returns the download URL.

        Returns:
            A confirmation with the export translation ID or download URL.
        """
        try:
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            result = await conn.export_step(doc_id, workspace_id, element_id)
            translation_id = result.get("id", "")
            return (
                f"STEP export started (translation_id={translation_id}). "
                f"Use get_export_status to check progress."
            )
        except OnshapeConnectionError as exc:
            return f"Error exporting STEP: {exc}"

    # ------------------------------------------------------------------
    # Part Studio Export — IGES
    # ------------------------------------------------------------------

    @mcp.tool()
    async def export_iges(
        doc_id: str,
        workspace_id: str,
        element_id: str,
        output_path: str = "",
    ) -> str:
        """Export a Part Studio as IGES.

        Args:
            doc_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            element_id: The Part Studio element ID to export.
            output_path: Optional local file path to save the export.
                If empty, returns the download URL.

        Returns:
            A confirmation with the export translation ID or download URL.
        """
        try:
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            result = await conn.export_iges(doc_id, workspace_id, element_id)
            translation_id = result.get("id", "")
            return (
                f"IGES export started (translation_id={translation_id}). "
                f"Use get_export_status to check progress."
            )
        except OnshapeConnectionError as exc:
            return f"Error exporting IGES: {exc}"

    # ------------------------------------------------------------------
    # Drawing Export — PDF
    # ------------------------------------------------------------------

    @mcp.tool()
    async def export_pdf(
        doc_id: str,
        workspace_id: str,
        element_id: str,
        output_path: str = "",
    ) -> str:
        """Export a Drawing as PDF.

        Args:
            doc_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            element_id: The Drawing element ID to export.
            output_path: Optional local file path to save the export.
                If empty, returns the download URL.

        Returns:
            A confirmation with the export translation ID or download URL.
        """
        try:
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            result = await conn.export_pdf(doc_id, workspace_id, element_id)
            translation_id = result.get("id", "")
            return (
                f"PDF export started (translation_id={translation_id}). "
                f"Use get_export_status to check progress."
            )
        except OnshapeConnectionError as exc:
            return f"Error exporting PDF: {exc}"

    # ------------------------------------------------------------------
    # Translation Status
    # ------------------------------------------------------------------

    @mcp.tool()
    async def get_export_status(
        doc_id: str,
        workspace_id: str,
        translation_id: str,
    ) -> str:
        """Check the status of an export or import translation job.

        Args:
            doc_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            translation_id: The translation job ID returned by an
                import or export call.

        Returns:
            The current translation status (e.g. 'DONE', 'ACTIVE', 'FAILED').
        """
        try:
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            result = await conn.get_translation_status(translation_id)
            state = result.get("requestState", "UNKNOWN")
            return json.dumps(
                {
                    "translation_id": translation_id,
                    "status": state,
                    "result": result,
                },
                indent=2,
                default=str,
            )
        except OnshapeConnectionError as exc:
            return f"Error checking export status: {exc}"
