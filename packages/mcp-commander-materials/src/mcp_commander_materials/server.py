"""
mcp-commander-materials — Material selection and property lookup cartridge.

Provides engineering material search, property lookup, comparison, substitution
recommendations, compatibility checks, cost estimates, and supplier lookup
against an embedded database of common engineering materials.
"""
from __future__ import annotations

import json
import math
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

server = FastMCP("mcp-commander-materials")

# ---------------------------------------------------------------------------
# Embedded materials database
# ---------------------------------------------------------------------------
# Properties use SI units unless noted.
#   density              : kg/m³
#   yield_strength       : MPa
#   tensile_strength     : MPa
#   modulus              : GPa  (Young's modulus)
#   thermal_conductivity : W/(m·K)
#   cost_per_kg          : USD/kg  (representative bulk pricing)
#   melting_point        : °C
#   max_service_temp     : °C  (continuous, in air)
#   corrosion_resistance : 1-5 scale (5 = excellent)
#   category             : metal | polymer | ceramic | composite
#   common_forms         : list of typical stock forms
# ---------------------------------------------------------------------------

MATERIALS: dict[str, dict[str, Any]] = {
    "6061-T6 Aluminum": {
        "density": 2700,
        "yield_strength": 276,
        "tensile_strength": 310,
        "modulus": 68.9,
        "thermal_conductivity": 167,
        "cost_per_kg": 3.50,
        "melting_point": 582,
        "max_service_temp": 175,
        "corrosion_resistance": 3,
        "category": "metal",
        "common_forms": ["sheet", "plate", "bar", "tube", "extrusion"],
        "notes": "General-purpose structural alloy; good weldability and corrosion resistance.",
    },
    "7075-T6 Aluminum": {
        "density": 2810,
        "yield_strength": 503,
        "tensile_strength": 572,
        "modulus": 71.7,
        "thermal_conductivity": 130,
        "cost_per_kg": 8.00,
        "melting_point": 477,
        "max_service_temp": 150,
        "corrosion_resistance": 2,
        "category": "metal",
        "common_forms": ["plate", "bar", "sheet", "forging"],
        "notes": "High-strength alloy used in aerospace; lower corrosion resistance than 6xxx series.",
    },
    "304 Stainless Steel": {
        "density": 7900,
        "yield_strength": 215,
        "tensile_strength": 505,
        "modulus": 193,
        "thermal_conductivity": 16.2,
        "cost_per_kg": 4.00,
        "melting_point": 1450,
        "max_service_temp": 870,
        "corrosion_resistance": 5,
        "category": "metal",
        "common_forms": ["sheet", "plate", "bar", "tube", "wire"],
        "notes": "Austenitic stainless; excellent corrosion resistance and formability.",
    },
    "316 Stainless Steel": {
        "density": 8000,
        "yield_strength": 205,
        "tensile_strength": 515,
        "modulus": 193,
        "thermal_conductivity": 16.3,
        "cost_per_kg": 5.50,
        "melting_point": 1375,
        "max_service_temp": 870,
        "corrosion_resistance": 5,
        "category": "metal",
        "common_forms": ["sheet", "plate", "bar", "tube", "wire"],
        "notes": "Molybdenum-bearing austenitic stainless; superior pitting corrosion resistance.",
    },
    "4140 Alloy Steel": {
        "density": 7850,
        "yield_strength": 415,
        "tensile_strength": 655,
        "modulus": 205,
        "thermal_conductivity": 42.6,
        "cost_per_kg": 2.80,
        "melting_point": 1416,
        "max_service_temp": 500,
        "corrosion_resistance": 2,
        "category": "metal",
        "common_forms": ["bar", "plate", "tube", "forging"],
        "notes": "Chromium-molybdenum alloy steel; good hardenability and strength.",
    },
    "A36 Mild Steel": {
        "density": 7850,
        "yield_strength": 250,
        "tensile_strength": 400,
        "modulus": 200,
        "thermal_conductivity": 50,
        "cost_per_kg": 0.90,
        "melting_point": 1425,
        "max_service_temp": 400,
        "corrosion_resistance": 1,
        "category": "metal",
        "common_forms": ["plate", "bar", "angle", "channel", "beam"],
        "notes": "Common structural carbon steel; low cost but poor corrosion resistance.",
    },
    "Ti-6Al-4V Titanium": {
        "density": 4430,
        "yield_strength": 880,
        "tensile_strength": 950,
        "modulus": 114,
        "thermal_conductivity": 6.7,
        "cost_per_kg": 35.00,
        "melting_point": 1660,
        "max_service_temp": 350,
        "corrosion_resistance": 5,
        "category": "metal",
        "common_forms": ["bar", "sheet", "plate", "forging", "wire"],
        "notes": "Workhorse titanium alloy; excellent strength-to-weight and corrosion resistance.",
    },
    "Inconel 718": {
        "density": 8190,
        "yield_strength": 1035,
        "tensile_strength": 1240,
        "modulus": 200,
        "thermal_conductivity": 11.4,
        "cost_per_kg": 45.00,
        "melting_point": 1336,
        "max_service_temp": 700,
        "corrosion_resistance": 5,
        "category": "metal",
        "common_forms": ["bar", "sheet", "plate", "forging", "wire"],
        "notes": "Nickel superalloy; outstanding high-temperature strength and oxidation resistance.",
    },
    "Copper C110": {
        "density": 8960,
        "yield_strength": 70,
        "tensile_strength": 220,
        "modulus": 117,
        "thermal_conductivity": 391,
        "cost_per_kg": 9.00,
        "melting_point": 1083,
        "max_service_temp": 200,
        "corrosion_resistance": 3,
        "category": "metal",
        "common_forms": ["bar", "sheet", "tube", "wire", "plate"],
        "notes": "Electrolytic tough-pitch copper; excellent electrical and thermal conductivity.",
    },
    "Brass C260": {
        "density": 8530,
        "yield_strength": 120,
        "tensile_strength": 325,
        "modulus": 110,
        "thermal_conductivity": 120,
        "cost_per_kg": 7.00,
        "melting_point": 950,
        "max_service_temp": 200,
        "corrosion_resistance": 3,
        "category": "metal",
        "common_forms": ["bar", "sheet", "tube", "wire"],
        "notes": "Cartridge brass (70/30); good corrosion resistance and formability.",
    },
    "ABS Plastic": {
        "density": 1040,
        "yield_strength": 43,
        "tensile_strength": 45,
        "modulus": 2.3,
        "thermal_conductivity": 0.17,
        "cost_per_kg": 2.50,
        "melting_point": 105,
        "max_service_temp": 80,
        "corrosion_resistance": 4,
        "category": "polymer",
        "common_forms": ["sheet", "rod", "pellet", "filament"],
        "notes": "Tough thermoplastic; easy to machine and 3D print.",
    },
    "Nylon 6/6": {
        "density": 1140,
        "yield_strength": 55,
        "tensile_strength": 82,
        "modulus": 2.9,
        "thermal_conductivity": 0.25,
        "cost_per_kg": 5.00,
        "melting_point": 260,
        "max_service_temp": 120,
        "corrosion_resistance": 3,
        "category": "polymer",
        "common_forms": ["sheet", "rod", "tube", "pellet"],
        "notes": "Engineering nylon; good wear resistance and low friction.",
    },
    "Polycarbonate (PC)": {
        "density": 1200,
        "yield_strength": 62,
        "tensile_strength": 66,
        "modulus": 2.4,
        "thermal_conductivity": 0.20,
        "cost_per_kg": 4.00,
        "melting_point": 267,
        "max_service_temp": 115,
        "corrosion_resistance": 3,
        "category": "polymer",
        "common_forms": ["sheet", "rod", "film", "pellet"],
        "notes": "Transparent, impact-resistant thermoplastic; excellent optical clarity.",
    },
    "PEEK": {
        "density": 1310,
        "yield_strength": 91,
        "tensile_strength": 100,
        "modulus": 3.6,
        "thermal_conductivity": 0.25,
        "cost_per_kg": 120.00,
        "melting_point": 343,
        "max_service_temp": 250,
        "corrosion_resistance": 5,
        "category": "polymer",
        "common_forms": ["rod", "sheet", "pellet", "film"],
        "notes": "High-performance semi-crystalline polymer; outstanding chemical and thermal resistance.",
    },
    "PTFE (Teflon)": {
        "density": 2200,
        "yield_strength": 21,
        "tensile_strength": 28,
        "modulus": 0.5,
        "thermal_conductivity": 0.25,
        "cost_per_kg": 15.00,
        "melting_point": 327,
        "max_service_temp": 260,
        "corrosion_resistance": 5,
        "category": "polymer",
        "common_forms": ["sheet", "rod", "tube", "film"],
        "notes": "Exceptionally low friction; nearly universal chemical resistance.",
    },
    "Alumina (Al₂O₃) 99%": {
        "density": 3950,
        "yield_strength": None,
        "tensile_strength": 260,
        "modulus": 370,
        "thermal_conductivity": 30,
        "cost_per_kg": 25.00,
        "melting_point": 2072,
        "max_service_temp": 1700,
        "corrosion_resistance": 5,
        "category": "ceramic",
        "common_forms": ["rod", "tube", "plate", "substrate"],
        "notes": "High-purity alumina ceramic; excellent hardness, electrical insulation, wear resistance.",
    },
    "Silicon Carbide (SiC)": {
        "density": 3210,
        "yield_strength": None,
        "tensile_strength": 450,
        "modulus": 410,
        "thermal_conductivity": 120,
        "cost_per_kg": 40.00,
        "melting_point": 2730,
        "max_service_temp": 1600,
        "corrosion_resistance": 5,
        "category": "ceramic",
        "common_forms": ["plate", "tube", "powder"],
        "notes": "Extremely hard ceramic; high thermal conductivity and thermal shock resistance.",
    },
    "Carbon Fiber Composite (CFRP)": {
        "density": 1600,
        "yield_strength": None,
        "tensile_strength": 1500,
        "modulus": 135,
        "thermal_conductivity": 7.0,
        "cost_per_kg": 50.00,
        "melting_point": None,
        "max_service_temp": 180,
        "corrosion_resistance": 4,
        "category": "composite",
        "common_forms": ["sheet", "plate", "tube", "fabric", "prepreg"],
        "notes": "Unidirectional/pseudo-isotropic layup; exceptional specific strength and stiffness.",
    },
    "GFRP (Fiberglass) E-Glass/Epoxy": {
        "density": 2000,
        "yield_strength": None,
        "tensile_strength": 500,
        "modulus": 22,
        "thermal_conductivity": 0.4,
        "cost_per_kg": 8.00,
        "melting_point": None,
        "max_service_temp": 150,
        "corrosion_resistance": 4,
        "category": "composite",
        "common_forms": ["sheet", "plate", "rod", "fabric", "panel"],
        "notes": "Glass-fiber-reinforced epoxy; cost-effective composite with good corrosion resistance.",
    },
}

# Flat list for easier iteration
MATERIAL_NAMES: list[str] = list(MATERIALS.keys())

# Known supplier database (representative, not exhaustive)
SUPPLIERS: dict[str, list[dict[str, str]]] = {
    "metal": [
        {"name": "OnlineMetals.com", "specialty": "Small-quantity metals, cut-to-size", "url": "https://www.onlinemetals.com"},
        {"name": "McMaster-Carr", "specialty": "Broad industrial supply, fast shipping", "url": "https://www.mcmaster.com"},
        {"name": "Metal Supermarkets", "specialty": "Walk-in and online metal distributor", "url": "https://www.metalsupermarkets.com"},
        {"name": "Speedy Metals", "specialty": "Cut metals with quick turnaround", "url": "https://www.speedymetals.com"},
    ],
    "polymer": [
        {"name": "McMaster-Carr", "specialty": "Broad industrial supply, plastics included", "url": "https://www.mcmaster.com"},
        {"name": "Professional Plastics", "specialty": "Engineering plastics in sheet/rod/tube", "url": "https://www.professionalplastics.com"},
        {"name": "ePlastics", "specialty": "Retail and bulk plastic stock shapes", "url": "https://www.eplastics.com"},
    ],
    "ceramic": [
        {"name": "McMaster-Carr", "specialty": "Select ceramic stock shapes", "url": "https://www.mcmaster.com"},
        {"name": "CoorsTek", "specialty": "Technical ceramics and custom components", "url": "https://www.coorstek.com"},
        {"name": "Ceramic Substrates & Components", "specialty": "Alumina and advanced ceramics", "url": "https://www.ceramicssubstrates.com"},
    ],
    "composite": [
        {"name": "Fibre Glast", "specialty": "Carbon fiber, fiberglass, epoxy, tools", "url": "https://www.fibreglast.com"},
        {"name": "McMaster-Carr", "specialty": "Select composite panels and sheets", "url": "https://www.mcmaster.com"},
        {"name": "AeroComposit", "specialty": "Aerospace-grade prepreg and fabrics", "url": "https://www.aerocomposit.com"},
    ],
}


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _fuzzy_match(query: str, name: str) -> bool:
    """Return True if *query* tokens all appear (case-insensitive) in *name*."""
    q_tokens = query.lower().split()
    n_lower = name.lower()
    return all(tok in n_lower for tok in q_tokens)


def _prop_ranges_met(
    mat: dict[str, Any],
    min_density: Optional[float] = None,
    max_density: Optional[float] = None,
    min_yield: Optional[float] = None,
    max_yield: Optional[float] = None,
    min_tensile: Optional[float] = None,
    max_tensile: Optional[float] = None,
    min_modulus: Optional[float] = None,
    max_modulus: Optional[float] = None,
    min_thermal: Optional[float] = None,
    max_thermal: Optional[float] = None,
    min_cost: Optional[float] = None,
    max_cost: Optional[float] = None,
) -> bool:
    """Check whether a material dictionary satisfies all supplied range filters."""
    checks = [
        (min_density, mat["density"] >= min_density if min_density else True),
        (max_density, mat["density"] <= max_density if max_density else True),
        (min_yield, (mat["yield_strength"] or 0) >= min_yield if min_yield else True),
        (max_yield, (mat["yield_strength"] or float("inf")) <= max_yield if max_yield else True),
        (min_tensile, mat["tensile_strength"] >= min_tensile if min_tensile else True),
        (max_tensile, mat["tensile_strength"] <= max_tensile if max_tensile else True),
        (min_modulus, mat["modulus"] >= min_modulus if min_modulus else True),
        (max_modulus, mat["modulus"] <= max_modulus if max_modulus else True),
        (min_thermal, mat["thermal_conductivity"] >= min_thermal if min_thermal else True),
        (max_thermal, mat["thermal_conductivity"] <= max_thermal if max_thermal else True),
        (min_cost, mat["cost_per_kg"] >= min_cost if min_cost else True),
        (max_cost, mat["cost_per_kg"] <= max_cost if max_cost else True),
    ]
    return all(passed for _, passed in checks)


def _material_summary(name: str, mat: dict[str, Any]) -> dict[str, Any]:
    """Return a compact summary dict for a material."""
    return {
        "name": name,
        "category": mat["category"],
        "density_kg_m3": mat["density"],
        "yield_strength_MPa": mat["yield_strength"],
        "tensile_strength_MPa": mat["tensile_strength"],
        "modulus_GPa": mat["modulus"],
        "thermal_conductivity_W_mK": mat["thermal_conductivity"],
        "cost_per_kg_USD": mat["cost_per_kg"],
        "melting_point_C": mat["melting_point"],
        "max_service_temp_C": mat["max_service_temp"],
        "corrosion_resistance": mat["corrosion_resistance"],
        "common_forms": mat["common_forms"],
    }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@server.tool()
async def search_materials(
    query: Optional[str] = None,
    category: Optional[str] = None,
    min_density: Optional[float] = None,
    max_density: Optional[float] = None,
    min_yield_strength: Optional[float] = None,
    max_yield_strength: Optional[float] = None,
    min_tensile_strength: Optional[float] = None,
    max_tensile_strength: Optional[float] = None,
    min_modulus: Optional[float] = None,
    max_modulus: Optional[float] = None,
    min_thermal_conductivity: Optional[float] = None,
    max_thermal_conductivity: Optional[float] = None,
    min_cost_per_kg: Optional[float] = None,
    max_cost_per_kg: Optional[float] = None,
) -> str:
    """
    Search the embedded engineering materials database.

    You can search by free-text *query* (matched against the material name),
    by *category* (metal, polymer, ceramic, composite), or by numeric property
    ranges.  Multiple filters are ANDed together.

    Returns a JSON array of matching material summaries sorted by name.
    """
    valid_categories = {"metal", "polymer", "ceramic", "composite"}
    if category and category.lower() not in valid_categories:
        return json.dumps({"error": f"Invalid category '{category}'. Must be one of: {', '.join(sorted(valid_categories))}"}, indent=2)

    results: list[dict[str, Any]] = []
    for name, mat in MATERIALS.items():
        # Text filter
        if query and not _fuzzy_match(query, name):
            continue
        # Category filter
        if category and mat["category"] != category.lower():
            continue
        # Numeric range filters
        if not _prop_ranges_met(
            mat,
            min_density=min_density,
            max_density=max_density,
            min_yield=min_yield_strength,
            max_yield=max_yield_strength,
            min_tensile=min_tensile_strength,
            max_tensile=max_tensile_strength,
            min_modulus=min_modulus,
            max_modulus=max_modulus,
            min_thermal=min_thermal_conductivity,
            max_thermal=max_thermal_conductivity,
            min_cost=min_cost_per_kg,
            max_cost=max_cost_per_kg,
        ):
            continue
        results.append(_material_summary(name, mat))

    results.sort(key=lambda r: r["name"])
    return json.dumps({"count": len(results), "materials": results}, indent=2)


@server.tool()
async def get_material_properties(material_name: str) -> str:
    """
    Get detailed mechanical, thermal, and chemical properties for a specific material.

    Provide the *material_name* exactly as listed (fuzzy matching is supported).
    Returns a JSON object with all stored properties plus notes.
    """
    # Exact match first
    if material_name in MATERIALS:
        mat = MATERIALS[material_name]
        return json.dumps({"name": material_name, **mat}, indent=2)

    # Fuzzy match
    matches = [n for n in MATERIAL_NAMES if _fuzzy_match(material_name, n)]
    if len(matches) == 1:
        mat = MATERIALS[matches[0]]
        return json.dumps({"name": matches[0], **mat}, indent=2)
    elif len(matches) > 1:
        return json.dumps({
            "error": f"Ambiguous material name '{material_name}'. Did you mean one of: {matches}?",
            "candidates": matches,
        }, indent=2)

    return json.dumps({
        "error": f"Material '{material_name}' not found in the database.",
        "available_materials": MATERIAL_NAMES,
    }, indent=2)


@server.tool()
async def compare_materials(material_names: list[str]) -> str:
    """
    Compare properties of multiple materials side by side.

    Pass a JSON-style list of material name strings.  Returns a table-oriented
    JSON object where each material is a key and the value is its full property
    set, making it easy for LLMs to contrast trade-offs.
    """
    comparison: dict[str, dict[str, Any]] = {}
    not_found: list[str] = []

    for name in material_names:
        # Exact match
        if name in MATERIALS:
            comparison[name] = MATERIALS[name]
            continue
        # Fuzzy match
        fuzzy = [n for n in MATERIAL_NAMES if _fuzzy_match(name, n)]
        if len(fuzzy) == 1:
            comparison[fuzzy[0]] = MATERIALS[fuzzy[0]]
        elif len(fuzzy) > 1:
            not_found.append(f"'{name}' is ambiguous — candidates: {fuzzy}")
        else:
            not_found.append(f"'{name}' not found")

    result: dict[str, Any] = {"comparison": comparison}
    if not_found:
        result["issues"] = not_found

    return json.dumps(result, indent=2)


@server.tool()
async def recommend_substitution(
    original_material: str,
    min_yield_strength: Optional[float] = None,
    max_density: Optional[float] = None,
    max_cost_per_kg: Optional[float] = None,
    min_corrosion_resistance: Optional[int] = None,
    prefer_category: Optional[str] = None,
) -> str:
    """
    Suggest material substitutions based on functional requirements and constraints.

    Given an *original_material* to replace, optionally specify minimum yield
    strength, maximum density, maximum cost, minimum corrosion resistance, or
    a preferred category.  Returns ranked candidates with a score indicating
    how closely they match requirements.
    """
    # Resolve original material
    if original_material not in MATERIALS:
        fuzzy = [n for n in MATERIAL_NAMES if _fuzzy_match(original_material, n)]
        if len(fuzzy) != 1:
            return json.dumps({"error": f"Cannot resolve original material '{original_material}'."}, indent=2)
        original_material = fuzzy[0]

    orig = MATERIALS[original_material]

    # Default constraints from original if not specified
    eff_min_yield = min_yield_strength if min_yield_strength is not None else (orig["yield_strength"] or 0) * 0.8
    eff_max_density = max_density if max_density is not None else orig["density"] * 1.2
    eff_max_cost = max_cost_per_kg if max_cost_per_kg is not None else orig["cost_per_kg"] * 1.5
    eff_min_corr = min_corrosion_resistance if min_corrosion_resistance is not None else 1

    candidates: list[dict[str, Any]] = []
    for name, mat in MATERIALS.items():
        if name == original_material:
            continue
        if prefer_category and mat["category"] != prefer_category.lower():
            continue

        ys = mat["yield_strength"] or 0
        if ys < eff_min_yield:
            continue
        if mat["density"] > eff_max_density:
            continue
        if mat["cost_per_kg"] > eff_max_cost:
            continue
        if mat["corrosion_resistance"] < eff_min_corr:
            continue

        # Simple scoring: lower is better for density and cost, higher is better for strength
        density_ratio = mat["density"] / orig["density"]
        cost_ratio = mat["cost_per_kg"] / orig["cost_per_kg"]
        strength_ratio = ys / (orig["yield_strength"] or 1)
        # Composite score (lower = better candidate): penalise heavy/expensive, reward strong
        score = (density_ratio * 0.3 + cost_ratio * 0.3) / max(strength_ratio, 0.1)

        candidates.append({
            "name": name,
            "category": mat["category"],
            "density_kg_m3": mat["density"],
            "yield_strength_MPa": mat["yield_strength"],
            "tensile_strength_MPa": mat["tensile_strength"],
            "modulus_GPa": mat["modulus"],
            "cost_per_kg_USD": mat["cost_per_kg"],
            "corrosion_resistance": mat["corrosion_resistance"],
            "score": round(score, 3),
        })

    candidates.sort(key=lambda c: c["score"])
    return json.dumps({
        "original_material": original_material,
        "constraints_used": {
            "min_yield_strength_MPa": eff_min_yield,
            "max_density_kg_m3": eff_max_density,
            "max_cost_per_kg_USD": eff_max_cost,
            "min_corrosion_resistance": eff_min_corr,
            "prefer_category": prefer_category,
        },
        "candidates": candidates,
    }, indent=2)


@server.tool()
async def check_compatibility(
    material_name: str,
    environment: str,
) -> str:
    """
    Check material compatibility for a specific environment or process.

    *environment* should describe the operating conditions, e.g. "saltwater",
    "high temperature 500C", "acidic pH 2", "UV exposure outdoor",
    "food contact", "cryogenic -196C", etc.

    Returns a JSON object with a compatibility rating, explanation, and
    any caveats.
    """
    # Resolve material name
    if material_name not in MATERIALS:
        fuzzy = [n for n in MATERIAL_NAMES if _fuzzy_match(material_name, n)]
        if len(fuzzy) != 1:
            return json.dumps({"error": f"Cannot resolve material '{material_name}'."}, indent=2)
        material_name = fuzzy[0]

    mat = MATERIALS[material_name]
    env_lower = environment.lower()

    results: list[dict[str, str]] = []

    # --- Temperature checks ---
    if any(kw in env_lower for kw in ["high temp", "high temperature", "elevated temp"]):
        # Try to extract a temperature value
        import re
        temp_match = re.search(r"(\d+)\s*[°c]?c", env_lower)
        temp = int(temp_match.group(1)) if temp_match else 300
        max_t = mat["max_service_temp"]
        if temp <= max_t:
            results.append({
                "factor": "High temperature",
                "rating": "COMPATIBLE",
                "detail": f"Max service temp {max_t}°C exceeds required {temp}°C.",
            })
        else:
            results.append({
                "factor": "High temperature",
                "rating": "NOT RECOMMENDED",
                "detail": f"Max service temp {max_t}°C is below required {temp}°C. Risk of strength loss or creep.",
            })

    if "cryogenic" in env_lower or "cryo" in env_lower or "-196" in env_lower or "liquid nitrogen" in env_lower or "ln2" in env_lower:
        # FCC metals, Ti alloys, some polymers (PTFE, PEEK) handle cryo well
        cryo_good = {"304 Stainless Steel", "316 Stainless Steel", "Ti-6Al-4V Titanium",
                     "Copper C110", "Inconel 718", "Alumina (Al₂O₃) 99%", "Silicon Carbide (SiC)"}
        cryo_caution = {"A36 Mild Steel", "4140 Alloy Steel", "Nylon 6/6", "ABS Plastic",
                        "Polycarbonate (PC)", "GFRP (Fiberglass) E-Glass/Epoxy"}
        if material_name in cryo_good:
            results.append({"factor": "Cryogenic", "rating": "COMPATIBLE",
                            "detail": "Material retains ductility and strength at cryogenic temperatures."})
        elif material_name in cryo_caution:
            results.append({"factor": "Cryogenic", "rating": "CAUTION",
                            "detail": "Material may become brittle at cryogenic temperatures. Verify with testing."})
        else:
            results.append({"factor": "Cryogenic", "rating": "REVIEW NEEDED",
                            "detail": "Insufficient data; evaluate low-temperature ductility for this material."})

    # --- Corrosion checks ---
    if any(kw in env_lower for kw in ["saltwater", "salt water", "marine", "seawater", "sea water"]):
        cr = mat["corrosion_resistance"]
        if cr >= 4:
            results.append({"factor": "Saltwater / Marine", "rating": "COMPATIBLE",
                            "detail": f"Corrosion resistance rating {cr}/5 — suitable for marine environments."})
        elif cr == 3:
            results.append({"factor": "Saltwater / Marine", "rating": "CAUTION",
                            "detail": "Moderate corrosion resistance. May require protective coating or periodic maintenance."})
        else:
            results.append({"factor": "Saltwater / Marine", "rating": "NOT RECOMMENDED",
                            "detail": f"Low corrosion resistance ({cr}/5). Rapid corrosion expected without protection."})

    if any(kw in env_lower for kw in ["acid", "acidic", "chemical", "corrosive"]):
        cr = mat["corrosion_resistance"]
        chem_resistant = {"PTFE (Teflon)", "PEEK", "316 Stainless Steel", "304 Stainless Steel",
                          "Inconel 718", "Alumina (Al₂O₃) 99%", "Silicon Carbide (SiC)"}
        if material_name in chem_resistant:
            results.append({"factor": "Acidic / Chemical", "rating": "COMPATIBLE",
                            "detail": "Material has good chemical resistance. Verify compatibility with specific chemicals."})
        elif cr >= 3:
            results.append({"factor": "Acidic / Chemical", "rating": "CAUTION",
                            "detail": "Moderate chemical resistance. Suitability depends on specific chemicals and concentrations."})
        else:
            results.append({"factor": "Acidic / Chemical", "rating": "NOT RECOMMENDED",
                            "detail": "Material has poor chemical resistance. Significant degradation expected."})

    # --- UV / Outdoor checks ---
    if any(kw in env_lower for kw in ["uv", "ultraviolet", "outdoor", "sunlight", "weather"]):
        uv_good = {"304 Stainless Steel", "316 Stainless Steel", "4140 Alloy Steel", "Ti-6Al-4V Titanium",
                    "Inconel 718", "Alumina (Al₂O₃) 99%", "Silicon Carbide (SiC)",
                    "Carbon Fiber Composite (CFRP)", "6061-T6 Aluminum", "7075-T6 Aluminum"}
        uv_bad = {"ABS Plastic", "Polycarbonate (PC)", "Nylon 6/6", "PTFE (Teflon)"}
        if material_name in uv_good:
            results.append({"factor": "UV / Outdoor", "rating": "COMPATIBLE",
                            "detail": "Material is resistant to UV degradation."})
        elif material_name in uv_bad:
            results.append({"factor": "UV / Outdoor", "rating": "CAUTION",
                            "detail": "Polymer may degrade under prolonged UV exposure. Consider UV-stabilized grade or coating."})
        else:
            results.append({"factor": "UV / Outdoor", "rating": "REVIEW NEEDED",
                            "detail": "Evaluate UV stability for this material."})

    # --- Food contact ---
    if "food" in env_lower or "fda" in env_lower or "potable" in env_lower or "drinking" in env_lower:
        food_safe = {"304 Stainless Steel", "316 Stainless Steel", "PTFE (Teflon)",
                      "Polycarbonate (PC)", "Nylon 6/6", "PEEK"}
        if material_name in food_safe:
            results.append({"factor": "Food contact", "rating": "COMPATIBLE",
                            "detail": "Generally regarded as food-safe in standard grades. Verify FDA compliance for specific grade."})
        else:
            results.append({"factor": "Food contact", "rating": "NOT RECOMMENDED",
                            "detail": "Not typically used in food-contact applications."})

    # --- Wear / Abrasion ---
    if any(kw in env_lower for kw in ["wear", "abrasion", "abrasive", "friction", "sliding"]):
        wear_good = {"Silicon Carbide (SiC)", "Alumina (Al₂O₃) 99%", "Ti-6Al-4V Titanium",
                      "4140 Alloy Steel", "Nylon 6/6", "PTFE (Teflon)", "Inconel 718"}
        if material_name in wear_good:
            results.append({"factor": "Wear / Abrasion", "rating": "COMPATIBLE",
                            "detail": "Material has good wear resistance for this environment."})
        else:
            results.append({"factor": "Wear / Abrasion", "rating": "CAUTION",
                            "detail": "Wear resistance may be limited. Consider surface treatment or harder material."})

    # --- Electrical conductivity ---
    if any(kw in env_lower for kw in ["electrical", "conductive", "insulat", "dielectric"]):
        if mat["category"] in ("polymer", "ceramic"):
            results.append({"factor": "Electrical", "rating": "COMPATIBLE",
                            "detail": "Material is electrically insulating."})
        elif mat["category"] == "composite":
            results.append({"factor": "Electrical", "rating": "CAUTION",
                            "detail": "Composites may have variable electrical properties depending on layup."})
        else:
            results.append({"factor": "Electrical", "rating": "CONDUCTIVE",
                            "detail": "Material is electrically conductive. Consider insulation if required."})

    # Fallback when no environment factors matched
    if not results:
        results.append({
            "factor": "General",
            "rating": "REVIEW NEEDED",
            "detail": f"Could not parse specific environment factors from '{environment}'. Material properties returned for manual review.",
        })

    # Determine overall rating
    ratings_order = ["NOT RECOMMENDED", "CAUTION", "REVIEW NEEDED", "COMPATIBLE"]
    worst = "COMPATIBLE"
    for r in results:
        if ratings_order.index(r["rating"]) < ratings_order.index(worst):
            worst = r["rating"]

    return json.dumps({
        "material": material_name,
        "environment": environment,
        "overall_rating": worst,
        "checks": results,
    }, indent=2)


@server.tool()
async def get_cost_estimate(
    material_name: str,
    quantity_kg: Optional[float] = None,
    quantity_volume_m3: Optional[float] = None,
) -> str:
    """
    Get relative cost estimate for a material per unit weight or volume.

    Specify either *quantity_kg* or *quantity_volume_m3* (or neither for just
    the per-unit rate).  Returns per-kg and per-liter pricing plus the total
    estimate if a quantity was given.

    NOTE: Prices are representative bulk estimates and do not reflect real-time
    market prices, shipping, machining, or volume discounts.
    """
    if material_name not in MATERIALS:
        fuzzy = [n for n in MATERIAL_NAMES if _fuzzy_match(material_name, n)]
        if len(fuzzy) != 1:
            return json.dumps({"error": f"Cannot resolve material '{material_name}'."}, indent=2)
        material_name = fuzzy[0]

    mat = MATERIALS[material_name]
    cost_kg = mat["cost_per_kg"]
    density = mat["density"]
    cost_per_liter = cost_kg * (density / 1000.0)  # 1 L = 0.001 m³

    result: dict[str, Any] = {
        "material": material_name,
        "category": mat["category"],
        "density_kg_m3": density,
        "cost_per_kg_USD": cost_kg,
        "cost_per_liter_USD": round(cost_per_liter, 2),
        "cost_per_in3_USD": round(cost_kg * (density / 1e6) * 16387.064, 4),  # 1 in³ = 1.6387e-5 m³
    }

    if quantity_kg is not None:
        result["quantity_kg"] = quantity_kg
        result["quantity_volume_m3"] = round(quantity_kg / density, 6)
        result["total_cost_USD"] = round(quantity_kg * cost_kg, 2)

    if quantity_volume_m3 is not None:
        mass = quantity_volume_m3 * density
        result["quantity_volume_m3"] = quantity_volume_m3
        result["quantity_kg"] = round(mass, 4)
        result["total_cost_USD"] = round(mass * cost_kg, 2)

    result["disclaimer"] = (
        "Prices are representative bulk estimates for material stock only. "
        "Actual costs vary by supplier, quantity, form, finish, and region. "
        "This estimate does not include machining, shipping, taxes, or volume discounts."
    )

    return json.dumps(result, indent=2)


@server.tool()
async def lookup_supplier(
    material_name: str,
    form: Optional[str] = None,
) -> str:
    """
    Look up potential suppliers for a given material and form.

    *form* is optional and can be a stock shape like "sheet", "bar", "tube",
    "plate", "rod", etc.  Results include the supplier name, specialty, URL,
    and whether the requested form is commonly available for that material.

    NOTE: This is a representative supplier list, not a live availability check.
    """
    if material_name not in MATERIALS:
        fuzzy = [n for n in MATERIAL_NAMES if _fuzzy_match(material_name, n)]
        if len(fuzzy) != 1:
            return json.dumps({"error": f"Cannot resolve material '{material_name}'."}, indent=2)
        material_name = fuzzy[0]

    mat = MATERIALS[material_name]
    category = mat["category"]
    common_forms = mat["common_forms"]

    # Determine if the requested form is typical
    form_available = True
    form_note = ""
    if form:
        form_lower = form.lower()
        if form_lower in common_forms:
            form_note = f"'{form}' is a common stock form for {material_name}."
        else:
            form_available = False
            form_note = f"'{form}' is not a typical stock form for {material_name}. Available forms: {common_forms}"

    # Get suppliers for the category
    suppliers = SUPPLIERS.get(category, [])

    supplier_results = []
    for sup in suppliers:
        entry = {
            "name": sup["name"],
            "specialty": sup["specialty"],
            "url": sup["url"],
        }
        if form:
            entry["likely_has_form"] = form_available
        supplier_results.append(entry)

    result: dict[str, Any] = {
        "material": material_name,
        "category": category,
        "common_forms": common_forms,
        "suppliers": supplier_results,
    }
    if form:
        result["requested_form"] = form
        result["form_availability_note"] = form_note

    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server using stdio transport."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
