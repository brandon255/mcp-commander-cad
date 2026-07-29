"""
Uncommon Methods Operation.

Suggest non-traditional manufacturing methods for engineering applications.
Covers methods beyond standard CNC machining, injection molding, and stamping,
including additive manufacturing, soft tooling, hybrid processes, and
low-volume production techniques.
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Non-traditional manufacturing methods database
# ---------------------------------------------------------------------------
METHODS_DB: list[dict[str, str | list[str]]] = [
    {
        "name": "3D Printed Jig / Fixture (FDM/FFF)",
        "category": "tooling",
        "description": "Print functional jigs, fixtures, and assembly aids directly from CAD. Use engineering-grade materials like PC, PETG-CF, or PEEK for load-bearing applications.",
        "suitable_for": [
            "Welding jigs",
            "Assembly fixtures",
            "Drilling guides",
            "Inspection gauges (low-precision)",
            "Cable routing guides",
            "Masking tools for painting/coating",
        ],
        "advantages": [
            "Lead time: hours to 1-2 days",
            "Cost: $5-$200 per fixture",
            "Fully customizable per part geometry",
            "No tooling investment",
            "Iterative optimization possible",
        ],
        "disadvantages": [
            "Limited temperature resistance (PLA ~60°C, PC ~140°C)",
            "Anisotropic strength (weaker in Z-axis)",
            "Surface finish may need post-processing",
            "Not suitable for high-precision gauging",
        ],
        "material_options": ["PLA", "PETG", "ABS", "ASA", "Polycarbonate", "Nylon-CF", "PEEK"],
        "typical_lead_time": "0.5-3 days",
        "cost_range_usd": "5-500",
        "typical_tolerance": "±0.2 mm",
    },
    {
        "name": "Foam Pattern / Lost-Foam Casting",
        "category": "casting",
        "description": "Carve or CNC-mill expanded polystyrene (EPS) patterns, embed in unbonded sand, and pour molten metal. The foam vaporizes, leaving the casting shape.",
        "suitable_for": [
            "Complex internal passages (manifolds, intake runners)",
            "Single-piece castings replacing multi-part assemblies",
            "Low-volume structural castings (brackets, housings)",
            "Prototyping before production die-cast commitment",
        ],
        "advantages": [
            "No cores needed for internal features",
            "No parting line flash",
            "Complex geometry at low tooling cost",
            "Pattern changes are cheap (re-cut foam)",
        ],
        "disadvantages": [
            "Surface finish rougher than die casting (~250 Ra μin)",
            "Dimensional control limited to ±0.5-1.0mm",
            "Only suitable for aluminum, iron, bronze (not steel easily)",
            "Foam residue can cause porosity",
        ],
        "material_options": ["A356 Aluminum", "Ductile Iron", "C95800 Bronze"],
        "typical_lead_time": "2-6 weeks",
        "cost_range_usd": "500-5000 per lot",
        "typical_tolerance": "±0.5 mm",
    },
    {
        "name": "Investment (Lost-Wax) Casting",
        "category": "casting",
        "description": "Inject wax pattern, build ceramic shell, melt out wax, pour metal. Produces investment-cast parts with excellent surface finish and thin walls.",
        "suitable_for": [
            "Turbine blades and airfoils",
            "Complex brackets with thin walls (≤1mm)",
            "Medical implants (CoCr, Ti-6Al-4V)",
            "Small-quantity precision metal parts",
            "Aesthetic hardware (hinges, latches, logos)",
        ],
        "advantages": [
            "Excellent surface finish (32-125 Ra μin)",
            "Thin walls possible (0.5-1.0mm)",
            "Very complex internal geometry via ceramic cores",
            "Near-net-shape (minimal machining)",
        ],
        "disadvantages": [
            "Pattern tooling cost ($2k-$20k)",
            "Lead time 6-12 weeks for first articles",
            "Size limitations (typically <500mm)",
            "Porosity risk requires NDT inspection",
        ],
        "material_options": ["Stainless Steel (316L, 17-4PH)", "Inconel 718", "Ti-6Al-4V", "CoCr", "Aluminum A356"],
        "typical_lead_time": "6-12 weeks",
        "cost_range_usd": "50-500 per part (production)",
        "typical_tolerance": "±0.05 mm / ±0.001 in per inch",
    },
    {
        "name": "Waterjet Cutting (Abrasive)",
        "category": "cutting",
        "description": "High-pressure water mixed with garnet abrasive cuts virtually any material up to 150mm thick with no heat-affected zone (HAZ).",
        "suitable_for": [
            "Thick plate cutting (steel, aluminum, titanium)",
            "Heat-sensitive materials (composites, rubber, plastics)",
            "Architectural metal panels and signage",
            "Prototype short-run parts from plate stock",
            "Gasket cutting from sheet material",
        ],
        "advantages": [
            "No HAZ — cold cutting process",
            "Cuts virtually any material",
            "No fixturing beyond clamping",
            "Good edge quality in most materials",
        ],
        "disadvantages": [
            "Slower than laser for thin sheet",
            "Edge taper in thick sections",
            "Striation marks visible on finish side",
            "Garnet waste disposal requirement",
        ],
        "material_options": ["Steel", "Aluminum", "Titanium", "Glass", "Ceramic", "Stone", "Composites", "Rubber"],
        "typical_lead_time": "1-5 days",
        "cost_range_usd": "50-500 per part",
        "typical_tolerance": "±0.1 mm",
    },
    {
        "name": "Wire EDM (Electrical Discharge Machining)",
        "category": "machining",
        "description": "Thin wire electrode erodes conductive material with spark discharge for ultra-precision cutting of complex profiles in hardened materials.",
        "suitable_for": [
            "Extrusion die apertures",
            "Gear profiles in hardened steel",
            "Tapered and contoured through-holes",
            "Stacked-plate components",
            "Precision stamping die inserts",
        ],
        "advantages": [
            "Extremely tight tolerances (±0.005mm)",
            "No cutting forces (zero distortion)",
            "Cuts hardened materials (HRC 60+)",
            " Burr-free finish",
        ],
        "disadvantages": [
            "Only works on electrically conductive materials",
            "Slow process (hours for complex parts)",
            "Limited to through-cuts (wire access required)",
            "Recast layer on surface may need removal",
        ],
        "material_options": ["Hardened Tool Steel", "Inconel", "Titanium", "Copper", "Tungsten Carbide"],
        "typical_lead_time": "3-10 days",
        "cost_range_usd": "100-2000 per part",
        "typical_tolerance": "±0.005 mm",
    },
    {
        "name": "RTV Silicone Tooling (Room-Temperature Vulcanization)",
        "category": "tooling",
        "description": "Pour silicone rubber around a master pattern to create a soft mold for low-volume urethane casting (5-50 parts).",
        "suitable_for": [
            "Low-volume production runs (10-100 parts)",
            "Bridge tooling before injection mold commitment",
            "Overmolding and insert molding trials",
            "Medical device prototypes for clinical trials",
            "Concept models in production-intent materials",
        ],
        "advantages": [
            "Tooling cost: $200-$2000",
            "Lead time: 1-2 weeks",
            "Can capture fine surface detail from master",
            "Parts have injection-mold-like quality",
        ],
        "disadvantages": [
            "Limited tool life (20-50 shots typical)",
            "Not suitable for high-temperature materials",
            "Silicone can tear with sharp undercuts",
            "Cast parts have lower mechanical properties than injection molded",
        ],
        "material_options": ["Rigid Urethane (Shore D 50-80)", "Flexible Urethane (Shore A 30-90)", "Clear Urethane", "Glass-filled Urethane"],
        "typical_lead_time": "1-2 weeks (tool) + 1-3 days per batch",
        "cost_range_usd": "10-100 per cast part",
        "typical_tolerance": "±0.1 mm",
    },
    {
        "name": "Electron Beam Welding (EBW)",
        "category": "joining",
        "description": "Focused electron beam in vacuum welds thick sections in a single pass with minimal distortion and no filler metal required.",
        "suitable_for": [
            "Thick-section titanium welding (>25mm)",
            "Dissimilar metal joints (copper to stainless)",
            "Hermetic seal welding (electronics, sensors)",
            "Aerospace engine component welding",
            "Nuclear fuel rod welding",
        ],
        "advantages": [
            "Deep penetration-to-width ratio (10:1+)",
            "Vacuum environment prevents oxidation",
            "Minimal heat input and distortion",
            "No filler material needed (autogenous)",
        ],
        "disadvantages": [
            "Vacuum chamber size limits part size",
            "High equipment cost",
            "Magnetic materials can deflect beam",
            "Joint preparation must be extremely precise",
        ],
        "material_options": ["Titanium", "Stainless Steel", "Inconel", "Refractory Metals", "Copper Alloys"],
        "typical_lead_time": "2-4 weeks",
        "cost_range_usd": "200-5000 per weld",
        "typical_tolerance": "±0.25 mm beam positioning",
    },
    {
        "name": "Additive Casting (3D Printed Shell + Cast Metal)",
        "category": "hybrid",
        "description": "3D print ceramic or sand shells directly, burn out binder, and pour molten metal. Combines AM freedom with casting material properties.",
        "suitable_for": [
            "Complex casting shapes impossible with traditional patterns",
            "Lattice-core metal parts",
            "Conformal cooling channels in mold inserts",
            "Small batch metal parts with internal features",
        ],
        "advantages": [
            "No pattern tooling required",
            "Internal geometry impossible with conventional casting",
            "Rapid iteration (print new shell in days)",
            "Full metal material properties in final part",
        ],
        "disadvantages": [
            "Surface finish limited by print layer resolution",
            "Shell strength can limit pour weight",
            "Requires foundry partnership",
            "Still maturing process; less predictable yields",
        ],
        "material_options": ["Aluminum A356", "Stainless Steel 316L", "Bronze C932"],
        "typical_lead_time": "1-3 weeks",
        "cost_range_usd": "100-2000 per part",
        "typical_tolerance": "±0.3 mm",
    },
    {
        "name": "Laser Powder Bed Fusion (L-PBF / DMLS / SLM)",
        "category": "additive_metal",
        "description": "Laser melts metal powder layer-by-layer in inert atmosphere to produce fully dense metal parts with complex internal geometry.",
        "suitable_for": [
            "Conformal-cooled injection mold inserts",
            "Topology-optimized aerospace brackets",
            "Medical implants with lattice structures",
            "Complex manifolds (fluid, hydraulic, gas)",
            "Heat exchangers with internal fin geometry",
        ],
        "advantages": [
            "Complex internal geometry (conformal channels, lattices)",
            "Near-full density (>99.5%)",
            "Good mechanical properties (approaching wrought for some alloys)",
            "No tooling required",
        ],
        "disadvantages": [
            "High cost per cm³ ($5-$20 for titanium)",
            "Surface roughness (Ra 5-15 μm) often needs post-machining",
            "Residual stress requires HIP or stress relief",
            "Build volume limited (typically 250-400mm cube)",
        ],
        "material_options": ["Ti-6Al-4V", "316L Stainless Steel", "Inconel 718", "AlSi10Mg", "CoCr", "Maraging Steel", "Copper (GRCop-84)"],
        "typical_lead_time": "3-10 days",
        "cost_range_usd": "200-10000 per part",
        "typical_tolerance": "±0.1 mm",
    },
]

# ---------------------------------------------------------------------------
# Category index
# ---------------------------------------------------------------------------
CATEGORY_INDEX: dict[str, list[int]] = {}
for _i, method in enumerate(METHODS_DB):
    cat = method["category"]
    CATEGORY_INDEX.setdefault(cat, []).append(_i)


def _search_methods(
    category: Optional[str] = None,
    suitable_for_keyword: Optional[str] = None,
    material: Optional[str] = None,
    max_lead_time_weeks: Optional[float] = None,
) -> list[dict]:
    """Filter methods database by search criteria."""
    results: list[dict] = []
    for method in METHODS_DB:
        if category and method["category"] != category:
            continue
        if suitable_for_keyword:
            kw_lower = suitable_for_keyword.lower()
            if not any(kw_lower in app.lower() for app in method["suitable_for"]):
                continue
        if material:
            mat_lower = material.lower()
            if not any(mat_lower in opt.lower() for opt in method["material_options"]):
                continue
        if max_lead_time_weeks:
            lead_str = method["typical_lead_time"]
            # Extract minimum weeks from lead time string
            parts = lead_str.replace("+", "-").replace(" per", "-").split("-")
            try:
                min_weeks = float(parts[0].strip().split()[0])
                if min_weeks > max_lead_time_weeks:
                    continue
            except (ValueError, IndexError):
                pass
        results.append(method)
    return results


def uncommon_methods(
    application: str,
    category: Optional[str] = None,
    material: Optional[str] = None,
    max_lead_time_weeks: Optional[float] = None,
) -> dict:
    """
    Suggest non-traditional manufacturing methods for a given application.

    Searches the database of uncommon manufacturing techniques including
    3D printed tooling, foam casting, investment casting, waterjet, wire EDM,
    RTV silicone tooling, electron beam welding, additive casting, and DMLS.

    Args:
        application: Description of what needs to be manufactured
            (e.g. "complex aluminum bracket with internal channels").
        category: Optional filter by method category:
            "tooling", "casting", "cutting", "machining", "joining",
            "hybrid", "additive_metal".
        material: Optional target material to filter methods.
        max_lead_time_weeks: Maximum acceptable lead time in weeks.

    Returns:
        Matching manufacturing methods with pros/cons, material options,
        cost ranges, and suitability assessments.
    """
    methods = _search_methods(
        category=category,
        suitable_for_keyword=application,
        material=material,
        max_lead_time_weeks=max_lead_time_weeks,
    )

    # Fallback: if keyword search yielded nothing, return all methods
    if not methods:
        methods = METHODS_DB

    all_categories = sorted(set(m["category"] for m in METHODS_DB))

    return {
        "application": application,
        "filters_applied": {
            "category": category,
            "material": material,
            "max_lead_time_weeks": max_lead_time_weeks,
        },
        "results_count": len(methods),
        "available_categories": all_categories,
        "methods": methods,
        "recommendation": (
            f"Top recommendation: {methods[0]['name']} — "
            f"typical lead time {methods[0]['typical_lead_time']}, "
            f"tolerance {methods[0]['typical_tolerance']}"
            if methods
            else "No matching methods found."
        ),
    }
