"""Feature tools — MCP tool registrations for Fusion 360 feature operations.

Provides 19 tools covering extrude, revolve, loft, sweep, fillet, chamfer,
shell, hole, thread, draft, pattern, mirror, combine, split, scale,
component creation, and joint origins.
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
    """Send a command through the global Fusion 360 connection."""
    conn = FusionConnection.get_global()
    if not conn.is_connected():
        await conn.connect()
    return await conn.send_command(command, params)


def register_feature_tools(mcp: FastMCP) -> None:
    """Register all feature-related tools on the given MCP server."""

    @mcp.tool()
    async def extrude(
        sketch_name: str,
        operation: str = "new_body",
        extent_type: str = "distance",
        distance: float = 1.0,
        direction_x: float = 0.0,
        direction_y: float = 0.0,
        direction_z: float = 1.0,
        symmetric: bool = False,
        taper_angle: float = 0.0,
        to_object_id: str = "",
    ) -> str:
        """Extrude a sketch profile to create a 3D body or modify an existing one.

        Args:
            sketch_name: Name of the sketch containing the profile(s).
            operation: Boolean operation: 'new_body', 'join', 'cut', 'intersect'.
            extent_type: Depth definition: 'distance', 'through_all', 'to_object', 'symmetric'.
            distance: Extrude distance in cm (for distance extent).
            direction_x: Direction vector X component.
            direction_y: Direction vector Y component.
            direction_z: Direction vector Z component.
            symmetric: Extrude equally in both directions.
            taper_angle: Taper angle in degrees (positive = narrows toward top).
            to_object_id: Target entity ID for to_object extent.

        Returns:
            Confirmation with feature name and created body count.
        """
        try:
            params: dict = {
                "sketch_name": sketch_name,
                "operation": operation,
                "extent_type": extent_type,
            }
            if extent_type == "distance":
                params["distance"] = distance
                params["symmetric"] = symmetric
            elif extent_type == "through_all":
                params["symmetric"] = symmetric
            elif extent_type == "to_object":
                params["to_object_id"] = to_object_id
            elif extent_type == "symmetric":
                params["distance"] = distance
            params["direction"] = {
                "x": direction_x,
                "y": direction_y,
                "z": direction_z,
            }
            params["taper_angle"] = taper_angle
            result = await _send("feature_extrude", params)
            fname = result.get("feature_name", "Extrude")
            bodies = result.get("bodies_affected", 0)
            return (
                f"Created extrude feature '{fname}' ({operation}, "
                f"{extent_type}) affecting {bodies} body/bodies."
            )
        except FusionConnectionError as exc:
            return f"Error creating extrude: {exc}"

    @mcp.tool()
    async def revolve(
        sketch_name: str,
        axis_x: float = 0.0,
        axis_y: float = 0.0,
        axis_z: float = 1.0,
        origin_x: float = 0.0,
        origin_y: float = 0.0,
        origin_z: float = 0.0,
        angle: float = 360.0,
        operation: str = "new_body",
    ) -> str:
        """Revolve a sketch profile about an axis to create a solid or cut.

        Args:
            sketch_name: Name of the sketch containing the profile(s).
            axis_x: Axis direction X component.
            axis_y: Axis direction Y component.
            axis_z: Axis direction Z component.
            origin_x: Point on the axis X (cm).
            origin_y: Point on the axis Y (cm).
            origin_z: Point on the axis Z (cm).
            angle: Revolution angle in degrees.
            operation: Boolean operation: 'new_body', 'join', 'cut', 'intersect'.

        Returns:
            Confirmation with feature details.
        """
        try:
            result = await _send("feature_revolve", {
                "sketch_name": sketch_name,
                "axis": {"x": axis_x, "y": axis_y, "z": axis_z},
                "origin": {"x": origin_x, "y": origin_y, "z": origin_z},
                "angle": angle,
                "operation": operation,
            })
            fname = result.get("feature_name", "Revolve")
            return (
                f"Created revolve feature '{fname}' ({angle}°, {operation})."
            )
        except FusionConnectionError as exc:
            return f"Error creating revolve: {exc}"

    @mcp.tool()
    async def loft(
        sketch_names: str,
        operation: str = "new_body",
        guide_rails: str = "",
        centerline: str = "",
    ) -> str:
        """Loft between two or more sketch profiles to create a smooth body.

        Args:
            sketch_names: Semicolon-separated sketch names in loft order.
            operation: Boolean operation: 'new_body', 'join', 'cut', 'intersect'.
            guide_rails: Comma-separated curve IDs used as guide rails.
            centerline: Curve ID used as a centerline guide.

        Returns:
            Confirmation with feature details.
        """
        try:
            names = [n.strip() for n in sketch_names.split(";") if n.strip()]
            if len(names) < 2:
                return "Error: loft requires at least 2 profile sketches."
            params: dict = {
                "sketch_names": names,
                "operation": operation,
            }
            if guide_rails:
                params["guide_rail_ids"] = [
                    r.strip() for r in guide_rails.split(",") if r.strip()
                ]
            if centerline:
                params["centerline_id"] = centerline
            result = await _send("feature_loft", params)
            fname = result.get("feature_name", "Loft")
            return (
                f"Created loft feature '{fname}' through {len(names)} profiles "
                f"({operation})."
            )
        except FusionConnectionError as exc:
            return f"Error creating loft: {exc}"

    @mcp.tool()
    async def sweep(
        sketch_name: str,
        path_entity_id: str,
        orientation: str = "perpendicular",
        operation: str = "new_body",
    ) -> str:
        """Sweep a profile along a path to create a 3D body.

        Args:
            sketch_name: Name of the sketch containing the profile to sweep.
            path_entity_id: ID of the path (sketch curve or model edge).
            orientation: Profile orientation: 'perpendicular', 'parallel', 'none'.
            operation: Boolean operation: 'new_body', 'join', 'cut', 'intersect'.

        Returns:
            Confirmation with feature details.
        """
        try:
            result = await _send("feature_sweep", {
                "sketch_name": sketch_name,
                "path_entity_id": path_entity_id,
                "orientation": orientation,
                "operation": operation,
            })
            fname = result.get("feature_name", "Sweep")
            return f"Created sweep feature '{fname}' ({operation})."
        except FusionConnectionError as exc:
            return f"Error creating sweep: {exc}"

    @mcp.tool()
    async def thicken(
        face_ids: str,
        thickness: float,
        side: str = "both",
        operation: str = "new_body",
    ) -> str:
        """Thicken a surface body into a solid or modify existing geometry.

        Args:
            face_ids: Comma-separated face IDs of the surface to thicken.
            thickness: Thickness in cm (must be positive).
            side: Which side to thicken: 'inside', 'outside', or 'both'.
            operation: Boolean operation: 'new_body', 'join', 'cut', 'intersect'.

        Returns:
            Confirmation with feature details.
        """
        try:
            ids = [fid.strip() for fid in face_ids.split(",") if fid.strip()]
            result = await _send("feature_thicken", {
                "face_ids": ids,
                "thickness": thickness,
                "side": side,
                "operation": operation,
            })
            fname = result.get("feature_name", "Thicken")
            return (
                f"Created thicken feature '{fname}' ({thickness} cm, "
                f"side={side}, {operation})."
            )
        except FusionConnectionError as exc:
            return f"Error creating thicken: {exc}"

    @mcp.tool()
    async def fillet(
        edge_ids: str,
        radius: float,
    ) -> str:
        """Apply a constant-radius fillet (round) to selected edges.

        Args:
            edge_ids: Comma-separated edge IDs to fillet.
            radius: Fillet radius in cm.

        Returns:
            Confirmation with fillet details.
        """
        try:
            ids = [eid.strip() for eid in edge_ids.split(",") if eid.strip()]
            result = await _send("feature_fillet", {
                "edge_ids": ids,
                "radius": radius,
            })
            fname = result.get("feature_name", "Fillet")
            return (
                f"Created fillet feature '{fname}' with radius {radius} cm "
                f"on {len(ids)} edge(s)."
            )
        except FusionConnectionError as exc:
            return f"Error creating fillet: {exc}"

    @mcp.tool()
    async def chamfer(
        edge_ids: str,
        chamfer_type: str = "equal_distance",
        distance1: float = 0.5,
        distance2: float = 0.5,
        angle: float = 45.0,
    ) -> str:
        """Apply a chamfer to selected edges.

        Args:
            edge_ids: Comma-separated edge IDs to chamfer.
            chamfer_type: Type: 'equal_distance', 'two_distances', 'distance_angle'.
            distance1: First chamfer distance in cm.
            distance2: Second distance (for two_distances type) in cm.
            angle: Chamfer angle in degrees (for distance_angle type).

        Returns:
            Confirmation with chamfer details.
        """
        try:
            ids = [eid.strip() for eid in edge_ids.split(",") if eid.strip()]
            params: dict = {
                "edge_ids": ids,
                "chamfer_type": chamfer_type,
                "distance1": distance1,
            }
            if chamfer_type == "two_distances":
                params["distance2"] = distance2
            elif chamfer_type == "distance_angle":
                params["angle"] = angle
            result = await _send("feature_chamfer", params)
            fname = result.get("feature_name", "Chamfer")
            return (
                f"Created chamfer feature '{fname}' ({chamfer_type}) "
                f"on {len(ids)} edge(s)."
            )
        except FusionConnectionError as exc:
            return f"Error creating chamfer: {exc}"

    @mcp.tool()
    async def shell(
        thickness: float,
        remove_face_ids: str = "",
    ) -> str:
        """Shell a solid body by removing selected faces and hollowing it.

        Args:
            thickness: Wall thickness in cm.
            remove_face_ids: Comma-separated face IDs to remove.

        Returns:
            Confirmation with shell details.
        """
        try:
            faces = [
                fid.strip() for fid in remove_face_ids.split(",") if fid.strip()
            ]
            result = await _send("feature_shell", {
                "thickness": thickness,
                "remove_face_ids": faces,
            })
            fname = result.get("feature_name", "Shell")
            return (
                f"Created shell feature '{fname}' "
                f"(thickness={thickness} cm, {len(faces)} face(s) removed)."
            )
        except FusionConnectionError as exc:
            return f"Error creating shell: {exc}"

    @mcp.tool()
    async def hole(
        placement_x: float,
        placement_y: float,
        placement_z: float,
        direction_x: float = 0.0,
        direction_y: float = 0.0,
        direction_z: float = -1.0,
        hole_type: str = "simple",
        diameter: float = 1.0,
        depth: float = 2.0,
        counterbore_diameter: float = 2.0,
        counterbore_depth: float = 0.5,
        countersink_diameter: float = 2.0,
        countersink_angle: float = 90.0,
    ) -> str:
        """Create a hole feature (simple, counterbore, or countersink).

        Args:
            placement_x: Hole center X (cm).
            placement_y: Hole center Y (cm).
            placement_z: Hole center Z (cm).
            direction_x: Hole axis direction X.
            direction_y: Hole axis direction Y.
            direction_z: Hole axis direction Z.
            hole_type: Type: 'simple', 'counterbore', 'countersink'.
            diameter: Primary hole diameter (cm).
            depth: Hole depth (cm).
            counterbore_diameter: Counterbore diameter (cm).
            counterbore_depth: Counterbore depth (cm).
            countersink_diameter: Countersink diameter (cm).
            countersink_angle: Countersink angle in degrees.

        Returns:
            Confirmation with hole details.
        """
        try:
            params: dict = {
                "position": {"x": placement_x, "y": placement_y, "z": placement_z},
                "direction": {"x": direction_x, "y": direction_y, "z": direction_z},
                "hole_type": hole_type,
                "diameter": diameter,
                "depth": depth,
            }
            if hole_type == "counterbore":
                params["counterbore_diameter"] = counterbore_diameter
                params["counterbore_depth"] = counterbore_depth
            elif hole_type == "countersink":
                params["countersink_diameter"] = countersink_diameter
                params["countersink_angle"] = countersink_angle
            result = await _send("feature_hole", params)
            fname = result.get("feature_name", "Hole")
            return (
                f"Created {hole_type} hole feature '{fname}' "
                f"(diameter={diameter} cm, depth={depth} cm)."
            )
        except FusionConnectionError as exc:
            return f"Error creating hole: {exc}"

    @mcp.tool()
    async def thread(
        face_id: str,
        thread_type: str = "ISO Metric",
        size: str = "M10",
        designation: str = "M10 x 1.5",
        full_depth: bool = True,
    ) -> str:
        """Add a thread to a cylindrical face.

        Args:
            face_id: ID of the cylindrical face.
            thread_type: Thread standard (e.g. 'ISO Metric', 'ANSI Unified').
            size: Thread size designation.
            designation: Full thread designation string.
            full_depth: If True, thread extends the full face length.

        Returns:
            Confirmation with thread details.
        """
        try:
            result = await _send("feature_thread", {
                "face_id": face_id,
                "thread_type": thread_type,
                "size": size,
                "designation": designation,
                "full_depth": full_depth,
            })
            fname = result.get("feature_name", "Thread")
            return (
                f"Created thread feature '{fname}' ({designation}) "
                f"on face '{face_id}'."
            )
        except FusionConnectionError as exc:
            return f"Error creating thread: {exc}"

    @mcp.tool()
    async def draft(
        face_ids: str,
        plane_id: str,
        angle: float,
        direction: str = "pull",
    ) -> str:
        """Apply a draft angle to selected faces.

        Args:
            face_ids: Comma-separated face IDs to draft.
            plane_id: ID of the neutral plane (draft hinge).
            angle: Draft angle in degrees.
            direction: 'pull' or 'push' relative to the draft plane.

        Returns:
            Confirmation with draft details.
        """
        try:
            ids = [fid.strip() for fid in face_ids.split(",") if fid.strip()]
            result = await _send("feature_draft", {
                "face_ids": ids,
                "plane_id": plane_id,
                "angle": angle,
                "direction": direction,
            })
            fname = result.get("feature_name", "Draft")
            return (
                f"Created draft feature '{fname}' "
                f"({angle}°, {len(ids)} face(s), {direction})."
            )
        except FusionConnectionError as exc:
            return f"Error creating draft: {exc}"

    @mcp.tool()
    async def pattern_rectangular(
        feature_name: str = "",
        body_names: str = "",
        count_x: int = 2,
        count_y: int = 1,
        count_z: int = 1,
        spacing_x: float = 5.0,
        spacing_y: float = 5.0,
        spacing_z: float = 5.0,
    ) -> str:
        """Create a rectangular pattern of features or bodies.

        Args:
            feature_name: Name of the feature to pattern (empty = use body_names).
            body_names: Semicolon-separated body names to pattern.
            count_x: Instance count along X axis.
            count_y: Instance count along Y axis.
            count_z: Instance count along Z axis.
            spacing_x: Spacing along X (cm).
            spacing_y: Spacing along Y (cm).
            spacing_z: Spacing along Z (cm).

        Returns:
            Confirmation with pattern details.
        """
        try:
            bodies = [
                b.strip() for b in body_names.split(";") if b.strip()
            ]
            result = await _send("feature_pattern_rectangular", {
                "feature_name": feature_name or None,
                "body_names": bodies or None,
                "count_x": count_x,
                "count_y": count_y,
                "count_z": count_z,
                "spacing_x": spacing_x,
                "spacing_y": spacing_y,
                "spacing_z": spacing_z,
            })
            total = result.get("total_instances", count_x * count_y * count_z)
            return (
                f"Created rectangular pattern ({count_x}x{count_y}x{count_z}) "
                f"with {total} instances."
            )
        except FusionConnectionError as exc:
            return f"Error creating rectangular pattern: {exc}"

    @mcp.tool()
    async def pattern_circular(
        feature_name: str = "",
        body_names: str = "",
        axis_x: float = 0.0,
        axis_y: float = 0.0,
        axis_z: float = 1.0,
        count: int = 6,
        angle_span: float = 360.0,
    ) -> str:
        """Create a circular pattern of features or bodies about an axis.

        Args:
            feature_name: Name of the feature to pattern (empty = use body_names).
            body_names: Semicolon-separated body names to pattern.
            axis_x: Rotation axis X component.
            axis_y: Rotation axis Y component.
            axis_z: Rotation axis Z component.
            count: Number of pattern instances (including original).
            angle_span: Total angular span in degrees.

        Returns:
            Confirmation with pattern details.
        """
        try:
            bodies = [
                b.strip() for b in body_names.split(";") if b.strip()
            ]
            result = await _send("feature_pattern_circular", {
                "feature_name": feature_name or None,
                "body_names": bodies or None,
                "axis": {"x": axis_x, "y": axis_y, "z": axis_z},
                "count": count,
                "angle_span": angle_span,
            })
            return (
                f"Created circular pattern of {count} instances "
                f"(span={angle_span}°)."
            )
        except FusionConnectionError as exc:
            return f"Error creating circular pattern: {exc}"

    @mcp.tool()
    async def mirror(
        feature_name: str = "",
        body_names: str = "",
        mirror_plane: str = "YZ",
    ) -> str:
        """Mirror features or bodies about a construction plane.

        Args:
            feature_name: Name of the feature to mirror (empty = use body_names).
            body_names: Semicolon-separated body names to mirror.
            mirror_plane: Reference plane: 'XY', 'XZ', 'YZ', or a face ID.

        Returns:
            Confirmation with mirror details.
        """
        try:
            bodies = [
                b.strip() for b in body_names.split(";") if b.strip()
            ]
            result = await _send("feature_mirror", {
                "feature_name": feature_name or None,
                "body_names": bodies or None,
                "mirror_plane": mirror_plane,
            })
            fname = result.get("feature_name", "Mirror")
            return f"Created mirror feature '{fname}' about '{mirror_plane}'."
        except FusionConnectionError as exc:
            return f"Error creating mirror: {exc}"

    @mcp.tool()
    async def combine(
        target_body_name: str,
        tool_body_names: str,
        operation: str = "join",
    ) -> str:
        """Combine two or more bodies using a boolean operation.

        Args:
            target_body_name: Name of the target body.
            tool_body_names: Semicolon-separated tool body names.
            operation: Boolean operation: 'join', 'cut', 'intersect'.

        Returns:
            Confirmation with combine details.
        """
        try:
            tools = [
                t.strip() for t in tool_body_names.split(";") if t.strip()
            ]
            result = await _send("feature_combine", {
                "target_body_name": target_body_name,
                "tool_body_names": tools,
                "operation": operation,
            })
            remaining = result.get("remaining_bodies", 0)
            return (
                f"Combined bodies ({operation}): target='{target_body_name}', "
                f"tool(s)={tools} -> {remaining} body/bodies remaining."
            )
        except FusionConnectionError as exc:
            return f"Error combining bodies: {exc}"

    @mcp.tool()
    async def split_body(
        target_body_name: str,
        tool_type: str = "face",
        tool_entity_id: str = "",
        split_all: bool = False,
    ) -> str:
        """Split a body using a splitting tool (face, plane, or surface).

        Args:
            target_body_name: Name of the body to split.
            tool_type: Tool type: 'face', 'plane', 'surface'.
            tool_entity_id: ID of the splitting tool entity.
            split_all: If True, split all bodies (not just target).

        Returns:
            Confirmation with split details.
        """
        try:
            result = await _send("feature_split_body", {
                "target_body_name": target_body_name,
                "tool_type": tool_type,
                "tool_entity_id": tool_entity_id,
                "split_all": split_all,
            })
            new_bodies = result.get("new_body_count", 0)
            return (
                f"Split body '{target_body_name}' with {tool_type} "
                f"-> {new_bodies} resulting bodies."
            )
        except FusionConnectionError as exc:
            return f"Error splitting body: {exc}"

    @mcp.tool()
    async def scale(
        body_name: str,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        scale_z: float = 1.0,
        origin_x: float = 0.0,
        origin_y: float = 0.0,
        origin_z: float = 0.0,
        uniform: bool = True,
    ) -> str:
        """Scale a body uniformly or non-uniformly.

        Args:
            body_name: Name of the body to scale.
            scale_x: Scale factor along X.
            scale_y: Scale factor along Y.
            scale_z: Scale factor along Z.
            origin_x: Scale origin X (cm).
            origin_y: Scale origin Y (cm).
            origin_z: Scale origin Z (cm).
            uniform: If True, use scale_x for all axes.

        Returns:
            Confirmation with scale details.
        """
        try:
            params: dict = {
                "body_name": body_name,
                "origin": {"x": origin_x, "y": origin_y, "z": origin_z},
                "uniform": uniform,
            }
            if uniform:
                params["scale"] = scale_x
            else:
                params["scale"] = {
                    "x": scale_x,
                    "y": scale_y,
                    "z": scale_z,
                }
            result = await _send("feature_scale", params)
            factor = scale_x if uniform else f"({scale_x}, {scale_y}, {scale_z})"
            return f"Scaled body '{body_name}' by {factor}."
        except FusionConnectionError as exc:
            return f"Error scaling body: {exc}"

    @mcp.tool()
    async def create_component(
        component_name: str,
        activate: bool = True,
    ) -> str:
        """Create a new component and optionally activate it.

        Args:
            component_name: Name for the new component.
            activate: If True, activate the new component.

        Returns:
            Confirmation with component name and activation status.
        """
        try:
            result = await _send("component_create", {
                "component_name": component_name,
                "activate": activate,
            })
            comp_id = result.get("component_id", "")
            status = "active" if activate else "inactive"
            return (
                f"Created component '{component_name}' (id={comp_id}, {status})."
            )
        except FusionConnectionError as exc:
            return f"Error creating component: {exc}"

    @mcp.tool()
    async def create_joint_origin(
        origin_x: float = 0.0,
        origin_y: float = 0.0,
        origin_z: float = 0.0,
        axis_x: float = 0.0,
        axis_y: float = 0.0,
        axis_z: float = 1.0,
        name: str = "",
    ) -> str:
        """Create a joint origin for assembly jointing operations.

        Args:
            origin_x: Joint origin X (cm).
            origin_y: Joint origin Y (cm).
            origin_z: Joint origin Z (cm).
            axis_x: Joint Z-axis direction X.
            axis_y: Joint Z-axis direction Y.
            axis_z: Joint Z-axis direction Z.
            name: Optional joint origin name.

        Returns:
            Confirmation with joint origin details.
        """
        try:
            result = await _send("joint_origin_create", {
                "origin": {"x": origin_x, "y": origin_y, "z": origin_z},
                "z_axis": {"x": axis_x, "y": axis_y, "z": axis_z},
                "name": name or None,
            })
            jo_id = result.get("joint_origin_id", "")
            return (
                f"Created joint origin (id={jo_id}) at "
                f"({origin_x}, {origin_y}, {origin_z})."
            )
        except FusionConnectionError as exc:
            return f"Error creating joint origin: {exc}"
