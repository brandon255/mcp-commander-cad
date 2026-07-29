"""
Cross-Domain Transfer Operation.

Transfer proven design solutions from one industry domain to another.
Maintains a knowledge base of cross-domain solution mappings where techniques
validated in one field are applicable to another with adaptation.
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Cross-domain solution transfer database
# ---------------------------------------------------------------------------
CROSS_DOMAIN_DB: list[dict[str, str]] = [
    # Aerospace → Other
    {
        "source_domain": "Aerospace",
        "source_solution": "Weight-optimized titanium bracket with integral stiffening ribs",
        "target_domain": "Medical Devices",
        "target_application": "Surgical instrument handle requiring high strength-to-weight and biocompatibility",
        "adaptation_notes": "Switch Ti-6Al-4V to Ti-6Al-7Nb for better biocompatibility; reduce certification burden by simplifying load cases to ergonomic forces only.",
        "transfer_quality": "high",
    },
    {
        "source_domain": "Aerospace",
        "source_solution": "Honeycomb core sandwich panel for flat structural panels",
        "target_domain": "Automotive",
        "target_application": "Lightweight floor pan with superior NVH (noise, vibration, harshness) performance",
        "adaptation_notes": "Use aluminum honeycomb bonded to prepreg FRP faces; tool for high-volume production using roll-bonding instead of autoclave.",
        "transfer_quality": "medium",
    },
    {
        "source_domain": "Aerospace",
        "source_solution": "Fuel tank baffles to prevent slosh and maintain center of gravity",
        "target_domain": "Agricultural Equipment",
        "target_application": "Chemical spray tank baffling to prevent liquid surge during field turns",
        "adaptation_notes": "Simplify baffle geometry; use roto-molded polyethylene tank with molded-in baffles instead of machined aluminum.",
        "transfer_quality": "high",
    },
    {
        "source_domain": "Aerospace",
        "source_solution": "Redundant O-ring seal with backup ring in hydraulic actuators",
        "target_domain": "Oil & Gas",
        "target_application": "Subsea valve stem seal requiring double-barrier integrity",
        "adaptation_notes": "Upgrade to HNBR or FKM compounds for chemical compatibility; add metal backup rings in Hastelloy for sour gas service.",
        "transfer_quality": "high",
    },
    # Automotive → Other
    {
        "source_domain": "Automotive",
        "source_solution": "Self-pierce riveting (SPR) for aluminum-to-steel joints",
        "target_domain": "Consumer Electronics",
        "target_application": "Joining aluminum heatsink to steel chassis in laptop enclosure",
        "adaptation_notes": "Downsize rivet and die set for thin-sheet application (0.5-1.0mm total stack); use 2kW servo riveter for low-force, low-noise operation.",
        "transfer_quality": "medium",
    },
    {
        "source_domain": "Automotive",
        "source_solution": "Structural adhesive (epoxy) with crash-durable formulation for body-in-white",
        "target_domain": "Rail Transit",
        "target_application": "Bonding aluminum extrusion carbody panels with crash energy absorption requirement",
        "adaptation_notes": "Specify fire-smoke-toxicity (FST) rated adhesive per EN 45545; increase lap joint length for sustained load in vibration environment.",
        "transfer_quality": "high",
    },
    {
        "source_domain": "Automotive",
        "source_solution": "Transmission-mount damping bracket with dual-rate elastomer",
        "target_domain": "Industrial Machinery",
        "target_application": "Compressor mounting bracket requiring torsional vibration isolation",
        "adaptation_notes": "Use NR (natural rubber) for better low-temperature performance if outdoor; design for continuous compression set over 5-year service life.",
        "transfer_quality": "medium",
    },
    # Medical → Other
    {
        "source_domain": "Medical Devices",
        "source_solution": "Cannula tip geometry optimized for minimal tissue trauma",
        "target_domain": "Food Processing",
        "target_application": "Injector nozzle for precise filling without product shear damage",
        "adaptation_notes": "Scale up geometry 10-50x; material change to 316SS with electropolish; adapt for viscous fluids instead of tissue.",
        "transfer_quality": "low",
    },
    {
        "source_domain": "Medical Devices",
        "source_solution": "Snap-fit assembly with audible/tactile click confirmation for surgical tool",
        "target_domain": "Consumer Products",
        "target_application": "Two-piece enclosure with consumer-verifiable snap assembly (no tools)",
        "adaptation_notes": "Reduce precision requirements; use polypropylene for living-hinge version; design for 1000+ cycles of consumer use.",
        "transfer_quality": "high",
    },
    # Marine → Other
    {
        "source_domain": "Marine",
        "source_solution": "Cathodic protection with sacrificial zinc anodes on submerged steel",
        "target_domain": "Infrastructure",
        "target_application": "Buried steel pipeline corrosion protection in high-resistivity soil",
        "adaptation_notes": "Switch to magnesium anodes in high-resistivity soil; add reference electrodes for potential monitoring; design for 20-year replacement cycle.",
        "transfer_quality": "high",
    },
    {
        "source_domain": "Marine",
        "source_solution": "Teak deck caulking with polysulfide compound for flexible, watertight seams",
        "target_domain": "Architecture",
        "target_application": "Exterior tile joint sealing in swimming pool decks exposed to pool chemicals",
        "adaptation_notes": "Use polyurethane caulk instead of polysulfide for UV resistance; select NSF 61-rated formulation for potable water splash zones.",
        "transfer_quality": "medium",
    },
    # Consumer Electronics → Other
    {
        "source_domain": "Consumer Electronics",
        "source_solution": "Shield can with EMI gasket for RF shielding of PCB modules",
        "target_domain": "Automotive",
        "target_application": "ECU housing with EMI shielding meeting CISPR 25 Class 5 requirements",
        "adaptation_notes": "Size for automotive temperature range (-40 to +125°C); use nickel-copper conductive gasket; design for vibration per ISO 16750-3.",
        "transfer_quality": "high",
    },
    {
        "source_domain": "Consumer Electronics",
        "source_solution": "Flexible PCB (FPC) with controlled-impedance traces for high-speed signal routing",
        "target_domain": "Medical Devices",
        "target_application": "Catheter-tip flex circuit for sensor integration in minimally invasive tools",
        "adaptation_notes": "Use biocompatible polyimide (Kapton) substrate; encapsulate with Parylene-C coating; design for sterilization (EtO or gamma).",
        "transfer_quality": "high",
    },
    # Semiconductor → Other
    {
        "source_domain": "Semiconductor Manufacturing",
        "source_solution": "Cleanroom-compatible wafer handling with vacuum pick-and-place end effector",
        "target_domain": "Optics",
        "target_application": "Cleanroom lens handling for precision optical assembly without contamination",
        "adaptation_notes": "Add compliant pad (Vespel or PEEK) to vacuum cup to avoid lens surface damage; incorporate force-torque sensor for contact detection.",
        "transfer_quality": "medium",
    },
    # Architecture → Other
    {
        "source_domain": "Architecture / Construction",
        "source_solution": "Post-tensioned concrete slab for long-span floor with minimal deflection",
        "target_domain": "Heavy Industrial",
        "target_application": "Machine tool foundation slab requiring minimal dynamic deflection under cutting loads",
        "adaptation_notes": "Add polymer grout for leveling and vibration isolation; use unbonded tendons for post-construction re-stress capability; embed anchor bolts for machine mounting.",
        "transfer_quality": "medium",
    },
]

# ---------------------------------------------------------------------------
# Domain index for quick lookup
# ---------------------------------------------------------------------------
DOMAIN_INDEX: dict[str, list[int]] = {}
for _i, entry in enumerate(CROSS_DOMAIN_DB):
    src = entry["source_domain"]
    tgt = entry["target_domain"]
    DOMAIN_INDEX.setdefault(src, []).append(_i)
    DOMAIN_INDEX.setdefault(tgt, []).append(_i)


def _find_transfers(
    source_domain: Optional[str] = None,
    target_domain: Optional[str] = None,
    min_quality: str = "low",
) -> list[dict]:
    """Search the cross-domain database for matching transfers."""
    quality_rank = {"low": 0, "medium": 1, "high": 2}
    min_rank = quality_rank.get(min_quality, 0)

    matches: list[dict] = []
    for entry in CROSS_DOMAIN_DB:
        # Filter by source domain
        if source_domain and entry["source_domain"].lower() != source_domain.lower():
            # Also check partial match
            if source_domain.lower() not in entry["source_domain"].lower():
                continue
        # Filter by target domain
        if target_domain and entry["target_domain"].lower() != target_domain.lower():
            if target_domain.lower() not in entry["target_domain"].lower():
                continue
        # Filter by minimum quality
        if quality_rank.get(entry["transfer_quality"], 0) < min_rank:
            continue
        matches.append(entry)

    return matches


def cross_domain_transfer(
    source_domain: Optional[str] = None,
    target_domain: Optional[str] = None,
    challenge: Optional[str] = None,
    min_quality: str = "low",
) -> dict:
    """
    Transfer proven design solutions from one industry domain to another.

    Searches the cross-domain knowledge base for validated design solutions
    in a source industry that can be adapted for use in a target industry.

    Args:
        source_domain: The industry or field to transfer from
            (e.g. "Aerospace", "Automotive", "Medical Devices").
        target_domain: The industry or field to transfer to.
        challenge: Optional description of the design challenge to match
            against target_application fields.
        min_quality: Minimum transfer quality to include: "low", "medium", or "high".

    Returns:
        Dictionary with matching cross-domain transfers, source and target
        details, adaptation notes, and transfer quality ratings.
    """
    matches = _find_transfers(source_domain, target_domain, min_quality)

    # If a challenge description is provided, rank matches by keyword overlap
    if challenge and matches:
        challenge_words = set(challenge.lower().split())
        for m in matches:
            app_words = set(m["target_application"].lower().split())
            m["relevance_score"] = len(challenge_words & app_words) / max(len(challenge_words), 1)
        matches.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    all_domains = sorted(
        {e["source_domain"] for e in CROSS_DOMAIN_DB}
        | {e["target_domain"] for e in CROSS_DOMAIN_DB}
    )

    return {
        "source_domain": source_domain or "any",
        "target_domain": target_domain or "any",
        "challenge": challenge,
        "min_quality_filter": min_quality,
        "total_matches": len(matches),
        "available_domains": all_domains,
        "transfers": matches,
        "summary": (
            f"Found {len(matches)} cross-domain transfer(s)"
            + (f" from '{source_domain}' to '{target_domain}'" if source_domain and target_domain else "")
            + f" with quality ≥ {min_quality}."
        ),
    }
