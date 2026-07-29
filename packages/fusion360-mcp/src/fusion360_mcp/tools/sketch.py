"""Sketch tools — MCP tool registrations for Fusion 360 sketch operations.

Provides 24 tools covering sketch creation, geometric entities (lines,
circles, arcs, rectangles, polygons, ellipses, splines, slots, text),
entity editing (offset, project, trim, extend), patterns, and
constraints/dimensions.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from fusion360_mcp.api.connection import FusionConnection, FusionConnectionError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


async def _send(command: str, params: dict | None = None) -> dict:
    """Send a command through the global Fusion 360 connection.

    Returns the result dict on success or raises ``FusionConnectionError``.
    """
    conn = FusionConnection.get_global()
    if not conn.is_connected():
        await conn.connect()
    return await conn.send_command(command, params)


def register_sketch_tools(mcp: FastMCP) -> None:
    """Register all sketch-related tools on the given MCP server."""

    # ------------------------------------------------------------------
    # Sketch creation
    # ------------------------------------------------------------------

    @mcp.tool()
    async def create_sketch(
        plane: str = "XY",
        component_name: str = "",
        sketch_name: str = "",
    ) -> str:
        """Create a new sketch on a construction plane or planar face.

        Args:
            plane: The reference plane or face. Use 'XY', 'XZ', 'YZ' for
                standard planes, or provide a face ID for a planar face.
            component_name: Target component name (empty = active component).
            sketch_name: Optional name for the new sketch.

        Returns:
            A confirmation message with the sketch name and ID.
        """
        try:
            result = await _send("sketch_create", {
                "plane": plane,
                "component_name": component_name or None,
                "sketch_name": sketch_name or None,
            })
            name = result.get("sketch_name", "unnamed")
            sid = result.get("sketch_id", "")
            return f"Created sketch '{name}' (id={sid}) on plane '{plane}'."
        except FusionConnectionError as exc:
            return f"Error creating sketch: {exc}"

    # ------------------------------------------------------------------
    # Geometric entities
    # ------------------------------------------------------------------

    @mcp.tool()
    async def sketch_line(
        sketch_name: str,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        is_construction: bool = False,
    ) -> str:
        """Draw a line segment between two points in a sketch.

        Args:
            sketch_name: Name of the target sketch.
            start_x: Start point X coordinate (cm).
            start_y: Start point Y coordinate (cm).
            end_x: End point X coordinate (cm).
            end_y: End point Y coordinate (cm).
            is_construction: If True, creates a construction (reference) line.

        Returns:
            Confirmation with line endpoints.
        """
        try:
            result = await _send("sketch_line", {
                "sketch_name": sketch_name,
                "start": {"x": start_x, "y": start_y},
                "end": {"x": end_x, "y": end_y},
                "is_construction": is_construction,
            })
            eid = result.get("entity_id", "")
            return (
                f"Created line (id={eid}) from ({start_x}, {start_y}) "
                f"to ({end_x}, {end_y}) in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error drawing line: {exc}"

    @mcp.tool()
    async def sketch_circle(
        sketch_name: str,
        center_x: float,
        center_y: float,
        radius: float,
        is_construction: bool = False,
    ) -> str:
        """Draw a circle defined by center point and radius.

        Args:
            sketch_name: Name of the target sketch.
            center_x: Center X coordinate (cm).
            center_y: Center Y coordinate (cm).
            radius: Circle radius (cm), must be positive.
            is_construction: If True, creates a construction circle.

        Returns:
            Confirmation with center and radius.
        """
        try:
            result = await _send("sketch_circle", {
                "sketch_name": sketch_name,
                "center": {"x": center_x, "y": center_y},
                "radius": radius,
                "is_construction": is_construction,
            })
            eid = result.get("entity_id", "")
            return (
                f"Created circle (id={eid}) at ({center_x}, {center_y}) "
                f"with radius {radius} cm in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error drawing circle: {exc}"

    @mcp.tool()
    async def sketch_arc(
        sketch_name: str,
        arc_type: str = "center_point",
        center_x: float = 0.0,
        center_y: float = 0.0,
        radius: float = 1.0,
        start_angle: float = 0.0,
        end_angle: float = 90.0,
        start_x: float = 0.0,
        start_y: float = 0.0,
        through_x: float = 1.0,
        through_y: float = 1.0,
        end_x: float = 0.0,
        end_y: float = 2.0,
    ) -> str:
        """Draw an arc using center-point or 3-point construction.

        Args:
            sketch_name: Name of the target sketch.
            arc_type: 'center_point' or 'three_point'.
            center_x: Center X for center-point arc (cm).
            center_y: Center Y for center-point arc (cm).
            radius: Radius for center-point arc (cm).
            start_angle: Start angle in degrees.
            end_angle: End angle in degrees.
            start_x: Start point X for 3-point arc.
            start_y: Start point Y for 3-point arc.
            through_x: Through point X for 3-point arc.
            through_y: Through point Y for 3-point arc.
            end_x: End point X for 3-point arc.
            end_y: End point Y for 3-point arc.

        Returns:
            Confirmation describing the created arc.
        """
        try:
            params: dict = {"sketch_name": sketch_name, "arc_type": arc_type}
            if arc_type == "center_point":
                params["center"] = {"x": center_x, "y": center_y}
                params["radius"] = radius
                params["start_angle"] = start_angle
                params["end_angle"] = end_angle
            else:
                params["start"] = {"x": start_x, "y": start_y}
                params["through"] = {"x": through_x, "y": through_y}
                params["end"] = {"x": end_x, "y": end_y}
            result = await _send("sketch_arc", params)
            eid = result.get("entity_id", "")
            return f"Created {arc_type} arc (id={eid}) in sketch '{sketch_name}'."
        except FusionConnectionError as exc:
            return f"Error drawing arc: {exc}"

    @mcp.tool()
    async def sketch_rectangle(
        sketch_name: str,
        rect_type: str = "two_point",
        x1: float = 0.0,
        y1: float = 0.0,
        x2: float = 5.0,
        y2: float = 3.0,
        x3: float = 5.0,
        y3: float = 5.0,
    ) -> str:
        """Draw a rectangle using 2-point or 3-point construction.

        Args:
            sketch_name: Name of the target sketch.
            rect_type: 'two_point' or 'three_point'.
            x1: First corner X (cm).
            y1: First corner Y (cm).
            x2: Second corner X (cm).
            y2: Second corner Y (cm).
            x3: Third corner X for 3-point rect (cm).
            y3: Third corner Y for 3-point rect (cm).

        Returns:
            Confirmation with corner coordinates.
        """
        try:
            params: dict = {
                "sketch_name": sketch_name,
                "rect_type": rect_type,
                "corner1": {"x": x1, "y": y1},
                "corner2": {"x": x2, "y": y2},
            }
            if rect_type == "three_point":
                params["corner3"] = {"x": x3, "y": y3}
            result = await _send("sketch_rectangle", params)
            eid = result.get("entity_id", "")
            return f"Created {rect_type} rectangle (id={eid}) in sketch '{sketch_name}'."
        except FusionConnectionError as exc:
            return f"Error drawing rectangle: {exc}"

    @mcp.tool()
    async def sketch_polygon(
        sketch_name: str,
        center_x: float,
        center_y: float,
        radius: float,
        sides: int = 6,
        rotation: float = 0.0,
        is_construction: bool = False,
    ) -> str:
        """Draw a regular polygon inscribed in a circle.

        Args:
            sketch_name: Name of the target sketch.
            center_x: Center X coordinate (cm).
            center_y: Center Y coordinate (cm).
            radius: Circumscribed circle radius (cm).
            sides: Number of sides (3 or more).
            rotation: Rotation angle in degrees from X axis.
            is_construction: If True, creates construction geometry.

        Returns:
            Confirmation with polygon details.
        """
        try:
            result = await _send("sketch_polygon", {
                "sketch_name": sketch_name,
                "center": {"x": center_x, "y": center_y},
                "radius": radius,
                "sides": sides,
                "rotation": rotation,
                "is_construction": is_construction,
            })
            eid = result.get("entity_id", "")
            return (
                f"Created {sides}-sided polygon (id={eid}) at "
                f"({center_x}, {center_y}) r={radius} cm in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error drawing polygon: {exc}"

    @mcp.tool()
    async def sketch_ellipse(
        sketch_name: str,
        center_x: float,
        center_y: float,
        major_radius: float,
        minor_radius: float,
        rotation: float = 0.0,
        is_construction: bool = False,
    ) -> str:
        """Draw an ellipse defined by center, major/minor radii, and rotation.

        Args:
            sketch_name: Name of the target sketch.
            center_x: Center X coordinate (cm).
            center_y: Center Y coordinate (cm).
            major_radius: Semi-major axis length (cm).
            minor_radius: Semi-minor axis length (cm).
            rotation: Rotation angle in degrees.
            is_construction: If True, creates construction geometry.

        Returns:
            Confirmation with ellipse parameters.
        """
        try:
            result = await _send("sketch_ellipse", {
                "sketch_name": sketch_name,
                "center": {"x": center_x, "y": center_y},
                "major_radius": major_radius,
                "minor_radius": minor_radius,
                "rotation": rotation,
                "is_construction": is_construction,
            })
            eid = result.get("entity_id", "")
            return (
                f"Created ellipse (id={eid}) at ({center_x}, {center_y}) "
                f"major={major_radius} cm, minor={minor_radius} cm "
                f"in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error drawing ellipse: {exc}"

    @mcp.tool()
    async def sketch_spline(
        sketch_name: str,
        points: str,
        fit_type: str = "fit_points",
        degree: int = 3,
        is_construction: bool = False,
    ) -> str:
        """Draw a spline through a series of points.

        Args:
            sketch_name: Name of the target sketch.
            points: Comma-separated x,y pairs, semicolon-delimited.
                Example: "0,0; 2,1; 5,0; 8,3"
            fit_type: 'fit_points' or 'control_points'.
            degree: Spline degree (3 = cubic).
            is_construction: If True, creates construction geometry.

        Returns:
            Confirmation with point count and spline ID.
        """
        try:
            parsed = []
            for pair in points.split(";"):
                parts = pair.strip().split(",")
                if len(parts) != 2:
                    raise ValueError(f"Invalid point format: '{pair.strip()}'")
                parsed.append({"x": float(parts[0].strip()), "y": float(parts[1].strip())})
            if len(parsed) < 2:
                return "Error: at least 2 points are required for a spline."
            result = await _send("sketch_spline", {
                "sketch_name": sketch_name,
                "points": parsed,
                "fit_type": fit_type,
                "degree": degree,
                "is_construction": is_construction,
            })
            eid = result.get("entity_id", "")
            return (
                f"Created {fit_type} spline (id={eid}) through {len(parsed)} points "
                f"deg={degree} in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error drawing spline: {exc}"
        except (ValueError, IndexError) as exc:
            return f"Error parsing spline points: {exc}"

    @mcp.tool()
    async def sketch_slot(
        sketch_name: str,
        slot_type: str = "center_to_center",
        point1_x: float = 0.0,
        point1_y: float = 0.0,
        point2_x: float = 5.0,
        point2_y: float = 0.0,
        width: float = 1.0,
        full_length: float = 6.0,
        is_construction: bool = False,
    ) -> str:
        """Draw a slot using center-to-center or overall construction.

        Args:
            sketch_name: Name of the target sketch.
            slot_type: 'center_to_center' or 'overall'.
            point1_x: First center/endpoint X (cm).
            point1_y: First center/endpoint Y (cm).
            point2_x: Second center/endpoint X (cm).
            point2_y: Second center/endpoint Y (cm).
            width: Slot width (cm).
            full_length: Full length for overall type (cm).
            is_construction: If True, creates construction geometry.

        Returns:
            Confirmation with slot dimensions.
        """
        try:
            params: dict = {
                "sketch_name": sketch_name,
                "slot_type": slot_type,
                "point1": {"x": point1_x, "y": point1_y},
                "width": width,
                "is_construction": is_construction,
            }
            if slot_type == "center_to_center":
                params["point2"] = {"x": point2_x, "y": point2_y}
            else:
                params["full_length"] = full_length
                params["direction"] = {"x": point2_x - point1_x, "y": point2_y - point1_y}
            result = await _send("sketch_slot", params)
            eid = result.get("entity_id", "")
            return (
                f"Created {slot_type} slot (id={eid}) width={width} cm "
                f"in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error drawing slot: {exc}"

    @mcp.tool()
    async def sketch_text(
        sketch_name: str,
        text: str,
        position_x: float,
        position_y: float,
        height: float = 0.5,
        font_name: str = "Arial",
        bold: bool = False,
        italic: bool = False,
    ) -> str:
        """Add text to a sketch at the specified position.

        Args:
            sketch_name: Name of the target sketch.
            text: The text string to add.
            position_x: Text insertion point X (cm).
            position_y: Text insertion point Y (cm).
            height: Text height (cm).
            font_name: Font family name.
            bold: Use bold weight.
            italic: Use italic style.

        Returns:
            Confirmation with text and position.
        """
        try:
            result = await _send("sketch_text", {
                "sketch_name": sketch_name,
                "text": text,
                "position": {"x": position_x, "y": position_y},
                "height": height,
                "font_name": font_name,
                "bold": bold,
                "italic": italic,
            })
            eid = result.get("entity_id", "")
            return (
                f"Created text '{text}' (id={eid}) at ({position_x}, {position_y}) "
                f"height={height} cm in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding text: {exc}"

    # ------------------------------------------------------------------
    # Entity editing
    # ------------------------------------------------------------------

    @mcp.tool()
    async def sketch_offset(
        sketch_name: str,
        entity_ids: str,
        distance: float,
        side: str = "both",
    ) -> str:
        """Offset sketch entities by a specified distance.

        Args:
            sketch_name: Name of the target sketch.
            entity_ids: Comma-separated entity IDs to offset.
            distance: Offset distance (cm), positive = outward.
            side: Which side to offset: 'inside', 'outside', or 'both'.

        Returns:
            Confirmation with offset details.
        """
        try:
            ids = [eid.strip() for eid in entity_ids.split(",") if eid.strip()]
            result = await _send("sketch_offset", {
                "sketch_name": sketch_name,
                "entity_ids": ids,
                "distance": distance,
                "side": side,
            })
            new_ids = result.get("new_entity_ids", [])
            return (
                f"Offset {len(ids)} entities by {distance} cm ({side}) "
                f"-> {len(new_ids)} new entities in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error offsetting entities: {exc}"

    @mcp.tool()
    async def sketch_project(
        sketch_name: str,
        source_type: str = "edge",
        source_ids: str = "",
    ) -> str:
        """Project geometry from model edges/faces onto the sketch plane.

        Args:
            sketch_name: Name of the target sketch.
            source_type: Type of geometry to project: 'edge', 'face', or 'vertex'.
            source_ids: Comma-separated IDs of edges/faces/vertices to project.

        Returns:
            Confirmation with projected entity count.
        """
        try:
            ids = [sid.strip() for sid in source_ids.split(",") if sid.strip()]
            result = await _send("sketch_project", {
                "sketch_name": sketch_name,
                "source_type": source_type,
                "source_ids": ids,
            })
            projected = result.get("projected_ids", [])
            return (
                f"Projected {len(projected)} {source_type}(s) onto "
                f"sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error projecting geometry: {exc}"

    @mcp.tool()
    async def sketch_trim(
        sketch_name: str,
        entity_ids: str,
        trim_point_x: float,
        trim_point_y: float,
    ) -> str:
        """Trim sketch entities at the intersection nearest to the trim point.

        Args:
            sketch_name: Name of the target sketch.
            entity_ids: Comma-separated entity IDs to trim.
            trim_point_x: X coordinate of the trim selection point (cm).
            trim_point_y: Y coordinate of the trim selection point (cm).

        Returns:
            Confirmation with trim result.
        """
        try:
            ids = [eid.strip() for eid in entity_ids.split(",") if eid.strip()]
            result = await _send("sketch_trim", {
                "sketch_name": sketch_name,
                "entity_ids": ids,
                "trim_point": {"x": trim_point_x, "y": trim_point_y},
            })
            remaining = result.get("remaining_count", 0)
            return (
                f"Trimmed {len(ids)} entities near ({trim_point_x}, {trim_point_y}) "
                f"-> {remaining} segments remain in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error trimming entities: {exc}"

    @mcp.tool()
    async def sketch_extend(
        sketch_name: str,
        entity_ids: str,
        to_entity_id: str = "",
        distance: float = 0.0,
    ) -> str:
        """Extend sketch entities to a boundary entity or by a distance.

        Args:
            sketch_name: Name of the target sketch.
            entity_ids: Comma-separated entity IDs to extend.
            to_entity_id: ID of the boundary entity to extend to.
            distance: Extension distance (cm) if not extending to an entity.

        Returns:
            Confirmation with extension details.
        """
        try:
            ids = [eid.strip() for eid in entity_ids.split(",") if eid.strip()]
            params: dict = {
                "sketch_name": sketch_name,
                "entity_ids": ids,
            }
            if to_entity_id:
                params["to_entity_id"] = to_entity_id
            elif distance > 0:
                params["distance"] = distance
            else:
                return "Error: provide either to_entity_id or a positive distance."
            result = await _send("sketch_extend", params)
            return f"Extended {len(ids)} entities in sketch '{sketch_name}'."
        except FusionConnectionError as exc:
            return f"Error extending entities: {exc}"

    # ------------------------------------------------------------------
    # Mirror and pattern
    # ------------------------------------------------------------------

    @mcp.tool()
    async def sketch_mirror(
        sketch_name: str,
        entity_ids: str,
        axis_entity_id: str,
    ) -> str:
        """Mirror sketch entities about a line entity.

        Args:
            sketch_name: Name of the target sketch.
            entity_ids: Comma-separated entity IDs to mirror.
            axis_entity_id: ID of the line entity to mirror about.

        Returns:
            Confirmation with mirrored entity count.
        """
        try:
            ids = [eid.strip() for eid in entity_ids.split(",") if eid.strip()]
            result = await _send("sketch_mirror", {
                "sketch_name": sketch_name,
                "entity_ids": ids,
                "axis_entity_id": axis_entity_id,
            })
            mirrored = result.get("mirrored_count", 0)
            return (
                f"Mirrored {len(ids)} entities about axis '{axis_entity_id}' "
                f"-> {mirrored} new entities in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error mirroring entities: {exc}"

    @mcp.tool()
    async def sketch_pattern_circular(
        sketch_name: str,
        entity_ids: str,
        center_x: float,
        center_y: float,
        count: int,
        angle_span: float = 360.0,
    ) -> str:
        """Create a circular pattern of sketch entities.

        Args:
            sketch_name: Name of the target sketch.
            entity_ids: Comma-separated entity IDs to pattern.
            center_x: Pattern center X (cm).
            center_y: Pattern center Y (cm).
            count: Number of pattern instances (including original).
            angle_span: Total angular span in degrees (360 = full circle).

        Returns:
            Confirmation with pattern details.
        """
        try:
            ids = [eid.strip() for eid in entity_ids.split(",") if eid.strip()]
            result = await _send("sketch_pattern_circular", {
                "sketch_name": sketch_name,
                "entity_ids": ids,
                "center": {"x": center_x, "y": center_y},
                "count": count,
                "angle_span": angle_span,
            })
            total = result.get("total_entities", 0)
            return (
                f"Created circular pattern of {count} instances "
                f"(span={angle_span}°) -> {total} entities in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error creating circular pattern: {exc}"

    @mcp.tool()
    async def sketch_pattern_rectangular(
        sketch_name: str,
        entity_ids: str,
        count_x: int,
        count_y: int,
        spacing_x: float,
        spacing_y: float,
    ) -> str:
        """Create a rectangular pattern of sketch entities.

        Args:
            sketch_name: Name of the target sketch.
            entity_ids: Comma-separated entity IDs to pattern.
            count_x: Number of instances along X.
            count_y: Number of instances along Y.
            spacing_x: Spacing between instances along X (cm).
            spacing_y: Spacing between instances along Y (cm).

        Returns:
            Confirmation with pattern details.
        """
        try:
            ids = [eid.strip() for eid in entity_ids.split(",") if eid.strip()]
            result = await _send("sketch_pattern_rectangular", {
                "sketch_name": sketch_name,
                "entity_ids": ids,
                "count_x": count_x,
                "count_y": count_y,
                "spacing_x": spacing_x,
                "spacing_y": spacing_y,
            })
            total = result.get("total_entities", 0)
            return (
                f"Created rectangular pattern {count_x}x{count_y} "
                f"(spacing={spacing_x}x{spacing_y} cm) -> {total} entities "
                f"in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error creating rectangular pattern: {exc}"

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    @mcp.tool()
    async def add_constraint_coincident(
        sketch_name: str,
        entity1_id: str,
        entity2_id: str,
    ) -> str:
        """Add a coincident constraint between two sketch entities.

        Args:
            sketch_name: Name of the target sketch.
            entity1_id: First entity ID.
            entity2_id: Second entity ID.

        Returns:
            Confirmation of constraint creation.
        """
        try:
            await _send("constraint_coincident", {
                "sketch_name": sketch_name,
                "entity1_id": entity1_id,
                "entity2_id": entity2_id,
            })
            return (
                f"Added coincident constraint between '{entity1_id}' and "
                f"'{entity2_id}' in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding coincident constraint: {exc}"

    @mcp.tool()
    async def add_constraint_horizontal(
        sketch_name: str,
        entity_id: str,
    ) -> str:
        """Add a horizontal constraint to a line or pair of points.

        Args:
            sketch_name: Name of the target sketch.
            entity_id: Line entity ID to make horizontal.

        Returns:
            Confirmation of constraint creation.
        """
        try:
            await _send("constraint_horizontal", {
                "sketch_name": sketch_name,
                "entity_id": entity_id,
            })
            return f"Made entity '{entity_id}' horizontal in sketch '{sketch_name}'."
        except FusionConnectionError as exc:
            return f"Error adding horizontal constraint: {exc}"

    @mcp.tool()
    async def add_constraint_vertical(
        sketch_name: str,
        entity_id: str,
    ) -> str:
        """Add a vertical constraint to a line or pair of points.

        Args:
            sketch_name: Name of the target sketch.
            entity_id: Line entity ID to make vertical.

        Returns:
            Confirmation of constraint creation.
        """
        try:
            await _send("constraint_vertical", {
                "sketch_name": sketch_name,
                "entity_id": entity_id,
            })
            return f"Made entity '{entity_id}' vertical in sketch '{sketch_name}'."
        except FusionConnectionError as exc:
            return f"Error adding vertical constraint: {exc}"

    @mcp.tool()
    async def add_constraint_tangent(
        sketch_name: str,
        entity1_id: str,
        entity2_id: str,
    ) -> str:
        """Add a tangent constraint between a curve and another entity.

        Args:
            sketch_name: Name of the target sketch.
            entity1_id: First entity ID (typically a curve).
            entity2_id: Second entity ID.

        Returns:
            Confirmation of constraint creation.
        """
        try:
            await _send("constraint_tangent", {
                "sketch_name": sketch_name,
                "entity1_id": entity1_id,
                "entity2_id": entity2_id,
            })
            return (
                f"Added tangent constraint between '{entity1_id}' and "
                f"'{entity2_id}' in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding tangent constraint: {exc}"

    @mcp.tool()
    async def add_constraint_perpendicular(
        sketch_name: str,
        entity1_id: str,
        entity2_id: str,
    ) -> str:
        """Add a perpendicular constraint between two lines.

        Args:
            sketch_name: Name of the target sketch.
            entity1_id: First line entity ID.
            entity2_id: Second line entity ID.

        Returns:
            Confirmation of constraint creation.
        """
        try:
            await _send("constraint_perpendicular", {
                "sketch_name": sketch_name,
                "entity1_id": entity1_id,
                "entity2_id": entity2_id,
            })
            return (
                f"Added perpendicular constraint between '{entity1_id}' and "
                f"'{entity2_id}' in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding perpendicular constraint: {exc}"

    @mcp.tool()
    async def add_constraint_parallel(
        sketch_name: str,
        entity1_id: str,
        entity2_id: str,
    ) -> str:
        """Add a parallel constraint between two lines.

        Args:
            sketch_name: Name of the target sketch.
            entity1_id: First line entity ID.
            entity2_id: Second line entity ID.

        Returns:
            Confirmation of constraint creation.
        """
        try:
            await _send("constraint_parallel", {
                "sketch_name": sketch_name,
                "entity1_id": entity1_id,
                "entity2_id": entity2_id,
            })
            return (
                f"Added parallel constraint between '{entity1_id}' and "
                f"'{entity2_id}' in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding parallel constraint: {exc}"

    @mcp.tool()
    async def add_constraint_equal(
        sketch_name: str,
        entity1_id: str,
        entity2_id: str,
    ) -> str:
        """Add an equal-length constraint between two line segments.

        Args:
            sketch_name: Name of the target sketch.
            entity1_id: First line entity ID.
            entity2_id: Second line entity ID.

        Returns:
            Confirmation of constraint creation.
        """
        try:
            await _send("constraint_equal", {
                "sketch_name": sketch_name,
                "entity1_id": entity1_id,
                "entity2_id": entity2_id,
            })
            return (
                f"Added equal constraint between '{entity1_id}' and "
                f"'{entity2_id}' in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding equal constraint: {exc}"

    @mcp.tool()
    async def add_constraint_symmetric(
        sketch_name: str,
        entity1_id: str,
        entity2_id: str,
        axis_entity_id: str,
    ) -> str:
        """Add a symmetric constraint between two entities about an axis line.

        Args:
            sketch_name: Name of the target sketch.
            entity1_id: First entity ID.
            entity2_id: Second entity ID.
            axis_entity_id: Line entity ID serving as the symmetry axis.

        Returns:
            Confirmation of constraint creation.
        """
        try:
            await _send("constraint_symmetric", {
                "sketch_name": sketch_name,
                "entity1_id": entity1_id,
                "entity2_id": entity2_id,
                "axis_entity_id": axis_entity_id,
            })
            return (
                f"Added symmetric constraint between '{entity1_id}' and "
                f"'{entity2_id}' about axis '{axis_entity_id}' "
                f"in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding symmetric constraint: {exc}"

    @mcp.tool()
    async def add_constraint_fix(
        sketch_name: str,
        entity_id: str,
    ) -> str:
        """Fix an entity at its current position, removing all degrees of freedom.

        Args:
            sketch_name: Name of the target sketch.
            entity_id: Entity ID to fix.

        Returns:
            Confirmation of constraint creation.
        """
        try:
            await _send("constraint_fix", {
                "sketch_name": sketch_name,
                "entity_id": entity_id,
            })
            return f"Fixed entity '{entity_id}' in sketch '{sketch_name}'."
        except FusionConnectionError as exc:
            return f"Error adding fix constraint: {exc}"

    @mcp.tool()
    async def add_dimension(
        sketch_name: str,
        dimension_type: str,
        entity1_id: str = "",
        entity2_id: str = "",
        point_x: float = 0.0,
        point_y: float = 0.0,
        value: float | None = None,
        expression: str | None = None,
    ) -> str:
        """Add a driving dimension to constrain sketch entities.

        Args:
            sketch_name: Name of the target sketch.
            dimension_type: Type: 'linear', 'radius', 'diameter', 'angular',
                'horizontal', 'vertical'.
            entity1_id: First entity ID.
            entity2_id: Second entity ID (for linear/angular dimensions).
            point_x: Dimension text placement X (cm).
            point_y: Dimension text placement Y (cm).
            value: Numerical value to set the dimension to.
            expression: Parametric expression (e.g. 'width * 2').

        Returns:
            Confirmation with dimension value.
        """
        try:
            params: dict = {
                "sketch_name": sketch_name,
                "dimension_type": dimension_type,
                "position": {"x": point_x, "y": point_y},
            }
            if entity1_id:
                params["entity1_id"] = entity1_id
            if entity2_id:
                params["entity2_id"] = entity2_id
            if value is not None:
                params["value"] = value
            elif expression is not None:
                params["expression"] = expression
            result = await _send("sketch_dimension", params)
            dim_value = result.get("value", "unset")
            return (
                f"Added {dimension_type} dimension (value={dim_value}) "
                f"in sketch '{sketch_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding dimension: {exc}"
