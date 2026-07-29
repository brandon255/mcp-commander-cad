"""Sheet metal tools — MCP tool registrations for Fusion 360 sheet metal
design operations.

Provides 13 tools covering sheet metal component creation, base flange,
edge flange, contour flange, hem, fold, bend, rip, corner relief, flat
pattern generation, bend allowance configuration, punch tools, and
geometry conversion.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from fusion360_mcp.api.connection import FusionConnection, FusionConnectionError

logger = logging.getLogger(__name__)


async def _send(command: str, params: dict | None = None) -> dict:
    """Send a command through the global Fusion 360 connection."""
    conn = FusionConnection.get_global()
    if not conn.is_connected():
        await conn.connect()
    return await conn.send_command(command, params)


def register_sheet_metal_tools(mcp: FastMCP) -> None:
    """Register all sheet metal-related tools on the given MCP server."""

    @mcp.tool()
    async def create_sheet_metal_component(
        component_name: str = "Sheet Metal",
        thickness: float = 0.2,
        material: str = "Steel",
        activate: bool = True,
    ) -> str:
        """Create a new sheet metal component with material and thickness.

        Args:
            component_name: Name for the new component.
            thickness: Sheet metal thickness (cm).
            material: Material name (e.g. 'Steel', 'Aluminum', 'Copper').
            activate: If True, activate the new component.

        Returns:
            Confirmation with component details and default settings.
        """
        try:
            result = await _send("sheet_metal_create_component", {
                "component_name": component_name,
                "thickness": thickness,
                "material": material,
                "activate": activate,
            })
            comp_id = result.get("component_id", "")
            return (
                f"Created sheet metal component '{component_name}' (id={comp_id}) "
                f"thickness={thickness} cm, material='{material}'."
            )
        except FusionConnectionError as exc:
            return f"Error creating sheet metal component: {exc}"

    @mcp.tool()
    async def create_base_flange(
        sketch_name: str,
        thickness: float = 0.2,
        direction: str = "symmetric",
        bend_radius: float = 0.3,
    ) -> str:
        """Create a base flange from a sketch profile to start a sheet metal part.

        Args:
            sketch_name: Name of the sketch with the open/closed profile.
            thickness: Sheet metal thickness (cm).
            direction: Extrude direction: 'symmetric', 'one_side', 'other_side'.
            bend_radius: Default inner bend radius (cm).

        Returns:
            Confirmation with base flange details.
        """
        try:
            result = await _send("sheet_metal_base_flange", {
                "sketch_name": sketch_name,
                "thickness": thickness,
                "direction": direction,
                "bend_radius": bend_radius,
            })
            fname = result.get("feature_name", "Base Flange")
            return (
                f"Created base flange '{fname}' from sketch '{sketch_name}' "
                f"(thickness={thickness} cm, bend_radius={bend_radius} cm)."
            )
        except FusionConnectionError as exc:
            return f"Error creating base flange: {exc}"

    @mcp.tool()
    async def add_flange(
        edge_id: str,
        height: float = 3.0,
        angle: float = 90.0,
        bend_radius: float | None = None,
        offset: float = 0.0,
        position: str = "bend_center",
        length_side: str = "inner",
    ) -> str:
        """Add an edge flange to a sheet metal body.

        Args:
            edge_id: ID of the edge to attach the flange.
            height: Flange height (cm).
            angle: Bend angle in degrees.
            bend_radius: Override bend radius (cm). None = use default.
            offset: Flange offset from edge along its length (cm).
            position: Flange position relative to edge:
                'inner', 'outer', 'bend_center'.
            length_side: Length dimension side: 'inner', 'outer'.

        Returns:
            Confirmation with flange details.
        """
        try:
            params: dict = {
                "edge_id": edge_id,
                "height": height,
                "angle": angle,
                "offset": offset,
                "position": position,
                "length_side": length_side,
            }
            if bend_radius is not None:
                params["bend_radius"] = bend_radius
            result = await _send("sheet_metal_add_flange", params)
            fname = result.get("feature_name", "Flange")
            return (
                f"Created edge flange '{fname}' on edge '{edge_id}' "
                f"(height={height} cm, angle={angle}°, offset={offset} cm)."
            )
        except FusionConnectionError as exc:
            return f"Error adding flange: {exc}"

    @mcp.tool()
    async def add_contour_flange(
        sketch_name: str,
        edge_id: str,
        thickness: float = 0.2,
        direction: str = "toward",
    ) -> str:
        """Add a contour flange along an edge using a sketch profile.

        Args:
            sketch_name: Name of the sketch defining the flange cross-section.
            edge_id: ID of the edge to sweep the flange along.
            thickness: Sheet thickness (cm).
            direction: Direction: 'toward', 'away', 'symmetric'.

        Returns:
            Confirmation with contour flange details.
        """
        try:
            result = await _send("sheet_metal_add_contour_flange", {
                "sketch_name": sketch_name,
                "edge_id": edge_id,
                "thickness": thickness,
                "direction": direction,
            })
            fname = result.get("feature_name", "Contour Flange")
            return (
                f"Created contour flange '{fname}' from sketch '{sketch_name}' "
                f"along edge '{edge_id}' (thickness={thickness} cm)."
            )
        except FusionConnectionError as exc:
            return f"Error adding contour flange: {exc}"

    @mcp.tool()
    async def add_hem(
        edge_id: str,
        hem_type: str = "single",
        length: float = 0.5,
        angle: float = 180.0,
    ) -> str:
        """Add a hem (folded edge) to a sheet metal body.

        Args:
            edge_id: ID of the edge to apply the hem.
            hem_type: Hem type: 'single', 'double', 'teardrop', 'rolled'.
            length: Hem length/depth (cm).
            angle: Hem fold angle in degrees.

        Returns:
            Confirmation with hem details.
        """
        try:
            result = await _send("sheet_metal_add_hem", {
                "edge_id": edge_id,
                "hem_type": hem_type,
                "length": length,
                "angle": angle,
            })
            fname = result.get("feature_name", "Hem")
            return (
                f"Created {hem_type} hem '{fname}' on edge '{edge_id}' "
                f"(length={length} cm, angle={angle}°)."
            )
        except FusionConnectionError as exc:
            return f"Error adding hem: {exc}"

    @mcp.tool()
    async def add_fold(
        sketch_line_id: str,
        fold_angle: float = 90.0,
        bend_radius: float | None = None,
        direction: str = "toward",
        fold_position: str = "bend_center",
    ) -> str:
        """Add a fold along a sketch line on a sheet metal body.

        Args:
            sketch_line_id: ID of the sketch line defining the fold location.
            fold_angle: Fold angle in degrees.
            bend_radius: Override bend radius (cm). None = use default.
            direction: Fold direction: 'toward', 'away'.
            fold_position: Fold position relative to sketch line:
                'bend_center', 'inside', 'outside'.

        Returns:
            Confirmation with fold details.
        """
        try:
            params: dict = {
                "sketch_line_id": sketch_line_id,
                "fold_angle": fold_angle,
                "direction": direction,
                "fold_position": fold_position,
            }
            if bend_radius is not None:
                params["bend_radius"] = bend_radius
            result = await _send("sheet_metal_add_fold", params)
            fname = result.get("feature_name", "Fold")
            return (
                f"Created fold '{fname}' along line '{sketch_line_id}' "
                f"(angle={fold_angle}°, direction={direction})."
            )
        except FusionConnectionError as exc:
            return f"Error adding fold: {exc}"

    @mcp.tool()
    async def add_bend(
        face1_id: str,
        face2_id: str,
        bend_radius: float = 0.3,
        bend_angle: float = 90.0,
    ) -> str:
        """Add a bend between two adjacent flat faces.

        Args:
            face1_id: First flat face ID.
            face2_id: Second flat face ID.
            bend_radius: Inner bend radius (cm).
            bend_angle: Bend angle in degrees.

        Returns:
            Confirmation with bend details.
        """
        try:
            result = await _send("sheet_metal_add_bend", {
                "face1_id": face1_id,
                "face2_id": face2_id,
                "bend_radius": bend_radius,
                "bend_angle": bend_angle,
            })
            fname = result.get("feature_name", "Bend")
            return (
                f"Created bend '{fname}' between faces '{face1_id}' and "
                f"'{face2_id}' (radius={bend_radius} cm, angle={bend_angle}°)."
            )
        except FusionConnectionError as exc:
            return f"Error adding bend: {exc}"

    @mcp.tool()
    async def add_rip(
        edge_id: str,
        rip_type: str = "single_edge",
        gap: float = 0.0,
    ) -> str:
        """Rip a sheet metal body along an edge or sketch line to open it.

        Args:
            edge_id: ID of the edge or sketch line to rip along.
            rip_type: Rip type: 'single_edge', 'point_to_point'.
            gap: Gap distance after rip (cm, 0 = no gap).

        Returns:
            Confirmation with rip details.
        """
        try:
            result = await _send("sheet_metal_add_rip", {
                "edge_id": edge_id,
                "rip_type": rip_type,
                "gap": gap,
            })
            fname = result.get("feature_name", "Rip")
            return (
                f"Created rip '{fname}' on edge '{edge_id}' "
                f"(gap={gap} cm)."
            )
        except FusionConnectionError as exc:
            return f"Error adding rip: {exc}"

    @mcp.tool()
    async def add_relief(
        corner_entity_id: str,
        relief_type: str = "circular",
        width: float = 0.3,
        depth: float = 0.3,
        relief_shape: str = "circular",
    ) -> str:
        """Add a corner relief to a sheet metal bend corner.

        Args:
            corner_entity_id: ID of the corner/bend entity.
            relief_type: Relief type: 'circular', 'square', 'linear',
                'obround', 'teardrop'.
            width: Relief width (cm).
            depth: Relief depth (cm).
            relief_shape: Shape of the relief cut.

        Returns:
            Confirmation with relief details.
        """
        try:
            result = await _send("sheet_metal_add_relief", {
                "corner_entity_id": corner_entity_id,
                "relief_type": relief_type,
                "width": width,
                "depth": depth,
                "relief_shape": relief_shape,
            })
            fname = result.get("feature_name", "Corner Relief")
            return (
                f"Created {relief_type} corner relief '{fname}' "
                f"(width={width} cm, depth={depth} cm)."
            )
        except FusionConnectionError as exc:
            return f"Error adding relief: {exc}"

    @mcp.tool()
    async def create_flat_pattern(
        orientation_face_id: str = "",
        show_flat_pattern: bool = True,
    ) -> str:
        """Create and optionally show the flat pattern representation.

        Args:
            orientation_face_id: Face to use as the fixed face during
                unfolding. Empty = auto-select.
            show_flat_pattern: If True, switch display to the flat pattern view.

        Returns:
            Confirmation with flat pattern status.
        """
        try:
            result = await _send("sheet_metal_create_flat_pattern", {
                "orientation_face_id": orientation_face_id or None,
                "show_flat_pattern": show_flat_pattern,
            })
            status = "shown" if show_flat_pattern else "created"
            area = result.get("flat_area_cm2", 0)
            return (
                f"Flat pattern {status} (area={area} cm²)."
            )
        except FusionConnectionError as exc:
            return f"Error creating flat pattern: {exc}"

    @mcp.tool()
    async def set_bend_allowance(
        allowance_type: str = "k_factor",
        k_factor: float | None = 0.44,
        bend_table_path: str | None = None,
        bend_allowance_value: float | None = None,
    ) -> str:
        """Configure bend allowance using K-factor, bend table, or direct value.

        Args:
            allowance_type: Method: 'k_factor', 'bend_table', 'bend_allowance'.
            k_factor: K-factor value (0.0–1.0).
            bend_table_path: Path to a CSV bend table file.
            bend_allowance_value: Direct bend allowance value (cm).

        Returns:
            Confirmation with bend allowance configuration.
        """
        try:
            params: dict = {"allowance_type": allowance_type}
            if allowance_type == "k_factor":
                params["k_factor"] = k_factor if k_factor is not None else 0.44
            elif allowance_type == "bend_table":
                params["bend_table_path"] = bend_table_path
            elif allowance_type == "bend_allowance":
                params["bend_allowance_value"] = bend_allowance_value
            result = await _send("sheet_metal_set_bend_allowance", params)
            if allowance_type == "k_factor":
                desc = f"K-factor={params['k_factor']}"
            elif allowance_type == "bend_table":
                desc = f"bend table at '{bend_table_path}'"
            else:
                desc = f"bend allowance={bend_allowance_value} cm"
            applied = result.get("applied", True)
            status = "applied" if applied else "failed"
            return f"Bend allowance {status}: {desc}."
        except FusionConnectionError as exc:
            return f"Error setting bend allowance: {exc}"

    @mcp.tool()
    async def punch_tool(
        sketch_point_id: str,
        punch_type: str = "standard",
        punch_name: str = "",
        angle: float = 0.0,
        depth: float = 0.0,
    ) -> str:
        """Apply a punch/press tool at a sketch point on a sheet metal face.

        Args:
            sketch_point_id: ID of the center point for the punch.
            punch_type: Punch type: 'standard', 'custom', 'user'.
            punch_name: Name/ID of the punch tool definition.
            angle: Punch rotation angle in degrees.
            depth: Punch depth override (cm, 0 = default).

        Returns:
            Confirmation with punch tool details.
        """
        try:
            params: dict = {
                "sketch_point_id": sketch_point_id,
                "punch_type": punch_type,
                "angle": angle,
            }
            if punch_name:
                params["punch_name"] = punch_name
            if depth > 0:
                params["depth"] = depth
            result = await _send("sheet_metal_punch_tool", params)
            fname = result.get("feature_name", "Punch")
            return (
                f"Applied {punch_type} punch '{fname}' at point "
                f"'{sketch_point_id}' (angle={angle}°)."
            )
        except FusionConnectionError as exc:
            return f"Error applying punch tool: {exc}"

    @mcp.tool()
    async def convert_to_sheet_metal(
        body_name: str,
        thickness: float = 0.2,
        select_fixed_face: bool = True,
        fixed_face_id: str = "",
        keep_bends: bool = True,
    ) -> str:
        """Convert imported solid geometry into a sheet metal body.

        Args:
            body_name: Name of the solid body to convert.
            thickness: Target sheet metal thickness (cm).
            select_fixed_face: If True, manually select the fixed face.
            fixed_face_id: ID of the face to remain fixed during unfolding.
            keep_bends: If True, attempt to detect and preserve existing bends.

        Returns:
            Confirmation with conversion result.
        """
        try:
            result = await _send("sheet_metal_convert", {
                "body_name": body_name,
                "thickness": thickness,
                "select_fixed_face": select_fixed_face,
                "fixed_face_id": fixed_face_id or None,
                "keep_bends": keep_bends,
            })
            bends = result.get("bends_detected", 0)
            return (
                f"Converted body '{body_name}' to sheet metal "
                f"(thickness={thickness} cm, {bends} bend(s) detected)."
            )
        except FusionConnectionError as exc:
            return f"Error converting to sheet metal: {exc}"
