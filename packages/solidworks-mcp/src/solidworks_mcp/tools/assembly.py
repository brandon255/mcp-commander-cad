"""
Assembly tools for Solidworks MCP server.
Provides assembly creation, component insertion, mating, exploding, and BOM tools.
"""
from solidworks_mcp.api.connection import get_sw_app, get_active_doc

# Mate type constants
SW_MATE_COINCIDENT = 0
SW_MATE_CONCENTRIC = 1
SW_MATE_DISTANCE = 3
SW_MATE_ANGLE = 5
SW_MATE_TANGENT = 8
SW_MATE_LOCK = 18
SW_MATE_WIDTH = 20
SW_MATE_GEAR = 22
SW_MATE_RACK_PINION = 23
SW_MATE_HINGE = 24
SW_MATE_CAM = 25
SW_MATE_ADVANCED = 26

# Document type constants
SW_DOC_PART = 1
SW_DOC_ASSEMBLY = 2
SW_DOC_DRAWING = 3


def register_assembly_tools(mcp):
    @mcp.tool()
    def create_assembly(template_path: str = "") -> str:
        """Create a new assembly document.
        
        Args:
            template_path: Path to an assembly template file (.asmdot). Empty for default.
        """
        try:
            sw_app = get_sw_app()
            if template_path:
                doc = sw_app.NewDocument2(template_path, 0)
            else:
                doc = sw_app.NewDocument2("", SW_DOC_ASSEMBLY)
            
            if doc:
                return "New assembly document created"
            return "Failed to create assembly document"
        except Exception as e:
            return f"Error creating assembly: {e}"

    @mcp.tool()
    def insert_component(
        part_filepath: str,
        pos_x: float = 0.0,
        pos_y: float = 0.0,
        pos_z: float = 0.0
    ) -> str:
        """Insert a part or sub-assembly into the active assembly at a given position.
        
        Args:
            part_filepath: Absolute path to the part (.sldprt) or assembly (.sldasm) file
            pos_x, pos_y, pos_z: Insertion position in assembly coordinates
        """
        try:
            doc = get_active_doc()
            
            errors = doc.AddComponent5(
                part_filepath,     # file path
                0,                 # component config
                pos_x, pos_y, pos_z  # position
            )
            
            if errors == 0:
                from os.path import basename
                name = basename(part_filepath)
                return f"Component '{name}' inserted at ({pos_x}, {pos_y}, {pos_z})"
            return f"Failed to insert component (error code: {errors})"
        except Exception as e:
            return f"Error inserting component: {e}"

    @mcp.tool()
    def add_mate_coincident(entity1: str = "", entity2: str = "", align: str = "closest") -> str:
        """Add a coincident mate between two faces, planes, or edges.
        The two selected entities will be made coplanar or coincident.
        
        Args:
            entity1: Name or description of the first entity
            entity2: Name or description of the second entity
            align: Alignment - 'closest', 'anti-aligned', or 'aligned'
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            align_map = {"closest": 0, "anti-aligned": -1, "aligned": 1}
            align_val = align_map.get(align.lower(), 0)
            
            mate = feature_mgr.AddMate3(
                SW_MATE_COINCIDENT,  # mate type
                align_val,           # alignment
                False,               # flip
                0,                   # distance
                0,                   # angle
                0,                   # gear ratio
                0,                   # width mate options
                False,               # reverse
                0,                   # mate error
                0                    # mate error2
            )
            
            if mate:
                return f"Coincident mate added between '{entity1}' and '{entity2}' ({align})"
            return "Failed to add coincident mate. Select two faces/planes/edges first."
        except Exception as e:
            return f"Error adding coincident mate: {e}"

    @mcp.tool()
    def add_mate_concentric(entity1: str = "", entity2: str = "") -> str:
        """Add a concentric mate between two cylindrical faces, edges, or axes.
        
        Args:
            entity1: Description of the first cylindrical entity
            entity2: Description of the second cylindrical entity
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            mate = feature_mgr.AddMate3(
                SW_MATE_CONCENTRIC,
                0, False,
                0, 0, 0, 0, False, 0, 0
            )
            
            if mate:
                return f"Concentric mate added between '{entity1}' and '{entity2}'"
            return "Failed to add concentric mate. Select two cylindrical faces/edges first."
        except Exception as e:
            return f"Error adding concentric mate: {e}"

    @mcp.tool()
    def add_mate_distance(
        entity1: str = "",
        entity2: str = "",
        distance: float = 10.0,
        flip: bool = False
    ) -> str:
        """Add a distance mate between two faces or planes.
        
        Args:
            entity1: Description of the first face/plane
            entity2: Description of the second face/plane
            distance: Distance between the two entities
            flip: Flip the direction of the distance measurement
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            mate = feature_mgr.AddMate3(
                SW_MATE_DISTANCE,
                0,
                flip,
                distance,   # distance value
                0, 0, 0, False, 0, 0
            )
            
            if mate:
                return f"Distance mate added: {distance} between '{entity1}' and '{entity2}'"
            return "Failed to add distance mate. Select two faces/planes first."
        except Exception as e:
            return f"Error adding distance mate: {e}"

    @mcp.tool()
    def add_mate_angle(
        entity1: str = "",
        entity2: str = "",
        angle: float = 90.0,
        flip: bool = False
    ) -> str:
        """Add an angle mate between two faces or edges.
        
        Args:
            entity1: Description of the first entity
            entity2: Description of the second entity
            angle: Angle in degrees between the entities
            flip: Flip the angle direction
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            mate = feature_mgr.AddMate3(
                SW_MATE_ANGLE,
                0,
                flip,
                0,          # distance (not used)
                angle,      # angle value
                0, 0, False, 0, 0
            )
            
            if mate:
                return f"Angle mate added: {angle} degrees between '{entity1}' and '{entity2}'"
            return "Failed to add angle mate. Select two faces/edges first."
        except Exception as e:
            return f"Error adding angle mate: {e}"

    @mcp.tool()
    def add_mate_tangent(entity1: str = "", entity2: str = "") -> str:
        """Add a tangent mate between a cylindrical face and a planar or cylindrical face.
        
        Args:
            entity1: Description of the first entity
            entity2: Description of the second entity
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            mate = feature_mgr.AddMate3(
                SW_MATE_TANGENT,
                0, False,
                0, 0, 0, 0, False, 0, 0
            )
            
            if mate:
                return f"Tangent mate added between '{entity1}' and '{entity2}'"
            return "Failed to add tangent mate. Select appropriate faces first."
        except Exception as e:
            return f"Error adding tangent mate: {e}"

    @mcp.tool()
    def add_mate_lock(component_name: str = "") -> str:
        """Lock a component in its current position, preventing movement.
        
        Args:
            component_name: Name of the component to lock
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            mate = feature_mgr.AddMate3(
                SW_MATE_LOCK,
                0, False,
                0, 0, 0, 0, False, 0, 0
            )
            
            if mate:
                return f"Lock mate added for component '{component_name}'"
            return "Failed to add lock mate. Select a component first."
        except Exception as e:
            return f"Error adding lock mate: {e}"

    @mcp.tool()
    def add_mate_advanced(
        mate_type: str = "width",
        distance: float = 0.0,
        angle: float = 0.0,
        gear_ratio: float = 1.0,
        entity1: str = "",
        entity2: str = "",
        entity3: str = ""
    ) -> str:
        """Add an advanced mate (width, cam, hinge, gear, or rack-pinion).
        
        Args:
            mate_type: Type of advanced mate - width, cam, hinge, gear, rack_pinion
            distance: Distance parameter (width mate)
            angle: Angle parameter (hinge mate)
            gear_ratio: Gear ratio (gear/rack-pinion mates)
            entity1: First entity description
            entity2: Second entity description
            entity3: Third entity description (width mate center plane)
        """
        try:
            doc = get_active_doc()
            feature_mgr = doc.FeatureManager
            
            type_map = {
                "width": SW_MATE_WIDTH,
                "cam": SW_MATE_CAM,
                "hinge": SW_MATE_HINGE,
                "gear": SW_MATE_GEAR,
                "rack_pinion": SW_MATE_RACK_PINION,
            }
            
            m_type = type_map.get(mate_type.lower())
            if m_type is None:
                return f"Error: unknown mate type '{mate_type}'. Valid: {', '.join(type_map.keys())}"
            
            mate = feature_mgr.AddMate3(
                m_type,
                0, False,
                distance,
                angle,
                gear_ratio,
                0, False, 0, 0
            )
            
            if mate:
                return f"Advanced mate ({mate_type}) added"
            return f"Failed to add {mate_type} mate"
        except Exception as e:
            return f"Error adding advanced mate: {e}"

    @mcp.tool()
    def explode_assembly(
        create_new: bool = True,
        step_distance: float = 50.0
    ) -> str:
        """Create or edit an exploded view of the assembly.
        
        Args:
            create_new: If True, create a new exploded view; if False, edit existing
            step_distance: Distance for automatic explode steps
        """
        try:
            doc = get_active_doc()
            
            if create_new:
                explode_view = doc.CreateExplodedView()
                if explode_view:
                    return "New exploded view configuration created. Use Solidworks to adjust individual component positions."
                return "Failed to create exploded view"
            else:
                explode_view = doc.EditExplodedView()
                if explode_view:
                    return "Editing exploded view"
                return "No existing exploded view to edit"
        except Exception as e:
            return f"Error with exploded view: {e}"

    @mcp.tool()
    def assembly_bom(include_nested: bool = False) -> str:
        """Generate bill of materials data from the active assembly.
        
        Args:
            include_nested: If True, include components from sub-assemblies
        """
        try:
            doc = get_active_doc()
            
            bom_feature = doc.FeatureManager.FeatureBOM
            if bom_feature is None:
                # Alternative: traverse components manually
                components = doc.GetComponents(False)
                if components is None:
                    return "No components found in the assembly"
                
                lines = []
                lines.append("Assembly BOM:")
                lines.append("-" * 60)
                lines.append(f"{'#':<5} {'Component Name':<40} {'Quantity':<10}")
                lines.append("-" * 60)
                
                comp = components
                idx = 1
                seen = {}
                while comp:
                    name = comp.Name2
                    if name in seen:
                        seen[name] += 1
                    else:
                        seen[name] = 1
                        lines.append(f"{idx:<5} {name:<40} {1:<10}")
                        idx += 1
                    comp = comp.GetNextComponent
                
                lines.append("-" * 60)
                lines.append(f"Total unique components: {len(seen)}")
                return "\n".join(lines)
            
            return "BOM data retrieved from feature"
        except Exception as e:
            return f"Error generating BOM: {e}"

    @mcp.tool()
    def check_interference(include_components: list[str] | None = None) -> str:
        """Run interference detection between assembly components.
        
        Args:
            include_components: List of component names to check. Empty = check all components.
        """
        try:
            doc = get_active_doc()
            
            num_interferences = 0
            interference_data = doc.InterferenceCheck(
                0,      # number of components
                False,  # all components
                True,   # include sub-assemblies
                False,  # treat sub-assemblies as components
                True,   # visualize interference
                True,   # silent
                0, 0    # start/stop component indices
            )
            
            if interference_data:
                num_interferences = interference_data.GetInterferenceCount()
                if num_interferences > 0:
                    lines = [f"Found {num_interferences} interference(s):"]
                    for i in range(num_interferences):
                        inter = interference_data.GetInterference(i)
                        if inter:
                            vol = inter.Volume
                            comp1 = inter.Component1.Name2 if inter.Component1 else "Unknown"
                            comp2 = inter.Component2.Name2 if inter.Component2 else "Unknown"
                            lines.append(f"  {i+1}. {comp1} <-> {comp2} (volume: {vol:.6f})")
                    return "\n".join(lines)
                return "No interferences found. All components clear."
            
            return "Interference check completed (results may need manual verification)"
        except Exception as e:
            return f"Error checking interference: {e}"
