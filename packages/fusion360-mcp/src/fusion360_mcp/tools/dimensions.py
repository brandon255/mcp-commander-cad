"""Dimension tools — MCP tool registrations for Fusion 360 drawing dimension
and annotation operations.

Provides 9 tools covering linear, angular, radial, diametric, and ordinate
dimensions, tolerances, precision control, geometric tolerances (GD&T),
and datum feature symbols.
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


def register_dimension_tools(mcp: FastMCP) -> None:
    """Register all dimension-related tools on the given MCP server."""

    @mcp.tool()
    async def add_linear_dim(
        sheet_name: str = "Sheet1",
        view_name: str = "",
        point1_x: float = 0.0,
        point1_y: float = 0.0,
        point2_x: float = 10.0,
        point2_y: float = 0.0,
        text_position_x: float = 5.0,
        text_position_y: float = -2.0,
        value: float | None = None,
        orientation: str = "horizontal",
    ) -> str:
        """Add a linear dimension between two points in a drawing view.

        Args:
            sheet_name: Target sheet name.
            view_name: Name of the drawing view.
            point1_x: First point X (cm).
            point1_y: First point Y (cm).
            point2_x: Second point X (cm).
            point2_y: Second point Y (cm).
            text_position_x: Dimension text placement X (cm).
            text_position_y: Dimension text placement Y (cm).
            value: Override value (None = auto-measure).
            orientation: Dimension orientation: 'horizontal', 'vertical', 'aligned'.

        Returns:
            Confirmation with dimension value and placement.
        """
        try:
            params: dict = {
                "sheet_name": sheet_name,
                "view_name": view_name,
                "point1": {"x": point1_x, "y": point1_y},
                "point2": {"x": point2_x, "y": point2_y},
                "text_position": {"x": text_position_x, "y": text_position_y},
                "orientation": orientation,
            }
            if value is not None:
                params["value"] = value
            result = await _send("drawing_add_linear_dimension", params)
            dim_value = result.get("measured_value", value)
            dim_id = result.get("dimension_id", "")
            return (
                f"Added {orientation} linear dimension (id={dim_id}) "
                f"value={dim_value} cm on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding linear dimension: {exc}"

    @mcp.tool()
    async def add_angular_dim(
        sheet_name: str = "Sheet1",
        view_name: str = "",
        vertex_x: float = 0.0,
        vertex_y: float = 0.0,
        line1_end_x: float = 10.0,
        line1_end_y: float = 0.0,
        line2_end_x: float = 5.0,
        line2_end_y: float = 8.66,
        text_position_x: float = 6.0,
        text_position_y: float = 3.0,
        value: float | None = None,
    ) -> str:
        """Add an angular dimension between two lines meeting at a vertex.

        Args:
            sheet_name: Target sheet name.
            view_name: Name of the drawing view.
            vertex_x: Vertex point X (cm).
            vertex_y: Vertex point Y (cm).
            line1_end_x: First line endpoint X (cm).
            line1_end_y: First line endpoint Y (cm).
            line2_end_x: Second line endpoint X (cm).
            line2_end_y: Second line endpoint Y (cm).
            text_position_x: Text placement X (cm).
            text_position_y: Text placement Y (cm).
            value: Override angle value in degrees (None = auto-measure).

        Returns:
            Confirmation with angle value.
        """
        try:
            params: dict = {
                "sheet_name": sheet_name,
                "view_name": view_name,
                "vertex": {"x": vertex_x, "y": vertex_y},
                "line1_end": {"x": line1_end_x, "y": line1_end_y},
                "line2_end": {"x": line2_end_x, "y": line2_end_y},
                "text_position": {"x": text_position_x, "y": text_position_y},
            }
            if value is not None:
                params["value"] = value
            result = await _send("drawing_add_angular_dimension", params)
            angle = result.get("measured_value", value)
            dim_id = result.get("dimension_id", "")
            return (
                f"Added angular dimension (id={dim_id}) value={angle}° "
                f"on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding angular dimension: {exc}"

    @mcp.tool()
    async def add_radial_dim(
        sheet_name: str = "Sheet1",
        view_name: str = "",
        center_x: float = 0.0,
        center_y: float = 0.0,
        edge_x: float = 5.0,
        edge_y: float = 0.0,
        text_position_x: float = 3.0,
        text_position_y: float = -2.0,
        value: float | None = None,
    ) -> str:
        """Add a radial dimension from center to an arc/circle edge.

        Args:
            sheet_name: Target sheet name.
            view_name: Name of the drawing view.
            center_x: Arc/circle center X (cm).
            center_y: Arc/circle center Y (cm).
            edge_x: Edge point X (cm).
            edge_y: Edge point Y (cm).
            text_position_x: Text placement X (cm).
            text_position_y: Text placement Y (cm).
            value: Override radius value (None = auto-measure).

        Returns:
            Confirmation with radius value.
        """
        try:
            params: dict = {
                "sheet_name": sheet_name,
                "view_name": view_name,
                "center": {"x": center_x, "y": center_y},
                "edge": {"x": edge_x, "y": edge_y},
                "text_position": {"x": text_position_x, "y": text_position_y},
            }
            if value is not None:
                params["value"] = value
            result = await _send("drawing_add_radial_dimension", params)
            radius = result.get("measured_value", value)
            dim_id = result.get("dimension_id", "")
            return (
                f"Added radial dimension (id={dim_id}) R={radius} cm "
                f"on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding radial dimension: {exc}"

    @mcp.tool()
    async def add_diametric_dim(
        sheet_name: str = "Sheet1",
        view_name: str = "",
        point1_x: float = -5.0,
        point1_y: float = 0.0,
        point2_x: float = 5.0,
        point2_y: float = 0.0,
        text_position_x: float = 0.0,
        text_position_y: float = -2.0,
        value: float | None = None,
    ) -> str:
        """Add a diametric dimension across a circle or arc.

        Args:
            sheet_name: Target sheet name.
            view_name: Name of the drawing view.
            point1_x: First diameter endpoint X (cm).
            point1_y: First diameter endpoint Y (cm).
            point2_x: Second diameter endpoint X (cm).
            point2_y: Second diameter endpoint Y (cm).
            text_position_x: Text placement X (cm).
            text_position_y: Text placement Y (cm).
            value: Override diameter value (None = auto-measure).

        Returns:
            Confirmation with diameter value.
        """
        try:
            params: dict = {
                "sheet_name": sheet_name,
                "view_name": view_name,
                "point1": {"x": point1_x, "y": point1_y},
                "point2": {"x": point2_x, "y": point2_y},
                "text_position": {"x": text_position_x, "y": text_position_y},
            }
            if value is not None:
                params["value"] = value
            result = await _send("drawing_add_diametric_dimension", params)
            diameter = result.get("measured_value", value)
            dim_id = result.get("dimension_id", "")
            return (
                f"Added diametric dimension (id={dim_id}) ⌀={diameter} cm "
                f"on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding diametric dimension: {exc}"

    @mcp.tool()
    async def add_ordinate_dim(
        sheet_name: str = "Sheet1",
        view_name: str = "",
        origin_x: float = 0.0,
        origin_y: float = 0.0,
        direction: str = "horizontal",
        points: str = "0,5; 0,10; 0,15",
        leader_length: float = 0.5,
    ) -> str:
        """Add an ordinate dimension set from a common origin.

        Args:
            sheet_name: Target sheet name.
            view_name: Name of the drawing view.
            origin_x: Ordinate set origin X (cm).
            origin_y: Ordinate set origin Y (cm).
            direction: Dimension direction: 'horizontal' or 'vertical'.
            points: Semicolon-separated x,y pairs for dimension points.
            leader_length: Leader line length (cm).

        Returns:
            Confirmation with ordinate dimension count and values.
        """
        try:
            parsed = []
            for pair in points.split(";"):
                parts = pair.strip().split(",")
                if len(parts) != 2:
                    return f"Error: invalid point format '{pair.strip()}'"
                parsed.append({
                    "x": float(parts[0].strip()),
                    "y": float(parts[1].strip()),
                })
            result = await _send("drawing_add_ordinate_dimension", {
                "sheet_name": sheet_name,
                "view_name": view_name,
                "origin": {"x": origin_x, "y": origin_y},
                "direction": direction,
                "points": parsed,
                "leader_length": leader_length,
            })
            count = result.get("dimension_count", len(parsed))
            return (
                f"Added ordinate dimension set ({count} dims, {direction}) "
                f"on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding ordinate dimension: {exc}"
        except (ValueError, IndexError) as exc:
            return f"Error parsing ordinate points: {exc}"

    @mcp.tool()
    async def set_tolerance(
        sheet_name: str = "Sheet1",
        dimension_id: str = "",
        tolerance_type: str = "bilateral",
        upper_value: float = 0.1,
        lower_value: float = -0.1,
        fits_class: str = "",
    ) -> str:
        """Set tolerance on a dimension (bilateral, unilateral, limits, or fits).

        Args:
            sheet_name: Sheet containing the dimension.
            dimension_id: ID of the dimension to modify.
            tolerance_type: Type: 'bilateral', 'unilateral', 'limits', 'fit'.
            upper_value: Upper tolerance value (cm).
            lower_value: Lower tolerance value (cm).
            fits_class: Fits class string (e.g. 'H7/g6') for fit tolerance.

        Returns:
            Confirmation with tolerance details.
        """
        try:
            params: dict = {
                "sheet_name": sheet_name,
                "dimension_id": dimension_id,
                "tolerance_type": tolerance_type,
                "upper_value": upper_value,
                "lower_value": lower_value,
            }
            if tolerance_type == "fit" and fits_class:
                params["fits_class"] = fits_class
            result = await _send("drawing_set_tolerance", params)
            applied = result.get("tolerance_applied", True)
            desc = f"{tolerance_type} +{upper_value} / {lower_value}"
            if tolerance_type == "fit":
                desc = f"fit {fits_class}"
            status = "applied" if applied else "failed"
            return (
                f"Tolerance {status} to dimension '{dimension_id}': "
                f"{desc} on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error setting tolerance: {exc}"

    @mcp.tool()
    async def set_precision(
        sheet_name: str = "Sheet1",
        dimension_id: str = "",
        decimal_places: int = 2,
        display_type: str = "decimal",
    ) -> str:
        """Set the decimal precision and display format of a dimension.

        Args:
            sheet_name: Sheet containing the dimension.
            dimension_id: ID of the dimension to modify.
            decimal_places: Number of decimal places (0-8).
            display_type: Format: 'decimal', 'fractional', 'degrees_min_sec'.

        Returns:
            Confirmation with precision details.
        """
        try:
            await _send("drawing_set_precision", {
                "sheet_name": sheet_name,
                "dimension_id": dimension_id,
                "decimal_places": decimal_places,
                "display_type": display_type,
            })
            return (
                f"Set dimension '{dimension_id}' precision to "
                f"{decimal_places} decimal places ({display_type}) "
                f"on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error setting precision: {exc}"

    @mcp.tool()
    async def add_gdt(
        sheet_name: str = "Sheet1",
        view_name: str = "",
        attachment_x: float = 5.0,
        attachment_y: float = 5.0,
        tolerance_type: str = "position",
        tolerance_value: float = 0.05,
        datum_a: str = "",
        datum_b: str = "",
        datum_c: str = "",
        leader_x: float = 5.0,
        leader_y: float = 8.0,
        material_condition: str = "none",
    ) -> str:
        """Add a geometric dimensioning and tolerancing (GD&T) symbol.

        Args:
            sheet_name: Target sheet name.
            view_name: Name of the drawing view.
            attachment_x: Feature control frame attachment X (cm).
            attachment_y: Feature control frame attachment Y (cm).
            tolerance_type: GD&T type: 'position', 'perpendicularity',
                'parallelism', 'angularity', 'concentricity', 'cylindricity',
                'circularity', 'flatness', 'straightness', 'symmetry',
                'profile_of_a_line', 'profile_of_a_surface',
                'runout_circular', 'runout_total'.
            tolerance_value: Tolerance zone value (cm or degrees).
            datum_a: Primary datum reference letter.
            datum_b: Secondary datum reference letter.
            datum_c: Tertiary datum reference letter.
            leader_x: Leader end X (cm).
            leader_y: Leader end Y (cm).
            material_condition: Modifier: 'none', 'MMC', 'LMC', 'RFS'.

        Returns:
            Confirmation with GD&T symbol details.
        """
        try:
            result = await _send("drawing_add_gdt", {
                "sheet_name": sheet_name,
                "view_name": view_name,
                "attachment": {"x": attachment_x, "y": attachment_y},
                "tolerance_type": tolerance_type,
                "tolerance_value": tolerance_value,
                "datum_a": datum_a or None,
                "datum_b": datum_b or None,
                "datum_c": datum_c or None,
                "leader": {"x": leader_x, "y": leader_y},
                "material_condition": material_condition,
            })
            gdt_id = result.get("gdt_id", "")
            datums = [d for d in [datum_a, datum_b, datum_c] if d]
            datum_str = f"-{','.join(datums)}" if datums else ""
            mc = f" ({material_condition})" if material_condition != "none" else ""
            return (
                f"Added GD&T symbol (id={gdt_id}): {tolerance_type} "
                f"⌀{tolerance_value}{datum_str}{mc} "
                f"on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding GD&T symbol: {exc}"

    @mcp.tool()
    async def add_datum_feature(
        sheet_name: str = "Sheet1",
        view_name: str = "",
        attachment_x: float = 0.0,
        attachment_y: float = 0.0,
        datum_letter: str = "A",
        leader_x: float = 0.0,
        leader_y: float = -3.0,
    ) -> str:
        """Add a datum feature symbol with a leader line on a drawing.

        Args:
            sheet_name: Target sheet name.
            view_name: Name of the drawing view.
            attachment_x: Datum symbol attachment X (cm).
            attachment_y: Datum symbol attachment Y (cm).
            datum_letter: Datum letter (A-Z).
            leader_x: Leader end X (cm).
            leader_y: Leader end Y (cm).

        Returns:
            Confirmation with datum feature symbol details.
        """
        try:
            result = await _send("drawing_add_datum_feature", {
                "sheet_name": sheet_name,
                "view_name": view_name,
                "attachment": {"x": attachment_x, "y": attachment_y},
                "datum_letter": datum_letter,
                "leader": {"x": leader_x, "y": leader_y},
            })
            df_id = result.get("datum_id", "")
            return (
                f"Added datum feature symbol '{datum_letter}' (id={df_id}) "
                f"at ({attachment_x}, {attachment_y}) on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding datum feature: {exc}"
