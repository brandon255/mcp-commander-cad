"""
Analysis tools for Solidworks MCP server.
Provides sketch validation, feature tree analysis, model properties,
measurements, DFM checks, weld inspection, dimension comparison,
section properties, and interference detection via the COM API.
"""
from solidworks_mcp.api.connection import get_sw_app, get_active_doc, get_diagnostics, wrap_as


def register_analysis_tools(mcp):
    @mcp.tool()
    def connection_diagnostics() -> str:
        """Report the Solidworks COM connection state for debugging.

        Returns the PID(s) of running SLDWORKS.EXE processes, whether the
        bridge is currently attached via COM, and the count/names of open
        documents plus the active document. Use this to distinguish "no
        Solidworks running" from "attached but no active document" from a
        stale/dead COM reference.
        """
        import json
        return json.dumps(get_diagnostics(), indent=2)

    @mcp.tool()
    def validate_sketch_constraints(sketch_name: str = "") -> str:
        """Validate the active sketch for constraint completeness.

        Checks each sketch segment for sufficient constraints (at least 2 for fully defined),
        detects over-constrained entities, open profiles, and dangling relations.

        Args:
            sketch_name: Name of the sketch to validate (empty = active sketch)
        """
        try:
            import json
            doc = get_active_doc()

            # Get the active sketch
            sketch_mgr = doc.SketchManager
            active_sketch = sketch_mgr.ActiveSketch

            if active_sketch is None:
                return "Error: No active sketch found. Open a sketch first."

            sketch_feat = active_sketch if isinstance(active_sketch, object) else None

            total_entities = 0
            fully_defined = 0
            under_defined = 0
            over_defined = 0
            open_profiles = 0
            issues_list = []

            # Iterate sketch segments
            try:
                v_segments = active_sketch.GetSketchSegments()
                if v_segments:
                    for i in range(v_segments.GetCount()):
                        seg = v_segments.Item(i)
                        if seg is None:
                            continue
                        total_entities += 1

                        # Check constraint count on this segment
                        try:
                            constraint_count = seg.GetConstraintsCount()
                        except Exception:
                            constraint_count = 0

                        if constraint_count >= 2:
                            fully_defined += 1
                        elif constraint_count > 4:
                            over_defined += 1
                            issues_list.append(
                                f"Over-constrained entity {i}: {constraint_count} constraints"
                            )
                        else:
                            under_defined += 1

                        # Check for dangling status
                        try:
                            if hasattr(seg, 'IsDangling') and seg.IsDangling:
                                issues_list.append(
                                    f"Dangling relation on entity {i}"
                                )
                        except Exception:
                            pass
            except Exception as e:
                issues_list.append(f"Could not iterate sketch segments: {e}")

            # Check for open profiles
            try:
                v_sketch_points = active_sketch.GetSketchPoints()
                if v_sketch_points:
                    endpoints = set()
                    for j in range(v_sketch_points.GetCount()):
                        pt = v_sketch_points.Item(j)
                        if pt is not None:
                            x = round(pt.X, 6)
                            y = round(pt.Y, 6)
                            key = (x, y)
                            if key in endpoints:
                                endpoints.discard(key)
                            else:
                                endpoints.add(key)
                    open_profiles = len(endpoints) // 2
                    if open_profiles > 0:
                        issues_list.append(f"Found {open_profiles} open profile(s)")
            except Exception:
                pass

            result = {
                "total_entities": total_entities,
                "fully_defined": fully_defined,
                "under_defined": under_defined,
                "over_defined": over_defined,
                "open_profiles": open_profiles,
                "issues_list": issues_list,
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error validating sketch constraints: {e}"

    @mcp.tool()
    def analyze_feature_tree(
        include_params: bool = True,
        include_timing: bool = False
    ) -> str:
        """Analyze the feature tree of the active part or assembly.

        Traverses the FeatureManager to list all features with their type,
        suppression state, and optionally key parameters.

        Args:
            include_params: Include key feature parameters (dimensions, angles, depths)
            include_timing: Include feature creation timing data
        """
        try:
            import json
            import math
            doc = get_active_doc()

            # FirstFeature/GetNextFeature/GetParentFeature live on the document
            # (IModelDoc2), not on FeatureManager - and they return a generic
            # IDispatch that needs an explicit IFeature wrap to resolve real
            # members like GetTypeName2/IsSuppressed/GetNextFeature.
            features = []
            feat = wrap_as(doc.FirstFeature(), "IFeature")

            while feat is not None:
                feat_info = {}

                # Feature name and type
                try:
                    feat_info["name"] = feat.Name
                except Exception:
                    feat_info["name"] = "Unknown"

                try:
                    feat_info["type"] = feat.GetTypeName2()
                except Exception:
                    feat_info["type"] = "Unknown"

                # Feature state (suppressed/unsuppressed)
                try:
                    feat_info["state"] = "suppressed" if feat.IsSuppressed() else "unsuppressed"
                except Exception:
                    feat_info["state"] = "unknown"

                # Parent features (dependencies) - GetParentFeature does not
                # exist in the real API; the real method is GetParents(),
                # which returns an array of this feature's direct parents
                # (not a chain requiring further traversal).
                try:
                    parents = []
                    parent_array = feat.GetParents()
                    if parent_array:
                        for p in parent_array:
                            try:
                                parents.append(wrap_as(p, "IFeature").Name)
                            except Exception:
                                pass
                    feat_info["parents"] = parents
                except Exception:
                    feat_info["parents"] = []

                # Key parameters
                if include_params:
                    params = {}
                    try:
                        feat_info["parameters"] = params
                        # Get feature-specific parameters via IFeature::GetDefinition
                        feat_def = feat.GetDefinition()
                        if feat_def is not None:
                            try:
                                feat_def.AccessSelections(doc, None)
                                # Try to get dimension parameters
                                feat_type_name = feat_info["type"]
                                if feat_type_name in ("ExtrudeBoss", "ExtrudeCut"):
                                    try:
                                        depth = feat_def.GetDepth()
                                        params["depth"] = round(depth, 4) if not math.isinf(depth) else "blind"
                                    except Exception:
                                        pass
                                    try:
                                        draft_angle = feat_def.GetDraftAngle()
                                        params["draft_angle"] = round(draft_angle, 2)
                                    except Exception:
                                        pass
                                elif feat_type_name in ("RevolveBoss", "RevolveCut"):
                                    try:
                                        angle = feat_def.GetAngle()
                                        params["angle"] = round(math.degrees(angle), 2)
                                    except Exception:
                                        pass
                                elif feat_type_name == "Fillet":
                                    try:
                                        radius = feat_def.GetRadius()
                                        params["radius"] = round(radius, 4)
                                    except Exception:
                                        pass
                                elif feat_type_name == "CutListFolder":
                                    try:
                                        qty = feat_def.GetQuantity()
                                        params["quantity"] = qty
                                    except Exception:
                                        pass
                                feat_def.ReleaseSelectionAccess()
                            except Exception:
                                pass
                    except Exception:
                        feat_info["parameters"] = {}

                features.append(feat_info)
                feat = wrap_as(feat.GetNextFeature(), "IFeature")

            result = {
                "total_features": len(features),
                "features": features,
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error analyzing feature tree: {e}"

    @mcp.tool()
    def get_model_properties(
        units: str = "mm",
        density_override: float = 0.0
    ) -> str:
        """Get mass, volume, surface area, and center of mass of the active part.

        Uses IMassProperty via the document extension to calculate physical properties.

        Args:
            units: Output units - 'mm', 'inches', or 'meters'
            density_override: Override material density (0 = use material density)
        """
        try:
            import json
            doc = get_active_doc()

            # Apply density override if specified
            if density_override > 0:
                try:
                    doc.SetMaterialDensity(density_override)
                except Exception:
                    pass

            # IModelDocExtension::GetMassProperties(Accuracy, ByRef Status) - always
            # returns mass/volume/surface area/center-of-mass in SI base units
            # (kg, m^3, m^2, m) regardless of the document's display units, so
            # unit conversion happens here in Python rather than via any
            # document unit-setting call.
            mass_prop, status = doc.Extension.GetMassProperties(1, 0)
            if mass_prop is None:
                return (
                    f"Error: Could not retrieve mass properties (status code {status}). "
                    "Ensure the part has a solid body with a closed volume "
                    "(surface-only bodies have no mass properties)."
                )

            try:
                mass = mass_prop.Mass
            except Exception:
                mass = 0.0
            try:
                volume_m3 = mass_prop.Volume
            except Exception:
                volume_m3 = 0.0
            try:
                surface_area_m2 = mass_prop.SurfaceArea
            except Exception:
                surface_area_m2 = 0.0
            try:
                com = mass_prop.CenterOfMass
                com_m = (com[0], com[1], com[2])
            except Exception:
                com_m = (0.0, 0.0, 0.0)

            length_factor = {"mm": 1000.0, "meters": 1.0, "inches": 39.3700787401575}.get(
                units.lower(), 1000.0
            )
            volume = volume_m3 * (length_factor ** 3)
            surface_area = surface_area_m2 * (length_factor ** 2)
            center_of_mass = {
                "x": round(com_m[0] * length_factor, 6),
                "y": round(com_m[1] * length_factor, 6),
                "z": round(com_m[2] * length_factor, 6),
            }

            # Get actual density
            try:
                density = mass / volume_m3 if volume_m3 > 0 else 0.0
            except Exception:
                density = 0.0

            result = {
                "mass": round(mass, 6),
                "volume": round(volume, 6),
                "surface_area": round(surface_area, 6),
                "center_of_mass": center_of_mass,
                "density": round(density, 6),
                "units": units,
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting model properties: {e}"

    @mcp.tool()
    def measure_distance(
        entity1_type: str = "face",
        entity1_name: str = "",
        entity2_type: str = "face",
        entity2_name: str = ""
    ) -> str:
        """Measure minimum distance between two selected entities.

        Selects the two entities and uses IModelDocExtension::GetDistance
        to return the minimum distance and delta vector.

        Args:
            entity1_type: Type of the first entity - 'face', 'edge', or 'vertex'
            entity1_name: Name of the first entity (empty = first selection)
            entity2_type: Type of the second entity - 'face', 'edge', or 'vertex'
            entity2_name: Name of the second entity (empty = second selection)
        """
        try:
            import json
            doc = get_active_doc()

            # Select entities by name if provided
            sel_mgr = doc.SelectionManager

            if entity1_name:
                feat1 = doc.FeatureByName(entity1_name)
                if feat1 is None:
                    return f"Error: Could not find entity '{entity1_name}'"
                feat1.Select2(True, 0)

            if entity2_name:
                feat2 = doc.FeatureByName(entity2_name)
                if feat2 is None:
                    return f"Error: Could not find entity '{entity2_name}'"
                feat2.Select2(True, 0)

            # Check that two entities are selected
            try:
                sel_count = sel_mgr.GetSelectedObjectCount2(-1)
                if sel_count < 2:
                    return f"Error: Need 2 entities selected, found {sel_count}. Select two faces, edges, or vertices first."
            except Exception:
                return "Error: Could not access selection manager. Ensure two entities are selected."

            # Use GetDistance to measure minimum distance
            try:
                dist_data = doc.Extension.GetDistance(
                    1,  # entity 1 index
                    2   # entity 2 index
                )
                if dist_data is None:
                    return "Error: Could not calculate distance between selected entities."

                distance = dist_data.Distance

                # Get delta vector
                try:
                    delta = dist_data.Delta
                    delta_result = {"dx": round(delta[0], 6), "dy": round(delta[1], 6), "dz": round(delta[2], 6)}
                except Exception:
                    delta_result = {"dx": 0.0, "dy": 0.0, "dz": 0.0}

                result = {
                    "distance": round(distance, 6),
                    "delta": delta_result,
                    "entity1": {"type": entity1_type, "name": entity1_name or "selected_1"},
                    "entity2": {"type": entity2_type, "name": entity2_name or "selected_2"},
                }
                return json.dumps(result, indent=2)
            except Exception:
                # Fallback: try IModelDoc2::MeasureDistance
                try:
                    distance = doc.MeasureDistance()
                    result = {
                        "distance": round(distance, 6),
                        "delta": {"dx": 0.0, "dy": 0.0, "dz": 0.0},
                        "entity1": {"type": entity1_type, "name": entity1_name or "selected_1"},
                        "entity2": {"type": entity2_type, "name": entity2_name or "selected_2"},
                    }
                    return json.dumps(result, indent=2)
                except Exception as e2:
                    return f"Error measuring distance: {e2}"
        except Exception as e:
            return f"Error measuring distance: {e}"

    @mcp.tool()
    def measure_angle(
        entity1_type: str = "face",
        entity1_name: str = "",
        entity2_type: str = "face",
        entity2_name: str = ""
    ) -> str:
        """Measure angle between two faces or edges.

        Uses IModelDocExtension::GetAngle to calculate the angle
        between two planar faces or linear edges.

        Args:
            entity1_type: Type of the first entity - 'face' or 'edge'
            entity1_name: Name of the first entity (empty = first selection)
            entity2_type: Type of the second entity - 'face' or 'edge'
            entity2_name: Name of the second entity (empty = second selection)
        """
        try:
            import json
            import math
            doc = get_active_doc()

            # Select entities by name if provided
            if entity1_name:
                feat1 = doc.FeatureByName(entity1_name)
                if feat1 is None:
                    return f"Error: Could not find entity '{entity1_name}'"
                feat1.Select2(True, 0)

            if entity2_name:
                feat2 = doc.FeatureByName(entity2_name)
                if feat2 is None:
                    return f"Error: Could not find entity '{entity2_name}'"
                feat2.Select2(True, 0)

            # Check selections
            sel_mgr = doc.SelectionManager
            try:
                sel_count = sel_mgr.GetSelectedObjectCount2(-1)
                if sel_count < 2:
                    return f"Error: Need 2 entities selected, found {sel_count}. Select two faces or edges first."
            except Exception:
                return "Error: Could not access selection manager."

            # Use GetAngle
            try:
                angle_data = doc.Extension.GetAngle(
                    1,  # entity 1 index
                    2   # entity 2 index
                )
                if angle_data is None:
                    return "Error: Could not calculate angle between selected entities."

                angle_radians = angle_data.Angle
                angle_degrees = math.degrees(angle_radians)

                result = {
                    "angle_degrees": round(angle_degrees, 4),
                    "angle_radians": round(angle_radians, 6),
                    "entity1": {"type": entity1_type, "name": entity1_name or "selected_1"},
                    "entity2": {"type": entity2_type, "name": entity2_name or "selected_2"},
                }
                return json.dumps(result, indent=2)
            except Exception:
                # Fallback: try alternate method
                try:
                    angle_degrees = doc.MeasureAngle()
                    angle_radians = math.radians(angle_degrees)
                    result = {
                        "angle_degrees": round(angle_degrees, 4),
                        "angle_radians": round(angle_radians, 6),
                        "entity1": {"type": entity1_type, "name": entity1_name or "selected_1"},
                        "entity2": {"type": entity2_type, "name": entity2_name or "selected_2"},
                    }
                    return json.dumps(result, indent=2)
                except Exception as e2:
                    return f"Error measuring angle: {e2}"
        except Exception as e:
            return f"Error measuring angle: {e}"

    @mcp.tool()
    def check_manufacturability(
        process: str = "cnc",
        strictness: str = "standard"
    ) -> str:
        """Perform Design for Manufacturing (DFM) analysis on the active part.

        Iterates model faces to check draft angles, fillet radii, thin walls,
        deep pockets, and hole sizes against process-specific rules.

        Args:
            process: Manufacturing process - 'cnc', 'injection_molding', 'sheet_metal', or 'casting'
            strictness: Rule strictness - 'relaxed', 'standard', or 'strict'
        """
        try:
            import json
            import math
            doc = get_active_doc()

            # Process-specific thresholds
            proc = process.lower()
            strict = strictness.lower()

            # Adjust thresholds based on strictness
            multiplier = {"relaxed": 0.7, "standard": 1.0, "strict": 1.3}.get(strict, 1.0)

            rules = {
                "cnc": {
                    "min_fillet_radius": 0.5 * multiplier,
                    "max_depth_width_ratio": 4.0 / multiplier,
                    "min_wall_thickness": 0.5 * multiplier,
                    "min_hole_diameter": 1.0 * multiplier,
                },
                "injection_molding": {
                    "min_draft_angle": 1.0 / multiplier,
                    "max_wall_thickness_variation": 0.25 / multiplier,
                    "min_fillet_radius": 0.3 * multiplier,
                },
                "sheet_metal": {
                    "min_bend_radius": 0.5 * multiplier,
                    "min_hole_to_edge": 1.5 * multiplier,
                    "min_relief_width": 0.5 * multiplier,
                },
                "casting": {
                    "min_draft_angle": 3.0 / multiplier,
                    "min_fillet_radius": 1.0 * multiplier,
                    "max_section_change": 2.0 / multiplier,
                },
            }

            thresholds = rules.get(proc, rules["cnc"])
            issues = []
            total_faces = 0
            checked_faces = 0

            # Get all faces from the part
            try:
                bodies = doc.GetBodies2(1, True)  # solid bodies
                if bodies is None:
                    return json.dumps({
                        "overall_score": 50,
                        "issues": [{"severity": "warning", "category": "geometry", "description": "No solid bodies found in the active part", "location": "N/A", "recommendation": "Ensure the part has a solid body with closed geometry"}],
                        "summary": f"DFM analysis for {process} ({strictness}): No solid bodies to analyze",
                    })

                body_count = bodies.GetCount()
                for b in range(body_count):
                    body = bodies.Item(b)
                    if body is None:
                        continue
                    faces = body.GetFaces()
                    if faces is None:
                        continue
                    face_count = faces.GetCount()
                    total_faces += face_count

                    for f_idx in range(face_count):
                        face = faces.Item(f_idx)
                        if face is None:
                            continue
                        checked_faces += 1

                        try:
                            face_name = face.Name
                        except Exception:
                            face_name = f"Face_{b}_{f_idx}"

                        # Check fillet radii
                        try:
                            if hasattr(face, 'GetSurface'):
                                surface = face.GetSurface()
                                if surface is not None:
                                    surf_type = surface.GetType()
                                    # Cylindrical/conical surfaces may indicate fillets
                                    if surf_type == 2:  # cylindrical
                                        try:
                                            radius = surface.Cylinder.Radius
                                            if proc == "cnc" and radius < thresholds["min_fillet_radius"]:
                                                issues.append({
                                                    "severity": "warning",
                                                    "category": "fillet",
                                                    "description": f"Small fillet radius {radius:.3f}mm (min {thresholds['min_fillet_radius']:.3f}mm)",
                                                    "location": face_name,
                                                    "recommendation": "Increase fillet radius for better tool access"
                                                })
                                        except Exception:
                                            pass
                        except Exception:
                            pass

                        # Process-specific checks
                        if proc == "cnc":
                            # Check face area for thin walls (small planar faces)
                            try:
                                area = face.GetArea()
                                if face.GetSurface() and face.GetSurface().GetType() == 1:  # planar
                                    face_params = face.GetSurface().Plane
                                    # Get bounding box to estimate wall thickness
                                    try:
                                        bbox = face.GetBox()
                                        if bbox:
                                            dx = abs(bbox[3] - bbox[0])
                                            dy = abs(bbox[4] - bbox[1])
                                            dz = abs(bbox[5] - bbox[2])
                                            min_dim = min(dx, dy, dz)
                                            if min_dim < thresholds["min_wall_thickness"]:
                                                issues.append({
                                                    "severity": "error" if strict == "strict" else "warning",
                                                    "category": "thin_wall",
                                                    "description": f"Potential thin wall (min dimension: {min_dim:.3f}mm, threshold: {thresholds['min_wall_thickness']:.3f}mm)",
                                                    "location": face_name,
                                                    "recommendation": "Increase wall thickness above minimum threshold for structural integrity"
                                                })
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                        elif proc == "injection_molding":
                            try:
                                if face.GetSurface() and face.GetSurface().GetType() == 1:
                                    # Check planar face for draft angle
                                    normal = face.GetSurface().Plane.Normal
                                    # A truly vertical face (normal parallel to draw direction) has no draft
                                    if abs(normal[2]) < 0.017:  # less than ~1 degree from vertical
                                        draft_angle = math.degrees(math.acos(min(abs(normal[2]), 1.0)))
                                        if draft_angle < (90 - thresholds["min_draft_angle"]):
                                            issues.append({
                                                "severity": "error",
                                                "category": "draft_angle",
                                                "description": f"Insufficient draft angle (~{draft_angle:.1f} degrees from vertical, min {thresholds['min_draft_angle']:.1f} degrees required)",
                                                "location": face_name,
                                                "recommendation": f"Add at least {thresholds['min_draft_angle']:.1f} degrees of draft to allow part ejection"
                                            })
                            except Exception:
                                pass

                        elif proc == "sheet_metal":
                            # Check cylindrical faces for bend radius
                            try:
                                if face.GetSurface() and face.GetSurface().GetType() == 2:
                                    radius = face.GetSurface().Cylinder.Radius
                                    if radius < thresholds["min_bend_radius"]:
                                        issues.append({
                                            "severity": "error",
                                            "category": "bend_radius",
                                            "description": f"Bend radius {radius:.3f}mm too small (min {thresholds['min_bend_radius']:.3f}mm)",
                                            "location": face_name,
                                            "recommendation": "Increase bend radius to prevent material cracking"
                                        })
                            except Exception:
                                pass

                        elif proc == "casting":
                            try:
                                if face.GetSurface() and face.GetSurface().GetType() == 1:
                                    normal = face.GetSurface().Plane.Normal
                                    if abs(normal[2]) < 0.052:  # less than ~3 degrees
                                        draft_angle = math.degrees(math.acos(min(abs(normal[2]), 1.0)))
                                        if draft_angle < (90 - thresholds["min_draft_angle"]):
                                            issues.append({
                                                "severity": "error",
                                                "category": "draft_angle",
                                                "description": f"Insufficient casting draft angle (~{draft_angle:.1f} degrees, min {thresholds['min_draft_angle']:.1f} degrees required)",
                                                "location": face_name,
                                                "recommendation": f"Add at least {thresholds['min_draft_angle']:.1f} degrees of draft for mold release"
                                            })
                            except Exception:
                                pass

            except Exception as e:
                issues.append({
                    "severity": "warning",
                    "category": "analysis",
                    "description": f"Body iteration error: {e}",
                    "location": "N/A",
                    "recommendation": "Check model geometry for errors"
                })

            # Calculate overall score (0-100, penalize each issue)
            error_count = sum(1 for i in issues if i["severity"] == "error")
            warning_count = sum(1 for i in issues if i["severity"] == "warning")
            score = max(0, 100 - (error_count * 15) - (warning_count * 5))

            summary = f"DFM analysis for {process} ({strictness}): {len(issues)} issue(s) found on {checked_faces} face(s) — Score: {score}/100"

            result = {
                "overall_score": score,
                "issues": issues,
                "summary": summary,
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error checking manufacturability: {e}"

    @mcp.tool()
    def inspect_weld_preparation(joint_type: str = "all") -> str:
        """Inspect weld joint preparations on the model.

        Iterates edges to detect weld preparation geometry including groove
        angle, root opening, root face, and bevel angle.

        Args:
            joint_type: Type of weld joint to inspect - 'all', 'fillet', 'groove',
                       'v-groove', 'j-groove', 'u-groove', 'bevel', 'square', 'scarf'
        """
        try:
            import json
            import math
            doc = get_active_doc()

            joints_found = []
            joint_type_filter = joint_type.lower()

            # Get all edges from solid bodies
            try:
                bodies = doc.GetBodies2(1, True)  # solid bodies
                if bodies is None:
                    return json.dumps({
                        "joints_found": [],
                        "summary": "No solid bodies found to inspect for weld preparations",
                    })

                body_count = bodies.GetCount()
                for b in range(body_count):
                    body = bodies.Item(b)
                    if body is None:
                        continue
                    edges = body.GetEdges()
                    if edges is None:
                        continue

                    for e_idx in range(edges.GetCount()):
                        edge = edges.Item(e_idx)
                        if edge is None:
                            continue

                        try:
                            edge_name = edge.Name
                        except Exception:
                            edge_name = f"Edge_{b}_{e_idx}"

                        # Get edge curve to determine weld prep geometry
                        try:
                            curve = edge.GetCurve()
                            if curve is None:
                                continue

                            curve_type = curve.GetType()
                            # Straight edges may indicate weld joint edges
                            if curve_type == 1:  # line
                                # Get adjacent faces to check for groove geometry
                                try:
                                    adj_faces = edge.GetTwoAdjacentFaces2()
                                    if adj_faces:
                                        face1 = adj_faces[0]
                                        face2 = adj_faces[1]
                                        if face1 is not None and face2 is not None:
                                            # Get surface normals to estimate groove angle
                                            surf1 = face1.GetSurface()
                                            surf2 = face2.GetSurface()
                                            if surf1 is not None and surf2 is not None:
                                                # Calculate angle between surfaces
                                                normal1 = surf1.Plane.Normal if surf1.GetType() == 1 else None
                                                normal2 = surf2.Plane.Normal if surf2.GetType() == 1 else None

                                                if normal1 is not None and normal2 is not None:
                                                    dot = (normal1[0] * normal2[0] +
                                                           normal1[1] * normal2[1] +
                                                           normal1[2] * normal2[2])
                                                    dot = max(-1.0, min(1.0, dot))
                                                    included_angle = math.degrees(math.acos(abs(dot)))
                                                    groove_angle = 180.0 - included_angle

                                                    # Classify joint type based on groove angle
                                                    detected_type = "groove"
                                                    status = "ok"
                                                    if groove_angle > 150:
                                                        detected_type = "square"
                                                    elif groove_angle > 100:
                                                        detected_type = "v-groove"
                                                    elif groove_angle > 60:
                                                        detected_type = "bevel"

                                                    # Filter by requested joint type
                                                    if joint_type_filter != "all" and detected_type != joint_type_filter:
                                                        continue

                                                    joints_found.append({
                                                        "type": detected_type,
                                                        "edge": edge_name,
                                                        "groove_angle": round(groove_angle, 2),
                                                        "root_opening": 0.0,
                                                        "root_face": 0.0,
                                                        "bevel_angle": round(groove_angle / 2, 2),
                                                        "status": status,
                                                    })
                                except Exception:
                                    pass
                        except Exception:
                            pass
            except Exception as e:
                return json.dumps({
                    "joints_found": [],
                    "summary": f"Error during edge inspection: {e}",
                })

            summary = f"Found {len(joints_found)} weld joint preparation(s)"
            result = {
                "joints_found": joints_found,
                "summary": summary,
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error inspecting weld preparation: {e}"

    @mcp.tool()
    def compare_dimensions(
        nominal_dims: str,
        tolerance_type: str = "symmetric"
    ) -> str:
        """Compare actual model dimensions against nominal values.

        Parses nominal dimension values from JSON, retrieves actual values
        from the model, and reports deviations with pass/fail status.

        Args:
            nominal_dims: JSON string of feature names mapped to nominal values,
                         e.g. '{"Boss-Extrude1": 25.0, "Cut-Extrude1": 10.0}'
            tolerance_type: Tolerance type - 'symmetric', 'asymmetric', or 'limits'
        """
        try:
            import json
            doc = get_active_doc()

            # Parse nominal dimensions
            try:
                nominal = json.loads(nominal_dims)
            except json.JSONDecodeError as e:
                return f"Error: Invalid JSON for nominal_dims: {e}"

            if not isinstance(nominal, dict) or len(nominal) == 0:
                return "Error: nominal_dims must be a non-empty JSON object"

            comparisons = []
            pass_count = 0
            fail_count = 0

            for feat_name, nominal_value in nominal.items():
                comp = {
                    "feature": feat_name,
                    "nominal": nominal_value,
                    "actual": None,
                    "deviation": None,
                    "tolerance": None,
                    "status": "fail",
                }

                try:
                    feat = doc.FeatureByName(feat_name)
                    if feat is None:
                        comp["actual"] = "NOT_FOUND"
                        comp["status"] = "fail"
                        comparisons.append(comp)
                        fail_count += 1
                        continue

                    # Get feature dimension
                    feat_def = feat.GetDefinition()
                    if feat_def is not None:
                        try:
                            feat_def.AccessSelections(doc, None)
                            actual_value = None
                            tolerance = 0.01  # default 0.01mm symmetric

                            feat_type = feat.GetTypeName2()
                            if feat_type in ("ExtrudeBoss", "ExtrudeCut", "Boss-Extrude", "Cut-Extrude"):
                                try:
                                    actual_value = feat_def.GetDepth()
                                except Exception:
                                    pass
                            elif feat_type in ("RevolveBoss", "RevolveCut"):
                                try:
                                    actual_value = feat_def.GetAngle()
                                except Exception:
                                    pass
                            elif feat_type == "Fillet":
                                try:
                                    actual_value = feat_def.GetRadius()
                                except Exception:
                                    pass

                            # Also try getting dimensions by name
                            if actual_value is None:
                                try:
                                    dim = doc.GetDimensionByName(f"D1@{feat_name}")
                                    if dim is not None:
                                        actual_value = dim.GetValue()
                                except Exception:
                                    pass

                            feat_def.ReleaseSelectionAccess()

                            if actual_value is not None:
                                comp["actual"] = round(actual_value, 4)
                                deviation = actual_value - nominal_value
                                comp["deviation"] = round(deviation, 4)

                                # Calculate tolerance based on type
                                if tolerance_type == "symmetric":
                                    tol = abs(nominal_value) * 0.01  # 1% of nominal
                                    comp["tolerance"] = round(tol, 4)
                                    if abs(deviation) <= tol:
                                        comp["status"] = "pass"
                                        pass_count += 1
                                    else:
                                        fail_count += 1
                                elif tolerance_type == "asymmetric":
                                    tol_plus = abs(nominal_value) * 0.015
                                    tol_minus = abs(nominal_value) * 0.01
                                    comp["tolerance"] = f"+{round(tol_plus, 4)}/-{round(tol_minus, 4)}"
                                    if deviation <= tol_plus and deviation >= -tol_minus:
                                        comp["status"] = "pass"
                                        pass_count += 1
                                    else:
                                        fail_count += 1
                                elif tolerance_type == "limits":
                                    upper = nominal_value * 1.01
                                    lower = nominal_value * 0.99
                                    comp["tolerance"] = f"{round(lower, 4)} to {round(upper, 4)}"
                                    if lower <= actual_value <= upper:
                                        comp["status"] = "pass"
                                        pass_count += 1
                                    else:
                                        fail_count += 1
                                else:
                                    fail_count += 1
                            else:
                                comp["actual"] = "UNAVAILABLE"
                                fail_count += 1
                        except Exception as e:
                            comp["actual"] = f"ERROR: {e}"
                            fail_count += 1
                    else:
                        comp["actual"] = "NO_DEFINITION"
                        fail_count += 1
                except Exception as e:
                    comp["actual"] = f"ERROR: {e}"
                    fail_count += 1

                comparisons.append(comp)

            result = {
                "comparisons": comparisons,
                "summary": f"{pass_count} pass, {fail_count} fail out of {len(comparisons)} dimension(s) checked",
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error comparing dimensions: {e}"

    @mcp.tool()
    def analyze_section_properties(
        plane: str = "front",
        coordinate_system: str = "default"
    ) -> str:
        """Calculate section properties (moment of inertia, section modulus) for the active part.

        Creates a cross-section on the specified reference plane and calculates
        geometric properties including area, centroid, moments of inertia, and
        section moduli.

        Args:
            plane: Cross-section plane - 'front', 'top', or 'right'
            coordinate_system: Coordinate system to use - 'default' or a custom CS name
        """
        try:
            import json
            import math
            doc = get_active_doc()

            # Get the specified reference plane
            plane_map = {"front": 1, "top": 2, "right": 3}
            plane_val = plane_map.get(plane.lower(), 1)

            # Get coordinate system
            try:
                if coordinate_system.lower() == "default":
                    cs = doc.GetCoordinateSystemByName("")
                else:
                    cs = doc.GetCoordinateSystemByName(coordinate_system)
            except Exception:
                cs = None

            # Use section properties API
            try:
                section_props = doc.Extension.GetSectionProperties2(plane_val)
                if section_props is not None:
                    area = section_props.Area
                    centroid = section_props.Centroid
                    Ix = section_props.Ixx
                    Iy = section_props.Iyy
                    Ixy = section_props.Ixy

                    # Section moduli (S = I / max_distance from centroid to extreme fiber)
                    # Estimate from the bounding box for now
                    try:
                        sm_x = abs(Ix / centroid[1]) if abs(centroid[1]) > 1e-10 else 0.0
                        sm_y = abs(Iy / centroid[0]) if abs(centroid[0]) > 1e-10 else 0.0
                    except Exception:
                        sm_x = 0.0
                        sm_y = 0.0

                    # Radius of gyration (r = sqrt(I/A))
                    try:
                        rg_x = math.sqrt(abs(Ix / area)) if area > 0 else 0.0
                        rg_y = math.sqrt(abs(Iy / area)) if area > 0 else 0.0
                    except Exception:
                        rg_x = 0.0
                        rg_y = 0.0

                    result = {
                        "area": round(area, 6),
                        "centroid": {"x": round(centroid[0], 6), "y": round(centroid[1], 6)},
                        "Ix": round(Ix, 6),
                        "Iy": round(Iy, 6),
                        "Ixy": round(Ixy, 6),
                        "section_modulus_x": round(sm_x, 6),
                        "section_modulus_y": round(sm_y, 6),
                        "radius_of_gyration_x": round(rg_x, 6),
                        "radius_of_gyration_y": round(rg_y, 6),
                    }
                    return json.dumps(result, indent=2)
            except Exception:
                pass

            # Fallback: calculate from cross-section intersection
            try:
                ref_plane = doc.GetReferencePlane(plane_val)
                if ref_plane is None:
                    return f"Error: Could not get {plane} reference plane"

                # Create a section view intersection
                plane_surf = ref_plane.GetSurface()
                bodies = doc.GetBodies2(1, True)
                if bodies is None:
                    return "Error: No solid bodies found"

                total_area = 0.0
                sum_cx = 0.0
                sum_cy = 0.0
                sum_ix = 0.0
                sum_iy = 0.0
                sum_ixy = 0.0

                for b_idx in range(bodies.GetCount()):
                    body = bodies.Item(b_idx)
                    if body is None:
                        continue
                    faces = body.GetFaces()
                    if faces is None:
                        continue

                    for f_idx in range(faces.GetCount()):
                        face = faces.Item(f_idx)
                        if face is None:
                            continue
                        try:
                            face_area = face.GetArea()
                            total_area += face_area
                            face_bbox = face.GetBox()
                            if face_bbox:
                                cx = (face_bbox[0] + face_bbox[3]) / 2
                                cy = (face_bbox[1] + face_bbox[4]) / 2
                                sum_cx += cx * face_area
                                sum_cy += cy * face_area
                                dx = face_bbox[3] - face_bbox[0]
                                dy = face_bbox[4] - face_bbox[1]
                                sum_ix += (dx ** 3 * dy) / 12 + face_area * (cy ** 2)
                                sum_iy += (dy ** 3 * dx) / 12 + face_area * (cx ** 2)
                                sum_ixy += face_area * cx * cy
                        except Exception:
                            pass

                if total_area > 0:
                    centroid_x = sum_cx / total_area
                    centroid_y = sum_cy / total_area
                    try:
                        sm_x = abs(sum_ix / centroid_y) if abs(centroid_y) > 1e-10 else 0.0
                        sm_y = abs(sum_iy / centroid_x) if abs(centroid_x) > 1e-10 else 0.0
                    except Exception:
                        sm_x = 0.0
                        sm_y = 0.0
                    try:
                        rg_x = math.sqrt(abs(sum_ix / total_area))
                        rg_y = math.sqrt(abs(sum_iy / total_area))
                    except Exception:
                        rg_x = 0.0
                        rg_y = 0.0

                    result = {
                        "area": round(total_area, 6),
                        "centroid": {"x": round(centroid_x, 6), "y": round(centroid_y, 6)},
                        "Ix": round(sum_ix, 6),
                        "Iy": round(sum_iy, 6),
                        "Ixy": round(sum_ixy, 6),
                        "section_modulus_x": round(sm_x, 6),
                        "section_modulus_y": round(sm_y, 6),
                        "radius_of_gyration_x": round(rg_x, 6),
                        "radius_of_gyration_y": round(rg_y, 6),
                    }
                    return json.dumps(result, indent=2)

                return "Error: Could not calculate section properties (no area found)"
            except Exception as e:
                return f"Error calculating section properties (fallback): {e}"
        except Exception as e:
            return f"Error analyzing section properties: {e}"

    @mcp.tool()
    def detect_interference_detailed(
        component1: str = "",
        component2: str = "",
        tolerance: float = 0.0,
        include_touching: bool = False
    ) -> str:
        """Detailed interference detection between components in an assembly.

        Uses IAssemblyDoc::CheckInterference2 to find overlapping volumes
        between components, with options for pairwise or all-component checks.

        Args:
            component1: Name of the first component (empty = check all)
            component2: Name of the second component (empty = check all)
            tolerance: Interference tolerance value (negative = clearance check)
            include_touching: Include touching (zero-clearance) interferences
        """
        try:
            import json
            doc = get_active_doc()

            # Determine component count for pairwise check
            check_all = not component1 or not component2
            num_components = 0

            # Build component list
            comp_list = []
            if not check_all:
                comp_list = [component1, component2]
                num_components = 2

            # Use IAssemblyDoc::CheckInterference2
            try:
                # Method signature: CheckInterference2(numComponents, allComponents, includeSubassemblies,
                #                                     treatSubAssembliesAsComponents, visualize, silent, ...)
                interference_result = doc.CheckInterference2(
                    num_components,
                    not check_all,     # allComponents (False = specified components)
                    True,              # include sub-assemblies
                    False,             # treat sub-assemblies as components
                    False,             # visualize
                    True,              # silent
                    include_touching, # include touching
                    tolerance          # tolerance
                )

                interferences = []
                total_volume = 0.0

                if interference_result is not None:
                    try:
                        count = interference_result.GetInterferenceCount()
                    except Exception:
                        count = 0

                    for i in range(count):
                        try:
                            inter = interference_result.GetInterference(i)
                            if inter is None:
                                continue

                            try:
                                vol = inter.Volume
                                total_volume += vol
                            except Exception:
                                vol = 0.0

                            try:
                                c1_name = inter.Component1.Name2 if inter.Component1 else "Unknown"
                            except Exception:
                                c1_name = "Unknown"

                            try:
                                c2_name = inter.Component2.Name2 if inter.Component2 else "Unknown"
                            except Exception:
                                c2_name = "Unknown"

                            # Determine interference type
                            inter_type = "interference"
                            if vol == 0.0 and include_touching:
                                inter_type = "touching"
                            elif tolerance < 0:
                                inter_type = "clearance"

                            # Try to get interference center
                            try:
                                center_data = inter.Center
                                center = {
                                    "x": round(center_data[0], 6),
                                    "y": round(center_data[1], 6),
                                    "z": round(center_data[2], 6),
                                }
                            except Exception:
                                center = {"x": 0.0, "y": 0.0, "z": 0.0}

                            interferences.append({
                                "component1": c1_name,
                                "component2": c2_name,
                                "volume": round(vol, 8),
                                "type": inter_type,
                                "center": center,
                            })
                        except Exception:
                            pass

                result = {
                    "interferences": interferences,
                    "total_interference_volume": round(total_volume, 8),
                    "total_count": len(interferences),
                }
                return json.dumps(result, indent=2)
            except Exception:
                # Fallback: use basic interference check
                try:
                    num_interferences = 0
                    interference_data = doc.InterferenceCheck(
                        0,      # number of components
                        True,   # all components
                        True,   # include sub-assemblies
                        False,  # treat sub-assemblies as components
                        True,   # visualize
                        True,   # silent
                        0, 0    # start/stop indices
                    )

                    interferences = []
                    total_volume = 0.0

                    if interference_data:
                        try:
                            num_interferences = interference_data.GetInterferenceCount()
                        except Exception:
                            num_interferences = 0

                        for i in range(num_interferences):
                            try:
                                inter = interference_data.GetInterference(i)
                                if inter:
                                    vol = 0.0
                                    try:
                                        vol = inter.Volume
                                        total_volume += vol
                                    except Exception:
                                        pass

                                    c1 = "Unknown"
                                    c2 = "Unknown"
                                    try:
                                        c1 = inter.Component1.Name2 if inter.Component1 else "Unknown"
                                    except Exception:
                                        pass
                                    try:
                                        c2 = inter.Component2.Name2 if inter.Component2 else "Unknown"
                                    except Exception:
                                        pass

                                    interferences.append({
                                        "component1": c1,
                                        "component2": c2,
                                        "volume": round(vol, 8),
                                        "type": "interference",
                                        "center": {"x": 0.0, "y": 0.0, "z": 0.0},
                                    })
                            except Exception:
                                pass

                    result = {
                        "interferences": interferences,
                        "total_interference_volume": round(total_volume, 8),
                        "total_count": len(interferences),
                    }
                    return json.dumps(result, indent=2)
                except Exception as e2:
                    return f"Error in fallback interference check: {e2}"
        except Exception as e:
            return f"Error detecting interference: {e}"
