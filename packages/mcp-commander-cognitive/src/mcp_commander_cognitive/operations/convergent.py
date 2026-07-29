"""
Convergent Thinking Operation.

Evaluate and rank design alternatives against weighted engineering criteria
including cost, weight, manufacturability, strength, and lead time. Applies
a scoring matrix (Pugh-like) to provide a structured decision basis.
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Default evaluation criteria with descriptions and units
# ---------------------------------------------------------------------------
CRITERIA: dict[str, dict[str, str]] = {
    "cost": {
        "description": "Estimated per-unit cost including material and labor",
        "unit": "USD",
        "scale": "lower is better",
        "weight_default": 0.25,
    },
    "weight": {
        "description": "Mass of the component or assembly",
        "unit": "grams or kg",
        "scale": "lower is better",
        "weight_default": 0.20,
    },
    "manufacturability": {
        "description": "Ease of production (tooling complexity, process maturity, yield rate)",
        "unit": "1-10 subjective",
        "scale": "higher is better",
        "weight_default": 0.20,
    },
    "strength": {
        "description": "Ultimate or yield strength capability relative to requirement",
        "unit": "1-10 subjective",
        "scale": "higher is better",
        "weight_default": 0.20,
    },
    "lead_time": {
        "description": "Time from design release to first-article production",
        "unit": "weeks",
        "scale": "lower is better",
        "weight_default": 0.15,
    },
}

# ---------------------------------------------------------------------------
# Scoring normalization helpers
# ---------------------------------------------------------------------------

# Reference values for cost normalization (USD per part, typical ranges)
_COST_RANGES: dict[str, tuple[float, float]] = {
    "injection_molded_plastic": (0.10, 5.00),
    "sheet_metal_bracket": (1.00, 25.00),
    "cnc_machined_aluminum": (5.00, 150.00),
    "die_cast_part": (0.50, 10.00),
    "3d_printed_fdm": (2.00, 50.00),
    "3d_printed_sls": (5.00, 100.00),
    "investment_cast": (10.00, 200.00),
    "welded_assembly": (5.00, 100.00),
    "stamped_part": (0.05, 2.00),
}

# Reference values for weight normalization (grams)
_WEIGHT_RANGES: dict[str, tuple[float, float]] = {
    "light": (1.0, 50.0),
    "medium": (50.0, 500.0),
    "heavy": (500.0, 5000.0),
}

# Reference values for lead time normalization (weeks)
_LEAD_TIME_RANGES: dict[str, tuple[float, float]] = {
    "rapid_prototype": (0.5, 4.0),
    "production": (4.0, 16.0),
    "tooling_intensive": (12.0, 40.0),
}


def _normalize(value: float, low: float, high: float, higher_is_better: bool) -> float:
    """Normalize a value to a 0-1 scale given reference range."""
    if high == low:
        return 0.5
    norm = (value - low) / (high - low)
    norm = max(0.0, min(1.0, norm))
    if not higher_is_better:
        norm = 1.0 - norm
    return round(norm, 3)


def _infer_range_category(criterion: str, alternative_name: str) -> str:
    """Infer a rough category for normalization based on the alternative name."""
    name_lower = alternative_name.lower()
    if criterion == "cost":
        for cat in _COST_RANGES:
            if any(kw in name_lower for kw in cat.split("_")):
                return cat
        return "cnc_machined_aluminum"
    elif criterion == "weight":
        if "light" in name_lower or "thin" in name_lower:
            return "light"
        elif "heavy" in name_lower or "thick" in name_lower:
            return "heavy"
        return "medium"
    elif criterion == "lead_time":
        if "prototype" in name_lower or "rapid" in name_lower:
            return "rapid_prototype"
        elif "tooling" in name_lower or "die" in name_lower:
            return "tooling_intensive"
        return "production"
    return "default"


def _get_range(criterion: str, category: str) -> tuple[float, float]:
    """Retrieve the reference range for a criterion and category."""
    ranges_map = {
        "cost": _COST_RANGES,
        "weight": _WEIGHT_RANGES,
        "lead_time": _LEAD_TIME_RANGES,
    }
    mapping = ranges_map.get(criterion, {})
    return mapping.get(category, (0.0, 100.0))


def _estimate_scores_from_name(
    alternative_name: str,
    criteria_weights: dict[str, float],
) -> dict[str, float]:
    """
    Estimate scores for an alternative based on heuristic keywords in its name.
    Returns a dict mapping criterion name to raw score estimate.
    """
    name_lower = alternative_name.lower()
    scores: dict[str, float] = {}

    # Cost heuristics
    if any(kw in name_lower for kw in ["injection", "stamped", "die cast"]):
        scores["cost"] = 1.5
    elif any(kw in name_lower for kw in ["3d printed", "additive", "fdm"]):
        scores["cost"] = 8.0
    elif any(kw in name_lower for kw in ["cnc", "machined"]):
        scores["cost"] = 25.0
    elif any(kw in name_lower for kw in ["investment cast", "sand cast"]):
        scores["cost"] = 50.0
    elif any(kw in name_lower for kw in ["welded", "assembly"]):
        scores["cost"] = 15.0
    else:
        scores["cost"] = 10.0

    # Weight heuristics
    if any(kw in name_lower for kw in ["carbon fiber", "magnesium", "thin-wall", "lattice"]):
        scores["weight"] = 20.0
    elif any(kw in name_lower for kw in ["aluminum", "plastic", "nylon"]):
        scores["weight"] = 80.0
    elif any(kw in name_lower for kw in ["steel", "stainless", "iron"]):
        scores["weight"] = 250.0
    elif any(kw in name_lower for kw in ["titanium"]):
        scores["weight"] = 150.0
    else:
        scores["weight"] = 100.0

    # Manufacturability heuristics (1-10, higher better)
    if any(kw in name_lower for kw in ["injection", "stamped", "die cast"]):
        scores["manufacturability"] = 9.0
    elif any(kw in name_lower for kw in ["sheet metal", "welded"]):
        scores["manufacturability"] = 7.0
    elif any(kw in name_lower for kw in ["cnc", "machined"]):
        scores["manufacturability"] = 5.0
    elif any(kw in name_lower for kw in ["3d printed", "additive"]):
        scores["manufacturability"] = 6.0
    else:
        scores["manufacturability"] = 6.0

    # Strength heuristics (1-10, higher better)
    if any(kw in name_lower for kw in ["titanium", "steel", "forged"]):
        scores["strength"] = 9.0
    elif any(kw in name_lower for kw in ["aluminum 7075", "carbon fiber"]):
        scores["strength"] = 8.0
    elif any(kw in name_lower for kw in ["aluminum 6061", "die cast"]):
        scores["strength"] = 6.0
    elif any(kw in name_lower for kw in ["plastic", "nylon", "injection"]):
        scores["strength"] = 4.0
    else:
        scores["strength"] = 5.0

    # Lead time heuristics (weeks)
    if any(kw in name_lower for kw in ["3d printed", "additive", "prototype"]):
        scores["lead_time"] = 1.0
    elif any(kw in name_lower for kw in ["cnc", "machined"]):
        scores["lead_time"] = 3.0
    elif any(kw in name_lower for kw in ["welded", "sheet metal"]):
        scores["lead_time"] = 4.0
    elif any(kw in name_lower for kw in ["injection"]):
        scores["lead_time"] = 12.0
    elif any(kw in name_lower for kw in ["die cast", "investment cast"]):
        scores["lead_time"] = 16.0
    else:
        scores["lead_time"] = 6.0

    return scores


def convergent_thinking(
    alternatives: list[str],
    weights: Optional[dict[str, float]] = None,
    explicit_scores: Optional[dict[str, dict[str, float]]] = None,
) -> dict:
    """
    Evaluate and rank design alternatives against engineering criteria.

    Uses a Pugh-like weighted scoring matrix to compare alternatives across
    cost, weight, manufacturability, strength, and lead time. If explicit
    scores are provided they are used directly; otherwise, heuristic estimates
    are generated from alternative names.

    Args:
        alternatives: List of alternative approach names/descriptions to evaluate.
        weights: Optional dict of criterion name to weight (must sum to 1.0).
            Defaults to cost=0.25, weight=0.20, manufacturability=0.20,
            strength=0.20, lead_time=0.15.
        explicit_scores: Optional dict mapping alternative name to dict of
            {criterion_name: raw_value}. If provided, used instead of estimates.

    Returns:
        Ranked results with weighted scores, per-criterion breakdowns,
        and recommendation.
    """
    if weights is None:
        weights = {c: v["weight_default"] for c, v in CRITERIA.items()}
    else:
        # Validate weights
        total = sum(weights.values())
        if abs(total - 1.0) > 0.05:
            normalized = {k: v / total for k, v in weights.items()}
            weights = normalized

    criteria_list = list(CRITERIA.keys())
    results: list[dict] = []

    for alt_name in alternatives:
        # Get raw scores
        if explicit_scores and alt_name in explicit_scores:
            raw = explicit_scores[alt_name]
        else:
            raw = _estimate_scores_from_name(alt_name, weights)

        # Normalize and compute weighted score
        normalized_scores: dict[str, float] = {}
        component_scores: dict[str, float] = {}

        for criterion in criteria_list:
            if criterion not in raw:
                continue
            category = _infer_range_category(criterion, alt_name)
            low, high = _get_range(criterion, category)
            higher_is_better = CRITERIA[criterion]["scale"] == "higher is better"
            norm = _normalize(raw[criterion], low, high, higher_is_better)
            normalized_scores[criterion] = norm
            w = weights.get(criterion, 0.0)
            component_scores[criterion] = round(norm * w, 4)

        total_score = round(sum(component_scores.values()), 4)

        results.append(
            {
                "alternative": alt_name,
                "raw_estimates": raw,
                "normalized_scores": normalized_scores,
                "weighted_components": component_scores,
                "total_weighted_score": total_score,
            }
        )

    # Sort by total score descending
    results.sort(key=lambda x: x["total_weighted_score"], reverse=True)

    return {
        "criteria": {c: CRITERIA[c] for c in criteria_list},
        "weights": weights,
        "ranked_alternatives": results,
        "recommendation": results[0]["alternative"] if results else "none",
        "rationale": (
            f"Highest scoring alternative: {results[0]['alternative']} "
            f"with weighted score {results[0]['total_weighted_score']}"
            if results
            else "No alternatives provided."
        ),
    }
