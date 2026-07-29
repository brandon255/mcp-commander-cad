"""
Spatial Reasoning Operation.

Infer 3D spatial relationships from voice/text descriptions of geometry.
Parses natural language descriptions of mechanical components and extracts
positional, orientational, and relational information.
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Spatial relationship vocabulary and definitions
# ---------------------------------------------------------------------------
SPATIAL_RELATIONS: dict[str, dict[str, str | list[str]]] = {
    "concentric": {
        "definition": "Two cylindrical or spherical features share the same central axis. One is inside the other.",
        "typical_application": "Bearings in housings, shafts through bores, bushings in pins, O-ring on piston.",
        "keywords": [
            "centered", "coaxial", "concentric", "same axis", "aligned on center",
            "runs through the center", "shares the axis", "inline",
        ],
        "implied_constraints": ["Coaxiality tolerance (○) between features", "Radial clearance or interference specification"],
        "geometry_type": "revolution",
    },
    "perpendicular": {
        "definition": "Two features meet at exactly 90° (± specified tolerance).",
        "typical_application": "Flange face to bore axis, mounting surface to reference datum, pin to base plate.",
        "keywords": [
            "perpendicular", "at 90 degrees", "right angle", "normal to",
            "square to", "orthogonal", "crosses at ninety",
        ],
        "implied_constraints": ["Perpendicularity tolerance (⊥) to datum", "Squareness verification"],
        "geometry_type": "planar/linear",
    },
    "coplanar": {
        "definition": "Two or more planar features lie in the same plane or parallel planes with controlled offset.",
        "typical_application": "Mating flange faces, mounting pads on same surface, seal land faces.",
        "keywords": [
            "coplanar", "same plane", "flat with", "level with", "flush",
            "in the same surface", "co-planar", "flush-mounted",
        ],
        "implied_constraints": ["Flatness of combined surface", "Parallelism between sub-features"],
        "geometry_type": "planar",
    },
    "parallel": {
        "definition": "Two features maintain constant distance along their length, at 0° angle between them.",
        "typical_application": "Guide rails, shaft centerlines in a gearbox, slot walls, plate surfaces.",
        "keywords": [
            "parallel", "runs alongside", "equidistant", "same direction",
            "side by side", "track", "rail",
        ],
        "implied_constraints": ["Parallelism tolerance (//) between features", "Distance between parallel features"],
        "geometry_type": "linear/planar",
    },
    "offset": {
        "definition": "Two features are displaced from each other by a specified distance in one or more directions.",
        "typical_application": "Staggered bolt holes, eccentric shaft, offset mounting bracket.",
        "keywords": [
            "offset", "staggered", "displaced", "shifted", "eccentric",
            "misaligned by", "off-center", "spaced apart by",
        ],
        "implied_constraints": ["Positional tolerance for offset dimension", "Offset distance with tolerance"],
        "geometry_type": "positional",
    },
    "tangent": {
        "definition": "Two features touch at exactly one point/line with no intersection.",
        "typical_application": "Ball bearing in raceway, cam follower on cam surface, roller on flat surface.",
        "keywords": [
            "tangent", "touches at one point", "just touching", "rolling contact",
            "cam follower", "ball on surface", "kiss fit",
        ],
        "implied_constraints": ["Contact point location", "Surface continuity at tangent point"],
        "geometry_type": "curved/planar",
    },
    "symmetric": {
        "definition": "Features are mirrored across a plane, axis, or point (bilateral, axial, or point symmetry).",
        "typical_application": "Left/right housing halves, symmetric brackets, center-mounted components.",
        "keywords": [
            "symmetric", "mirrored", "mirror image", "balanced", "same on both sides",
            "identical left and right", "symmetrical", "center-symmetric",
        ],
        "implied_constraints": ["Symmetry tolerance", "Datum plane for mirror axis", "Equal dimensions on both sides"],
        "geometry_type": "transformative",
    },
    "intersecting": {
        "definition": "Two features cross through each other, sharing a volume.",
        "typical_application": "Cross-drilled holes, intersecting shafts, pipe tee joints.",
        "keywords": [
            "intersect", "cross", "through", "penetrates", "passes through",
            " drilled through", "pierces", "cuts across",
        ],
        "implied_constraints": ["Intersection geometry (round, chamfered, or sharp)", "Break edge at intersection"],
        "geometry_type": "volumetric",
    },
    "angled": {
        "definition": "Two features meet at a specified angle other than 0° or 90°.",
        "typical_application": "Angled mounting faces, miter joints, chamfered edges, draft angles.",
        "keywords": [
            "angled", "beveled", "chamfered", "mitered", "inclined", "sloped",
            "at X degrees", "tapered", "tilted",
        ],
        "implied_constraints": ["Angular tolerance", "Angularity tolerance (∠) to datum"],
        "geometry_type": "angular",
    },
    "clearance_fit": {
        "definition": "Two cylindrical features with controlled gap allowing relative motion or assembly without force.",
        "typical_application": "Shaft in bearing, pin in clearance hole, piston in cylinder.",
        "keywords": [
            "clearance", "sliding fit", "running fit", "loose fit", "free to move",
            "slides into", "clearance hole", "gap of",
        ],
        "implied_constraints": ["Minimum and maximum clearance", "Fit class (H7/g6, etc.)", "Surface finish for sliding contacts"],
        "geometry_type": "cylindrical",
    },
    "interference_fit": {
        "definition": "Two cylindrical features with controlled overlap requiring force, thermal, or press assembly.",
        "typical_application": "Bearing races in housings, shaft collars, hub on shaft.",
        "keywords": [
            "interference", "press fit", "shrink fit", "force fit", "tight fit",
            "pressed in", "thermal shrink", "loctite retained",
        ],
        "implied_constraints": ["Minimum and maximum interference", "Assembly force or temperature differential", "Yield stress check at interface"],
        "geometry_type": "cylindrical",
    },
}

# ---------------------------------------------------------------------------
# Dimensional unit patterns
# ---------------------------------------------------------------------------
UNIT_PATTERNS: dict[str, list[str]] = {
    "mm": ["mm", "millimeter", "millimeters"],
    "cm": ["cm", "centimeter", "centimeters"],
    "m": ["m ", "meter", "meters"],
    "in": ["in", "inch", "inches", '"', '"'],
    "ft": ["ft", "feet", "foot", "'"],
    "deg": ["degree", "degrees", "°", "deg"],
    "rad": ["radian", "radians", "rad"],
}

# ---------------------------------------------------------------------------
# Feature type vocabulary
# ---------------------------------------------------------------------------
FEATURE_TYPES: dict[str, list[str]] = {
    "cylindrical": ["bore", "hole", "shaft", "pin", "rod", "cylinder", "tube", "pipe"],
    "planar": ["face", "surface", "plate", "panel", "flat", "wall", "flange", "face"],
    "revolved": ["boss", "hub", "spool", "cone", "sphere", "dome"],
    "linear": ["slot", "channel", "groove", "keyway", "track", "rail", "ledge"],
    "complex": ["fillet", "chamfer", "blend", "taper", "undercut", "draft"],
}

# ---------------------------------------------------------------------------
# Parsing functions
# ---------------------------------------------------------------------------


def _extract_dimensions(text: str) -> list[dict[str, str | float]]:
    """Extract dimensional values and units from text."""
    import re
    dimensions: list[dict[str, str | float]] = []
    # Match patterns like "50mm", "2.5 inches", "90 degrees"
    patterns = [
        r"(\d+(?:\.\d+)?)\s*(mm|millimeters?|cm|centimeters?|m |meters?|in(?:ches?)?|ft|feet|foot|°|degrees?|deg|radians?)",
    ]
    for pat in patterns:
        for match in re.finditer(pat, text, re.IGNORECASE):
            value = float(match.group(1))
            unit_str = match.group(2).strip()
            # Normalize unit
            unit = "unknown"
            for norm_unit, aliases in UNIT_PATTERNS.items():
                if unit_str in aliases:
                    unit = norm_unit
                    break
            dimensions.append({"value": value, "unit": unit})
    return dimensions


def _extract_features(text: str) -> list[str]:
    """Identify geometric feature types mentioned in text."""
    text_lower = text.lower()
    found: list[str] = []
    for feat_type, keywords in FEATURE_TYPES.items():
        for kw in keywords:
            if kw in text_lower:
                found.append(feat_type)
                break
    return found


def _extract_relationships(text: str) -> list[dict]:
    """Identify spatial relationships mentioned in text."""
    text_lower = text.lower()
    found: list[dict] = []
    for rel_name, rel_info in SPATIAL_RELATIONS.items():
        for kw in rel_info["keywords"]:
            if kw in text_lower:
                found.append({
                    "relationship": rel_name,
                    "definition": rel_info["definition"],
                    "matched_keyword": kw,
                    "implied_constraints": rel_info["implied_constraints"],
                    "geometry_type": rel_info["geometry_type"],
                })
                break
    return found


def spatial_reasoning(
    geometry_description: str,
    context: Optional[str] = None,
) -> dict:
    """
    Infer 3D spatial relationships from a text description of geometry.

    Parses natural-language descriptions of mechanical geometry to extract
    spatial relationships (concentric, perpendicular, coplanar, etc.),
    feature types, dimensional values, and implied engineering constraints.

    Args:
        geometry_description: Text description of the geometry, components,
            and their spatial arrangement
            (e.g. "A 25mm shaft runs through a 30mm bore, concentric with
            the housing, perpendicular to the mounting face.").
        context: Optional additional context about the assembly or
            application.

    Returns:
        Parsed spatial model with extracted features, relationships,
        dimensions, implied constraints, and a spatial summary.
    """
    # Extract all spatial information
    dimensions = _extract_dimensions(geometry_description)
    features = _extract_features(geometry_description)
    relationships = _extract_relationships(geometry_description)

    # Build a textual spatial summary
    summary_parts: list[str] = []
    if dimensions:
        dim_strs = [f"{d['value']} {d['unit']}" for d in dimensions]
        summary_parts.append(f"Dimensions found: {', '.join(dim_strs)}")
    if features:
        summary_parts.append(f"Feature types: {', '.join(set(features))}")
    if relationships:
        rel_strs = [f"{r['relationship']} (keyword: '{r['matched_keyword']}')" for r in relationships]
        summary_parts.append(f"Spatial relationships: {'; '.join(rel_strs)}")

    # Generate constraint checklist
    constraint_checklist: list[str] = []
    for rel in relationships:
        for constraint in rel["implied_constraints"]:
            constraint_checklist.append(constraint)

    return {
        "geometry_description": geometry_description,
        "context": context,
        "parsed": {
            "dimensions": dimensions,
            "feature_types": list(set(features)),
            "spatial_relationships": relationships,
        },
        "implied_constraints": list(dict.fromkeys(constraint_checklist)),
        "spatial_summary": " | ".join(summary_parts) if summary_parts else "No specific spatial relationships detected. Provide more detailed geometry description.",
        "constraint_checklist": [
            f"☐ Define {c}" for c in list(dict.fromkeys(constraint_checklist))
        ],
    }
