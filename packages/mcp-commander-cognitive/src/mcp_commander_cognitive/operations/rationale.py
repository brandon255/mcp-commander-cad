"""
Design Rationale Operation.

Capture and retrieve design rationale linking engineering decisions to
requirements. Provides an in-memory rationale store with search, categorize,
and audit trail capabilities.
"""

from __future__ import annotations

import time
import uuid
from typing import Optional

# ---------------------------------------------------------------------------
# In-memory rationale storage
# ---------------------------------------------------------------------------
# Each entry: {
#   "id": str,
#   "decision": str,
#   "rationale": str,
#   "requirement": str,
#   "category": str,
#   "alternatives_considered": list[str],
#   "timestamp": float,
#   "author": str,
#   "component": str,
#   "project": Optional[str],
#   "tags": list[str],
#   "weight": int,  # 1-10, higher = stronger rationale
# }
_rationale_store: list[dict] = []

# ---------------------------------------------------------------------------
# Design rationale categories
# ---------------------------------------------------------------------------
RATIONALE_CATEGORIES: dict[str, list[str]] = {
    "material_selection": [
        "Material chosen based on strength-to-weight ratio",
        "Material chosen for corrosion resistance in salt-spray environment",
        "Material chosen for thermal conductivity (heat spreading requirement)",
        "Material chosen for biocompatibility (ISO 10993)",
        "Material chosen for cost at volume (target <$X per unit)",
        "Material chosen for EMI shielding effectiveness",
        "Material chosen for chemical resistance (exposure to X solvent)",
        "Material chosen for food-contact compliance (FDA 21 CFR)",
    ],
    "manufacturing_process": [
        "Process selected for volume-appropriate cycle time and cost",
        "Process selected for achievable tolerance class",
        "Process selected for surface finish capability",
        "Process selected for material compatibility",
        "Process selected for internal feature accessibility",
        "Process selected for lead time requirements",
    ],
    "geometric_design": [
        "Feature geometry optimized for load path continuity",
        "Wall thickness set by structural requirement (min safety factor N)",
        "Radius sized to prevent stress concentration below allowable",
        "Draft angle added for mold release (≥X° per surface)",
        "Fillets added to distribute stress and improve fatigue life",
        "Rib pattern optimized for stiffness-to-weight ratio",
    ],
    "tolerance_allocation": [
        "Tolerance tightened for sealing surface (leak rate <X cc/min)",
        "Tolerance loosened on non-critical dimension to reduce cost",
        "GD&T applied to control feature relationship (position/perp/para)",
        "Tolerance stack analysis (RSS) verified assembly fit",
        "Tolerance budget allocated per VDI 3667 guidelines",
    ],
    "fastening_strategy": [
        "Fastener type selected for load case (shear vs. tension)",
        "Fastener material compatible with joined materials (no galvanic couple)",
        "Clamp force calculated per VDI 2230 for joint integrity",
        "Thread-locking method selected for vibration environment",
        "Fastener spacing designed to prevent gasket extrusion",
    ],
    "surface_treatment": [
        "Anodize specified for corrosion protection and dye acceptance",
        "Plating specified for wear resistance (hard chrome, nickel)",
        "Coating specified for chemical resistance (E-coat, PFA)",
        "Surface treatment specified for cosmetic appearance",
        "Passivation specified for stainless steel corrosion resistance",
    ],
    "safety_compliance": [
        "Design meets IP rating requirement (IP67 per IEC 60529)",
        "Safety factor of N per ASME / Eurocode / applicable code",
        "Crash/impact requirement met per relevant standard",
        "Fire resistance rating met per UL 94 / FAR 25.853",
        "Electrical safety clearance per IEC 62368-1",
    ],
    "cost_optimization": [
        "Design simplified to reduce BOM line items from N to M",
        "Material downgraded from X to Y (verified adequate for loads)",
        "Manufacturing process changed from X to Y for 30% cost reduction",
        "Feature removed as non-functional (cost avoidance)",
        "Standard part substituted for custom (catalog: X, PN: Y)",
    ],
}

# ---------------------------------------------------------------------------
# Common requirement keywords
# ---------------------------------------------------------------------------
REQUIREMENT_KEYWORDS: list[str] = [
    "shall", "must", "requires", "must be", "shall be", "will", "needs to",
    "specification", "requirement", "per standard", "per spec", "mandatory",
    "critical", "essential", "non-negotiable", "customer requirement",
    "regulatory", "compliance", "shall not", "must not", "prohibited",
]

# ---------------------------------------------------------------------------
# Rationale store operations
# ---------------------------------------------------------------------------


def _capture_rationale(
    decision: str,
    rationale: str,
    requirement: str,
    category: str,
    alternatives_considered: list[str],
    component: str,
    author: str = "system",
    project: Optional[str] = None,
    tags: Optional[list[str]] = None,
    weight: int = 5,
) -> dict:
    """Internal function to create a rationale entry."""
    entry = {
        "id": str(uuid.uuid4())[:8],
        "decision": decision,
        "rationale": rationale,
        "requirement": requirement,
        "category": category,
        "alternatives_considered": alternatives_considered,
        "timestamp": time.time(),
        "author": author,
        "component": component,
        "project": project,
        "tags": tags or [],
        "weight": max(1, min(10, weight)),
    }
    _rationale_store.append(entry)
    return entry


def _search_rationale(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    component: Optional[str] = None,
    project: Optional[str] = None,
    requirement_keyword: Optional[str] = None,
    min_weight: int = 1,
) -> list[dict]:
    """Search the rationale store with filters."""
    results: list[dict] = []
    for entry in _rationale_store:
        if category and entry["category"] != category:
            continue
        if component and entry["component"].lower() != component.lower():
            continue
        if project and entry.get("project", "").lower() != project.lower():
            continue
        if entry["weight"] < min_weight:
            continue
        if keyword:
            kw_lower = keyword.lower()
            searchable = (
                f"{entry['decision']} {entry['rationale']} "
                f"{entry['requirement']} {' '.join(entry['tags'])}"
            ).lower()
            if kw_lower not in searchable:
                continue
        if requirement_keyword:
            req_lower = requirement_keyword.lower()
            if req_lower not in entry["requirement"].lower():
                continue
        results.append(entry)
    # Sort by timestamp descending (most recent first)
    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return results


def _suggest_rationale_template(category: str, decision_hint: str) -> str:
    """Generate a rationale template based on category and decision hint."""
    templates = RATIONALE_CATEGORIES.get(category, [])
    if templates:
        best_template = templates[0]
        # Try to find a better match based on hint
        for t in templates:
            if any(word in t.lower() for word in decision_hint.lower().split()):
                best_template = t
                break
        return best_template
    return "Design decision rationale: [Explain why this decision was made, linking to specific engineering requirements, test data, or simulation results.]"


def design_rationale(
    action: str = "search",
    decision: Optional[str] = None,
    rationale: Optional[str] = None,
    requirement: Optional[str] = None,
    category: Optional[str] = None,
    alternatives_considered: Optional[list[str]] = None,
    component: Optional[str] = None,
    author: Optional[str] = None,
    project: Optional[str] = None,
    tags: Optional[list[str]] = None,
    keyword: Optional[str] = None,
    requirement_keyword: Optional[str] = None,
    min_weight: int = 1,
) -> dict:
    """
    Capture and retrieve design rationale linking decisions to engineering
    requirements.

    Supports two primary actions:
    - **capture**: Store a new design rationale entry with decision, rationale
      text, linked requirement, category, and alternatives considered.
    - **search**: Retrieve stored rationale entries filtered by keyword,
      category, component, project, or requirement.

    Args:
        action: "capture" to store a new entry, "search" to retrieve entries,
            or "suggest" to get a rationale template for a category.
        decision: The design decision made (required for capture).
        rationale: Engineering rationale explaining the decision (required for capture).
        requirement: The linked engineering requirement driving the decision
            (required for capture).
        category: Category of the decision (e.g. "material_selection",
            "manufacturing_process", "geometric_design", "tolerance_allocation",
            "fastening_strategy", "surface_treatment", "safety_compliance",
            "cost_optimization").
        alternatives_considered: List of alternative approaches that were
            evaluated and rejected (for capture).
        component: Component or part name (for capture and search filter).
        author: Author of the rationale (defaults to "system").
        project: Project identifier (for capture and search filter).
        tags: List of searchable tags for the entry.
        keyword: Search keyword to match against decision, rationale,
            requirement, and tags.
        requirement_keyword: Search specifically within requirement fields.
        min_weight: Minimum rationale weight/strength for search (1-10).

    Returns:
        For capture: the stored entry with ID and timestamp.
        For search: matching entries with filters applied.
        For suggest: a rationale template for the given category.
    """
    if action == "capture":
        if not decision or not rationale or not requirement:
            return {
                "error": "capture action requires 'decision', 'rationale', and 'requirement' parameters.",
                "action": action,
            }
        entry = _capture_rationale(
            decision=decision,
            rationale=rationale,
            requirement=requirement,
            category=category or "uncategorized",
            alternatives_considered=alternatives_considered or [],
            component=component or "unspecified",
            author=author or "system",
            project=project,
            tags=tags or [],
            weight=5,
        )
        return {
            "action": "capture",
            "status": "stored",
            "entry": entry,
            "total_entries_in_store": len(_rationale_store),
            "message": f"Rationale entry '{entry['id']}' captured for component '{entry['component']}'.",
        }

    elif action == "search":
        results = _search_rationale(
            keyword=keyword,
            category=category,
            component=component,
            project=project,
            requirement_keyword=requirement_keyword,
            min_weight=min_weight,
        )
        return {
            "action": "search",
            "filters": {
                "keyword": keyword,
                "category": category,
                "component": component,
                "project": project,
                "requirement_keyword": requirement_keyword,
                "min_weight": min_weight,
            },
            "results_count": len(results),
            "total_entries_in_store": len(_rationale_store),
            "results": results,
            "summary": (
                f"Found {len(results)} rationale entr(ies)"
                + (f" for component '{component}'" if component else "")
                + (f" in category '{category}'" if category else "")
                + "."
            ),
        }

    elif action == "suggest":
        if not category:
            return {
                "action": "suggest",
                "error": "suggest action requires 'category' parameter.",
            }
        template = _suggest_rationale_template(
            category, decision or ""
        )
        available_categories = list(RATIONALE_CATEGORIES.keys())
        return {
            "action": "suggest",
            "category": category,
            "available_categories": available_categories,
            "suggested_rationale_template": template,
            "guidance": (
                "Fill in this template with your specific engineering "
                "justification, referencing test data, simulation results, "
                "standards, or past experience."
            ),
        }

    else:
        return {
            "error": f"Unknown action '{action}'. Use 'capture', 'search', or 'suggest'.",
            "available_actions": ["capture", "search", "suggest"],
        }
