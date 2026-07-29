"""
mcp-commander-ideas MCP server.

Exposes design ideation, alternative generation, manufacturing exploration,
idea capture/search, and cross-domain transfer tools via the Model Context Protocol.
"""

import json
import uuid
import datetime
import mcp.server.fastmcp
from typing import Optional

server = mcp.server.fastmcp.FastMCP("mcp-commander-ideas")

# ── Local idea store (in-memory, session-scoped) ──
IDEA_STORE = []

# ── Cross-domain knowledge base ──
CROSS_DOMAIN_SOLUTIONS = {
    "mounting": {
        "aerospace": ["floating mount with dampers", "hard-point with vibration isolation", "bracket with thermal expansion slots"],
        "automotive": ["rubber-isolated bracket", "welded stud mount", "clip-on rail system"],
        "medical": ["biocompatible snap-fit", "sterilizable screw mount", "magnetic quick-attach"],
        "industrial": ["base plate with anchor bolts", "vibration-damped rail mount", "modular t-slot attachment"],
    },
    "sealing": {
        "aerospace": ["metallic C-seal", "wire-retained O-ring", "bonded elastomer seal"],
        "automotive": ["molded rubber gasket", "lip seal", "cork-rubber composite"],
        "medical": ["silicone O-ring", "bonded PTFE seal", "laser-welded hermetic seal"],
        "industrial": ["flat rubber gasket", "spiral wound gasket", "chevron v-ring pack"],
    },
    "fastening": {
        "aerospace": ["Hi-Lok pin", "AN bolt with castle nut", "riv nut with locking feature"],
        "automotive": ["weld nut", "self-clinching stud", "plastic push-clip"],
        "medical": ["captured thumbscrew", "bayonet fitting", "color-coded quick-release"],
        "industrial": ["hex bolt with lock washer", "T-slot nut", "weld-on stud"],
    },
    "cooling": {
        "aerospace": ["brazed fin stack", "impingement plate", "phase-change cold plate"],
        "automotive": ["extruded aluminum fin", "liquid-cooled jacket", "heat pipe array"],
        "medical": ["forced-air over fins", "thermoelectric cooler", "passive convection housing"],
        "industrial": ["fan-cooled fin bank", "water jacket", "oil-cooled heat exchanger"],
    },
    "cable_management": {
        "aerospace": ["conduit with strain relief", "lacing cord bundles", "split loom tubing"],
        "automotive": ["loom tape wrap", "corrugated split conduit", "integrated wire channel"],
        "medical": ["sealed trace routing", "snap-in conduit", "flexible circuit carrier"],
        "industrial": ["cable tray", "wire duct with cover", "daisy-chain bus system"],
    },
}

UNCOMMON_MANUFACTURING = {
    "3dp_jig": {
        "name": "3D-Printed Jig/Fixture",
        "description": "Print alignment jigs, drill guides, and assembly fixtures using FDM or SLA instead of machining aluminum",
        "when_to_use": ["low volume (<50 units)", "complex geometry", "frequent design changes", "rapid prototyping phase"],
        "typical_savings": "60-80% cost reduction vs machined fixture, 1-2 day lead time vs 1-2 weeks",
        "limitations": ["lower precision than machined", "temperature sensitive", "not for high-force applications"],
    },
    "foam_tooling": {
        "name": "Foam Tooling Pattern",
        "description": "Use CNC-cut foam (EPS/PU) as a pattern for sand casting, investment casting, or composite layup molds",
        "when_to_use": ["large parts (>500mm)", "one-off castings", "low-pressure casting", "rapid pattern iteration"],
        "typical_savings": "80-95% vs metal pattern, same-day turnaround",
        "limitations": ["single use or limited reuse", "surface finish depends on finish coat", "not for high-pressure casting"],
    },
    "printed_mandrel": {
        "name": "3D-Printed Composite Mandrel",
        "description": "Print a dissolvable or breakaway mandrel for composite tube/duct layup, then dissolve or crush to remove",
        "when_to_use": ["hollow composite structures", "complex internal geometry", "aerospace ducting", "custom tubing"],
        "typical_savings": "Eliminates expensive multi-piece metal tooling",
        "limitations": ["limited pressure during cure", "material compatibility with resin system"],
    },
    "laser_cut_flat": {
        "name": "Laser-Cut Flat Pattern",
        "description": "Convert 3D parts to flat patterns and laser cut from sheet, then fold/bend/weld to form",
        "when_to_use": ["sheet metal parts", "brackets", "enclosures", "thin-walled structures"],
        "typical_savings": "70-90% vs full 3-axis CNC for thin parts, seconds per part vs minutes",
        "limitations": ["sheet thickness only (<6mm steel)", "2.5D geometry", "bend radii limited by material"],
    },
    "wire_edm": {
        "name": "Wire EDM from Stock",
        "description": "Use wire EDM to cut complex profiles from thick plate stock instead of milling",
        "when_to_use": ["complex 2D profiles", "hard materials", "tight tolerances", "no draft angle needed"],
        "typical_savings": "Faster than milling for complex shapes in hard materials, superior surface finish",
        "limitations": ["through-cut only (no pockets)", "slow for large volumes", "kerf width ~0.25mm"],
    },
    "hydroforming": {
        "name": "Hydroforming from Flat Sheet",
        "description": "Form complex 3D shapes from sheet metal using hydraulic pressure against a die",
        "when_to_use": ["seamless tubular parts", "automotive panels", "complex curved surfaces", "aerospace skins"],
        "typical_savings": "Better material distribution, fewer welds, higher strength-to-weight vs stamping",
        "limitations": ["high tooling cost", "limited to ductile materials", "cycle time longer than stamping"],
    },
}


@server.tool()
def generate_alternatives(design_intent: str, constraints: Optional[str] = None) -> str:
    """Generate alternative design approaches for a given design intent."""
    intent_lower = design_intent.lower()

    alternatives = []

    # Match against known design patterns
    patterns = {
        "bracket": [
            {"approach": "Machined aluminum bracket", "pros": ["high strength", "precise tolerances"], "cons": ["expensive for low volumes", "long lead time"]},
            {"approach": "Sheet metal bent bracket", "pros": ["low cost at volume", "fast production"], "cons": ["limited geometry", "bend radius constraints"]},
            {"approach": "3D-printed polymer bracket", "pros": ["complex geometry free", "rapid iteration"], "cons": ["lower strength", "material cost for large parts"]},
            {"approach": "Welded assembly bracket", "pros": ["very strong", "can combine stock materials"], "cons": ["weld distortion", "secondary operations needed"]},
        ],
        "housing": [
            {"approach": "Injection-molded enclosure", "pros": ["excellent finish", "low unit cost at volume"], "cons": ["high tooling cost ($10K-50K)", "6-12 week tooling lead"]},
            {"approach": "Sheet metal enclosure", "pros": ["no mold needed", "EMI shielding"], "cons": ["limited shape complexity", "draft angles required"]},
            {"approach": "3D-printed enclosure", "pros": ["no tooling", "integrated features"], "cons": ["surface finish", "unit cost at volume"]},
            {"approach": "CNC-machined enclosure", "pros": ["precision", "no tooling investment"], "cons": ["expensive per unit", "slow for complex geometry"]},
        ],
        "shaft": [
            {"approach": "Turned from bar stock", "pros": ["standard process", "good tolerances"], "cons": ["material waste", "limited to rotationally symmetric"]},
            {"approach": "Cold-forged shaft", "pros": ["grain flow optimization", "high strength"], "cons": ["tooling cost", "limited geometry"]},
            {"approach": "Additive + finish machined", "pros": ["near-net shape", "complex internal features"], "cons": ["surface finish needs post-process", "build time"]},
        ],
        "seal": [
            {"approach": "O-ring gland", "pros": ["standardized", "cheap", "replaceable"], "cons": ["requires precise gland design", "compression set over time"]},
            {"approach": "Machined metal face seal", "pros": ["high pressure", "temperature resistant"], "cons": ["expensive", "surface finish critical"]},
            {"approach": "Elastomer molded seal", "pros": ["custom geometry", "chemical compatibility"], "cons": ["tooling cost", "minimum order quantities"]},
            {"approach": "PTFE lip seal", "pros": ["low friction", "chemical inert"], "cons": ["limited pressure", "temperature range"]},
        ],
    }

    for key, alts in patterns.items():
        if key in intent_lower or intent_lower in key:
            alternatives = alts
            break

    if not alternatives:
        # Generic fallback
        alternatives = [
            {"approach": "Standard machined component", "pros": ["well-understood process", "precise"], "cons": ["cost scales with complexity"]},
            {"approach": "Additive manufactured part", "pros": ["complex geometry", "consolidate assemblies"], "cons": ["surface finish", "material options"]},
            {"approach": "Sheet metal formed", "pros": ["low cost at volume", "fast"], "cons": ["limited geometry"]},
            {"approach": "Multi-material assembly", "pros": ["optimize each element"], "cons": ["assembly labor", "tolerance stackup"]},
        ]

    result = {
        "design_intent": design_intent,
        "alternatives": alternatives,
    }
    if constraints:
        result["constraints_considered"] = constraints

    return json.dumps(result, indent=2)


@server.tool()
def explore_manufacturing_methods(
    design_description: str,
    volume: str = "low",
) -> str:
    """Explore uncommon manufacturing methods for a design."""
    desc_lower = design_description.lower()
    results = []

    for key, method in UNCOMMON_MANUFACTURING.items():
        relevance = 0
        if any(term in desc_lower for term in ["jig", "fixture", "alignment", "guide"]):
            if key == "3dp_jig":
                relevance = 3
        if any(term in desc_lower for term in ["casting", "cast", "pattern", "mold"]):
            if key in ("foam_tooling", "printed_mandrel"):
                relevance = 3
        if any(term in desc_lower for term in ["tube", "duct", "hollow", "composite"]):
            if key == "printed_mandrel":
                relevance = 3
        if any(term in desc_lower for term in ["sheet", "thin", "flat", "bracket", "enclosure"]):
            if key == "laser_cut_flat":
                relevance = 3
        if any(term in desc_lower for term in ["hard", "titanium", "inconel", "hardened"]):
            if key == "wire_edm":
                relevance = 3
        if any(term in desc_lower for term in ["curved", "panel", "aerospace", "skin"]):
            if key == "hydroforming":
                relevance = 2

        if relevance > 0:
            results.append({"relevance_score": relevance, **method})

    if not results:
        # Return top 3 methods as suggestions regardless
        results = list(UNCOMMON_MANUFACTURING.values())[:3]

    results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    return json.dumps({
        "design_description": design_description,
        "production_volume": volume,
        "suggested_methods": results,
    }, indent=2)


@server.tool()
def capture_idea(
    title: str,
    description: str,
    category: str = "general",
    project: str = "default",
    tags: Optional[list[str]] = None,
) -> str:
    """Capture and store a design idea with metadata."""
    idea = {
        "id": str(uuid.uuid4())[:8],
        "title": title,
        "description": description,
        "category": category,
        "project": project,
        "tags": tags or [],
        "created": datetime.datetime.utcnow().isoformat(),
    }
    IDEA_STORE.append(idea)

    return json.dumps({
        "status": "captured",
        "idea_id": idea["id"],
        "title": idea["title"],
        "total_ideas_stored": len(IDEA_STORE),
    }, indent=2)


@server.tool()
def search_ideas(
    query: str,
    category: Optional[str] = None,
    project: Optional[str] = None,
) -> str:
    """Search stored design ideas by keyword, category, or project."""
    query_lower = query.lower()
    results = []

    for idea in IDEA_STORE:
        match = (
            query_lower in idea["title"].lower()
            or query_lower in idea["description"].lower()
            or any(query_lower in tag.lower() for tag in idea.get("tags", []))
        )
        if category and idea["category"] != category:
            match = False
        if project and idea["project"] != project:
            match = False
        if match:
            results.append(idea)

    return json.dumps({
        "query": query,
        "category": category,
        "project": project,
        "results": results,
        "count": len(results),
        "total_stored": len(IDEA_STORE),
    }, indent=2)


@server.tool()
def cross_domain_transfer(
    design_problem: str,
    source_domain: str,
    target_domain: str,
) -> str:
    """Transfer design solutions from one industry domain to another."""
    problem_lower = design_problem.lower()
    solutions = []

    # Find matching problem category
    for category, domains in CROSS_DOMAIN_SOLUTIONS.items():
        if category in problem_lower or any(word in problem_lower for word in category.split("_")):
            source_solutions = domains.get(source_domain.lower(), [])
            target_solutions = domains.get(target_domain.lower(), [])

            # Get solutions from source domain not already in target
            novel = [s for s in source_solutions if s not in target_solutions]

            if novel:
                solutions.extend([{
                    "transferred_from": source_domain,
                    "applied_to": target_domain,
                    "category": category,
                    "solutions": novel,
                }])

    if not solutions:
        # Fallback: just list source domain solutions
        for category, domains in CROSS_DOMAIN_SOLUTIONS.items():
            source_solutions = domains.get(source_domain.lower(), [])
            if source_solutions:
                solutions.append({
                    "transferred_from": source_domain,
                    "applied_to": target_domain,
                    "category": category,
                    "solutions": source_solutions,
                })

    return json.dumps({
        "design_problem": design_problem,
        "source_domain": source_domain,
        "target_domain": target_domain,
        "transferred_solutions": solutions,
        "available_domains": list(CROSS_DOMAIN_SOLUTIONS.get(list(CROSS_DOMAIN_SOLUTIONS.keys())[0], {}).keys()),
    }, indent=2)


def main():
    """Start the mcp-commander-ideas MCP server."""
    server.run()


if __name__ == "__main__":
    main()
