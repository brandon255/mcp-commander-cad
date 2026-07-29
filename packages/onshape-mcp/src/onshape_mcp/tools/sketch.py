"""Sketch tools — MCP tool registrations for Onshape sketch operations.

Provides 12 tools covering sketch creation, geometric entities (lines,
circles, arcs, rectangles, ellipses, splines), entity editing (offset,
pattern), constraints, and dimensions.
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


async def _send(
    command: str, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Send a request through the global Onshape connection.

    Returns the result dict on success or raises ``OnshapeConnectionError``.
    """
    conn = OnshapeConnection.get_global()
    if not conn.is_connected():
        await conn.connect()
    return await conn._request(command, json=params)


def register_sketch_tools(mcp: FastMCP) -> None:
    """Register all sketch-related tools on the given MCP server."""

    # ------------------------------------------------------------------
    # Sketch creation
    # ------------------------------------------------------------------

    @mcp.tool()
    async def create_sketch(
        document_id: str,
        workspace_id: str,
        plane: str = "XY",
    ) -> str:
        """Create a new sketch on a reference plane in an Onshape Part Studio.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID within the document.
            plane: Reference plane for the sketch ('XY', 'XZ', 'YZ', or a face ID).

        Returns:
            A confirmation message with the new sketch element ID.
        """
        try:
            # Find the Part Studio element in the workspace
            elements = await OnshapeConnection.get_global().get_document_elements(
                document_id, workspace_id
            )
            part_studios = [e for e in elements if e.get("type") == "Part Studio"]
            if not part_studios:
                return "Error: No Part Studio found in the document workspace."

            eid = part_studios[0]["id"]

            # Create sketch feature via the features API
            sketch_data = {
                "feature": {
                    "type": "sketch",
                    "typeName": "Sketch",
                    "parameters": {
                        "sketchPlane": {
                            "typeName": "Plane",
                            "parameters": {
                                "planeType": plane.upper(),
                            },
                        },
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, eid, sketch_data
            )
            feature_id = result.get("featureId", "")
            return (
                f"Created sketch on plane '{plane}' in Part Studio '{part_studios[0].get('name', '')}'. "
                f"Feature ID: {feature_id}"
            )
        except OnshapeConnectionError as exc:
            return f"Error creating sketch: {exc}"

    # ------------------------------------------------------------------
    # Geometric entities
    # ------------------------------------------------------------------

    @mcp.tool()
    async def sketch_line(
        document_id: str,
        workspace_id: str,
        element_id: str,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
    ) -> str:
        """Draw a line segment between two points in a sketch.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID.
            element_id: The Part Studio element ID containing the sketch.
            start_x: Start point X coordinate (meters).
            start_y: Start point Y coordinate (meters).
            end_x: End point X coordinate (meters).
            end_y: End point Y coordinate (meters).

        Returns:
            Confirmation with line endpoints.
        """
        try:
            line_data = {
                "feature": {
                    "type": "sketchLine",
                    "typeName": "Sketch Line",
                    "parameters": {
                        "startPoint": {"x": start_x, "y": start_y},
                        "endPoint": {"x": end_x, "y": end_y},
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, line_data
            )
            fid = result.get("featureId", "")
            return (
                f"Created line (feature={fid}) from ({start_x}, {start_y}) "
                f"to ({end_x}, {end_y})."
            )
        except OnshapeConnectionError as exc:
            return f"Error drawing line: {exc}"

    @mcp.tool()
    async def sketch_circle(
        document_id: str,
        workspace_id: str,
        element_id: str,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> str:
        """Draw a circle defined by center point and radius.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID.
            element_id: The Part Studio element ID.
            center_x: Center X coordinate (meters).
            center_y: Center Y coordinate (meters).
            radius: Circle radius in meters, must be positive.

        Returns:
            Confirmation with center and radius.
        """
        try:
            circle_data = {
                "feature": {
                    "type": "sketchCircle",
                    "typeName": "Sketch Circle",
                    "parameters": {
                        "center": {"x": center_x, "y": center_y},
                        "radius": radius,
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, circle_data
            )
            fid = result.get("featureId", "")
            return f"Created circle (feature={fid}) at ({center_x}, {center_y}) with radius {radius}."
        except OnshapeConnectionError as exc:
            return f"Error drawing circle: {exc}"

    @mcp.tool()
    async def sketch_arc(
        document_id: str,
        workspace_id: str,
        element_id: str,
        center_x: float,
        center_y: float,
        start_angle: float,
        end_angle: float,
        radius: float,
    ) -> str:
        """Draw an arc defined by center, angle range, and radius.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID.
            element_id: The Part Studio element ID.
            center_x: Arc center X coordinate (meters).
            center_y: Arc center Y coordinate (meters).
            start_angle: Start angle in degrees.
            end_angle: End angle in degrees.
            radius: Arc radius in meters.

        Returns:
            Confirmation with arc parameters.
        """
        try:
            arc_data = {
                "feature": {
                    "type": "sketchArc",
                    "typeName": "Sketch Arc",
                    "parameters": {
                        "center": {"x": center_x, "y": center_y},
                        "startAngle": start_angle,
                        "endAngle": end_angle,
                        "radius": radius,
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, arc_data
            )
            fid = result.get("featureId", "")
            return (
                f"Created arc (feature={fid}) at ({center_x}, {center_y}) "
                f"from {start_angle}° to {end_angle}° with radius {radius}."
            )
        except OnshapeConnectionError as exc:
            return f"Error drawing arc: {exc}"

    @mcp.tool()
    async def sketch_rectangle(
        document_id: str,
        workspace_id: str,
        element_id: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> str:
        """Draw an axis-aligned rectangle.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID.
            element_id: The Part Studio element ID.
            x: Bottom-left corner X coordinate (meters).
            y: Bottom-left corner Y coordinate (meters).
            width: Rectangle width in meters.
            height: Rectangle height in meters.

        Returns:
            Confirmation with rectangle dimensions.
        """
        try:
            rect_data = {
                "feature": {
                    "type": "sketchRectangle",
                    "typeName": "Sketch Rectangle",
                    "parameters": {
                        "corner": {"x": x, "y": y},
                        "width": width,
                        "height": height,
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, rect_data
            )
            fid = result.get("featureId", "")
            return (
                f"Created rectangle (feature={fid}) at ({x}, {y}) "
                f"with width={width}, height={height}."
            )
        except OnshapeConnectionError as exc:
            return f"Error drawing rectangle: {exc}"

    @mcp.tool()
    async def sketch_ellipse(
        document_id: str,
        workspace_id: str,
        element_id: str,
        center_x: float,
        center_y: float,
        major_radius: float,
        minor_radius: float,
    ) -> str:
        """Draw an ellipse defined by center and two radii.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID.
            element_id: The Part Studio element ID.
            center_x: Ellipse center X coordinate (meters).
            center_y: Ellipse center Y coordinate (meters).
            major_radius: Major (X) radius in meters.
            minor_radius: Minor (Y) radius in meters.

        Returns:
            Confirmation with ellipse parameters.
        """
        try:
            ellipse_data = {
                "feature": {
                    "type": "sketchEllipse",
                    "typeName": "Sketch Ellipse",
                    "parameters": {
                        "center": {"x": center_x, "y": center_y},
                        "majorRadius": major_radius,
                        "minorRadius": minor_radius,
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, ellipse_data
            )
            fid = result.get("featureId", "")
            return (
                f"Created ellipse (feature={fid}) at ({center_x}, {center_y}) "
                f"with major_radius={major_radius}, minor_radius={minor_radius}."
            )
        except OnshapeConnectionError as exc:
            return f"Error drawing ellipse: {exc}"

    @mcp.tool()
    async def sketch_spline(
        document_id: str,
        workspace_id: str,
        element_id: str,
        points: str,
    ) -> str:
        """Draw a spline through a series of control points.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID.
            element_id: The Part Studio element ID.
            points: JSON array of [x, y] coordinate pairs, e.g.
                '[[0, 0], [0.01, 0.005], [0.02, 0.01]]'.

        Returns:
            Confirmation with the number of spline control points.
        """
        try:
            parsed_points = json.loads(points)
            if not isinstance(parsed_points, list) or len(parsed_points) < 2:
                return "Error: 'points' must be a JSON array of at least 2 [x, y] pairs."

            spline_data = {
                "feature": {
                    "type": "sketchSpline",
                    "typeName": "Sketch Spline",
                    "parameters": {
                        "points": [
                            {"x": p[0], "y": p[1]} for p in parsed_points
                        ],
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, spline_data
            )
            fid = result.get("featureId", "")
            return f"Created spline (feature={fid}) through {len(parsed_points)} control points."
        except (json.JSONDecodeError, IndexError, TypeError) as exc:
            return f"Error parsing points: {exc}"
        except OnshapeConnectionError as exc:
            return f"Error drawing spline: {exc}"

    # ------------------------------------------------------------------
    # Entity editing
    # ------------------------------------------------------------------

    @mcp.tool()
    async def sketch_offset(
        document_id: str,
        workspace_id: str,
        element_id: str,
        distance: float,
    ) -> str:
        """Offset selected sketch entities by a specified distance.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID.
            element_id: The Part Studio element ID.
            distance: Offset distance in meters (positive = outward).

        Returns:
            Confirmation with the offset distance applied.
        """
        try:
            offset_data = {
                "feature": {
                    "type": "sketchOffset",
                    "typeName": "Sketch Offset",
                    "parameters": {
                        "distance": distance,
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, offset_data
            )
            fid = result.get("featureId", "")
            return f"Applied sketch offset (feature={fid}) with distance {distance}m."
        except OnshapeConnectionError as exc:
            return f"Error applying offset: {exc}"

    @mcp.tool()
    async def sketch_pattern(
        document_id: str,
        workspace_id: str,
        element_id: str,
        pattern_type: str,
        count: int,
        spacing: float,
    ) -> str:
        """Pattern (duplicate) sketch entities in a linear or circular arrangement.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID.
            element_id: The Part Studio element ID.
            pattern_type: Pattern type ('linear' or 'circular').
            count: Number of pattern instances (including original).
            spacing: Spacing between instances in meters (linear) or
                total angle in degrees (circular).

        Returns:
            Confirmation with pattern parameters.
        """
        try:
            pattern_data = {
                "feature": {
                    "type": "sketchPattern",
                    "typeName": "Sketch Pattern",
                    "parameters": {
                        "patternType": pattern_type,
                        "count": count,
                        "spacing": spacing,
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, pattern_data
            )
            fid = result.get("featureId", "")
            return (
                f"Created {pattern_type} sketch pattern (feature={fid}) "
                f"with {count} instances and spacing={spacing}."
            )
        except OnshapeConnectionError as exc:
            return f"Error creating sketch pattern: {exc}"

    # ------------------------------------------------------------------
    # Constraints and dimensions
    # ------------------------------------------------------------------

    @mcp.tool()
    async def add_constraint(
        document_id: str,
        workspace_id: str,
        element_id: str,
        constraint_type: str,
        entities: str,
    ) -> str:
        """Add a geometric constraint to sketch entities.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID.
            element_id: The Part Studio element ID.
            constraint_type: Constraint type (e.g. 'horizontal', 'vertical',
                'coincident', 'tangent', 'parallel', 'perpendicular',
                'equal', 'concentric', 'fixed').
            entities: JSON array of entity IDs to constrain,
                e.g. '["entity1", "entity2"]'.

        Returns:
            Confirmation with constraint type and affected entities.
        """
        try:
            parsed_entities = json.loads(entities)
            constraint_data = {
                "feature": {
                    "type": "sketchConstraint",
                    "typeName": "Sketch Constraint",
                    "parameters": {
                        "constraintType": constraint_type,
                        "entities": parsed_entities,
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, constraint_data
            )
            fid = result.get("featureId", "")
            return (
                f"Added {constraint_type} constraint (feature={fid}) "
                f"to {len(parsed_entities)} entities."
            )
        except (json.JSONDecodeError, TypeError) as exc:
            return f"Error parsing entities: {exc}"
        except OnshapeConnectionError as exc:
            return f"Error adding constraint: {exc}"

    @mcp.tool()
    async def add_dimension(
        document_id: str,
        workspace_id: str,
        element_id: str,
        dimension_type: str,
        value: float,
        entities: str,
    ) -> str:
        """Add a dimension constraint to sketch entities.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID.
            element_id: The Part Studio element ID.
            dimension_type: Dimension type (e.g. 'distance', 'angle',
                'radius', 'diameter', 'length').
            value: Dimension value in meters (or degrees for angle).
            entities: JSON array of entity IDs to dimension,
                e.g. '["entity1", "entity2"]'.

        Returns:
            Confirmation with dimension type and value.
        """
        try:
            parsed_entities = json.loads(entities)
            dimension_data = {
                "feature": {
                    "type": "sketchDimension",
                    "typeName": "Sketch Dimension",
                    "parameters": {
                        "dimensionType": dimension_type,
                        "value": value,
                        "entities": parsed_entities,
                    },
                },
            }
            result = await OnshapeConnection.get_global().create_feature(
                document_id, workspace_id, element_id, dimension_data
            )
            fid = result.get("featureId", "")
            return (
                f"Added {dimension_type} dimension (feature={fid}) "
                f"with value {value} to {len(parsed_entities)} entities."
            )
        except (json.JSONDecodeError, TypeError) as exc:
            return f"Error parsing entities: {exc}"
        except OnshapeConnectionError as exc:
            return f"Error adding dimension: {exc}"

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    @mcp.tool()
    async def list_sketches(
        document_id: str,
        workspace_id: str,
    ) -> str:
        """List all sketch features in the document's Part Studios.

        Args:
            document_id: The Onshape document ID.
            workspace_id: The workspace ID.

        Returns:
            A formatted list of sketch features with their IDs and names.
        """
        try:
            conn = OnshapeConnection.get_global()
            if not conn.is_connected():
                await conn.connect()
            elements = await conn.get_document_elements(
                document_id, workspace_id
            )
            part_studios = [e for e in elements if e.get("type") == "Part Studio"]

            if not part_studios:
                return "No Part Studios found in the document."

            sketch_list: list[str] = []
            for ps in part_studios:
                ps_name = ps.get("name", "unnamed")
                ps_eid = ps.get("id", "")
                try:
                    features = await conn.list_features(
                        document_id, workspace_id, ps_eid
                    )
                    sketches = [f for f in features if f.get("typeName", "").lower() == "sketch"]
                    for sk in sketches:
                        sketch_list.append(
                            f"  Sketch: '{sk.get('name', 'unnamed')}' "
                            f"(id={sk.get('id', '?')}, "
                            f"Part Studio='{ps_name}')"
                        )
                except OnshapeConnectionError:
                    sketch_list.append(f"  Part Studio '{ps_name}': unable to list features")

            if not sketch_list:
                return f"No sketches found in {len(part_studios)} Part Studio(s)."

            header = f"Sketches in document (Part Studios: {len(part_studios)}):\n"
            return header + "\n".join(sketch_list)
        except OnshapeConnectionError as exc:
            return f"Error listing sketches: {exc}"
