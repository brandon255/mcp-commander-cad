"""
Divergent Thinking Operation.

Generate alternative design approaches for a given design intent or constraint
set. Draws from a knowledge base of engineering approaches spanning fastener
alternatives, joint types, mounting methods, sealing approaches, structural
topologies, and material strategies.
"""

from __future__ import annotations

import re
import textwrap
from typing import Optional

# ---------------------------------------------------------------------------
# Engineering knowledge base: alternative approaches keyed by design category
# ---------------------------------------------------------------------------
KNOWLEDGE_BASE: dict[str, list[dict[str, str]]] = {
    "fastening": [
        {
            "approach": "Thread-forming screws into thermoplastic",
            "description": "Eliminate inserts by using thread-forming screws (Type PT, Type U) directly into plastic bosses. Reduces part count and assembly time.",
            "best_for": "Consumer products, low-load plastic enclosures, electronics housings",
            "tradeoffs": "Limited pull-out strength; requires wall thickness ≥2× screw diameter",
        },
        {
            "approach": "Snap-fit clip with living hinge",
            "description": "Molded snap-fit fingers that deflect during assembly and lock into place. Living hinge variants allow repeated access.",
            "best_for": "Two-piece enclosures, battery doors, panel covers",
            "tradeoffs": "Sensitive to material fatigue; requires precise deflection analysis",
        },
        {
            "approach": "Ultrasonic weld joint",
            "description": "Energy-director or shear-joint ultrasonic welding to fuse thermoplastic parts permanently.",
            "best_for": "Hermetic seals, high-volume assembly, medical disposables",
            "tradeoffs": "Material-specific (amorphous thermoplastics preferred); requires joint design upfront",
        },
        {
            "approach": "Adhesive bonding with structural epoxy",
            "description": "Two-part structural epoxy or acrylic adhesive for metal-to-metal and metal-to-composite joints.",
            "best_for": "Dissimilar material joints, load-bearing assemblies, vibration environments",
            "tradeoffs": "Surface preparation critical; cure time adds to cycle; inspection difficulty",
        },
        {
            "approach": "Self-clinching fastener (PEM-style)",
            "description": "Press-in nut or stud that mechanically locks into a sheet metal panel without welding.",
            "best_for": "Sheet metal enclosures, chassis, rack-mounted equipment",
            "tradeoffs": "Requires specific panel hardness; minimal protrusion on blind side",
        },
        {
            "approach": "Captive fastener with retainer",
            "description": "Fastener held in place by a retainer clip or molded feature so it cannot fall out during service.",
            "best_for": "Field-serviceable equipment, access panels, frequent disassembly",
            "tradeoffs": "Higher tooling cost; must select correct retainer for thread size",
        },
    ],
    "sealing": [
        {
            "approach": "O-ring gland with dynamic seal design",
            "description": "Machined or molded groove accepting a standard AS568 O-ring. Choose static (face seal) or dynamic (reciprocating/rotary) gland design per Parker O-Ring Handbook.",
            "best_for": "Hydraulic cylinders, pneumatic actuators, pump housings",
            "tradeoffs": "Gland dimensions must follow tolerance recommendations (±0.001 in typical)",
        },
        {
            "approach": "Molded-in-place gasket (FIPG)",
            "description": "Liquid gasket material dispensed onto flange and cured in place. Eliminates die-cut gasket inventory.",
            "best_for": "Engine covers, transmission housings, large flanged joints",
            "tradeoffs": "Dispensing equipment cost; cure time; rework requires removal and re-application",
        },
        {
            "approach": "PTFE lip seal with spring energizer",
            "description": "Spring-energized PTFE seal for chemical resistance and low friction in rotary shafts.",
            "best_for": "Chemical processing, food equipment, cryogenic applications",
            "tradeoffs": "Higher unit cost than elastomer seals; limited to moderate pressures",
        },
        {
            "approach": "Compression set with formed-in-place foam",
            "description": "Closed-cell foam tape or molded gasket compressed between two surfaces. Simple and low-cost.",
            "best_for": "Electronics enclosures (IP54), access doors, weather stripping",
            "tradeoffs": "Compression set over time; not suitable for high pressure or vacuum",
        },
    ],
    "mounting": [
        {
            "approach": "Vibration-isolated mount with wire rope isolator",
            "description": "Wire rope isolator provides multi-axis vibration isolation and shock attenuation without resonant amplification.",
            "best_for": "Mobile electronics, military shelters, avionics racks",
            "tradeoffs": "Larger envelope than elastomer mounts; directional stiffness varies",
        },
        {
            "approach": "Kinematic mounting (Kelvin clamp)",
            "description": "Three-point contact using balls in V-grooves or flat-and-ball pairs constraining exactly 6 DOF.",
            "best_for": "Optical benches, precision instruments, CMM fixtures",
            "tradeoffs": "Limited load capacity; requires precise machining of contact features",
        },
        {
            "approach": "Floating nut plate in structural channel",
            "description": "Sliding nut plate in T-slot or channel allowing adjustable mounting position without drilling.",
            "best_for": "Extrusion-based frames, modular enclosures, test rigs",
            "tradeoffs": "Can shift under vibration; requires locking feature or loctite",
        },
        {
            "approach": "Magetic mounting with rare-earth pads",
            "description": "Neodymium magnet pads for temporary mounting on ferromagnetic surfaces.",
            "best_for": "Fixturing, inspection equipment, temporary sensor mounts",
            "tradeoffs": "Force limited by contact area and air gap; temperature sensitive above 80°C",
        },
    ],
    "structural": [
        {
            "approach": "Topology-optimized bracket with lattice infill",
            "description": "Use generative design to create organic bracket shape with internal lattice for additive manufacturing.",
            "best_for": "Aerospace brackets, lightweight mounts, AM-produced components",
            "tradeoffs": "Requires AM (DMLS/SLM); post-processing needed; certification complexity",
        },
        {
            "approach": "Corrugated core sandwich panel",
            "description": "Two face sheets bonded to a corrugated core for high stiffness-to-weight ratio.",
            "best_for": "Floor panels, wall structures, lightweight covers",
            "tradeoffs": "Core shear must be checked; bonding process critical; repair difficulty",
        },
        {
            "approach": "Pultruded fiber-reinforced profile",
            "description": "Continuous fiber-reinforced polymer profile with consistent cross-section and high specific stiffness.",
            "best_for": "Structural framing, ladder rails, non-conductive structural members",
            "tradeoffs": "Limited to constant cross-section; joining requires adhesive or mechanical methods",
        },
    ],
    "material": [
        {
            "approach": "GFRP sheet molding compound (SMC)",
            "description": "Glass-fiber reinforced thermoset compression molded into complex shapes with good surface finish.",
            "best_for": "Automotive body panels, electrical enclosures, appliance housings",
            "tradeoffs": "High tooling cost; limited recyclability; cure shrinkage must be compensated",
        },
        {
            "approach": "3D-printed carbon-fiber nylon (PA12-CF)",
            "description": "FDM or SLS printed nylon reinforced with chopped carbon fiber for high stiffness and thermal stability.",
            "best_for": "Functional prototypes, jigs and fixtures, drone components",
            "tradeoffs": "Anisotropic properties; nozzle wear; higher material cost than standard nylon",
        },
        {
            "approach": "Die-cast magnesium alloy (AZ91D)",
            "description": "Lightest structural metal die casting alloy with excellent stiffness and damping.",
            "best_for": "Laptop frames, power tool housings, automotive interior structures",
            "tradeoffs": "Corrosion requires coating; flammability risk in molten state; limited weldability",
        },
    ],
    "heat_management": [
        {
            "approach": "Heat pipe embedded in aluminum baseplate",
            "description": "Sintered-wick or grooved heat pipe pressed into an aluminum plate for isothermal spreading.",
            "best_for": "LED thermal management, power electronics, battery cooling",
            "tradeoffs": "Orientation sensitivity (gravity-aided vs. against); limited heat flux per pipe",
        },
        {
            "approach": "Vapor chamber with sintered wick",
            "description": "Planar heat pipe providing two-dimensional isothermal spreading across a large area.",
            "best_for": "High-power CPU/GPU coolers, server thermal modules, 5G base stations",
            "tradeoffs": "Higher cost than round heat pipes; thickness adds to Z-height stackup",
        },
        {
            "approach": "Graphite thermal film (PGS)",
            "description": "Pyrolytic graphite sheet with extremely high in-plane thermal conductivity (1500-1700 W/mK).",
            "best_for": "Smartphones, tablets, thin-profile thermal spreading",
            "tradeoffs": "Very low through-plane conductivity; fragile; must be protected in assembly",
        },
    ],
}

# ---------------------------------------------------------------------------
# Category keyword mapping for intent classification
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "fastening": [
        "fasten", "bolt", "screw", "nut", "rivet", "clip", "join", "attach",
        "thread", "weld", "assemble", "connector", "insert", "stud", "washer",
    ],
    "sealing": [
        "seal", "gasket", "o-ring", "leak", "waterproof", "hermetic", "ip67",
        "ip68", "encapsulate", "gland", "lip seal", "weather", "pressure",
    ],
    "mounting": [
        "mount", "bracket", "support", "fixture", "base", "stand", "attach",
        "hang", "suspend", "vibration", "isolate", "dampen", "rigid mount",
    ],
    "structural": [
        "structure", "frame", "beam", "stiffness", "strength", "buckling",
        "bending", "torsion", "load path", "shell", "plate", "reinforce",
    ],
    "material": [
        "material", "alloy", "polymer", "composite", "plastic", "metal",
        "aluminum", "steel", "titanium", "carbon fiber", "nylon", "resin",
    ],
    "heat_management": [
        "heat", "thermal", "cool", "temperature", "dissipate", "sink",
        "conduction", "convection", "radiation", "heatsink", "heatpipe",
    ],
}


def _classify_intent(intent_text: str) -> list[str]:
    """Classify the design intent into one or more engineering categories."""
    text_lower = intent_text.lower()
    matched: list[str] = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                matched.append(category)
                break
    # Default to all categories if no match found
    return matched if matched else list(CATEGORY_KEYWORDS.keys())


def _pick_approaches(categories: list[str], count: int = 5) -> list[dict[str, str]]:
    """Select up to *count* approaches from the given categories, cycling."""
    pool: list[dict[str, str]] = []
    for cat in categories:
        pool.extend(KNOWLEDGE_BASE.get(cat, []))
    if count and count < len(pool):
        return pool[:count]
    return pool


def divergent_thinking(
    intent: str,
    constraints: Optional[str] = None,
    num_alternatives: int = 5,
) -> dict:
    """
    Generate alternative design approaches for a given design intent.

    Args:
        intent: Natural-language description of the design goal or problem
            (e.g. "I need to attach an aluminum panel to a steel frame").
        constraints: Optional comma-separated list of constraints
            (e.g. "must resist vibration, budget under $5/part").
        num_alternatives: Maximum number of alternative approaches to return (1-10).

    Returns:
        Dictionary with classified intent, constraints, and a list of
        alternative approaches with descriptions, best-use cases, and tradeoffs.
    """
    categories = _classify_intent(intent)
    approaches = _pick_approaches(categories, num_alternatives)

    result: dict = {
        "intent": intent,
        "classified_categories": categories,
        "constraints": constraints or "none specified",
        "alternatives": [],
        "total_approaches_available": sum(
            len(KNOWLEDGE_BASE.get(c, [])) for c in categories
        ),
    }

    for approach in approaches:
        result["alternatives"].append(
            {
                "approach": approach["approach"],
                "description": approach["description"],
                "best_for": approach["best_for"],
                "tradeoffs": approach["tradeoffs"],
            }
        )

    return result
