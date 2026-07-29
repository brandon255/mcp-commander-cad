"""Drawing tools — MCP tool registrations for Fusion 360 2D drawing operations.

Provides 13 tools covering drawing creation, views (base, projected, section,
detail, isometric), sheet management, BOM, balloons, centerlines, export,
and title blocks.
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


def register_drawing_tools(mcp: FastMCP) -> None:
    """Register all drawing-related tools on the given MCP server."""

    @mcp.tool()
    async def create_drawing(
        design_document: str = "",
        sheet_size: str = "A3",
        standard: str = "ISO",
    ) -> str:
        """Create a new 2D drawing document from a design.

        Args:
            design_document: Path or name of the design document to reference.
                Empty string uses the active design.
            sheet_size: Sheet size: 'A0', 'A1', 'A2', 'A3', 'A4',
                'A', 'B', 'C', 'D', 'E'.
            standard: Drawing standard: 'ISO', 'ANSI', 'DIN', 'JIS', 'GB'.

        Returns:
            Confirmation with drawing document name.
        """
        try:
            result = await _send("drawing_create", {
                "design_document": design_document or None,
                "sheet_size": sheet_size,
                "standard": standard,
            })
            doc_name = result.get("document_name", "Drawing")
            sheet_name = result.get("sheet_name", "Sheet1")
            return (
                f"Created drawing '{doc_name}' ({standard}, {sheet_size}) "
                f"with sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error creating drawing: {exc}"

    @mcp.tool()
    async def add_base_view(
        sheet_name: str = "Sheet1",
        orientation: str = "front",
        scale: float = 1.0,
        position_x: float = 15.0,
        position_y: float = 20.0,
        style: str = "hidden",
        design_document: str = "",
    ) -> str:
        """Add a base drawing view to a sheet.

        Args:
            sheet_name: Target sheet name.
            orientation: View orientation: 'front', 'back', 'top', 'bottom',
                'right', 'left', 'isometric_right', 'isometric_left',
                'isometric_top', 'isometric_bottom'.
            scale: View scale factor.
            position_x: View placement X (cm).
            position_y: View placement Y (cm).
            style: Display style: 'visible', 'hidden', 'shaded', 'shaded_hidden'.
            design_document: Design document to reference (empty = active).

        Returns:
            Confirmation with view name and placement.
        """
        try:
            result = await _send("drawing_add_base_view", {
                "sheet_name": sheet_name,
                "orientation": orientation,
                "scale": scale,
                "position": {"x": position_x, "y": position_y},
                "style": style,
                "design_document": design_document or None,
            })
            view_name = result.get("view_name", "Base View")
            return (
                f"Added base view '{view_name}' ({orientation}, scale={scale}) "
                f"at ({position_x}, {position_y}) on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding base view: {exc}"

    @mcp.tool()
    async def add_projected_view(
        parent_view_name: str,
        direction: str = "right",
        offset_x: float = 20.0,
        offset_y: float = 0.0,
        scale: float = 1.0,
        style: str = "hidden",
        sheet_name: str = "Sheet1",
    ) -> str:
        """Add a projected (orthographic) view derived from a parent view.

        Args:
            parent_view_name: Name of the parent base or projected view.
            direction: Projection direction: 'right', 'left', 'top', 'bottom',
                'top_right', 'bottom_right', 'top_left', 'bottom_left'.
            offset_x: X offset from parent view center (cm).
            offset_y: Y offset from parent view center (cm).
            scale: View scale (default = parent scale).
            style: Display style: 'visible', 'hidden', 'shaded', 'shaded_hidden'.
            sheet_name: Target sheet name.

        Returns:
            Confirmation with projected view details.
        """
        try:
            result = await _send("drawing_add_projected_view", {
                "parent_view_name": parent_view_name,
                "direction": direction,
                "offset": {"x": offset_x, "y": offset_y},
                "scale": scale,
                "style": style,
                "sheet_name": sheet_name,
            })
            view_name = result.get("view_name", "Projected View")
            return (
                f"Added projected view '{view_name}' ({direction}) "
                f"from '{parent_view_name}' on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding projected view: {exc}"

    @mcp.tool()
    async def add_section_view(
        parent_view_name: str,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        offset_x: float = 25.0,
        offset_y: float = 0.0,
        scale: float = 1.0,
        style: str = "hidden",
        section_label: str = "A",
        sheet_name: str = "Sheet1",
    ) -> str:
        """Add a section view by placing a cutting line through a parent view.

        Args:
            parent_view_name: Name of the parent view.
            start_x: Cutting line start X in sheet coordinates (cm).
            start_y: Cutting line start Y (cm).
            end_x: Cutting line end X (cm).
            end_y: Cutting line end Y (cm).
            offset_x: X offset for section view placement (cm).
            offset_y: Y offset for section view placement (cm).
            scale: Section view scale.
            style: Display style.
            section_label: Section label text (e.g. 'A', 'B', 'A-A').
            sheet_name: Target sheet name.

        Returns:
            Confirmation with section view details.
        """
        try:
            result = await _send("drawing_add_section_view", {
                "parent_view_name": parent_view_name,
                "cutting_line": {
                    "start": {"x": start_x, "y": start_y},
                    "end": {"x": end_x, "y": end_y},
                },
                "offset": {"x": offset_x, "y": offset_y},
                "scale": scale,
                "style": style,
                "section_label": section_label,
                "sheet_name": sheet_name,
            })
            view_name = result.get("view_name", "Section View")
            return (
                f"Added section view '{view_name}' (label={section_label}) "
                f"from '{parent_view_name}' on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding section view: {exc}"

    @mcp.tool()
    async def add_detail_view(
        parent_view_name: str,
        center_x: float,
        center_y: float,
        radius: float,
        offset_x: float = 20.0,
        offset_y: float = 20.0,
        scale: float = 2.0,
        style: str = "hidden",
        detail_label: str = "A",
        sheet_name: str = "Sheet1",
    ) -> str:
        """Add a detail (circular magnified) view of a region of a parent view.

        Args:
            parent_view_name: Name of the parent view.
            center_x: Detail circle center X in parent view coords (cm).
            center_y: Detail circle center Y (cm).
            radius: Detail circle radius (cm).
            offset_x: X offset for detail view placement (cm).
            offset_y: Y offset for detail view placement (cm).
            scale: Detail view scale (magnification).
            style: Display style.
            detail_label: Detail label text.
            sheet_name: Target sheet name.

        Returns:
            Confirmation with detail view details.
        """
        try:
            result = await _send("drawing_add_detail_view", {
                "parent_view_name": parent_view_name,
                "circle_center": {"x": center_x, "y": center_y},
                "circle_radius": radius,
                "offset": {"x": offset_x, "y": offset_y},
                "scale": scale,
                "style": style,
                "detail_label": detail_label,
                "sheet_name": sheet_name,
            })
            view_name = result.get("view_name", "Detail View")
            return (
                f"Added detail view '{view_name}' (label={detail_label}, "
                f"scale={scale}x) from '{parent_view_name}' "
                f"on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding detail view: {exc}"

    @mcp.tool()
    async def add_isometric_view(
        sheet_name: str = "Sheet1",
        scale: float = 1.0,
        position_x: float = 30.0,
        position_y: float = 20.0,
        style: str = "shaded",
        design_document: str = "",
    ) -> str:
        """Add an isometric or perspective view directly to a drawing sheet.

        Args:
            sheet_name: Target sheet name.
            scale: View scale factor.
            position_x: View placement X (cm).
            position_y: View placement Y (cm).
            style: Display style: 'visible', 'hidden', 'shaded', 'shaded_hidden'.
            design_document: Design to reference (empty = active).

        Returns:
            Confirmation with isometric view details.
        """
        try:
            result = await _send("drawing_add_isometric_view", {
                "sheet_name": sheet_name,
                "scale": scale,
                "position": {"x": position_x, "y": position_y},
                "style": style,
                "design_document": design_document or None,
            })
            view_name = result.get("view_name", "Isometric View")
            return (
                f"Added isometric view '{view_name}' (scale={scale}, "
                f"{style}) at ({position_x}, {position_y}) "
                f"on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding isometric view: {exc}"

    @mcp.tool()
    async def set_sheet_size(
        sheet_name: str = "Sheet1",
        sheet_size: str = "A3",
    ) -> str:
        """Change the size of an existing drawing sheet.

        Args:
            sheet_name: Name of the sheet to modify.
            sheet_size: New sheet size: 'A0'-'A4', 'A'-'E'.

        Returns:
            Confirmation of size change.
        """
        try:
            await _send("drawing_set_sheet_size", {
                "sheet_name": sheet_name,
                "sheet_size": sheet_size,
            })
            return f"Changed sheet '{sheet_name}' size to {sheet_size}."
        except FusionConnectionError as exc:
            return f"Error setting sheet size: {exc}"

    @mcp.tool()
    async def add_bom(
        sheet_name: str = "Sheet1",
        position_x: float = 40.0,
        position_y: float = 25.0,
        table_type: str = "top_level",
    ) -> str:
        """Add a bill of materials table to the drawing.

        Args:
            sheet_name: Target sheet name.
            position_x: BOM table insertion X (cm).
            position_y: BOM table insertion Y (cm).
            table_type: BOM type: 'top_level', 'parts_only', 'structured'.

        Returns:
            Confirmation with BOM details and item count.
        """
        try:
            result = await _send("drawing_add_bom", {
                "sheet_name": sheet_name,
                "position": {"x": position_x, "y": position_y},
                "table_type": table_type,
            })
            items = result.get("item_count", 0)
            return (
                f"Added {table_type} BOM table with {items} items "
                f"at ({position_x}, {position_y}) on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding BOM: {exc}"

    @mcp.tool()
    async def add_balloon(
        sheet_name: str = "Sheet1",
        view_name: str = "",
        point_x: float = 10.0,
        point_y: float = 10.0,
        item_number: int = 1,
        leader_type: str = "straight",
        balloon_style: str = "circular",
    ) -> str:
        """Add a balloon with a leader line pointing to a component in a view.

        Args:
            sheet_name: Target sheet name.
            view_name: Name of the drawing view to attach to.
            point_x: Balloon attachment point X (cm).
            point_y: Balloon attachment point Y (cm).
            item_number: BOM item number to display.
            leader_type: Leader style: 'straight', 'bent', 'none'.
            balloon_style: Balloon shape: 'circular', 'hexagonal', 'diamond'.

        Returns:
            Confirmation with balloon details.
        """
        try:
            result = await _send("drawing_add_balloon", {
                "sheet_name": sheet_name,
                "view_name": view_name,
                "point": {"x": point_x, "y": point_y},
                "item_number": item_number,
                "leader_type": leader_type,
                "balloon_style": balloon_style,
            })
            bid = result.get("balloon_id", "")
            return (
                f"Added balloon (id={bid}) item #{item_number} "
                f"at ({point_x}, {point_y}) on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding balloon: {exc}"

    @mcp.tool()
    async def add_centerline(
        sheet_name: str = "Sheet1",
        view_name: str = "",
        entity_type: str = "centerline",
        point1_x: float = 0.0,
        point1_y: float = 0.0,
        point2_x: float = 10.0,
        point2_y: float = 0.0,
    ) -> str:
        """Add centerlines or center marks to a drawing view.

        Args:
            sheet_name: Target sheet name.
            view_name: Name of the target drawing view.
            entity_type: Type: 'centerline', 'center_mark', 'hole_center',
                'bolt_circle'.
            point1_x: First defining point X (cm).
            point1_y: First defining point Y (cm).
            point2_x: Second defining point X (cm).
            point2_y: Second defining point Y (cm).

        Returns:
            Confirmation with centerline details.
        """
        try:
            result = await _send("drawing_add_centerline", {
                "sheet_name": sheet_name,
                "view_name": view_name,
                "entity_type": entity_type,
                "point1": {"x": point1_x, "y": point1_y},
                "point2": {"x": point2_x, "y": point2_y},
            })
            cl_id = result.get("centerline_id", "")
            return (
                f"Added {entity_type} (id={cl_id}) on sheet '{sheet_name}'."
            )
        except FusionConnectionError as exc:
            return f"Error adding centerline: {exc}"

    @mcp.tool()
    async def export_pdf(
        output_path: str,
        sheet_range: str = "all",
        dpi: int = 300,
    ) -> str:
        """Export the drawing to a PDF file.

        Args:
            output_path: Absolute output file path (.pdf).
            sheet_range: Sheets to export: 'all', 'active', or comma-separated
                sheet names.
            dpi: Resolution for rasterized elements (DPI).

        Returns:
            Confirmation with exported file path and size.
        """
        try:
            sheets = [s.strip() for s in sheet_range.split(",") if s.strip()]
            params: dict = {
                "output_path": output_path,
                "dpi": dpi,
            }
            if sheet_range == "all":
                params["sheet_range"] = "all"
            elif sheet_range == "active":
                params["sheet_range"] = "active"
            else:
                params["sheet_names"] = sheets
            result = await _send("drawing_export_pdf", params)
            fsize = result.get("file_size_bytes", 0)
            return (
                f"Exported drawing PDF to '{output_path}' "
                f"({fsize} bytes, {dpi} DPI)."
            )
        except FusionConnectionError as exc:
            return f"Error exporting PDF: {exc}"

    @mcp.tool()
    async def export_dxf(
        output_path: str,
        sheet_name: str = "Sheet1",
        version: str = "R2018",
    ) -> str:
        """Export a drawing sheet to a DXF file.

        Args:
            output_path: Absolute output file path (.dxf).
            sheet_name: Sheet to export.
            version: DXF version: 'R2018', 'R2013', 'R2010', 'R2007'.

        Returns:
            Confirmation with exported file path.
        """
        try:
            result = await _send("drawing_export_dxf", {
                "output_path": output_path,
                "sheet_name": sheet_name,
                "version": version,
            })
            fsize = result.get("file_size_bytes", 0)
            return (
                f"Exported sheet '{sheet_name}' to DXF '{output_path}' "
                f"({fsize} bytes, version={version})."
            )
        except FusionConnectionError as exc:
            return f"Error exporting DXF: {exc}"

    @mcp.tool()
    async def add_title_block(
        sheet_name: str = "Sheet1",
        title: str = "",
        author: str = "",
        drawn_date: str = "",
        material: str = "",
        scale: str = "",
        drawing_number: str = "",
        company: str = "",
    ) -> str:
        """Insert or edit the title block on a drawing sheet.

        Args:
            sheet_name: Target sheet name.
            title: Drawing title text.
            author: Author name.
            drawn_date: Date string (e.g. '2024-01-15').
            material: Material specification.
            scale: Scale text (e.g. '1:1').
            drawing_number: Drawing number / part number.
            company: Company name.

        Returns:
            Confirmation of title block creation/edit.
        """
        try:
            params: dict = {"sheet_name": sheet_name}
            if title:
                params["title"] = title
            if author:
                params["author"] = author
            if drawn_date:
                params["drawn_date"] = drawn_date
            if material:
                params["material"] = material
            if scale:
                params["scale"] = scale
            if drawing_number:
                params["drawing_number"] = drawing_number
            if company:
                params["company"] = company
            await _send("drawing_add_title_block", params)
            fields = [k for k, v in params.items() if k != "sheet_name" and v]
            return (
                f"Updated title block on '{sheet_name}' with fields: "
                f"{', '.join(fields)}."
            )
        except FusionConnectionError as exc:
            return f"Error adding title block: {exc}"
