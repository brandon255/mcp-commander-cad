"""
Feature tools for Solidworks MCP server.
Provides extrude, revolve, fillet, chamfer, hole wizard, sweep, loft, and pattern tools.
"""
from solidworks_mcp.api.connection import get_sw_app, get_active_doc

# End condition constants for Solidworks API
SW_ENDCOND_BLIND = 0
SW_ENDCOND_THROUGH_ALL = 1
SW_ENDCOND_THROUGH_BOTH = 2
SW_ENDCOND_MID_PLANE = 4
SW_ENDCOND_UP_TO_VERTEX = 5
SW_ENDCOND_UP_TO_SURFACE = 6
SW_ENDCOND_OFFSET_FROM_SURFACE = 7
SW_ENDCOND_UP_TO_BODY = 8

# Feature type constants
SW_FEAT_EXTRUDE_BOSS = 0
SW_FEAT_EXTRUDE_CUT = 1
SW_FEAT_REVOLVE_BOSS = 3
SW_FEAT_REVOLVE_CUT = 4
SW_FEAT_FILLET = 6
SW_FEAT_CHAMFER = 7

# Body operation constants
SW_BOOLEAN_ADD = 0
SW_BOOLEAN_SUBTRACT = 1
SW_BOOLEAN_COMMON = 2


def _get_end_condition(cond_str: str) -> int:
    """Map string end condition to Solidworks API constant."""
    mapping = {
        "blind": SW_ENDCOND_BLIND,
        "through_all": SW_ENDCOND_THROUGH_ALL,
        "through_both": SW_ENDCOND_THROUGH_BOTH,
        "mid_plane": SW_ENDCOND_MID_PLANE,
        "up_to_vertex": SW_ENDCOND_UP_TO_VERTEX,
        "up_to_surface": SW_ENDCOND_UP_TO_SURFACE,
        "offset_from_surface": SW_ENDCOND_OFFSET_FROM_SURFACE,
        "up_to_body": SW_ENDCOND_UP_TO_BODY,
    }
    return mapping.get(cond_str.lower(), SW_ENDCOND_BLIND)


def register_feature_tools(mcp):
    @mcp.tool()
    def extrude_boss(
        depth: float = 10.0,
        end_condition: str = "blind",
        draft_angle: float = 0.0,
        draft_outward: bool = False,
        merge: bool = True,
        flip: bool = False
    ) -> str:
        """Extrude the active sketch as a boss feature.
        
        Args:
            depth: Extrusion depth (used for blind/end conditions that need a distance)
            end_condition: How far to extrude - blind, through_all, mid_plane, up_to_surface, up_to_vertex, up_to_body
            draft_angle: Draft angle in degrees (0 = no draft)
            draft_outward: If True, draft angle goes outward
            merge: Merge result with existing bodies
            flip: Reverse the extrusion direction
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            end_cond = _get_end_condition(end_condition)
            flip_dir = 1 if flip else 0
            merge_flag = 1 if merge else 0
            
            feat = feature_mgr.FeatureExtrusion2(
                SW_FEAT_EXTRUDE_BOSS,  # sd
                False,                 # dir
                end_cond,              # t1
                end_cond,              # t2
                False,                 # d1
                False,                 # d2
                depth,                 # d3 (depth value)
                0,                     # d4
                draft_angle,           # draft angle
                draft_angle,           # draft angle 2
                draft_outward,         # draft outward
                True,                  # merge results
                True,                  # use feat scope
                flip_dir,              # flip direction
                True,                  # convert to精确
                False                  # absorption
            )
            
            if feat:
                return f"Extrude Boss created: depth={depth}, condition={end_condition}"
            return "Failed to create extrude boss feature"
        except Exception as e:
            return f"Error creating extrude boss: {e}"

    @mcp.tool()
    def extrude_cut(
        depth: float = 10.0,
        end_condition: str = "blind",
        draft_angle: float = 0.0,
        flip: bool = False,
        reverse_offset: bool = False
    ) -> str:
        """Extrude cut from the active sketch.
        
        Args:
            depth: Cut depth
            end_condition: End condition type
            draft_angle: Draft angle in degrees
            flip: Reverse cut direction
            reverse_offset: Reverse offset direction
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            end_cond = _get_end_condition(end_condition)
            flip_dir = 1 if flip else 0
            
            feat = feature_mgr.FeatureExtrusion2(
                SW_FEAT_EXTRUDE_CUT,  # sd = cut
                False,
                end_cond,
                SW_ENDCOND_BLIND,
                False,
                False,
                depth,
                0,
                draft_angle,
                0,
                False,
                True,
                True,
                flip_dir,
                True,
                False
            )
            
            if feat:
                return f"Extrude Cut created: depth={depth}, condition={end_condition}"
            return "Failed to create extrude cut feature"
        except Exception as e:
            return f"Error creating extrude cut: {e}"

    @mcp.tool()
    def revolve_boss(angle: float = 360.0, reverse: bool = False) -> str:
        """Revolve the active sketch profile about a sketched axis.
        
        Args:
            angle: Revolution angle in degrees (360 = full revolution)
            reverse: Reverse the revolution direction
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            angle_rad = angle * 3.14159265358979 / 180.0
            rev_dir = not reverse
            
            feat = feature_mgr.FeatureRevolve2(
                angle_rad,       # angle
                rev_dir,         # reverse
                False,           # use two directions
                False,           # merge
                True,            # use feat scope
                0,               # start angle
                0,               # end angle
                0,               # start angle 2
                0                # end angle 2
            )
            
            if feat:
                return f"Revolve Boss created: angle={angle} degrees"
            return "Failed to create revolve boss feature"
        except Exception as e:
            return f"Error creating revolve boss: {e}"

    @mcp.tool()
    def revolve_cut(angle: float = 360.0, reverse: bool = False) -> str:
        """Revolve cut from the active sketch profile about a sketched axis.
        
        Args:
            angle: Revolution angle in degrees
            reverse: Reverse the revolution direction
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            angle_rad = angle * 3.14159265358979 / 180.0
            
            feat = feature_mgr.FeatureRevolveCut2(
                angle_rad,       # angle
                not reverse,     # reverse
                False,           # use two directions
                False,           # merge
                True,            # use feat scope
                0, 0, 0, 0       # angles
            )
            
            if feat:
                return f"Revolve Cut created: angle={angle} degrees"
            return "Failed to create revolve cut feature"
        except Exception as e:
            return f"Error creating revolve cut: {e}"

    @mcp.tool()
    def fillet(
        radius: float = 1.0,
        variable_radius: bool = False,
        radius_values: list[dict] | None = None,
        full_round: bool = False
    ) -> str:
        """Add fillets to selected edges.
        
        Args:
            radius: Fillet radius (for constant radius fillets)
            variable_radius: If True, use variable radius fillet with radius_values
            radius_values: List of dicts with 'radius' and optionally 'position' keys for variable radius
            full_round: If True, create a full round fillet
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            if full_round:
                feat = feature_mgr.FeatureFillet3(
                    4,          # full round type
                    0,          # overwrite
                    0,          # keep edges
                    radius,     # radius
                    radius,     # radius2
                    0,          # radius3
                    0,          # setback
                    False,      # propagate
                    False,      # curvature continuous
                    False,      # default radius
                    0,          # point count
                    0           # setback distance
                )
            elif variable_radius and radius_values:
                import win32com.client
                num_pts = len(radius_values)
                radii_arr = win32com.client.VARIANT(
                    win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8,
                    [rv.get("radius", radius) for rv in radius_values]
                )
                positions_arr = win32com.client.VARIANT(
                    win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8,
                    [rv.get("position", i / max(num_pts - 1, 1)) for i, rv in enumerate(radius_values)]
                )
                feat = feature_mgr.FeatureFillet3(
                    2,              # variable radius type
                    0, 0,
                    radius, radius, 0,
                    0,
                    False, False, False,
                    num_pts,
                    0
                )
            else:
                feat = feature_mgr.FeatureFillet3(
                    0,              # constant radius
                    0,              # overwrite
                    0,              # keep edge
                    radius,         # radius
                    radius,         # radius 2
                    0,              # radius 3
                    0,              # setback
                    False,          # propagate to tangent faces
                    False,          # curvature continuous
                    False,          # default radius
                    0,              # point count
                    0               # setback distance
                )
            
            if feat:
                rtype = "variable" if variable_radius else "constant"
                return f"Fillet created: {rtype} radius, r={radius}"
            return "Failed to create fillet. Ensure edges are selected."
        except Exception as e:
            return f"Error creating fillet: {e}"

    @mcp.tool()
    def chamfer(
        distance: float = 1.0,
        angle: float = 45.0,
        chamfer_type: str = "angle_distance",
        distance2: float = 1.0,
        flip: bool = False
    ) -> str:
        """Add chamfer to selected edges.
        
        Args:
            distance: First chamfer distance
            angle: Chamfer angle in degrees (for angle-distance type)
            chamfer_type: 'angle_distance', 'distance_distance', or 'vertex_chamfer'
            distance2: Second distance (for distance-distance type)
            flip: Flip the chamfer direction
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            type_map = {
                "angle_distance": 0,
                "distance_distance": 1,
                "vertex_chamfer": 2,
            }
            c_type = type_map.get(chamfer_type, 0)
            
            feat = feature_mgr.FeatureChamfer(
                c_type,         # chamfer type
                distance,       # distance 1
                angle,          # angle
                distance2,      # distance 2
                not flip,       # flip direction
                False,          # keep features
                False,          # propagate
                0               # edge width
            )
            
            if feat:
                return f"Chamfer created: type={chamfer_type}, distance={distance}, angle={angle}"
            return "Failed to create chamfer. Ensure edges are selected."
        except Exception as e:
            return f"Error creating chamfer: {e}"

    @mcp.tool()
    def hole_wizard(
        hole_type: str = "counterbore",
        size: str = "M8",
        depth: float = 15.0,
        diameter: float = 8.0,
        counterbore_diameter: float = 14.0,
        counterbore_depth: float = 5.0
    ) -> str:
        """Create a standard hole using the Hole Wizard.
        
        Args:
            hole_type: Type of hole - counterbore, countersink, tapped, straight, tapered
            size: Standard size designation (e.g. 'M8', '1/4-20')
            depth: Hole depth
            diameter: Hole diameter
            counterbore_diameter: Counterbore diameter (for counterbore type)
            counterbore_depth: Counterbore depth (for counterbore type)
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            type_map = {
                "counterbore": 0,
                "countersink": 1,
                "tapped": 3,
                "straight": 2,
                "tapered": 4,
            }
            h_type = type_map.get(hole_type.lower(), 0)
            
            feat = feature_mgr.FeatureHoleWizard2(
                h_type,             # hole type
                0,                  # standard (0 = custom)
                size,               # fastener size
                "",                 # end condition
                depth,              # depth
                diameter,           # diameter
                counterbore_diameter,  # cbore diameter
                counterbore_depth,     # cbore depth
                0,                  # csk diameter
                0,                  # csk angle
                0,                  # thread depth
                0,                  # thread angle
                0,                  # near side hole diameter
                0,                  # near side hole depth
                False,              # reverse direction
                True,               # near side
                False               # tap drill
            )
            
            if feat:
                return f"Hole Wizard: {hole_type} hole, size={size}, diameter={diameter}"
            return "Failed to create hole wizard feature"
        except Exception as e:
            return f"Error creating hole wizard: {e}"

    @mcp.tool()
    def shell(thickness: float = 1.0, faces_to_remove: int = 0, multi_thickness: bool = False) -> str:
        """Shell a solid body by removing faces to a given wall thickness.
        
        Args:
            thickness: Wall thickness
            faces_to_remove: Number of faces to remove (select faces before calling)
            multi_thickness: Enable multi-thickness shell
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            feat = feature_mgr.FeatureShell(
                thickness,          # thickness
                multi_thickness,    # multi-thickness
                0                   # surface offset
            )
            
            if feat:
                return f"Shell created with wall thickness {thickness}"
            return "Failed to create shell feature"
        except Exception as e:
            return f"Error creating shell: {e}"

    @mcp.tool()
    def draft(
        angle: float = 2.0,
        direction: str = "outward",
        neutral_plane: str = ""
    ) -> str:
        """Apply draft angle to selected faces.
        
        Args:
            angle: Draft angle in degrees
            direction: 'outward' or 'inward'
            neutral_plane: Name of the neutral plane (select before calling if empty)
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            is_outward = direction.lower() == "outward"
            
            feat = feature_mgr.FeatureDraft2(
                0,              # pull direction type
                angle,          # draft angle
                is_outward,     # outward
                True,           # propagate
                0,              # number of faces
                0,              # number of edges
                0,              # number of loops
                0,              # number of radii
                False           # step draft
            )
            
            if feat:
                return f"Draft applied: angle={angle} degrees, direction={direction}"
            return "Failed to apply draft. Select faces and a neutral plane first."
        except Exception as e:
            return f"Error applying draft: {e}"

    @mcp.tool()
    def sweep(
        profile_sketch: str = "",
        path_sketch: str = "",
        twist: float = 0.0,
        follow_path: bool = True
    ) -> str:
        """Sweep a profile along a path.
        
        Args:
            profile_sketch: Name of the profile sketch
            path_sketch: Name of the path sketch
            twist: Twist angle along the path
            follow_path: Keep profile normal to the path
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            feat = feature_mgr.FeatureSweep2(
                0,                  # options
                0,                  # twist
                follow_path,        # follow path
                0,                  # alignment
                False,              # merge result
                True                # use feat scope
            )
            
            if feat:
                return f"Sweep feature created along path"
            return "Failed to create sweep. Ensure profile and path sketches are selected."
        except Exception as e:
            return f"Error creating sweep: {e}"

    @mcp.tool()
    def loft(
        num_profiles: int = 2,
        guide_curves: int = 0,
        thin_feature: bool = False
    ) -> str:
        """Create a loft feature between multiple profiles.
        
        Args:
            num_profiles: Number of profile sketches to loft between (select before calling)
            guide_curves: Number of guide curves (select before calling)
            thin_feature: Create as thin feature
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            feat = feature_mgr.FeatureLoft2(
                0,                  # options
                0,                  # start constraint
                0,                  # end constraint
                False,              # closed loft
                thin_feature,       # thin feature
                False,              # merge result
                True,               # use feat scope
                0,                  # start tangent length
                0                   # end tangent length
            )
            
            if feat:
                return f"Loft created through {num_profiles} profiles"
            return "Failed to create loft. Select profile sketches in order."
        except Exception as e:
            return f"Error creating loft: {e}"

    @mcp.tool()
    def mirror_feature(
        mirror_plane: str = "",
        bodies_to_mirror: bool = True
    ) -> str:
        """Mirror features or bodies about a plane.
        
        Args:
            mirror_plane: Name of the mirror plane (select before calling if empty)
            bodies_to_mirror: If True, mirror solid bodies
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            feat = feature_mgr.FeatureMirror(
                False,              # merge result
                bodies_to_mirror,   # bodies only
                True                # use feat scope
            )
            
            if feat:
                return f"Mirror feature created about plane"
            return "Failed to create mirror feature. Select features and a mirror plane."
        except Exception as e:
            return f"Error creating mirror feature: {e}"

    @mcp.tool()
    def pattern_linear(
        count: int = 4,
        spacing: float = 20.0,
        direction: str = "x",
        vary_sketch: bool = False
    ) -> str:
        """Create a linear pattern of selected features.
        
        Args:
            count: Total number of instances (including original)
            spacing: Distance between instances
            direction: Pattern direction - 'x' or 'y'
            vary_sketch: Vary the sketch for each instance
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            d_flag = 0 if direction.lower() == "x" else 1
            
            feat = feature_mgr.FeatureLinearPattern2(
                count,              # num instances D1
                spacing,            # spacing D1
                1,                  # num instances D2
                0,                  # spacing D2
                d_flag,             # direction
                vary_sketch,        # vary sketch
                False,              # merge
                True                # use feat scope
            )
            
            if feat:
                return f"Linear pattern created: {count} instances, spacing={spacing} in {direction} direction"
            return "Failed to create linear pattern. Select features to pattern first."
        except Exception as e:
            return f"Error creating linear pattern: {e}"

    @mcp.tool()
    def pattern_circular(
        count: int = 6,
        total_angle: float = 360.0,
        equal_spacing: bool = True
    ) -> str:
        """Create a circular pattern of selected features.
        
        Args:
            count: Total number of instances (including original)
            total_angle: Total angle of the pattern in degrees
            equal_spacing: Use equal spacing between instances
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            angle_rad = total_angle * 3.14159265358979 / 180.0
            
            feat = feature_mgr.FeatureCircularPattern2(
                count,              # num instances
                angle_rad,          # total angle
                equal_spacing,      # equal spacing
                False,              # vary sketch
                False,              # merge
                True                # use feat scope
            )
            
            if feat:
                return f"Circular pattern created: {count} instances over {total_angle} degrees"
            return "Failed to create circular pattern. Select features and an axis first."
        except Exception as e:
            return f"Error creating circular pattern: {e}"

    @mcp.tool()
    def scale(scale_factor: float = 1.0, scale_about: str = "origin") -> str:
        """Scale the part about a reference point.
        
        Args:
            scale_factor: Scale factor (1.0 = no change)
            scale_about: Reference point - 'origin', 'centroid', or 'coordinate_system'
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            about_map = {"origin": 0, "centroid": 1, "coordinate_system": 2}
            about = about_map.get(scale_about.lower(), 0)
            
            feat = feature_mgr.FeatureScale2(
                scale_factor,       # scale factor
                about,              # scale about
                True                # use feat scope
            )
            
            if feat:
                return f"Part scaled by factor {scale_factor} about {scale_about}"
            return "Failed to scale part"
        except Exception as e:
            return f"Error scaling part: {e}"
