"""
Sheet metal tools for Solidworks MCP server.
Provides base flange, edge flange, miter flange, tabs, hems, jogs, bends, and forming tools.
"""
from solidworks_mcp.api.connection import get_sw_app, get_active_doc

# Sheet metal bend allowance type constants
SW_BEND_ALLOWANCE_K_FACTOR = 0
SW_BEND_ALLOWANCE_BEND_TABLE = 1
SW_BEND_ALLOWANCE_CUSTOM = 2

# Relief type constants
SW_RELIEF_RECTANGULAR = 0
SW_RELIEF_OBLONG = 1
SW_RELIEF_TEAR = 2
SW_RELIEF_NONE = 3

# Bend type constants
SW_BEND_SHARP = 0
SW_BEND_ROUND = 1


def register_sheet_metal_tools(mcp):
    @mcp.tool()
    def create_base_flange(
        thickness: float = 1.0,
        bend_radius: float = 1.0,
        k_factor: float = 0.5,
        reverse_direction: bool = False
    ) -> str:
        """Create a base flange from the active closed sketch profile.
        
        Args:
            thickness: Sheet metal thickness
            bend_radius: Default bend radius
            k_factor: K-factor for bend allowance calculation (0.0 to 1.0)
            reverse_direction: Extrude in the reverse direction
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            feat = feature_mgr.FeatureSheetMetalBaseFlange2(
                thickness,              # thickness
                reverse_direction,      # reverse direction
                bend_radius,            # bend radius
                k_factor,               # k-factor
                SW_BEND_ALLOWANCE_K_FACTOR,  # bend allowance type
                0,                      # auto relief
                0,                      # relief ratio
                0,                      # relief width
                0,                      # relief depth
                SW_RELIEF_RECTANGULAR,  # relief type
                False,                  # use gauge table
                "",                     # gauge table path
                "",                     # bend allowance table path
                0                       # override thickness
            )
            
            if feat:
                return f"Base flange created: thickness={thickness}, bend_radius={bend_radius}, k-factor={k_factor}"
            return "Failed to create base flange. Ensure a closed sketch profile is active."
        except Exception as e:
            return f"Error creating base flange: {e}"

    @mcp.tool()
    def add_edge_flange(
        angle: float = 90.0,
        length: float = 20.0,
        offset: float = 0.0,
        flange_position: str = "material_inside",
        gap_distance: float = 0.0
    ) -> str:
        """Add an edge flange to a selected sheet metal edge.
        
        Args:
            angle: Flange angle in degrees
            length: Flange length (height)
            offset: Offset from the selected edge
            flange_position: Position relative to the bend - material_inside, material_outside, bend_outside
            gap_distance: Gap distance for mitered flanges
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            pos_map = {
                "material_inside": 0,
                "material_outside": 1,
                "bend_outside": 2
            }
            f_pos = pos_map.get(flange_position.lower(), 0)
            
            feat = feature_mgr.FeatureSheetMetalEdgeFlange(
                angle,          # flange angle
                length,         # flange length
                offset,         # offset
                f_pos,          # flange position
                False,          # reverse direction
                False,          # trim side bends
                False,          # use default bend radius
                gap_distance,   # gap distance
                0,              # start offset
                0,              # end offset
                False,          # custom bend allowance
                False,          # custom bend relief
                0,              # relief type
                0, 0, 0        # relief dimensions
            )
            
            if feat:
                return f"Edge flange added: angle={angle}, length={length}, position={flange_position}"
            return "Failed to add edge flange. Select a sheet metal edge first."
        except Exception as e:
            return f"Error adding edge flange: {e}"

    @mcp.tool()
    def add_miter_flange(
        angle: float = 90.0,
        length: float = 20.0,
        offset: float = 0.0,
        gap_distance: float = 0.5,
        start_offset: float = 0.0,
        end_offset: float = 0.0
    ) -> str:
        """Add a miter flange to one or more connected edges.
        
        Args:
            angle: Flange angle in degrees
            length: Flange length
            offset: Offset distance
            gap_distance: Gap between adjacent miter flanges
            start_offset: Start offset from the edge
            end_offset: End offset from the edge
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            feat = feature_mgr.FeatureSheetMetalMiterFlange(
                angle,          # angle
                length,         # length
                offset,         # offset
                0,              # position
                False,          # reverse
                gap_distance,   # gap
                start_offset,   # start offset
                end_offset,     # end offset
                False,          # use default bend radius
                False,          # custom bend allowance
                False,          # custom bend relief
                0, 0, 0        # relief params
            )
            
            if feat:
                return f"Miter flange added: angle={angle}, length={length}, gap={gap_distance}"
            return "Failed to add miter flange. Select one or more connected edges."
        except Exception as e:
            return f"Error adding miter flange: {e}"

    @mcp.tool()
    def add_tab(sketch_name: str = "", thickness: float = 0.0) -> str:
        """Add a tab (sketch-bend) feature using a closed sketch on the sheet metal face.
        
        Args:
            sketch_name: Name of the sketch to use for the tab (select before calling if empty)
            thickness: Tab thickness (0 = use sheet metal thickness)
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            feat = feature_mgr.FeatureSheetMetalTab(
                False,          # use default thickness
                thickness,      # thickness override
                False,          # reverse direction
                False,          # use gauge table
                "",             # gauge table
                0,              # auto relief
                0, 0, 0, 0     # relief params
            )
            
            if feat:
                return f"Tab feature added using sketch '{sketch_name or 'selected'}'"
            return "Failed to add tab. Draw a closed sketch on a sheet metal face first."
        except Exception as e:
            return f"Error adding tab: {e}"

    @mcp.tool()
    def add_lofted_bend(thickness: float = 1.0, k_factor: float = 0.5) -> str:
        """Create a lofted bend transition between two open sketch profiles.
        
        Args:
            thickness: Sheet metal thickness
            k_factor: K-factor for bend calculations
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            feat = feature_mgr.FeatureSheetMetalLoftedBend(
                thickness,      # thickness
                False,          # reverse direction
                k_factor,       # k-factor
                False,          # use gauge table
                "",             # gauge table
                False,          # custom bend allowance
                0, 0, 0, 0     # relief params
            )
            
            if feat:
                return f"Lofted bend created: thickness={thickness}, k-factor={k_factor}"
            return "Failed to create lofted bend. Select two open sketch profiles."
        except Exception as e:
            return f"Error creating lofted bend: {e}"

    @mcp.tool()
    def add_hem(
        hem_type: str = "closed",
        length: float = 5.0,
        gap: float = 0.0,
        bend_radius: float = 0.0
    ) -> str:
        """Add a hem (folded edge) to a selected sheet metal edge.
        
        Args:
            hem_type: Type of hem - closed, open, tear_drop, rolled
            length: Hem length (fold height)
            gap: Gap for open hem type
            bend_radius: Custom bend radius (0 = use default)
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            type_map = {"closed": 0, "open": 1, "tear_drop": 2, "rolled": 3}
            h_type = type_map.get(hem_type.lower(), 0)
            
            feat = feature_mgr.FeatureSheetMetalHem(
                h_type,            # hem type
                length,            # hem length
                False,             # reverse direction
                gap,               # gap
                bend_radius,       # bend radius
                False,             # use default bend radius
                False,             # custom bend allowance
                False,             # custom bend relief
                0, 0, 0, 0        # relief params
            )
            
            if feat:
                return f"Hem added: type={hem_type}, length={length}"
            return "Failed to add hem. Select a sheet metal edge first."
        except Exception as e:
            return f"Error adding hem: {e}"

    @mcp.tool()
    def add_jog(
        jog_angle: float = 90.0,
        jog_distance: float = 5.0,
        fixed_face: str = "left"
    ) -> str:
        """Add a jog (offset bend) to the sheet metal part.
        
        Args:
            jog_angle: Jog angle in degrees
            jog_distance: Jog offset distance
            fixed_face: Which side to fix - 'left' or 'right'
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            fix_face = 0 if fixed_face.lower() == "left" else 1
            
            feat = feature_mgr.FeatureSheetMetalJog(
                jog_angle,         # jog angle
                jog_distance,      # jog distance
                fix_face,          # fixed face side
                False,             # reverse direction
                False,             # use default bend radius
                False,             # custom bend allowance
                False,             # custom bend relief
                0, 0, 0, 0        # relief params
            )
            
            if feat:
                return f"Jog added: angle={jog_angle}, distance={jog_distance}"
            return "Failed to add jog. Draw a jog line on a sheet metal face first."
        except Exception as e:
            return f"Error adding jog: {e}"

    @mcp.tool()
    def add_fold(
        bend_angle: float = 90.0,
        bend_radius: float = 1.0,
        fixed_face: str = "above"
    ) -> str:
        """Create a sketch fold on a sheet metal face.
        
        Args:
            bend_angle: Bend angle in degrees
            bend_radius: Bend radius
            fixed_face: Fixed face side - 'above' or 'below'
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            fix_face = 0 if fixed_face.lower() == "above" else 1
            
            feat = feature_mgr.FeatureSheetMetalFold(
                bend_angle,        # bend angle
                bend_radius,       # bend radius
                fix_face,          # fixed face
                False,             # reverse direction
                False,             # use default radius
                False,             # custom bend allowance
                0, 0, 0, 0        # relief params
            )
            
            if feat:
                return f"Fold created: angle={bend_angle}, radius={bend_radius}"
            return "Failed to create fold. Draw a sketch line on a sheet metal face first."
        except Exception as e:
            return f"Error creating fold: {e}"

    @mcp.tool()
    def add_rip(
        rip_gap: float = 0.5,
        rip_type: str = "single_edge"
    ) -> str:
        """Rip (cut open) a sheet metal edge to allow flattening.
        
        Args:
            rip_gap: Gap distance for the rip
            rip_type: Type of rip - single_edge, two_edges, or edge_to_edge
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            type_map = {"single_edge": 0, "two_edges": 1, "edge_to_edge": 2}
            r_type = type_map.get(rip_type.lower(), 0)
            
            feat = feature_mgr.FeatureSheetMetalRip(
                r_type,            # rip type
                rip_gap,           # gap
                0,                 # rip offset
                False              # keep cuts
            )
            
            if feat:
                return f"Rip created: type={rip_type}, gap={rip_gap}"
            return "Failed to create rip. Select sheet metal edge(s) first."
        except Exception as e:
            return f"Error creating rip: {e}"

    @mcp.tool()
    def add_gusset(
        width: float = 10.0,
        height: float = 10.0,
        thickness: float = 1.0,
        position: str = "center"
    ) -> str:
        """Add a gusset (triangular reinforcement) to a sheet metal bend.
        
        Args:
            width: Gusset width
            height: Gusset height
            thickness: Gusset thickness
            position: Position along the bend - start, center, end
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            pos_map = {"start": 0, "center": 1, "end": 2}
            g_pos = pos_map.get(position.lower(), 1)
            
            feat = feature_mgr.FeatureSheetMetalGusset(
                width,             # width
                height,            # height
                thickness,         # thickness
                g_pos,             # position
                False,             # offset
                0,                 # offset distance
                False,             # reverse direction
                0, 0, 0, 0        # relief params
            )
            
            if feat:
                return f"Gusset added: {width}x{height}, position={position}"
            return "Failed to add gusset. Select a sheet metal bend face first."
        except Exception as e:
            return f"Error adding gusset: {e}"

    @mcp.tool()
    def flatten() -> str:
        """Flatten the sheet metal part to show the flat pattern.
        Unsuppresses the flat pattern feature to display the unfolded sheet.
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            # Look for the flat pattern feature
            feat = doc.FirstFeature()
            flat_pattern = None
            while feat:
                if feat.GetTypeName2() == "FlatPattern":
                    flat_pattern = feat
                    break
                feat = feat.GetNextFeature()
            
            if flat_pattern:
                result = flat_pattern.Unsuppress2(False)
                if result:
                    return "Sheet metal part flattened. Flat pattern is now displayed."
                return "Failed to unsuppress flat pattern"
            
            # Alternative: use the flat pattern display mode
            doc.ShowFlatPatternView()
            return "Sheet metal part flattened"
        except Exception as e:
            return f"Error flattening sheet metal: {e}"

    @mcp.tool()
    def fold_flat() -> str:
        """Show the folded state of the sheet metal part.
        Suppresses the flat pattern to return to the folded view.
        """
        try:
            doc = get_active_doc()
            
            feat = doc.FirstFeature()
            flat_pattern = None
            while feat:
                if feat.GetTypeName2() == "FlatPattern":
                    flat_pattern = feat
                    break
                feat = feat.GetNextFeature()
            
            if flat_pattern:
                result = flat_pattern.Suppress2(False)
                if result:
                    return "Sheet metal part returned to folded state"
                return "Failed to suppress flat pattern"
            
            return "No flat pattern feature found. Part may already be in folded state."
        except Exception as e:
            return f"Error returning to folded state: {e}"

    @mcp.tool()
    def set_bend_allowance(
        allowance_type: str = "k_factor",
        k_factor: float = 0.5,
        bend_table_path: str = "",
        custom_value: float = 0.0
    ) -> str:
        """Set the bend allowance method for the sheet metal part.
        
        Args:
            allowance_type: Type - k_factor, bend_table, or custom
            k_factor: K-factor value (0.0 to 1.0, used when type is k_factor)
            bend_table_path: Path to a bend table file (.xls, .csv, or .txt)
            custom_value: Custom bend allowance value
        """
        try:
            doc = get_active_doc()
            
            type_map = {
                "k_factor": SW_BEND_ALLOWANCE_K_FACTOR,
                "bend_table": SW_BEND_ALLOWANCE_BEND_TABLE,
                "custom": SW_BEND_ALLOWANCE_CUSTOM,
            }
            
            a_type = type_map.get(allowance_type.lower(), SW_BEND_ALLOWANCE_K_FACTOR)
            
            sheet_metal = doc.GetSheetMetalProperties()
            if sheet_metal:
                if a_type == SW_BEND_ALLOWANCE_K_FACTOR:
                    doc.SetBendAllowanceKFactor(k_factor)
                    return f"Bend allowance set to K-factor: {k_factor}"
                elif a_type == SW_BEND_ALLOWANCE_BEND_TABLE:
                    if not bend_table_path:
                        return "Error: bend_table_path required for bend_table type"
                    doc.SetBendAllowanceBendTable(bend_table_path)
                    return f"Bend allowance set to bend table: {bend_table_path}"
                elif a_type == SW_BEND_ALLOWANCE_CUSTOM:
                    doc.SetBendAllowanceCustom(custom_value)
                    return f"Bend allowance set to custom value: {custom_value}"
            
            return f"Bend allowance configured: type={allowance_type}"
        except Exception as e:
            return f"Error setting bend allowance: {e}"

    @mcp.tool()
    def set_gauge_table(table_path: str, material: str = "") -> str:
        """Set the material gauge table for the sheet metal part.
        
        Args:
            table_path: Absolute path to the gauge table file
            material: Material name from the gauge table (empty = first available)
        """
        try:
            doc = get_active_doc()
            
            if not table_path:
                return "Error: gauge table path is required"
            
            result = doc.SetGaugeTable(table_path, material)
            
            if result:
                return f"Gauge table set: {table_path}, material={material or 'default'}"
            return "Failed to set gauge table. Verify the file path and format."
        except Exception as e:
            return f"Error setting gauge table: {e}"

    @mcp.tool()
    def convert_to_sheet_metal(
        thickness: float = 1.0,
        bend_radius: float = 1.0,
        k_factor: float = 0.5,
        rip_edges: bool = True
    ) -> str:
        """Convert an imported solid body to a sheet metal part.
        
        Args:
            thickness: Sheet metal thickness
            bend_radius: Default bend radius
            k_factor: K-factor for bend allowance
            rip_edges: Automatically find and rip edges to allow flattening
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            feat = feature_mgr.InsertSheetMetalBendAllowance(
                thickness,              # thickness
                bend_radius,            # bend radius
                k_factor,               # k-factor
                SW_BEND_ALLOWANCE_K_FACTOR,  # allowance type
                rip_edges               # auto rip
            )
            
            if feat:
                return f"Solid converted to sheet metal: thickness={thickness}, radius={bend_radius}"
            return "Failed to convert to sheet metal. Ensure a solid body is present."
        except Exception as e:
            return f"Error converting to sheet metal: {e}"

    @mcp.tool()
    def insert_dies(
        forming_tool_path: str,
        position_x: float = 0.0,
        position_y: float = 0.0,
        angle: float = 0.0
    ) -> str:
        """Insert a forming tool (die) into the sheet metal part.
        
        Args:
            forming_tool_path: Absolute path to the forming tool file (.sldprt)
            position_x, position_y: Position for the forming tool on the face
            angle: Rotation angle of the forming tool
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            feat = feature_mgr.InsertFormingTool(
                forming_tool_path,     # forming tool path
                position_x,            # position X
                position_y,            # position Y
                angle,                 # rotation angle
                False,                 # flip
                True,                  # use locating dimensions
                0,                     # locate using
                False                  # auto position
            )
            
            if feat:
                from os.path import basename
                name = basename(forming_tool_path)
                return f"Forming tool '{name}' inserted at ({position_x}, {position_y})"
            return "Failed to insert forming tool. Select a face on the sheet metal part first."
        except Exception as e:
            return f"Error inserting forming tool: {e}"
