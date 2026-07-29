"""Assembly tools — MCP tool registrations for Onshape assembly operations.

Provides 5 tools covering assembly creation, structure inspection, instance
listing, mate constraint insertion, and assembly listing.  Each tool
delegates to the ``OnshapeConnection`` REST client.
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


def register_assembly_tools(mcp: FastMCP) -> None:
    """Register all assembly-related tools on the given MCP server."""

    # ------------------------------------------------------------------
    # Get Assembly Structure
    # ------------------------------------------------------------------

    @mcp.tool()
    async def get_assembly_structure(
        doc_id: str,
        workspace_id: str,
        element_id: str,
    ) -> str:
        """Get the full assembly tree structure.

        Args:
            doc_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            element_id: The Assembly element ID.

        Returns:
            A JSON-formatted string with the assembly structure including
            root assembly, instances, occurrences, and mates.
        """
        try:
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            result = await conn.get_assembly(doc_id, workspace_id, element_id)
            return json.dumps(result, indent=2, default=str)
        except OnshapeConnectionError as exc:
            return f"Error getting assembly structure: {exc}"

    # ------------------------------------------------------------------
    # List Assembly Instances
    # ------------------------------------------------------------------

    @mcp.tool()
    async def list_assembly_instances(
        doc_id: str,
        workspace_id: str,
        element_id: str,
    ) -> str:
        """List all instances in an assembly.

        Args:
            doc_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            element_id: The Assembly element ID.

        Returns:
            A formatted list of assembly instances with their IDs, paths,
            and types.
        """
        try:
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            instances = await conn.list_assembly_instances(
                doc_id, workspace_id, element_id
            )
            if not instances:
                return "No instances found in the assembly."
            instance_list: list[str] = []
            for inst in instances:
                instance_list.append(
                    f"  Instance: '{inst.get('name', 'unnamed')}' "
                    f"(id={inst.get('id', '?')}, "
                    f"type={inst.get('type', '?')})"
                )
            header = f"Assembly instances ({len(instances)} total):\n"
            return header + "\n".join(instance_list)
        except OnshapeConnectionError as exc:
            return f"Error listing assembly instances: {exc}"

    # ------------------------------------------------------------------
    # Add Mate
    # ------------------------------------------------------------------

    @mcp.tool()
    async def add_mate(
        doc_id: str,
        workspace_id: str,
        assembly_id: str,
        mate_type: str = "fastened",
        mate_data: str = "{}",
    ) -> str:
        """Insert a mate constraint into an assembly.

        Args:
            doc_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            assembly_id: The Assembly element ID.
            mate_type: Type of mate — 'fastened', 'revolute', 'slider',
                'planar', 'cylindrical', 'pin_slot', 'ball', 'parallel',
                'tangent', 'distance', 'angle', or 'coincident'.
            mate_data: JSON string with mate definition including
                'matedEntities' array and any additional parameters.
                Example: '{"matedEntities": [{"entityA": "...", "entityB": "..."}]}'

        Returns:
            A confirmation with the created mate's ID.
        """
        try:
            parsed_data = json.loads(mate_data)
            parsed_data["mateType"] = mate_type
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            result = await conn.insert_mate(
                doc_id, workspace_id, assembly_id, parsed_data
            )
            mate_id = result.get("id", "")
            return (
                f"Added {mate_type} mate (mate_id={mate_id}) "
                f"to assembly {assembly_id}."
            )
        except (json.JSONDecodeError, TypeError) as exc:
            return f"Error parsing mate data: {exc}"
        except OnshapeConnectionError as exc:
            return f"Error adding mate: {exc}"

    # ------------------------------------------------------------------
    # Create Assembly
    # ------------------------------------------------------------------

    @mcp.tool()
    async def create_assembly(
        doc_id: str,
        workspace_id: str,
        name: str,
    ) -> str:
        """Create a new empty assembly element in an Onshape document.

        Args:
            doc_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            name: Name for the new assembly.

        Returns:
            A confirmation message with the new assembly element ID.
        """
        try:
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            result = await conn.create_assembly_element(
                doc_id, workspace_id, name
            )
            element_id = result.get("id", "")
            assembly_name = result.get("name", name)
            return (
                f"Created assembly '{assembly_name}' "
                f"(element_id={element_id}) in document {doc_id}."
            )
        except OnshapeConnectionError as exc:
            return f"Error creating assembly: {exc}"

    # ------------------------------------------------------------------
    # List Assemblies
    # ------------------------------------------------------------------

    @mcp.tool()
    async def list_assemblies(
        doc_id: str,
        workspace_id: str,
    ) -> str:
        """List all assemblies in an Onshape document.

        Args:
            doc_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.

        Returns:
            A formatted list of assembly elements with their IDs and names.
        """
        try:
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            elements = await conn.get_document_elements(doc_id, workspace_id)
            assemblies = [e for e in elements if e.get("type") == "Assembly"]
            if not assemblies:
                return "No assemblies found in the document."
            assembly_list: list[str] = []
            for asm in assemblies:
                assembly_list.append(
                    f"  Assembly: '{asm.get('name', 'unnamed')}' "
                    f"(id={asm.get('id', '?')})"
                )
            header = f"Assemblies in document ({len(assemblies)} total):\n"
            return header + "\n".join(assembly_list)
        except OnshapeConnectionError as exc:
            return f"Error listing assemblies: {exc}"
