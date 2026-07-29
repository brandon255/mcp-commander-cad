"""
mcp-commander-quoting MCP server.

Exposes material cost estimation, machining time calculation,
quote generation, process comparison, lead time estimation,
and machinability lookup tools through the Model Context Protocol.
"""

import json
import math
import mcp.server.fastmcp
from typing import Optional

server = mcp.server.fastmcp.FastMCP("mcp-commander-quoting")

# ── Reference data (local-first, no cloud dependency) ──

MATERIAL_COSTS_USD_PER_KG = {
    "6061-T6 Aluminum": 4.50,
    "304 Stainless Steel": 11.00,
    "316 Stainless Steel": 13.50,
    "AISI 4140 Steel": 7.50,
    "Titanium Ti-6Al-4V": 65.00,
    "Inconel 718": 110.00,
    "ABS": 3.20,
    "Nylon 6/6": 5.50,
    "PEEK": 165.00,
    "Carbon Fiber Composite": 95.00,
}

MACHINABILITY_RATINGS = {
    "6061-T6 Aluminum": {"rating": "A", "surface_speed_m_min": 300, "feed_mm_rev": 0.15, "notes": "Excellent machinability"},
    "304 Stainless Steel": {"rating": "C", "surface_speed_m_min": 120, "feed_mm_rev": 0.10, "notes": "Work hardens — use sharp tools, lower feeds"},
    "316 Stainless Steel": {"rating": "C", "surface_speed_m_min": 110, "feed_mm_rev": 0.10, "notes": "Similar to 304, tougher on tools"},
    "AISI 4140 Steel": {"rating": "B", "surface_speed_m_min": 150, "feed_mm_rev": 0.12, "notes": "Pre-hardened: reduce speed 30%"},
    "Titanium Ti-6Al-4V": {"rating": "D", "surface_speed_m_min": 50, "feed_mm_rev": 0.08, "notes": "Low thermal conductivity — flood coolant mandatory"},
    "Inconel 718": {"rating": "E", "surface_speed_m_min": 25, "feed_mm_rev": 0.06, "notes": "Extreme tool wear — ceramic inserts recommended"},
    "ABS": {"rating": "A", "surface_speed_m_min": 400, "feed_mm_rev": 0.20, "notes": "Use sharp tools, avoid heat buildup"},
    "Nylon 6/6": {"rating": "A", "surface_speed_m_min": 350, "feed_mm_rev": 0.18, "notes": "Use diamond tooling for best finish"},
    "PEEK": {"rating": "B", "surface_speed_m_min": 200, "feed_mm_rev": 0.12, "notes": "High temperature polymer — use coolant"},
}

PROCESS_BASE_RATES_USD_PER_HR = {
    "cnc_3axis": 65,
    "cnc_4axis": 85,
    "cnc_5axis": 120,
    "turning": 55,
    "edm_wire": 90,
    "edm_sink": 95,
    "sheet_metal_laser": 75,
    "sheet_metal_bend": 45,
    "3dp_fdm": 8,
    "3dp_sla": 35,
    "3dp_sls": 55,
    "investment_casting": 110,
    "sand_casting": 45,
}


# ── MCP Tools ──

@server.tool()
def estimate_material_cost(
    material_name: str,
    volume_cm3: float,
    waste_factor: float = 1.5,
    currency: str = "USD",
) -> str:
    """Calculate material cost based on part volume and material properties."""
    cost_per_kg = MATERIAL_COSTS_USD_PER_KG.get(material_name)
    if not cost_per_kg:
        available = list(MATERIAL_COSTS_USD_PER_KG.keys())
        return json.dumps({"error": f"Unknown material '{material_name}'.", "available": available}, indent=2)

    density = _get_density(material_name)
    if not density:
        return json.dumps({"error": f"Density data not available for '{material_name}'."}, indent=2)

    mass_kg = (volume_cm3 / 1e6) * density * waste_factor
    cost = mass_kg * cost_per_kg

    return json.dumps({
        "material": material_name,
        "volume_cm3": volume_cm3,
        "density_kg_m3": density,
        "mass_kg": round(mass_kg, 3),
        "cost_per_kg": cost_per_kg,
        "waste_factor": waste_factor,
        "total_material_cost": round(cost, 2),
        "currency": currency,
    }, indent=2)


@server.tool()
def estimate_machining_time(
    volume_cm3: float,
    complexity: str = "medium",
    material_name: Optional[str] = None,
    process: str = "cnc_3axis",
) -> str:
    """Estimate CNC machining time based on part complexity and volume."""
    complexity_factors = {"simple": 1.0, "medium": 2.5, "complex": 5.0, "highly_complex": 10.0}
    factor = complexity_factors.get(complexity.lower(), 2.5)

    # Base removal rate: 100 cm3/min for a 3-axis CNC (simplified model)
    base_rate = 100.0

    # Adjust for material machinability
    if material_name:
        mach = MACHINABILITY_RATINGS.get(material_name)
        if mach:
            mach_factors = {"A": 1.0, "B": 1.3, "C": 1.8, "D": 2.5, "E": 4.0}
            factor *= mach_factors.get(mach["rating"], 1.0)

    # Adjust for process type
    process_factors = {
        "cnc_3axis": 1.0, "cnc_4axis": 1.4, "cnc_5axis": 2.0,
        "turning": 0.8, "edm_wire": 5.0, "edm_sink": 4.0,
    }
    factor *= process_factors.get(process.lower(), 1.0)

    machining_time_min = (volume_cm3 / base_rate) * factor
    setup_time_min = 30 if complexity in ("complex", "highly_complex") else 15
    total_time_hr = (machining_time_min + setup_time_min) / 60

    return json.dumps({
        "volume_cm3": volume_cm3,
        "complexity": complexity,
        "material": material_name or "unknown",
        "process": process,
        "machining_time_min": round(machining_time_min, 1),
        "setup_time_min": setup_time_min,
        "total_time_hr": round(total_time_hr, 2),
    }, indent=2)


@server.tool()
def generate_quote(
    material_name: str,
    volume_cm3: float,
    complexity: str = "medium",
    quantity: int = 1,
    process: str = "cnc_3axis",
) -> str:
    """Generate a manufacturing cost quote with full breakdown."""
    # Material cost
    mat_cost_result = estimate_material_cost(material_name, volume_cm3)
    mat_cost_data = json.loads(mat_cost_result)
    if "error" in mat_cost_data:
        return mat_cost_result
    material_cost = mat_cost_data["total_material_cost"]

    # Machining cost
    time_result = estimate_machining_time(volume_cm3, complexity, material_name, process)
    time_data = json.loads(time_result)
    total_hours = time_data["total_time_hr"]

    rate = PROCESS_BASE_RATES_USD_PER_HR.get(process.lower(), 65)
    labor_cost = total_hours * rate

    # Overhead (typically 30-50% of labor)
    overhead_rate = 0.4
    overhead = labor_cost * overhead_rate

    # Quality inspection (per-part)
    inspection = 25.0 if complexity in ("complex", "highly_complex") else 10.0

    # Quantity discount
    discount_factor = 1.0
    if quantity >= 100:
        discount_factor = 0.75
    elif quantity >= 50:
        discount_factor = 0.82
    elif quantity >= 10:
        discount_factor = 0.90

    unit_cost = material_cost + labor_cost + overhead + inspection
    total_cost = unit_cost * quantity * discount_factor

    return json.dumps({
        "material": material_name,
        "volume_cm3": volume_cm3,
        "complexity": complexity,
        "process": process,
        "quantity": quantity,
        "breakdown_per_unit": {
            "material": round(material_cost, 2),
            "labor": round(labor_cost, 2),
            "overhead": round(overhead, 2),
            "inspection": round(inspection, 2),
            "unit_total": round(unit_cost, 2),
        },
        "machining_time_hr": total_hours,
        "quantity_discount": round(discount_factor * 100, 1),
        "total_cost": round(total_cost, 2),
        "cost_per_unit": round(total_cost / quantity, 2),
        "currency": "USD",
        "validity_days": 30,
    }, indent=2)


@server.tool()
def compare_processes(
    material_name: str,
    volume_cm3: float,
    quantity: int = 1,
) -> str:
    """Compare cost of different manufacturing processes."""
    comparisons = []

    for process_name, rate in PROCESS_BASE_RATES_USD_PER_HR.items():
        try:
            quote = generate_quote(material_name, volume_cm3, "medium", quantity, process_name)
            data = json.loads(quote)
            if "error" not in data:
                comparisons.append({
                    "process": process_name,
                    "cost_per_unit": data["cost_per_unit"],
                    "total_cost": data["total_cost"],
                    "time_hr": data["machining_time_hr"],
                })
        except Exception:
            continue

    comparisons.sort(key=lambda x: x["cost_per_unit"])

    return json.dumps({
        "material": material_name,
        "volume_cm3": volume_cm3,
        "quantity": quantity,
        "comparison": comparisons,
        "recommendation": comparisons[0]["process"] if comparisons else "none",
    }, indent=2)


@server.tool()
def calculate_lead_time(
    complexity: str = "medium",
    process: str = "cnc_3axis",
    quantity: int = 1,
) -> str:
    """Estimate manufacturing lead time based on part complexity and process."""
    base_days = {"simple": 5, "medium": 10, "complex": 18, "highly_complex": 25}
    process_multipliers = {
        "cnc_3axis": 1.0, "cnc_4axis": 1.2, "cnc_5axis": 1.5,
        "turning": 0.8, "edm_wire": 2.0, "edm_sink": 1.8,
        "investment_casting": 2.5, "sand_casting": 2.0,
        "sheet_metal_laser": 0.7, "sheet_metal_bend": 0.6,
        "3dp_fdm": 0.5, "3dp_sla": 0.8, "3dp_sls": 1.0,
    }

    base = base_days.get(complexity.lower(), 10)
    mult = process_multipliers.get(process.lower(), 1.0)

    # Quantity scaling
    if quantity <= 5:
        qty_mult = 1.0
    elif quantity <= 20:
        qty_mult = 1.5
    elif quantity <= 100:
        qty_mult = 2.5
    else:
        qty_mult = 3.5 + (quantity - 100) * 0.01

    lead_days = math.ceil(base * mult * qty_mult)

    return json.dumps({
        "complexity": complexity,
        "process": process,
        "quantity": quantity,
        "estimated_lead_time_days": lead_days,
        "breakdown": {
            "base_days": base,
            "process_multiplier": mult,
            "quantity_multiplier": round(qty_mult, 2),
        },
    }, indent=2)


@server.tool()
def lookup_machinability(material_name: str) -> str:
    """Look up machinability ratings and recommended parameters for a material."""
    data = MACHINABILITY_RATINGS.get(material_name)
    if not data:
        available = list(MACHINABILITY_RATINGS.keys())
        return json.dumps({"error": f"No machinability data for '{material_name}'.", "available": available}, indent=2)

    return json.dumps({
        "material": material_name,
        "machinability_rating": data["rating"],
        "recommended_surface_speed_m_min": data["surface_speed_m_min"],
        "recommended_feed_mm_rev": data["feed_mm_rev"],
        "notes": data["notes"],
    }, indent=2)


def _get_density(material_name: str) -> Optional[float]:
    """Internal helper to get material density."""
    density_map = {
        "6061-T6 Aluminum": 2700,
        "304 Stainless Steel": 8000,
        "316 Stainless Steel": 8000,
        "AISI 4140 Steel": 7850,
        "Titanium Ti-6Al-4V": 4430,
        "Inconel 718": 8190,
        "ABS": 1040,
        "Nylon 6/6": 1140,
        "PEEK": 1320,
        "Carbon Fiber Composite": 1600,
    }
    return density_map.get(material_name)


def main():
    """Start the mcp-commander-quoting MCP server."""
    server.run()


if __name__ == "__main__":
    main()
