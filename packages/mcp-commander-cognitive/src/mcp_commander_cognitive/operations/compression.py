"""
Compression Thinking Operation.

Simplify over-engineered assemblies by identifying redundant features,
consolidation opportunities, and part-count reduction strategies. Provides
rules-based analysis for assembly simplification.
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Assembly simplification rules database
# ---------------------------------------------------------------------------
SIMPLIFICATION_RULES: list[dict[str, str | list[str]]] = [
    {
        "rule_id": "SIM-001",
        "name": "Fastener Consolidation",
        "description": "Replace multiple fasteners of the same size/type in a local area with fewer, larger fasteners or a single connection method.",
        "trigger_conditions": [
            "3+ identical bolts within 100mm diameter circle",
            "Adjacent rows of screws serving same clamping function",
            "Bolted flange with >8 fasteners on non-pressure joint",
            "Multiple rivets in a row where weld or adhesive could replace",
        ],
        "consolidation_strategy": "Evaluate load path: if clamping force distributes evenly, reduce fastener count by 30-50%. Replace with: larger bolt (1 size up), weld seam, structural adhesive, or snap-fit.",
        "estimated_savings": "15-40% reduction in fastener cost and assembly time.",
        "risk": "Verify via FEA that stress concentrations remain below allowable after consolidation.",
    },
    {
        "rule_id": "SIM-002",
        "name": "Feature Merging",
        "description": "Combine multiple machined or molded features into a single integrated feature that serves multiple functions.",
        "trigger_conditions": [
            "Separate bracket and spacer on same bolt pattern",
            "Locating pin + bolt hole within 10mm of each other",
            "Multiple gussets reinforcing same corner",
            "Separate seal groove and locating step on same surface",
        ],
        "consolidation_strategy": "Design a single feature that combines functions: e.g., locating shoulder integrated into bolt hole (shoulder bolt), or seal groove that also acts as a snap-fit undercut.",
        "estimated_savings": "1-3 fewer parts per assembly; reduced tolerance stack.",
        "risk": "Combined feature may be more complex to manufacture; verify process capability.",
    },
    {
        "rule_id": "SIM-003",
        "name": "Material Unification",
        "description": "Standardize materials across an assembly to reduce part count variability and enable bulk procurement.",
        "trigger_conditions": [
            "Assembly uses 3+ different aluminum alloys (6061, 7075, 5052)",
            "Multiple steel grades on non-critical structural parts",
            "Mix of POM and Nylon where one would suffice",
            "Steel fasteners on aluminum plates (dissimilar corrosion risk)",
        ],
        "consolidation_strategy": "Select the highest-grade material that meets all requirements. Document substitution rationale. For fasteners: use compatible material or add isolation (anodize, nylon washer).",
        "estimated_savings": "10-30% material procurement savings through volume consolidation; reduced BOM complexity.",
        "risk": "May slightly over-spec some components; confirm all load cases with unified material properties.",
    },
    {
        "rule_id": "SIM-004",
        "name": "Tolerance Stack Reduction",
        "description": "Reduce the number of tolerance-critical interfaces in an assembly by combining features or using datum-driven design.",
        "trigger_conditions": [
            "5+ parts in a linear tolerance stack",
            "Multiple datum references chained (A→B→C→D)",
            "Shims or adjustment features required for fit",
            "Assembly rework rate >5% due to dimensional issues",
        ],
        "consolidation_strategy": "Reduce part interfaces in the stack. Use single-piece machined components to replace multi-part stacks. Apply GD&T with a single primary datum for the critical dimension. Consider molded/cast parts that integrate datum features.",
        "estimated_savings": "30-60% reduction in assembly fit issues; elimination of shim operations.",
        "risk": "Single-piece replacement may require larger machine or casting capability.",
    },
    {
        "rule_id": "SIM-005",
        "name": "Multi-Function Part Integration",
        "description": "Combine multiple parts that serve different functions into a single monolithic part using appropriate manufacturing.",
        "trigger_conditions": [
            "Separate bracket + cable clamp + ground lug on same panel",
            "Multiple sheet metal parts that could be one stamped piece",
            "Separate housing + heatsink that could be extruded together",
            "Machined spacer + washer + nut stack on threaded rod",
        ],
        "consolidation_strategy": "Evaluate manufacturing options: stamping for combined sheet metal, extrusion for housing+fin, casting for integrated bracket+boss, 3D printing for complex multi-function prototypes. Target: reduce BOM line items by 20-30%.",
        "estimated_savings": "Reduced inventory, assembly steps, and inspection points. Typical 25% reduction in assembly time.",
        "risk": "Monolithic parts are harder to replace individually in service; design for serviceability.",
    },
    {
        "rule_id": "SIM-006",
        "name": "Redundant Stiffening",
        "description": "Identify over-stiffened regions where material can be removed without compromising structural integrity.",
        "trigger_conditions": [
            "FEM shows safety factor >4.0 in multiple regions",
            "Thick gussets on both sides of a plate",
            "Multiple rib patterns on plastic part where one pattern suffices",
            "I-beam flanges thicker than web by >5x",
        ],
        "consolidation_strategy": "Run topology optimization to identify load paths. Remove material from low-stress regions. Replace heavy uniform sections with optimized profiles. Target: reduce mass by 20-40% in over-stiffened regions.",
        "estimated_savings": "20-40% weight reduction in affected areas; proportional material cost savings.",
        "risk": "Must validate with FEA including buckling and fatigue analysis after material removal.",
    },
    {
        "rule_id": "SIM-007",
        "name": "Process Step Elimination",
        "description": "Eliminate manufacturing operations by redesigning for the process or changing processes entirely.",
        "trigger_conditions": [
            "Part requires machining after investment casting (near-net should suffice)",
            "Sheet metal part requires secondary forming operations after stamping",
            "CNC part has 5+ setups that could be 2 with redesign",
            "Molded part requires post-mold machining for threaded holes",
        ],
        "consolidation_strategy": "Redesign for the primary process: add molded-in threads (self-tapping or ultrasonic insert), redesign sheet metal for single-hit stamping, orient CNC part for 3+2 axis instead of 5 separate setups.",
        "estimated_savings": "30-60% reduction in per-part operations; proportional labor and cycle time savings.",
        "risk": "Process-specific redesign requires DFM expertise; may change tooling approach.",
    },
    {
        "rule_id": "SIM-008",
        "name": "Sub-Assembly Elimination",
        "description": "Replace a multi-part sub-assembly with a single purchased component or monolithic part.",
        "trigger_conditions": [
            "Custom cable assembly could be replaced with off-the-shelf harness",
            "Custom hinge made from 5 parts when a commercial hinge fits",
            "Custom pump mounting bracket assembly when a standard mount exists",
            "Manually assembled filter housing when a commercial filter element fits",
        ],
        "consolidation_strategy": "Audit sub-assemblies against standard component catalogs. Replace custom assemblies with single-line commercial parts where performance matches. Negotiate custom variants with suppliers for non-standard requirements.",
        "estimated_savings": "50-90% reduction in sub-assembly labor; improved reliability from proven components.",
        "risk": "Dependency on single supplier; must qualify commercial part for application requirements.",
    },
]

# ---------------------------------------------------------------------------
# Consolidation opportunity keywords
# ---------------------------------------------------------------------------
CONSOLIDATION_KEYWORDS: dict[str, list[str]] = {
    "fasteners": ["bolt", "screw", "nut", "rivet", "fastener", "washer", "stud", "thread"],
    "features": ["boss", "rib", "gusset", "flange", "bracket", "spacer", "shoulder", "groove"],
    "materials": ["aluminum", "steel", "plastic", "nylon", "titanium", "stainless", "brass", "pvc"],
    "assemblies": ["assembly", "sub-assembly", "subassembly", "mount", "housing", "cover", "panel", "frame"],
    "operations": ["machine", "stamp", "weld", "bend", "drill", "tap", "grind", "polish", "anneal"],
}


def _analyze_assembly(description: str) -> list[dict]:
    """Analyze a design description for applicable simplification rules."""
    desc_lower = description.lower()
    results: list[dict] = []

    for rule in SIMPLIFICATION_RULES:
        # Check if trigger conditions match
        triggers_matched = 0
        for trigger in rule["trigger_conditions"]:
            trigger_words = set(trigger.lower().split())
            desc_words = set(desc_lower.split())
            overlap = len(trigger_words & desc_words)
            if overlap >= 2:
                triggers_matched += 1
        if triggers_matched >= 1 or _broad_category_match(desc_lower, rule):
            results.append({
                **rule,
                "triggers_matched": triggers_matched,
                "applicable": True,
            })

    return results


def _broad_category_match(desc_lower: str, rule: dict) -> bool:
    """Broad category matching: if the description and rule share common keywords."""
    for category, keywords in CONSOLIDATION_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            rule_desc = (rule["description"] + " " + " ".join(rule["trigger_conditions"])).lower()
            if any(kw in rule_desc for kw in keywords):
                return True
    return False


def compression_thinking(
    design_description: str,
    part_count: Optional[int] = None,
    current_weight_grams: Optional[float] = None,
) -> dict:
    """
    Simplify over-engineered assemblies by identifying redundant features
    and consolidation opportunities.

    Analyzes the design description against 8 simplification rules covering
    fastener consolidation, feature merging, material unification, tolerance
    stack reduction, multi-function integration, redundant stiffening,
    process step elimination, and sub-assembly elimination.

    Args:
        design_description: Text description of the assembly, components,
            or sub-assembly to simplify.
        part_count: Optional current part count for context.
        current_weight_grams: Optional current assembly weight for context.

    Returns:
        Applicable simplification rules with trigger analysis, consolidation
        strategies, estimated savings, risks, and a prioritized action plan.
    """
    applicable_rules = _analyze_assembly(design_description)

    # Prioritize by number of triggers matched
    applicable_rules.sort(
        key=lambda x: x.get("triggers_matched", 0), reverse=True
    )

    # Estimate potential savings
    total_part_reduction_pct = 0
    total_weight_reduction_pct = 0
    for rule in applicable_rules:
        est = rule.get("estimated_savings", "")
        # Extract numeric percentages from estimated savings
        import re
        percentages = re.findall(r"(\d+)-?(\d+)?%", est)
        if percentages:
            low = int(percentages[0][0])
            high = int(percentages[0][1]) if percentages[0][1] else low
            avg_pct = (low + high) / 2
            if any(kw in rule["name"].lower() for kw in ["fastener", "part", "assembly", "sub-assembly"]):
                total_part_reduction_pct = max(total_part_reduction_pct, avg_pct)
            if any(kw in rule["name"].lower() for kw in ["stiffening", "material", "weight"]):
                total_weight_reduction_pct += avg_pct * 0.5  # Diminishing returns

    return {
        "design_description": design_description,
        "context": {
            "current_part_count": part_count,
            "current_weight_grams": current_weight_grams,
        },
        "rules_applicable": len(applicable_rules),
        "simplification_rules": applicable_rules,
        "estimated_impact": {
            "part_count_reduction_pct": round(total_part_reduction_pct, 1),
            "weight_reduction_pct": round(min(total_weight_reduction_pct, 60), 1),
            "estimated_simplified_part_count": (
                round(part_count * (1 - total_part_reduction_pct / 100))
                if part_count
                else None
            ),
        },
        "action_plan": [
            f"1. Review '{rule['name']}' (Rule {rule['rule_id']})"
            for rule in applicable_rules[:5]
        ],
        "summary": (
            f"Identified {len(applicable_rules)} simplification opportunity(ies). "
            f"Potential part count reduction: ~{total_part_reduction_pct:.0f}%, "
            f"weight reduction: ~{total_weight_reduction_pct:.0f}%."
        ),
    }
