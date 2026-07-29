"""
Context Diagnostics Operation.

Identify missing constraints, incomplete definitions, and gaps in a design
description. Checks for commonly omitted engineering specifications that
are necessary for a complete, manufacturable design.
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Required engineering specification categories and their check rules
# ---------------------------------------------------------------------------
DIAGNOSTIC_RULES: list[dict[str, str | list[str]]] = [
    {
        "rule_id": "CHK-001",
        "category": "material",
        "specification": "Material Specification",
        "description": "The material must be fully specified including grade, temper, and applicable standard.",
        "required_keywords": [
            "aluminum", "steel", "titanium", "plastic", "nylon", "polycarbonate",
            "abs", "peek", "brass", "copper", "stainless", "carbon steel",
            "grade", "alloy", "temper", "6061", "7075", "316l", "304",
            "a356", "az91d", "pa6", "pa12", "pom", "peek", "peek",
        ],
        "red_flags": [
            '"metal"', '"plastic"', '"alloy"', "generic terms without grade",
        ],
        "question": "What specific material grade, temper/condition, and applicable standard (ASTM/AMS) is required?",
        "severity": "critical",
    },
    {
        "rule_id": "CHK-002",
        "category": "tolerance",
        "specification": "Dimensional Tolerances",
        "description": "Critical dimensions must have tolerances defined. General tolerances should reference a standard.",
        "required_keywords": [
            "±", "tolerance", "tolerancing", "iso 2768", "gd&t", "position",
            "flatness", "cylindricity", "true position", "concentricity",
            "perpendicularity", "angularity", "parallelism", "roundness",
        ],
        "red_flags": [
            "No tolerance symbols mentioned",
            "Dimensions given without ± values",
        ],
        "question": "What tolerances apply to critical mating features? What general tolerance class (ISO 2768-m/f/c) for non-critical dimensions?",
        "severity": "critical",
    },
    {
        "rule_id": "CHK-003",
        "category": "loading",
        "specification": "Loading / Force Definition",
        "description": "Applied loads, forces, moments, and pressure must be characterized for structural analysis.",
        "required_keywords": [
            "load", "force", "moment", "torque", "pressure", "stress", "n",
            "lbf", "newton", "nm", "psi", "mpa", "ksi", "fem", "fea",
            "finite element", "static", "dynamic", "fatigue", "impact",
        ],
        "red_flags": [
            "Structural part with no load case mentioned",
            '"must be strong"', '"needs to handle force"',
        ],
        "question": "What are the applied loads (magnitude, direction, location, type: static, dynamic, fatigue, impact)? What safety factor is required?",
        "severity": "critical",
    },
    {
        "rule_id": "CHK-004",
        "category": "environment",
        "specification": "Environmental Conditions",
        "description": "Operating environment affects material selection, corrosion protection, and sealing requirements.",
        "required_keywords": [
            "temperature", "humidity", "corrosion", "salt spray", "uv",
            "outdoor", "indoor", "cleanroom", "food", "medical", "sterile",
            "vacuum", "underwater", "submerged", "chemical", "abrasive",
            "operating temperature", "storage temperature",
        ],
        "red_flags": [
            "No mention of where or how the part will be used",
            "No temperature range specified for any application",
        ],
        "question": "What is the operating temperature range, humidity, exposure to chemicals, UV, salt spray, or other environmental factors?",
        "severity": "high",
    },
    {
        "rule_id": "CHK-005",
        "category": "surface_finish",
        "specification": "Surface Finish Requirements",
        "description": "Surface roughness affects function (sealing, bearing, cosmetic), cost, and process selection.",
        "required_keywords": [
            "ra", "rz", "surface finish", "polish", "grind", "electropolish",
            "anodize", "plating", "coating", "paint", "powder coat",
            "chrome", "nickel", "zinc", "passivate", "blasting",
        ],
        "red_flags": [
            "Sealing surface with no finish specification",
            "Bearing surface with no finish requirement",
        ],
        "question": "What surface finish (Ra/Rz) is required for functional surfaces? Are there cosmetic or corrosion protection requirements?",
        "severity": "medium",
    },
    {
        "rule_id": "CHK-006",
        "category": "quantity",
        "specification": "Production Volume",
        "description": "Annual volume determines manufacturing process selection and tooling investment justification.",
        "required_keywords": [
            "quantity", "volume", "annual", "per year", "lot size", "batch",
            "production", "units per", "pieces per", "ea/yr", "annual volume",
            "prototype", "low volume", "high volume", "mass production",
        ],
        "red_flags": [
            "No mention of how many parts are needed",
            "No indication of prototype vs. production phase",
        ],
        "question": "What is the expected annual production volume and total lifetime quantity? Is this a prototype, bridge, or production part?",
        "severity": "high",
    },
    {
        "rule_id": "CHK-007",
        "category": "regulatory",
        "specification": "Regulatory / Standards Compliance",
        "description": "Industry standards and regulatory requirements constrain material selection, design, and testing.",
        "required_keywords": [
            "iso", "astm", "iec", "ul", "ce", "fcc", "rohs", "reach",
            "fda", "medical", "automotive", "aerospace", "mil-spec",
            "as9100", "ts16949", "ansi", "din", "jis", "sae",
        ],
        "red_flags": [
            "Medical application without FDA/ISO 13485 mention",
            "Automotive without IATF 16949 or PPAP mention",
        ],
        "question": "What industry standards, regulatory requirements, or certifications apply (FDA, UL, CE, MIL-SPEC, automotive PPAP, etc.)?",
        "severity": "high",
    },
    {
        "rule_id": "CHK-008",
        "category": "assembly",
        "specification": "Assembly / Joining Method",
        "description": "How parts are joined or assembled affects tolerance allocation, access, and serviceability.",
        "required_keywords": [
            "bolt", "screw", "weld", "adhesive", "snap", "press fit", "rivet",
            "assembly", "install", "mount", "fasten", "torque", "clamp",
            "stake", "crimp", "solder", "braze", "ultrasonic",
        ],
        "red_flags": [
            "Multi-part assembly with no joining method specified",
            "Critical joint with no fastener or adhesive details",
        ],
        "question": "How are parts assembled? What joining methods (bolted, welded, adhesive, snap-fit) are used? What assembly torque or process parameters?",
        "severity": "medium",
    },
    {
        "rule_id": "CHK-009",
        "category": "inspection",
        "specification": "Inspection / Quality Requirements",
        "description": "Quality inspection requirements determine measurement equipment, sampling plans, and documentation needs.",
        "required_keywords": [
            "inspection", "qa", "quality", "cmm", "ndt", "x-ray", "dimensional",
            "first article", "fa", "ppap", "spc", "cpk", "sampling",
            "visual", "functional test", "leak test", "pressure test",
        ],
        "red_flags": [
            "Critical dimension with no inspection method",
            "Pressure vessel with no test specification",
        ],
        "question": "What inspection methods are required (CMM, visual, NDT, functional test)? Is First Article Inspection (FAI) required? What Cpk targets?",
        "severity": "medium",
    },
    {
        "rule_id": "CHK-010",
        "category": "interface",
        "specification": "Interface / Mating Part Definition",
        "description": "Mating parts and interfaces must be defined to ensure proper fit and function.",
        "required_keywords": [
            "mates with", "interfaces with", "connects to", "mounts to",
            "fits into", "attaches to", "bolts to", "aligns with",
            "clearance for", "interference with",
        ],
        "red_flags": [
            "Part designed in isolation without mating interface specs",
            "No reference to mating component geometry or part number",
        ],
        "question": "What are the mating parts and interfaces? What clearance or interference is required? Are mating part drawings or models available?",
        "severity": "high",
    },
]

# ---------------------------------------------------------------------------
# Severity ranking
# ---------------------------------------------------------------------------
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _run_diagnostics(description: str) -> list[dict]:
    """Run all diagnostic checks against the design description."""
    desc_lower = description.lower()
    issues: list[dict] = []

    for rule in DIAGNOSTIC_RULES:
        # Check if any required keywords are present
        found_keywords = [
            kw for kw in rule["required_keywords"]
            if kw.lower() in desc_lower
        ]

        if found_keywords:
            # Specification appears to be present
            continue
        else:
            # Check for red flags
            red_flags_found = [
                rf for rf in rule["red_flags"]
                if rf.lower() in desc_lower
            ]
            issues.append({
                "rule_id": rule["rule_id"],
                "category": rule["category"],
                "specification": rule["specification"],
                "status": "MISSING" if not red_flags_found else "INCOMPLETE",
                "red_flags_detected": red_flags_found,
                "question": rule["question"],
                "severity": rule["severity"],
            })

    # Sort by severity
    issues.sort(key=lambda x: SEVERITY_ORDER.get(x["severity"], 99))
    return issues


def context_diagnostics(
    design_description: str,
    design_type: Optional[str] = None,
) -> dict:
    """
    Identify missing constraints, incomplete definitions, and gaps in a
    design description.

    Checks the provided description against 10 diagnostic categories:
    material, tolerance, loading, environment, surface finish, quantity,
    regulatory, assembly, inspection, and interface. Each category is
    assessed as PRESENT, INCOMPLETE, or MISSING with a guiding question.

    Args:
        design_description: Text description of the design, component,
            or assembly to diagnose.
        design_type: Optional design type hint (e.g. "structural",
            "enclosure", "mechanism", "thermal") for additional context.

    Returns:
        Diagnostic report with a completeness score, issues list sorted
        by severity, and a prioritized action checklist.
    """
    issues = _run_diagnostics(design_description)

    # Calculate completeness score
    total_rules = len(DIAGNOSTIC_RULES)
    issues_count = len(issues)
    completeness_pct = round((1 - issues_count / total_rules) * 100, 1)

    critical_count = sum(1 for i in issues if i["severity"] == "critical")
    high_count = sum(1 for i in issues if i["severity"] == "high")
    medium_count = sum(1 for i in issues if i["severity"] == "medium")

    # Build action checklist
    action_checklist: list[str] = []
    for issue in issues:
        action_checklist.append(
            f"☐ [{issue['severity'].upper()}] {issue['specification']}: "
            f"{issue['question']}"
        )

    return {
        "design_description": design_description,
        "design_type": design_type,
        "completeness_score": completeness_pct,
        "issues_summary": {
            "total_issues": issues_count,
            "critical": critical_count,
            "high": high_count,
            "medium": medium_count,
            "specifications_present": total_rules - issues_count,
        },
        "issues": issues,
        "action_checklist": action_checklist,
        "verdict": (
            f"Design description is {completeness_pct}% complete. "
            f"{critical_count} critical, {high_count} high, {medium_count} medium "
            f"specification(s) missing or incomplete."
        ),
    }
