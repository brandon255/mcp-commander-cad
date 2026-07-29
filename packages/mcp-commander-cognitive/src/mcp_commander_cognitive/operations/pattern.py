"""
Pattern Recognition Operation.

Identify recurring design inefficiencies and anti-patterns across engineering
projects. Maintains a knowledge base of common over-engineering, cost waste,
and manufacturability issues encountered in mechanical and product design.
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Design inefficiency pattern database
# ---------------------------------------------------------------------------
INEFFICIENCY_PATTERNS: list[dict[str, str | list[str]]] = [
    {
        "pattern_id": "PAT-001",
        "name": "Over-Tolerancing",
        "category": "tolerancing",
        "description": "Specifying tighter tolerances than functionally necessary, driving up machining cost exponentially.",
        "symptoms": [
            "General tolerances specified as ±0.01mm on non-critical faces",
            "Surface finish specified as Ra 0.4μm on hidden surfaces",
            "Positional tolerance of Ø0.05mm on non-mating features",
            "IT5-IT6 tolerance grades on features with no fit requirement",
        ],
        "impact": "Machining cost increases 3-10x; adds inspection overhead and scrap risk.",
        "recommendation": "Apply GD&T properly: tight tolerances only on datum references and critical mating surfaces. Use ISO 2768-m for general dimensions on machined parts.",
        "severity": "high",
    },
    {
        "pattern_id": "PAT-002",
        "name": "Redundant Fasteners",
        "category": "fastening",
        "description": "Using more fasteners than needed for the applied loads, increasing weight, cost, and assembly time.",
        "symptoms": [
            "Bolt pattern with 12+ fasteners on lightly loaded cover",
            "Every corner of a rectangular panel has 4 fasteners (16 total)",
            "Identical fastener sizes used where different sizes would suffice",
            "No engineering justification for fastener quantity in FEA",
        ],
        "impact": "Adds $0.50-$2.00 per excess fastener in material and installation cost; increases assembly cycle time.",
        "recommendation": "Calculate required clamp force, use VDI 2230 guidelines. A 4-bolt pattern is often sufficient for covers under 300mm. Consider pinning + 2 bolts for larger panels.",
        "severity": "medium",
    },
    {
        "pattern_id": "PAT-003",
        "name": "Unnecessary Stock Size Upgrade",
        "category": "material",
        "description": "Ordering oversized raw stock when standard sizes would suffice, wasting material and machining time.",
        "symptoms": [
            "CNC blank is 2x the finished part envelope",
            "Raw stock specified as 50mm plate when 25mm would suffice after machining",
            "Buying from standard catalog but selecting next-size-up 'for safety'",
            "No machinability analysis comparing stock-to-finished ratio",
        ],
        "impact": "Material cost 2-4x higher; longer cycle times; more chips to manage; larger machine required.",
        "recommendation": "Size raw stock to finished envelope + 3mm per face for cleanup. Use saw-cut blanks when possible. Consider near-net processes (casting, forging, waterjet) for high buy-to-fly ratios.",
        "severity": "medium",
    },
    {
        "pattern_id": "PAT-004",
        "name": "Over-Constrained Mounting",
        "category": "mechanical",
        "description": "Mounting a component with more degrees-of-freedom constrained than needed, causing assembly difficulty and thermal stress.",
        "symptoms": [
            "4 or more bolts on a flat interface without clearance holes (all reamed)",
            "No slot or clearance feature to accommodate thermal expansion",
            "Tight-fitting dowel pins at all 4 corners of a plate",
            "Assembly requires mallet to align parts that should slide-fit",
        ],
        "impact": "Assembly time increase; risk of binding, warping, or stress-induced fatigue. Thermal cycling may cause cracking.",
        "recommendation": "Use kinematic (3-point) mounting for precision, or 2 fixed + 2 slotted holes for general assemblies. Leave thermal expansion clearance per αΔTL calculation.",
        "severity": "high",
    },
    {
        "pattern_id": "PAT-005",
        "name": "Feature Creep in Sheet Metal",
        "category": "sheet_metal",
        "description": "Adding too many features (embosses, louvers, bends) to a single sheet metal part, driving tooling complexity beyond necessity.",
        "symptoms": [
            "Single bracket has 8+ bends in different planes",
            "Embossed ribs combined with formed louvers on same part",
            "Bend radii varying from 0.5mm to 5mm on same gauge",
            "Requires progressive die with 15+ stations for simple bracket",
        ],
        "impact": "Die cost 5-20x higher; longer setup; reduced bend accuracy at complex intersections; higher scrap rate.",
        "recommendation": "Split into 2-3 simpler stamped parts joined by spot welds or PEM fasteners. Use standard bend radii (1× material thickness minimum).",
        "severity": "medium",
    },
    {
        "pattern_id": "PAT-006",
        "name": "Ignoring Standard Parts",
        "category": "procurement",
        "description": "Designing custom components when equivalent standard parts (DIN, ISO, ANSI, JIS) are commercially available.",
        "symptoms": [
            "Custom hinge design when a McMaster-Carr or Bossard hinge fits",
            "Custom shaft shoulder when DIN 6721 circlip groove suffices",
            "Custom O-ring gland design not following Parker handbook",
            "Custom spring design when a Lee Spring stock spring matches",
        ],
        "impact": "Lead time 8-20 weeks vs. off-the-shelf 1-3 days. Higher per-unit cost. No interchangeability.",
        "recommendation": "Check standard part catalogs (McMaster, Misumi, Bossard, Reid Supply) before designing custom. Start from standard geometry and modify only if needed.",
        "severity": "high",
    },
    {
        "pattern_id": "PAT-007",
        "name": "Excessive Surface Finish Specification",
        "category": "tolerancing",
        "description": "Specifying Ra or Rz values tighter than the manufacturing process naturally achieves, requiring secondary finishing operations.",
        "symptoms": [
            "Ra 0.8μm specified on turned shaft (turning naturally achieves Ra 1.6μm)",
            "Mirror polish (Ra 0.1μm) required on non-visible internal surface",
            "Electropolish specified on a surface that will be painted over",
            "Superfinish on bearing journal when standard grind meets spec",
        ],
        "impact": "Adds grinding, lapping, or polishing operations ($50-$500 per part). May create unintended surface integrity issues.",
        "recommendation": "Match surface finish to manufacturing process capability. Use Ra 3.2 for rough machining, Ra 1.6 for general machined, Ra 0.8 for mating surfaces, Ra 0.4 for seal surfaces.",
        "severity": "medium",
    },
    {
        "pattern_id": "PAT-008",
        "name": "Inadequate Draft Angle on Molded Parts",
        "category": "injection_molding",
        "description": "Designing injection-molded features with insufficient or no draft angle, causing ejection issues and surface defects.",
        "symptoms": [
            "Vertical walls with 0° draft on textured surface",
            "Core pins without draft specified",
            "Interior ribs and bosses at 0.5° when 1-2° is needed",
            "No draft specified for side-action slides",
        ],
        "impact": "Parts stick in mold, causing drag marks, warpage, and increased cycle time. May require mold rework ($5k-$50k).",
        "recommendation": "Minimum 1° draft on all surfaces (1.5-2° preferred). Textured surfaces need 1° per 0.02mm texture depth. Use 3°+ for deep cores.",
        "severity": "high",
    },
    {
        "pattern_id": "PAT-009",
        "name": "Tolerance Stack Ignored in Assemblies",
        "category": "tolerancing",
        "description": "Assembling multiple parts without performing a tolerance stack-up analysis, resulting in interference or excessive gaps.",
        "symptoms": [
            "5+ part stack-up with all dimensions at nominal",
            "No worst-case (WC) or root-sum-square (RSS) analysis",
            "Shims added as a band-aid during assembly",
            "Assembly technicians manually filing parts to fit",
        ],
        "impact": "High rework rate, inconsistent assembly quality, warranty returns from misaligned mechanisms.",
        "recommendation": "Perform 1D tolerance stack analysis (WC and RSS) on all critical assemblies. Use GD&T bonus tolerances and MMC/LMC modifiers to maximize allowable variation.",
        "severity": "high",
    },
    {
        "pattern_id": "PAT-010",
        "name": "Over-Engineering Wall Thickness",
        "category": "structural",
        "description": "Using wall thicknesses far beyond what structural analysis requires, adding unnecessary weight and material cost.",
        "symptoms": [
            "6mm aluminum walls on a 100mm bracket that could be 3mm",
            "Plastic walls at 5mm on a non-structural enclosure (typical 2-3mm)",
            "Steel plate 12mm thick on a cover panel with no structural load",
            "No FEA or hand calculation to justify wall thickness",
        ],
        "impact": "Material cost increase 50-200%. Weight increase affects shipping, handling, and downstream structural requirements.",
        "recommendation": "Use hand calculations (bending stress, buckling) or FEA to determine minimum wall. For plastic: 2-3mm typical, 1.5mm for small parts. For aluminum: stiffener ribs allow thinner walls.",
        "severity": "medium",
    },
]

# ---------------------------------------------------------------------------
# Severity ranking
# ---------------------------------------------------------------------------
SEVERITY_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}


def _scan_for_patterns(
    design_description: str,
    category: Optional[str] = None,
    min_severity: str = "low",
) -> list[dict]:
    """
    Scan a design description for known inefficiency patterns using
    keyword matching against pattern symptoms.
    """
    desc_lower = design_description.lower()
    min_rank = SEVERITY_RANK.get(min_severity, 0)
    matched: list[dict] = []

    for pattern in INEFFICIENCY_PATTERNS:
        # Filter by severity
        if SEVERITY_RANK.get(pattern["severity"], 0) < min_rank:
            continue
        # Filter by category
        if category and pattern["category"] != category:
            continue
        # Keyword matching against symptoms and description
        desc_words = set(desc_lower.split())
        pattern_keywords = set(pattern["description"].lower().split())
        symptom_keywords = set()
        for symptom in pattern["symptoms"]:
            symptom_keywords.update(symptom.lower().split())

        overlap_desc = len(desc_words & pattern_keywords)
        overlap_symptom = len(desc_words & symptom_keywords)
        overlap_total = overlap_desc + overlap_symptom

        if overlap_total > 0:
            matched.append({**pattern, "match_score": overlap_total})

    # Sort by match score descending
    matched.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return matched


def pattern_recognition(
    design_description: str,
    category: Optional[str] = None,
    min_severity: str = "low",
) -> dict:
    """
    Identify recurring design inefficiencies and patterns.

    Scans the provided design description against a knowledge base of 10
    known anti-patterns covering over-tolerancing, redundant fasteners,
    over-constrained mounting, feature creep, standard parts avoidance,
    and more.

    Args:
        design_description: Text description of the design, assembly,
            or engineering approach to analyze.
        category: Optional category filter (e.g. "tolerancing", "fastening",
            "sheet_metal", "injection_molding", "structural", "mechanical",
            "material", "procurement").
        min_severity: Minimum severity to report: "low", "medium", or "high".

    Returns:
        Dictionary with matched patterns, severity ratings, symptoms found,
        recommendations, and a summary.
    """
    matched = _scan_for_patterns(design_description, category, min_severity)

    # If no keyword matches, return all patterns as awareness items
    if not matched:
        # Return patterns filtered by category only
        for p in INEFFICIENCY_PATTERNS:
            if category and p["category"] != category:
                continue
            if SEVERITY_RANK.get(p["severity"], 0) < SEVERITY_RANK.get(min_severity, 0):
                continue
            matched.append({**p, "match_score": 0})

    all_categories = sorted(set(p["category"] for p in INEFFICIENCY_PATTERNS))

    high_severity_count = sum(1 for m in matched if m.get("severity") == "high")

    return {
        "design_description": design_description,
        "patterns_detected": len(matched),
        "high_severity_count": high_severity_count,
        "available_categories": all_categories,
        "patterns": matched,
        "summary": (
            f"Found {len(matched)} potential inefficiency pattern(s), "
            f"{high_severity_count} of high severity. "
            f"Review recommendations for cost and quality improvements."
        ),
    }
