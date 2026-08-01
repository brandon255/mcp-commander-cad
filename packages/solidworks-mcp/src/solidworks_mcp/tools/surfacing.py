"""
Surface modeling tools for Solidworks MCP server.

Knit, fill, shut-off, offset, planar, and extend surfaces - part of the
toolkit needed to turn a surface shell (e.g. from an imported/repaired mesh)
into a true closed solid body natively in Solidworks.

Feature inspiration (which SolidWorks operations to expose) came from Eduardo
Font Cruz's Eduardof0nt/Solidworks-MCP-Server (MIT License),
https://github.com/Eduardof0nt/Solidworks-MCP-Server - but the actual method
names/signatures below were re-derived from this machine's real, generated
SolidWorks 2026 COM type library, not copied from that repo. Its method names
targeted SolidWorks 2024 and several have since been renamed/moved (e.g.
InsertKnitSurface -> InsertSewRefSurface, InsertFilledSurface ->
InsertFillSurface, InsertShutOffSurfaces -> InsertMoldShutOffSurface, and
InsertOffsetSurface/InsertPlanarRefSurface/InsertExtendSurface live on the
document object directly, not FeatureManager). Every method below was called
against a live SolidWorks 2026 session and confirmed to exist before being
committed here.

thicken_surface and trim_surface are NOT implemented: no equivalent single-
call FeatureManager/document method could be found in the real 2026 type
library (FeatureBossThicken/FeatureCutThicken are a different operation -
thickening relative to an existing face, not converting a selected surface
into a standalone solid; surface trim only exposes a two-phase
PreTrimSurface/PostTrimSurface pair that needs live UI-style interaction to
drive correctly). Shipping a guessed signature for either would repeat the
exact mistake this file's history is a record of fixing - left out rather
than risk it.
"""
from solidworks_mcp.api.connection import get_active_doc

MM_TO_M = 0.001


def register_surfacing_tools(mcp):
    @mcp.tool()
    def knit_surfaces(try_form_solid: bool = True, use_gap_filters: bool = False,
                       merge_entities: bool = False, gap_tolerance: float = 0.0) -> str:
        """Knit selected surface bodies into a single surface, or a closed solid if the result is watertight.

        Select all surface bodies to knit first (e.g. via select_entity, append=True for multiple).
        If the knitted result forms a closed volume, Solidworks automatically produces a solid body.

        Args:
            try_form_solid: Attempt to create a solid body if the knit result is closed
            use_gap_filters: Attempt to knit surfaces with small gaps between edges
            merge_entities: Merge coincident/redundant entities during knit
            gap_tolerance: Gap tolerance in mm (only meaningful when use_gap_filters=True)
        """
        try:
            doc = get_active_doc()
            feat = doc.FeatureManager.InsertSewRefSurface(
                use_gap_filters, try_form_solid, merge_entities, gap_tolerance * MM_TO_M, gap_tolerance * MM_TO_M
            )
            if feat is None:
                return "Error: Knit surfaces failed. Select surface bodies to knit first."
            return f"Knit surfaces created: feature={feat.Name}"
        except Exception as e:
            return f"Error knitting surfaces: {e}"

    @mcp.tool()
    def planar_surface() -> str:
        """Create a planar surface from a selected closed sketch profile or a closed loop of edges.

        Select the closed sketch/edges first.
        """
        try:
            doc = get_active_doc()
            feat = doc.InsertPlanarRefSurface()
            if feat is None:
                return "Error: Planar surface failed. Select a closed sketch or edge loop first."
            return f"Planar surface created: feature={feat.Name}"
        except Exception as e:
            return f"Error creating planar surface: {e}"

    @mcp.tool()
    def filled_surface(resolution: int = 0) -> str:
        """Fill a closed boundary of edges with a new surface (patches holes in a surface shell).

        Select the closed boundary edges first.

        Args:
            resolution: 0 = normal resolution, higher values increase surface quality/complexity
        """
        try:
            doc = get_active_doc()
            feat = doc.FeatureManager.InsertFillSurface(resolution)
            if feat is None:
                return "Error: Filled surface failed. Select closed boundary edges first."
            return f"Filled surface created: feature={feat.Name}"
        except Exception as e:
            return f"Error creating filled surface: {e}"

    @mcp.tool()
    def shut_off_surface() -> str:
        """Automatically create shut-off surfaces over every open hole in the selected surface/solid body.

        Useful for turning a surface shell with stray openings into a closed, waterproof body in one call -
        select the body first.
        """
        try:
            doc = get_active_doc()
            feat = doc.FeatureManager.InsertMoldShutOffSurface()
            if feat is None:
                return "Error: Shut-off surface failed. Select a body with open holes first."
            return f"Shut-off surfaces created: feature={feat.Name}"
        except Exception as e:
            return f"Error creating shut-off surfaces: {e}"

    @mcp.tool()
    def offset_surface(distance: float, flip: bool = False) -> str:
        """Offset a selected face or surface by a distance to create a new offset surface.

        Args:
            distance: Offset distance in mm
            flip: Reverse the offset direction
        """
        try:
            doc = get_active_doc()
            feat = doc.InsertOffsetSurface(distance * MM_TO_M, flip)
            if feat is None:
                return "Error: Offset surface failed. Select a face/surface first."
            return f"Offset surface created: feature={feat.Name}, distance_mm={distance}"
        except Exception as e:
            return f"Error offsetting surface: {e}"

    @mcp.tool()
    def extend_surface(distance: float, linear: bool = True, end_condition: int = 0) -> str:
        """Extend a selected surface edge by a distance.

        Select the surface edge(s) to extend first.

        Args:
            distance: Extension distance in mm
            linear: True = extend linearly (straight), False = extend following the surface's curvature
            end_condition: 0 = distance, 1 = up to point, 2 = up to surface (point/surface must be
                           pre-selected along with the edge when using 1 or 2)
        """
        try:
            doc = get_active_doc()
            feat = doc.InsertExtendSurface(linear, end_condition, distance * MM_TO_M)
            if feat is None:
                return "Error: Extend surface failed. Select a surface edge first."
            return f"Extend surface created: feature={feat.Name}, distance_mm={distance}"
        except Exception as e:
            return f"Error extending surface: {e}"
