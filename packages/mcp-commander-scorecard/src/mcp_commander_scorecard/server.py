"""
mcp-commander-scorecard MCP server.

Exposes scorecard creation, alternative scoring, comparison, and
export tools through the Model Context Protocol.
"""

import json
import uuid
import datetime
import mcp.server.fastmcp
from typing import Optional

server = mcp.server.fastmcp.FastMCP("mcp-commander-scorecard")

# ── Local scorecard store ──
SCORECARD_STORE = {}

# ── Common evaluation criteria presets ──
CRITERIA_PRESETS = {
    "structural_bracket": {
        "criteria": [
            {"name": "strength", "weight": 0.25, "description": "Load-bearing capacity"},
            {"name": "weight", "weight": 0.20, "description": "Mass optimization"},
            {"name": "cost", "weight": 0.20, "description": "Manufacturing cost"},
            {"name": "manufacturability", "weight": 0.15, "description": "Ease of production"},
            {"name": "corrosion_resistance", "weight": 0.10, "description": "Environmental durability"},
            {"name": "lead_time", "weight": 0.10, "description": "Time to production"},
        ],
    },
    "enclosure": {
        "criteria": [
            {"name": "protection", "weight": 0.25, "description": "IP rating / environmental seal"},
            {"name": "cost", "weight": 0.20, "description": "Unit cost at target volume"},
            {"name": "aesthetics", "weight": 0.15, "description": "Visual finish quality"},
            {"name": "assembly", "weight": 0.15, "description": "Ease of assembly/disassembly"},
            {"name": "tooling_cost", "weight": 0.15, "description": "Initial tooling investment"},
            {"name": "emi_shielding", "weight": 0.10, "description": "Electromagnetic interference blocking"},
        ],
    },
    "rotating_shaft": {
        "criteria": [
            {"name": "torsional_strength", "weight": 0.25, "description": "Torque capacity"},
            {"name": "fatigue_life", "weight": 0.20, "description": "Cyclic loading endurance"},
            {"name": "surface_finish", "weight": 0.15, "description": "Bearing interface quality"},
            {"name": "cost", "weight": 0.15, "description": "Material and machining cost"},
            {"name": "balance", "weight": 0.15, "description": "Rotational balance quality"},
            {"name": "corrosion_resistance", "weight": 0.10, "description": "Environmental durability"},
        ],
    },
    "general": {
        "criteria": [
            {"name": "performance", "weight": 0.30, "description": "Primary functional requirement"},
            {"name": "cost", "weight": 0.25, "description": "Total cost (material + labor + overhead)"},
            {"name": "manufacturability", "weight": 0.20, "description": "Ease of production and assembly"},
            {"name": "reliability", "weight": 0.15, "description": "Durability and failure resistance"},
            {"name": "lead_time", "weight": 0.10, "description": "Time to first article"},
        ],
    },
}


@server.tool()
def create_scorecard(
    name: str,
    decision: str,
    preset: Optional[str] = None,
    criteria: Optional[list[dict]] = None,
) -> str:
    """Create a weighted evaluation scorecard for a design decision."""
    if criteria:
        eval_criteria = criteria
    elif preset and preset.lower() in CRITERIA_PRESETS:
        eval_criteria = CRITERIA_PRESETS[preset.lower()]["criteria"]
    else:
        eval_criteria = CRITERIA_PRESETS["general"]["criteria"]

    # Validate weights sum to ~1.0
    total_weight = sum(c["weight"] for c in eval_criteria)
    if abs(total_weight - 1.0) > 0.05:
        # Normalize
        for c in eval_criteria:
            c["weight"] = round(c["weight"] / total_weight, 3)

    scorecard_id = str(uuid.uuid4())[:8]
    SCORECARD_STORE[scorecard_id] = {
        "id": scorecard_id,
        "name": name,
        "decision": decision,
        "criteria": eval_criteria,
        "alternatives": {},
        "created": datetime.datetime.utcnow().isoformat(),
    }

    return json.dumps({
        "status": "created",
        "scorecard_id": scorecard_id,
        "name": name,
        "decision": decision,
        "criteria": eval_criteria,
        "total_weight": sum(c["weight"] for c in eval_criteria),
    }, indent=2)


@server.tool()
def score_alternative(
    scorecard_id: str,
    alternative_name: str,
    scores: dict,
) -> str:
    """Score a design alternative against scorecard criteria. Scores are 1-10 for each criterion."""
    if scorecard_id not in SCORECARD_STORE:
        return json.dumps({"error": f"Scorecard '{scorecard_id}' not found."}, indent=2)

    card = SCORECARD_STORE[scorecard_id]
    criteria_names = [c["name"] for c in card["criteria"]]

    # Validate scores
    invalid = [k for k in scores if k not in criteria_names]
    missing = [k for k in criteria_names if k not in scores]

    if invalid:
        return json.dumps({"error": f"Unknown criteria: {invalid}. Valid: {criteria_names}"}, indent=2)

    # Clamp scores to 1-10
    for key in scores:
        scores[key] = max(1, min(10, scores[key]))

    # Calculate weighted score
    weighted_total = 0
    details = []
    for crit in card["criteria"]:
        raw = scores.get(crit["name"], 1)
        weighted = raw * crit["weight"]
        weighted_total += weighted
        details.append({
            "criterion": crit["name"],
            "raw_score": raw,
            "weight": crit["weight"],
            "weighted_score": round(weighted, 3),
        })

    card["alternatives"][alternative_name] = {
        "scores": scores,
        "details": details,
        "total_score": round(weighted_total, 3),
    }

    return json.dumps({
        "status": "scored",
        "alternative": alternative_name,
        "total_score": round(weighted_total, 3),
        "max_possible": 10.0,
        "details": details,
    }, indent=2)


@server.tool()
def compare_alternatives(scorecard_id: str) -> str:
    """Compare multiple scored alternatives and rank them."""
    if scorecard_id not in SCORECARD_STORE:
        return json.dumps({"error": f"Scorecard '{scorecard_id}' not found."}, indent=2)

    card = SCORECARD_STORE[scorecard_id]
    alternatives = card["alternatives"]

    if len(alternatives) < 1:
        return json.dumps({"error": "No alternatives scored yet."}, indent=2)

    ranked = sorted(
        [{"name": name, "score": data["total_score"]} for name, data in alternatives.items()],
        key=lambda x: x["score"],
        reverse=True,
    )

    # Build comparison matrix
    matrix = []
    for crit in card["criteria"]:
        row = {"criterion": crit["name"], "weight": crit["weight"]}
        for alt_name, alt_data in alternatives.items():
            row[alt_name] = alt_data["scores"].get(crit["name"], 0)
        matrix.append(row)

    return json.dumps({
        "scorecard": card["name"],
        "decision": card["decision"],
        "ranking": ranked,
        "winner": ranked[0] if ranked else None,
        "comparison_matrix": matrix,
        "total_alternatives": len(alternatives),
    }, indent=2)


@server.tool()
def export_scorecard(scorecard_id: str) -> str:
    """Export a scorecard comparison as structured data for documentation."""
    if scorecard_id not in SCORECARD_STORE:
        return json.dumps({"error": f"Scorecard '{scorecard_id}' not found."}, indent=2)

    card = SCORECARD_STORE[scorecard_id]

    return json.dumps({
        "export_format": "mcp_commander_scorecard_v1",
        "scorecard_id": card["id"],
        "name": card["name"],
        "decision": card["decision"],
        "created": card["created"],
        "criteria": card["criteria"],
        "alternatives": card["alternatives"],
        "summary": {
            "total_alternatives": len(card["alternatives"]),
            "ranking": sorted(
                [{"name": n, "score": d["total_score"]} for n, d in card["alternatives"].items()],
                key=lambda x: x["score"],
                reverse=True,
            ),
        },
    }, indent=2)


def main():
    """Start the mcp-commander-scorecard MCP server."""
    server.run()


if __name__ == "__main__":
    main()
