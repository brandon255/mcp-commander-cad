"""Feature tools — MCP tool registrations for Onshape feature operations.

Provides 8 tools covering part-modification features: extrude, revolve,
fillet, chamfer, pattern, mirror, shell, and boolean.  Each tool follows
the same convention as the sketch tools — accepting ``document_id``,
``workspace_id``, and ``element_id`` plus feature-specific parameters,
and delegating to ``OnshapeConnection.get_global().create_feature()``.
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


def register_feature_tools(mcp: FastMCP) -> None:
    """Register all feature-related tools on the given MCP server."""

    # ------------------------------------------------------------------
    # Extrude
    # ------------------------------------------------------------------

    @mcp.tool()
    async def extrude_feature(
        document_id: str,
        workspace_id: str,
        element_id: str,
        depth: float,
        direction: str = "one_sided",
        operation: str = "new",
    ) -> str:
        """Create an extrude feature from a sketch profile.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            element_id: The Part Studio element ID.
            depth: Extrusion depth in meters (must be positive).
            direction: Extrude direction — 'one_sided', 'two_sided', or 'symmetric'.
            operation: Boolean operation — 'new', 'add', 'remove', or 'intersect'.

        Returns:
            Confirmation with the new feature ID.
        """
        try:
            feature_data = {
                "feature": {
                    "type": "extrude",
                    "typeName": "Extrude",
                    "parameters": {
                        "depth": depth,
                        "direction": direction,
                        "operationType": operation,
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, feature_data
            )
            fid = result.get("featureId", "")
            return (
                f"Created extrude feature (id={fid}) with "
                f"depth={depth}m, direction={direction}, operation={operation}."
            )
        except OnshapeConnectionError as exc:
            return f"Error creating extrude feature: {exc}"

    # ------------------------------------------------------------------
    # Revolve
    # ------------------------------------------------------------------

    @mcp.tool()
    async def revolve_feature(
        document_id: str,
        workspace_id: str,
        element_id: str,
        angle: float,
        axis: str = "x",
        operation: str = "new",
    ) -> str:
        """Create a revolve feature from a sketch profile.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            element_id: The Part Studio element ID.
            angle: Revolution angle in degrees.
            axis: Axis of revolution — 'x', 'y', or 'z'.
            operation: Boolean operation — 'new', 'add', 'remove', or 'intersect'.

        Returns:
            Confirmation with the new feature ID.
        """
        try:
            feature_data = {
                "feature": {
                    "type": "revolve",
                    "typeName": "Revolve",
                    "parameters": {
                        "angle": angle,
                        "axis": axis,
                        "operationType": operation,
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, feature_data
            )
            fid = result.get("featureId", "")
            return (
                f"Created revolve feature (id={fid}) with "
                f"angle={angle}°, axis={axis}, operation={operation}."
            )
        except OnshapeConnectionError as exc:
            return f"Error creating revolve feature: {exc}"

    # ------------------------------------------------------------------
    # Fillet
    # ------------------------------------------------------------------

    @mcp.tool()
    async def fillet_feature(
        document_id: str,
        workspace_id: str,
        element_id: str,
        radius: float,
        edges: str = "[]",
    ) -> str:
        """Apply fillets to edges in an Onshape part.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            element_id: The Part Studio element ID.
            radius: Fillet radius in meters (must be positive).
            edges: JSON array of edge IDs to fillet, e.g.
                '["edge1", "edge2"]'.  Empty applies to all selected edges.

        Returns:
            Confirmation with the new feature ID.
        """
        try:
            parsed_edges = json.loads(edges)
            feature_data = {
                "feature": {
                    "type": "fillet",
                    "typeName": "Fillet",
                    "parameters": {
                        "radius": radius,
                        "edges": parsed_edges,
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, feature_data
            )
            fid = result.get("featureId", "")
            return (
                f"Created fillet feature (id={fid}) with "
                f"radius={radius}m on {len(parsed_edges)} edge(s)."
            )
        except (json.JSONDecodeError, TypeError) as exc:
            return f"Error parsing edges: {exc}"
        except OnshapeConnectionError as exc:
            return f"Error creating fillet feature: {exc}"

    # ------------------------------------------------------------------
    # Chamfer
    # ------------------------------------------------------------------

    @mcp.tool()
    async def chamfer_feature(
        document_id: str,
        workspace_id: str,
        element_id: str,
        distance: float,
        edges: str = "[]",
        chamfer_type: str = "equal",
    ) -> str:
        """Apply chamfers to edges in an Onshape part.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            element_id: The Part Studio element ID.
            distance: Chamfer distance in meters (must be positive).
            edges: JSON array of edge IDs to chamfer, e.g.
                '["edge1", "edge2"]'.  Empty applies to all selected edges.
            chamfer_type: Chamfer style — 'equal' (symmetric) or 'distance_angle'.

        Returns:
            Confirmation with the new feature ID.
        """
        try:
            parsed_edges = json.loads(edges)
            feature_data = {
                "feature": {
                    "type": "chamfer",
                    "typeName": "Chamfer",
                    "parameters": {
                        "distance": distance,
                        "chamferType": chamfer_type,
                        "edges": parsed_edges,
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, feature_data
            )
            fid = result.get("featureId", "")
            return (
                f"Created chamfer feature (id={fid}) with "
                f"distance={distance}m, type={chamfer_type} on {len(parsed_edges)} edge(s)."
            )
        except (json.JSONDecodeError, TypeError) as exc:
            return f"Error parsing edges: {exc}"
        except OnshapeConnectionError as exc:
            return f"Error creating chamfer feature: {exc}"

    # ------------------------------------------------------------------
    # Pattern
    # ------------------------------------------------------------------

    @mcp.tool()
    async def pattern_feature(
        document_id: str,
        workspace_id: str,
        element_id: str,
        pattern_type: str,
        count: int,
        spacing: float,
        instances: str = "[]",
    ) -> str:
        """Create a linear or circular pattern of features.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            element_id: The Part Studio element ID.
            pattern_type: Pattern type — 'linear' or 'circular'.
            count: Total number of pattern instances (including original).
            spacing: Spacing between instances in meters (linear) or
                total angle in degrees (circular).
            instances: JSON array of feature IDs to pattern, e.g.
                '["feature1", "feature2"]'.

        Returns:
            Confirmation with the new feature ID.
        """
        try:
            parsed_instances = json.loads(instances)
            feature_data = {
                "feature": {
                    "type": "pattern",
                    "typeName": "Pattern",
                    "parameters": {
                        "patternType": pattern_type,
                        "count": count,
                        "spacing": spacing,
                        "instances": parsed_instances,
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, feature_data
            )
            fid = result.get("featureId", "")
            return (
                f"Created {pattern_type} pattern feature (id={fid}) with "
                f"{count} instances, spacing={spacing}, patterning {len(parsed_instances)} feature(s)."
            )
        except (json.JSONDecodeError, TypeError) as exc:
            return f"Error parsing instances: {exc}"
        except OnshapeConnectionError as exc:
            return f"Error creating pattern feature: {exc}"

    # ------------------------------------------------------------------
    # Mirror
    # ------------------------------------------------------------------

    @mcp.tool()
    async def mirror_feature(
        document_id: str,
        workspace_id: str,
        element_id: str,
        plane: str = "XY",
        instances: str = "[]",
    ) -> str:
        """Mirror features about a plane.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            element_id: The Part Studio element ID.
            plane: Mirror plane — 'XY', 'XZ', 'YZ', or a face ID.
            instances: JSON array of feature IDs to mirror, e.g.
                '["feature1", "feature2"]'.

        Returns:
            Confirmation with the new feature ID.
        """
        try:
            parsed_instances = json.loads(instances)
            feature_data = {
                "feature": {
                    "type": "mirror",
                    "typeName": "Mirror",
                    "parameters": {
                        "mirrorPlane": plane,
                        "instances": parsed_instances,
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, feature_data
            )
            fid = result.get("featureId", "")
            return (
                f"Created mirror feature (id={fid}) about plane '{plane}', "
                f"mirroring {len(parsed_instances)} feature(s)."
            )
        except (json.JSONDecodeError, TypeError) as exc:
            return f"Error parsing instances: {exc}"
        except OnshapeConnectionError as exc:
            return f"Error creating mirror feature: {exc}"

    # ------------------------------------------------------------------
    # Shell
    # ------------------------------------------------------------------

    @mcp.tool()
    async def shell_feature(
        document_id: str,
        workspace_id: str,
        element_id: str,
        thickness: float,
        faces: str = "[]",
    ) -> str:
        """Create a shell by removing faces from a part.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            element_id: The Part Studio element ID.
            thickness: Shell wall thickness in meters (must be positive).
            faces: JSON array of face IDs to remove, e.g.
                '["face1", "face2"]'.

        Returns:
            Confirmation with the new feature ID.
        """
        try:
            parsed_faces = json.loads(faces)
            feature_data = {
                "feature": {
                    "type": "shell",
                    "typeName": "Shell",
                    "parameters": {
                        "thickness": thickness,
                        "facesToRemove": parsed_faces,
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, feature_data
            )
            fid = result.get("featureId", "")
            return (
                f"Created shell feature (id={fid}) with "
                f"thickness={thickness}m, removing {len(parsed_faces)} face(s)."
            )
        except (json.JSONDecodeError, TypeError) as exc:
            return f"Error parsing faces: {exc}"
        except OnshapeConnectionError as exc:
            return f"Error creating shell feature: {exc}"

    # ------------------------------------------------------------------
    # Boolean
    # ------------------------------------------------------------------

    @mcp.tool()
    async def boolean_feature(
        document_id: str,
        workspace_id: str,
        element_id: str,
        operation: str = "union",
        targets: str = "[]",
    ) -> str:
        """Perform boolean operations between parts.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            element_id: The Part Studio element ID.
            operation: Boolean operation type — 'union', 'subtract', or 'intersect'.
            targets: JSON array of part/feature IDs to combine with, e.g.
                '["partId1", "partId2"]'.

        Returns:
            Confirmation with the new feature ID.
        """
        try:
            parsed_targets = json.loads(targets)
            feature_data = {
                "feature": {
                    "type": "boolean",
                    "typeName": "Boolean",
                    "parameters": {
                        "booleanType": operation,
                        "targets": parsed_targets,
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, feature_data
            )
            fid = result.get("featureId", "")
            return (
                f"Created boolean {operation} feature (id={fid}) "
                f"with {len(parsed_targets)} target(s)."
            )
        except (json.JSONDecodeError, TypeError) as exc:
            return f"Error parsing targets: {exc}"
        except OnshapeConnectionError as exc:
            return f"Error creating boolean feature: {exc}"
