"""Analysis tools — MCP tool registrations for Fusion 360 analysis operations.

Provides 11 tools covering sketch constraint validation, feature tree analysis,
model physical properties, distance/angle measurement, manufacturability checks,
section properties, interference detection, curvature analysis, viewport
screenshots, and wall thickness analysis.
"""

from __future__ import annotations

import json
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


def register_analysis_tools(mcp: FastMCP) -> None:
    """Register all analysis-related tools on the given MCP server."""

    @mcp.tool()
    async def validate_sketch_constraints(sketch_name: str = "") -> str:
        """Validate constraints on a sketch and report status.

        Checks constraint status for all entities, reporting which are
        fully constrained, under-constrained, or over-constrained, plus
        a list of specific issues found.

        Args:
            sketch_name: Name of the sketch to validate. Empty string validates
                the active sketch.

        Returns:
            Constraint validation report with entity counts and issues.
        """
        try:
            params: dict = {"sketch_name": sketch_name}
            result = await _send("sketch_validate_constraints", params)
            return json.dumps(
                {
                    "status": "ok",
                    "sketch_name": sketch_name or result.get("sketch_name", "active"),
                    "entities": result.get("entities", []),
                    "fully_constrained": result.get("fully_constrained", 0),
                    "under_constrained": result.get("under_constrained", 0),
                    "over_constrained": result.get("over_constrained", 0),
                    "issues": result.get("issues", []),
                }
            )
        except FusionConnectionError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def analyze_feature_tree(
        include_params: bool = True,
        include_timing: bool = False,
    ) -> str:
        """Analyze the parametric feature tree of the active design.

        Returns an ordered list of features with their type, state,
        parameters (optionally), and dependency chain.

        Args:
            include_params: Include feature parameters in the output.
            include_timing: Include computation/regeneration timing data.

        Returns:
            Feature tree analysis with per-feature metadata.
        """
        try:
            params = {
                "include_params": include_params,
                "include_timing": include_timing,
            }
            result = await _send("feature_analyze_tree", params)
            return json.dumps(
                {
                    "status": "ok",
                    "features": result.get("features", []),
                    "total_features": result.get("total_features", 0),
                    "timeline": result.get("timeline", []),
                }
            )
        except FusionConnectionError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def get_model_properties(
        units: str = "cm",
        precision: int = 4,
    ) -> str:
        """Get physical properties of the active model.

        Returns mass, volume, surface area, bounding box, center of mass,
        and density for all bodies in the design.

        Args:
            units: Length units for output. One of: "cm", "mm", "m", "in", "ft".
            precision: Decimal precision for property values.

        Returns:
            Physical properties with per-body breakdown.
        """
        try:
            params = {"units": units, "precision": precision}
            result = await _send("analysis_get_physical_properties", params)
            return json.dumps(
                {
                    "status": "ok",
                    "units": units,
                    "bodies": result.get("bodies", []),
                    "total_mass": result.get("total_mass", 0),
                    "total_volume": result.get("total_volume", 0),
                    "total_surface_area": result.get("total_surface_area", 0),
                    "bounding_box": result.get("bounding_box", {}),
                    "center_of_mass": result.get("center_of_mass", {}),
                    "density": result.get("density", 0),
                }
            )
        except FusionConnectionError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def measure_distance(
        entity1_type: str = "face",
        entity1_name: str = "",
        entity2_type: str = "face",
        entity2_name: str = "",
    ) -> str:
        """Measure the minimum distance between two entities.

        Supports measuring between faces, edges, vertices, or sketch entities.
        Returns both the distance and the delta XYZ components.

        Args:
            entity1_type: Type of first entity: 'face', 'edge', 'vertex', 'sketch_entity'.
            entity1_name: Name or ID of the first entity.
            entity2_type: Type of second entity: 'face', 'edge', 'vertex', 'sketch_entity'.
            entity2_name: Name or ID of the second entity.

        Returns:
            Distance measurement with delta XYZ components.
        """
        try:
            params = {
                "entity1": {"type": entity1_type, "name": entity1_name},
                "entity2": {"type": entity2_type, "name": entity2_name},
            }
            result = await _send("analysis_measure_distance", params)
            return json.dumps(
                {
                    "status": "ok",
                    "distance": result.get("distance", 0),
                    "delta_x": result.get("delta_x", 0),
                    "delta_y": result.get("delta_y", 0),
                    "delta_z": result.get("delta_z", 0),
                    "entity1_point": result.get("entity1_point", {}),
                    "entity2_point": result.get("entity2_point", {}),
                }
            )
        except FusionConnectionError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def measure_angle(
        entity1_type: str = "face",
        entity1_name: str = "",
        entity2_type: str = "face",
        entity2_name: str = "",
    ) -> str:
        """Measure the angle between two entities.

        Supports measuring angles between faces, edges, or sketch lines.
        Returns the angle in both degrees and radians.

        Args:
            entity1_type: Type of first entity: 'face', 'edge', 'sketch_line'.
            entity1_name: Name or ID of the first entity.
            entity2_type: Type of second entity: 'face', 'edge', 'sketch_line'.
            entity2_name: Name or ID of the second entity.

        Returns:
            Angle measurement in degrees and radians.
        """
        try:
            params = {
                "entity1": {"type": entity1_type, "name": entity1_name},
                "entity2": {"type": entity2_type, "name": entity2_name},
            }
            result = await _send("analysis_measure_angle", params)
            return json.dumps(
                {
                    "status": "ok",
                    "angle_degrees": result.get("angle_degrees", 0),
                    "angle_radians": result.get("angle_radians", 0),
                    "supplementary_degrees": result.get("supplementary_degrees", 0),
                    "supplementary_radians": result.get("supplementary_radians", 0),
                }
            )
        except FusionConnectionError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def check_manufacturability(
        process: str = "cnc",
        strictness: str = "standard",
    ) -> str:
        """Check the active design for manufacturability issues (DFM).

        Analyzes geometry for potential manufacturing problems based on
        the selected process and strictness level. Returns a DFM score
        from 0 to 100 with specific issues and severity ratings.

        Args:
            process: Manufacturing process to check against. Options: 'cnc',
                'turning', 'laser', 'waterjet', 'edm', 'injection_molding',
                '3d_print', 'sheet_metal', 'die_casting', 'sand_casting'.
            strictness: Analysis strictness: 'relaxed', 'standard', 'strict'.

        Returns:
            DFM score and list of issues with severity levels.
        """
        try:
            params = {"process": process, "strictness": strictness}
            result = await _send("analysis_check_manufacturability", params)
            return json.dumps(
                {
                    "status": "ok",
                    "process": process,
                    "strictness": strictness,
                    "dfm_score": result.get("dfm_score", 0),
                    "issues": result.get("issues", []),
                    "summary": result.get("summary", ""),
                }
            )
        except FusionConnectionError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def analyze_section_properties(
        plane: str = "XY",
        profile: str = "all",
    ) -> str:
        """Analyze section properties of cross-sections.

        Calculates area, centroid, moments of inertia, and section moduli
        for the selected cutting plane through the model.

        Args:
            plane: Section plane orientation. Options: 'XY', 'XZ', 'YZ', or a
                custom plane name.
            profile: Which profile to analyze. Options: 'all', or a specific
                profile name/ID.

        Returns:
            Section properties including area, centroid, moments of inertia.
        """
        try:
            params = {"plane": plane, "profile": profile}
            result = await _send("analysis_section_properties", params)
            return json.dumps(
                {
                    "status": "ok",
                    "plane": plane,
                    "area": result.get("area", 0),
                    "centroid": result.get("centroid", {}),
                    "Ix": result.get("Ix", 0),
                    "Iy": result.get("Iy", 0),
                    "Ixy": result.get("Ixy", 0),
                    "J": result.get("J", 0),
                    "section_modulus_x": result.get("section_modulus_x", 0),
                    "section_modulus_y": result.get("section_modulus_y", 0),
                    "radius_of_gyration": result.get("radius_of_gyration", {}),
                }
            )
        except FusionConnectionError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def detect_interference_detailed(
        component1: str = "",
        component2: str = "",
        tolerance: float = 0.0,
    ) -> str:
        """Detect interference between components with detailed results.

        Finds intersections and interferences between bodies, returning
        volume and center point of each interference region.

        Args:
            component1: Name of the first component. Empty for all bodies.
            component2: Name of the second component. Empty to check against all.
            tolerance: Interference detection tolerance in cm.

        Returns:
            List of interferences with volume and center coordinates.
        """
        try:
            params = {
                "component1": component1,
                "component2": component2,
                "tolerance": tolerance,
            }
            result = await _send("analysis_interference", params)
            return json.dumps(
                {
                    "status": "ok",
                    "interferences_found": result.get("interferences_found", 0),
                    "interferences": result.get("interferences", []),
                    "total_interference_volume": result.get(
                        "total_interference_volume", 0
                    ),
                }
            )
        except FusionConnectionError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def analyze_curvature(
        face_name: str = "",
        analysis_type: str = "gaussian",
    ) -> str:
        """Analyze surface curvature of model faces.

        Computes curvature statistics for specified faces using Gaussian,
        mean, principal, or maximum curvature analysis.

        Args:
            face_name: Name or ID of the face to analyze. Empty for all faces.
            analysis_type: Type of curvature analysis. Options: 'gaussian',
                'mean', 'principal', 'maximum', 'minimum'.

        Returns:
            Curvature statistics per face including min, max, mean, and std dev.
        """
        try:
            params = {"face_name": face_name, "analysis_type": analysis_type}
            result = await _send("analysis_curvature", params)
            return json.dumps(
                {
                    "status": "ok",
                    "analysis_type": analysis_type,
                    "faces": result.get("faces", []),
                    "total_faces_analyzed": result.get("total_faces_analyzed", 0),
                }
            )
        except FusionConnectionError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def export_screenshot(
        view_type: str = "isometric",
        width: int = 1920,
        height: int = 1080,
        output_path: str = "",
        background_color: str = "white",
    ) -> str:
        """Capture a viewport screenshot of the active design.

        Renders the current view to an image file at the specified resolution.

        Args:
            view_type: Camera view type. Options: 'isometric', 'front', 'back',
                'top', 'bottom', 'left', 'right', 'perspective'.
            width: Image width in pixels.
            height: Image height in pixels.
            output_path: File path for the saved image. Empty for auto-generated.
            background_color: Background color: 'white', 'black', 'gray', or
                a hex color string like '#RRGGBB'.

        Returns:
            File path and image dimensions of the captured screenshot.
        """
        try:
            params = {
                "view_type": view_type,
                "width": width,
                "height": height,
                "output_path": output_path,
                "background_color": background_color,
            }
            result = await _send("viewport_capture", params)
            return json.dumps(
                {
                    "status": "ok",
                    "file_path": result.get("file_path", ""),
                    "width": result.get("width", width),
                    "height": result.get("height", height),
                    "view_type": result.get("view_type", view_type),
                }
            )
        except FusionConnectionError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def analyze_wall_thickness(
        target_thickness: float = 0.0,
        threshold_percent: float = 20.0,
    ) -> str:
        """Analyze wall thickness throughout the model.

        Identifies areas that are too thin or too thick relative to the target
        thickness, based on the specified threshold percentage.

        Args:
            target_thickness: Target wall thickness in cm. 0 for automatic.
            threshold_percent: Percentage deviation from target to flag as issue.
                E.g., 20 means flag areas more than 20% thinner or thicker.

        Returns:
            Wall thickness analysis with min, max, average, and problem areas.
        """
        try:
            params = {
                "target_thickness": target_thickness,
                "threshold_percent": threshold_percent,
            }
            result = await _send("analysis_wall_thickness", params)
            return json.dumps(
                {
                    "status": "ok",
                    "target_thickness": result.get("target_thickness", target_thickness),
                    "min_thickness": result.get("min_thickness", 0),
                    "max_thickness": result.get("max_thickness", 0),
                    "avg_thickness": result.get("avg_thickness", 0),
                    "thin_areas": result.get("thin_areas", []),
                    "thick_areas": result.get("thick_areas", []),
                    "summary": result.get("summary", ""),
                }
            )
        except FusionConnectionError as e:
            return f"Error: {e}"
