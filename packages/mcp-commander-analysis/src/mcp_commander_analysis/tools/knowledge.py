"""Knowledge Search MCP tools.

Registers tools for searching the CAD knowledge base, explaining GD&T
symbols, and recommending design improvements based on drawing analysis.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Global singleton for the knowledge base (lazy-initialized on first use)
_kb_instance: Any | None = None


def _get_knowledge_base():
    """Get or create the global KnowledgeBase singleton."""
    global _kb_instance
    if _kb_instance is None:
        from mcp_commander_analysis.api.embeddings import KnowledgeBase
        _kb_instance = KnowledgeBase()
    return _kb_instance


# ---------------------------------------------------------------------------
# GD&T symbol reference database
# ---------------------------------------------------------------------------

_GDNT_REFERENCE: dict[str, dict[str, str]] = {
    "flatness": {
        "name": "Flatness",
        "symbol": "⌢",
        "category": "Form",
        "standard": "ASME Y14.5-2018",
        "feature_controlled": "A single planar surface (no datum required).",
        "datum_requirements": "None — flatness does not reference datums.",
        "tolerance_zone": "Two parallel planes separated by the specified tolerance value.",
        "interpretation": (
            "Every point on the controlled surface must lie between two parallel "
            "planes that are the specified tolerance apart. Flatness controls the "
            "form of a surface independently of its orientation or location."
        ),
        "applications": [
            "Mating/sealing surfaces (flanges, gasket surfaces)",
            "Bearing mounting surfaces",
            "Machine mounting bases",
            "Datum feature surfaces that will be referenced by other tolerances",
            "Precision sliding surfaces (ways, guide rails)",
        ],
    },
    "straightness": {
        "name": "Straightness",
        "symbol": "⏤",
        "category": "Form",
        "standard": "ASME Y14.5-2018",
        "feature_controlled": "A line element (surface line or derived median line).",
        "datum_requirements": "Surface line — no datum. Derived median line — requires datums.",
        "tolerance_zone": "Two parallel lines (2D) or a cylindrical zone (3D axis).",
        "interpretation": (
            "For a surface line: every point on the line element must lie between two "
            "parallel lines separated by the tolerance. For a derived median line "
            "(axis straightness): the axis must fit within a cylinder of the specified diameter."
        ),
        "applications": [
            "Shaft axis straightness for bearing fit",
            "Long structural members (bars, rails)",
            "Edge straightness of sheet metal parts",
            "Piston rod straightness for hydraulic cylinders",
        ],
    },
    "circularity": {
        "name": "Circularity (Roundness)",
        "symbol": "○",
        "category": "Form",
        "standard": "ASME Y14.5-2018",
        "feature_controlled": "A circular cross-section (cylinder, cone, sphere).",
        "datum_requirements": "None — applies to each cross-section independently.",
        "tolerance_zone": "Two concentric circles separated by the specified tolerance (radial distance).",
        "interpretation": (
            "Each cross-section perpendicular to the axis must lie between two concentric "
            "circles whose radial separation equals the tolerance. Controls out-of-roundness "
            "like ovality, lobing, and waviness."
        ),
        "applications": [
            "Bearing journals",
            "Piston/cylinder mating surfaces",
            "Seal surfaces (O-ring grooves)",
            "Precision rotating components (spindles, arbors)",
        ],
    },
    "cylindricity": {
        "name": "Cylindricity",
        "symbol": "⌭",
        "category": "Form",
        "standard": "ASME Y14.5-2018",
        "feature_controlled": "A cylindrical surface (overall form).",
        "datum_requirements": "None — controls the entire cylindrical surface.",
        "tolerance_zone": "Two coaxial cylinders separated by the specified tolerance (radial distance).",
        "interpretation": (
            "The entire cylindrical surface must lie between two coaxial cylinders "
            "whose radial separation equals the tolerance. Cylindricity simultaneously "
            "controls circularity, straightness, and taper of the cylinder."
        ),
        "applications": [
            "Precision bore cylinders",
            "Hydraulic/pneumatic cylinder bores",
            "Bearing races",
            "Precision shafts for interference fits",
        ],
    },
    "perpendicularity": {
        "name": "Perpendicularity",
        "symbol": "⊥",
        "category": "Orientation",
        "standard": "ASME Y14.5-2018",
        "feature_controlled": "A surface, axis, or line element at 90° to a datum.",
        "datum_requirements": "One datum reference required (the reference plane/axis).",
        "tolerance_zone": "Two parallel planes or a cylindrical zone perpendicular to the datum.",
        "interpretation": (
            "The controlled feature must lie within the tolerance zone that is perpendicular "
            "to the specified datum. For a surface: between two parallel planes perpendicular "
            "to the datum. For an axis: within a cylinder perpendicular to the datum."
        ),
        "applications": [
            "Flange faces perpendicular to a shaft axis",
            "Hole axes perpendicular to mounting surfaces",
            "Machine column alignment",
            "Locating pin orientation",
        ],
    },
    "parallelism": {
        "name": "Parallelism",
        "symbol": "∥",
        "category": "Orientation",
        "standard": "ASME Y14.5-2018",
        "feature_controlled": "A surface or axis parallel to a datum.",
        "datum_requirements": "One datum reference required.",
        "tolerance_zone": "Two parallel planes or a cylindrical zone parallel to the datum.",
        "interpretation": (
            "The controlled feature must lie within the tolerance zone that is parallel "
            "to the specified datum. Controls orientation but not location."
        ),
        "applications": [
            "Guide rail surfaces",
            "Opposite faces of a slot or channel",
            "Parallel bore axes in multi-spindle heads",
            "Clamp jaw alignment",
        ],
    },
    "angularity": {
        "name": "Angularity",
        "symbol": "∠",
        "category": "Orientation",
        "standard": "ASME Y14.5-2018",
        "feature_controlled": "A surface, axis, or line at a specified angle to a datum.",
        "datum_requirements": "One datum reference required (and a basic angle dimension).",
        "tolerance_zone": "Two parallel planes at the specified angle to the datum.",
        "interpretation": (
            "The controlled feature must lie within two parallel planes separated by the "
            "tolerance and oriented at the specified basic angle to the datum."
        ),
        "applications": [
            "Angled mounting surfaces",
            "V-groove features",
            "Tapered hole axes",
            "Weld preparation angles",
        ],
    },
    "position": {
        "name": "Position",
        "symbol": "⌖",
        "category": "Location",
        "standard": "ASME Y14.5-2018",
        "feature_controlled": "The location of a feature (hole, slot, boss) from datums.",
        "datum_requirements": "One or more datum references required (typically A, B, C).",
        "tolerance_zone": "A cylindrical zone (for holes) or two parallel planes (for slots) "
        "centered at the true position.",
        "interpretation": (
            "The axis of the controlled feature must fall within the specified tolerance zone "
            "centered at the true position (theoretically exact location defined by basic dimensions). "
            "At MMC, bonus tolerance is added as the feature departs from MMC."
        ),
        "applications": [
            "Bolt hole patterns",
            "Pin locations for alignment",
            "Critical bore locations in housings",
            "Connector mounting holes on PCBs",
            "Feature locations in multi-cavity molds",
        ],
    },
    "concentricity": {
        "name": "Concentricity",
        "symbol": "◎",
        "category": "Location",
        "standard": "ASME Y14.5-2018",
        "feature_controlled": "The median points of a cylindrical feature relative to a datum axis.",
        "datum_requirements": "One datum axis reference required.",
        "tolerance_zone": "A cylindrical zone coaxial with the datum axis.",
        "interpretation": (
            "The median points of the controlled feature must lie within a cylindrical zone "
            "coaxial with the datum axis. Concentricity controls both form and location. "
            "Note: often replaced by runout or position for practical applications."
        ),
        "applications": [
            "Balance-critical rotating parts",
            "Precision bearing journals",
            "Coaxial bores in multi-stage gearboxes",
        ],
    },
    "symmetry": {
        "name": "Symmetry",
        "symbol": "⌯",
        "category": "Location",
        "standard": "ASME Y14.5-2018",
        "feature_controlled": "The median points of two opposed features relative to a datum center plane.",
        "datum_requirements": "One datum center plane reference required.",
        "tolerance_zone": "Two parallel planes equidistant about the datum center plane.",
        "interpretation": (
            "The median points of the controlled feature must lie between two parallel planes "
            "equidistant about the datum center plane, with total separation equal to the tolerance."
        ),
        "applications": [
            "Keyways symmetric about a shaft centerline",
            "Symmetrically located features on housings",
        ],
    },
    "circular_runout": {
        "name": "Circular Runout",
        "symbol": "↗",
        "category": "Runout",
        "standard": "ASME Y14.5-2018",
        "feature_controlled": "Cross-sectional variation of a surface during one full rotation.",
        "datum_requirements": "One datum axis reference required.",
        "tolerance_zone": "A circular zone (indicator dial reading) at each cross-section.",
        "interpretation": (
            "At each cross-section, the total indicator reading (TIR) of the surface during one "
            "full rotation about the datum axis must not exceed the specified tolerance. Controls "
            "circularity, coaxiality, and straightness at each cross-section independently."
        ),
        "applications": [
            "Shaft surfaces running in bearings",
            "Flange faces perpendicular to a rotating axis",
            "Seal surface runout",
        ],
    },
    "total_runout": {
        "name": "Total Runout",
        "symbol": "↗↗",
        "category": "Runout",
        "standard": "ASME Y14.5-2018",
        "feature_controlled": "Full-surface cumulative variation during rotation.",
        "datum_requirements": "One datum axis reference required.",
        "tolerance_zone": "A cylindrical zone (3D envelope) about the datum axis.",
        "interpretation": (
            "The entire surface must lie within the specified tolerance zone during full rotation "
            "about the datum axis. Unlike circular runout (which checks individual sections), "
            "total runout controls the entire surface simultaneously — including cylindricity, "
            "coaxiality, straightness, taper, and perpendicularity."
        ),
        "applications": [
            "Critical rotating shaft assemblies",
            "High-speed spindle surfaces",
            "Aerospace engine components",
        ],
    },
}


def register_knowledge_tools(mcp: Any) -> None:
    """Register all knowledge search tools on the given FastMCP server."""

    @mcp.tool()
    def search_cad_tutorials(
        query: str,
        category: str = "all",
        top_k: int = 5,
    ) -> str:
        """Search the CAD knowledge base for tutorials, standards, and best practices.

        Uses a RAG (Retrieval-Augmented Generation) system with sentence-transformer
        embeddings and FAISS similarity search to find relevant knowledge entries.
        On first call, the knowledge base is initialized with 22 built-in entries
        covering GD&T, sheet metal, machining, tolerancing, and more.

        Args:
            query: Natural language search query (e.g., "how to specify position
                tolerance for bolt holes", "minimum bend radius for aluminum").
            category: Filter by knowledge category. One of: "all", "sketching",
                "dimensioning", "gdnt", "sheet_metal", "assembly",
                "drawing_views", "materials", "manufacturing", "standards".
            top_k: Maximum number of results to return (default 5).

        Returns:
            Ranked list of relevant knowledge entries with titles, content
            excerpts, relevance scores, and source information.
        """
        try:
            kb = _get_knowledge_base()
            results = kb.search(query, top_k=top_k)

            if not results:
                return (
                    f"No results found for query: '{query}'\n"
                    f"Category filter: {category}\n"
                    f"Tip: Try broader search terms or different category."
                )

            # Apply category filter if not "all"
            if category != "all":
                results = [r for r in results if r.get("category", "") == category]
                if not results:
                    return (
                        f"No results found for query: '{query}' in category '{category}'.\n"
                        f"Try 'all' categories or a different search term."
                    )

            parts: list[str] = [
                f"Knowledge Search Results for: '{query}'",
                f"Category: {category} | Results: {len(results)}\n",
            ]

            for i, r in enumerate(results, 1):
                parts.append(f"[{i}] {r['title']} (score: {r['score']:.3f})")
                parts.append(f"    Category: {r.get('category', 'N/A')}")
                parts.append(f"    Source: {r.get('source', 'N/A')}")
                # Truncate content for readability
                content = r.get("content", "")
                if len(content) > 300:
                    content = content[:300] + "..."
                parts.append(f"    Content: {content}")
                parts.append("")

            return "\n".join(parts)

        except ImportError as exc:
            logger.warning("Knowledge base dependencies not available: %s", exc)
            return (
                f"Error: Knowledge search unavailable — {exc}\n"
                "Install sentence-transformers and faiss-cpu to enable knowledge search."
            )
        except Exception as exc:
            logger.exception("Knowledge search failed")
            return f"Error: Knowledge search failed: {exc}"

    @mcp.tool()
    def explain_gdnt_symbol(
        symbol: str,
        context: str = "",
    ) -> str:
        """Explain a GD&T (Geometric Dimensioning and Tolerancing) symbol.

        Provides comprehensive information about a GD&T symbol including its name,
        ASME Y14.5 category, feature controlled, datum requirements, tolerance
        zone shape, practical interpretation, and common application examples.

        Args:
            symbol: The GD&T symbol name. Options: "flatness", "straightness",
                "circularity", "cylindricity", "perpendicularity", "parallelism",
                "angularity", "position", "concentricity", "symmetry",
                "circular_runout", "total_runout".
            context: Optional context about where or how the symbol is used
                (e.g., "on a bearing journal surface", "for a bolt hole pattern").
                This adds application-specific advice to the explanation.

        Returns:
            Detailed explanation of the GD&T symbol with all properties and
            context-aware recommendations.
        """
        symbol_lower = symbol.strip().lower()

        # Handle aliases
        alias_map = {
            "roundness": "circularity",
            "profile_line": "profile_of_line",
            "profile_surface": "profile_of_surface",
            "true_position": "position",
        }
        symbol_lower = alias_map.get(symbol_lower, symbol_lower)

        ref = _GDNT_REFERENCE.get(symbol_lower)

        if ref is None:
            available = ", ".join(sorted(_GDNT_REFERENCE.keys()))
            return (
                f"GD&T symbol '{symbol}' not recognized.\n"
                f"Available symbols: {available}\n\n"
                "Tip: Use the exact symbol name (e.g., 'flatness', 'position', 'perpendicularity')."
            )

        parts: list[str] = [
            f"GD&T Symbol: {ref['symbol']} {ref['name']}",
            f"Category: {ref['category']} | Standard: {ref['standard']}",
            "",
            f"Feature Controlled: {ref['feature_controlled']}",
            f"Datum Requirements: {ref['datum_requirements']}",
            f"Tolerance Zone: {ref['tolerance_zone']}",
            "",
            f"Interpretation:\n  {ref['interpretation']}",
            "",
            "Common Applications:",
        ]

        for app in ref["applications"]:
            parts.append(f"  • {app}")

        if context:
            parts.append("")
            parts.append(f"Context-Specific Advice (for: {context}):")
            # Generate contextual advice based on the symbol
            advice = _contextual_advice(symbol_lower, context)
            parts.append(f"  {advice}")

        return "\n".join(parts)

    @mcp.tool()
    def recommend_design_improvements(
        analysis_text: str,
        focus: str = "all",
        urgency: str = "all",
    ) -> str:
        """Recommend design improvements based on a drawing analysis.

        Analyzes the drawing analysis text (from analyze_drawing_image or similar)
        and generates actionable, prioritized recommendations for improving the
        design. Uses an LLM when available; falls back to template-based
        recommendations.

        Args:
            analysis_text: The text output from a drawing analysis tool
                (e.g., analyze_drawing_image). Should contain observations
                about the drawing's features, dimensions, and potential issues.
            focus: Area to focus recommendations on. One of: "all",
                "manufacturability", "tolerancing", "annotation",
                "view_layout", "cost".
            urgency: Filter by urgency level. One of: "all", "critical",
                "important", "nice_to_have".

        Returns:
            Prioritized list of recommendations with priority level, category,
            issue description, specific recommendation, estimated impact,
            and implementation effort.
        """
        try:
            import os

            has_llm = bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
        except Exception:
            has_llm = False

        if not has_llm:
            return _template_recommendations(analysis_text, focus, urgency)

        try:
            from openai import OpenAI

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            prompt = (
                f"You are an expert mechanical design engineer reviewing a drawing analysis.\n\n"
                f"Drawing Analysis:\n{analysis_text[:3000]}\n\n"
                f"Focus areas: {focus}\n"
                f"Urgency filter: {urgency}\n\n"
                f"Generate specific, actionable design improvement recommendations.\n"
                f"For each recommendation, provide:\n"
                f"1. Priority: CRITICAL / IMPORTANT / NICE_TO_HAVE\n"
                f"2. Category: manufacturability / tolerancing / annotation / view_layout / cost\n"
                f"3. Issue: What problem was identified\n"
                f"4. Recommendation: Specific action to take\n"
                f"5. Estimated Impact: high / medium / low\n"
                f"6. Effort: high / medium / low\n\n"
                f"Format as structured text."
            )

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2048,
            )

            result = response.choices[0].message.content or ""
            return (
                f"Design Improvement Recommendations\n"
                f"Focus: {focus} | Urgency: {urgency}\n\n"
                f"{result}"
            )

        except Exception as exc:
            logger.exception("LLM recommendation failed")
            return f"Error: LLM recommendation failed: {exc}\n\n" + _template_recommendations(
                analysis_text, focus, urgency
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _contextual_advice(symbol: str, context: str) -> str:
    """Generate contextual advice for a GD&T symbol given usage context."""
    ctx_lower = context.lower()

    if "bearing" in ctx_lower:
        if symbol in ("circularity", "cylindricity", "roundness"):
            return (
                "For bearing surfaces, ensure cylindricity is tight enough for the "
                "bearing class. Precision bearings typically require Ra ≤ 0.4 µm "
                "and cylindricity ≤ 0.005 mm. Verify surface finish specification."
            )
        if symbol == "position":
            return (
                "For bearing housing holes, position tolerance controls alignment. "
                "Use composite position: PLTZF for pattern location, FRTZF for "
                "hole-to-hole spacing. Consider MMC for bonus tolerance."
            )

    if "bolt" in ctx_lower or "fastener" in ctx_lower:
        if symbol == "position":
            return (
                "For bolt hole patterns, use position at MMC for maximum bonus tolerance. "
                "Fixed fasteners: position tolerance = (hole MMC - bolt MMC) / 2. "
                "Floating fasteners: position tolerance = (hole MMC - bolt MMC) / 0."
            )

    if "seal" in ctx_lower or "gasket" in ctx_lower:
        if symbol == "flatness":
            return (
                "Sealing surfaces require very tight flatness. Typical gasket surfaces: "
                "flatness ≤ 0.05 mm. For O-ring grooves, flatness + surface finish "
                "(Ra ≤ 0.8 µm) are both critical."
            )

    return (
        f"Based on the context '{context}', ensure the {symbol} tolerance is "
        f"appropriate for the functional requirement and the manufacturing process "
        f"can achieve it cost-effectively."
    )


def _template_recommendations(
    analysis_text: str,
    focus: str,
    urgency: str,
) -> str:
    """Generate template-based recommendations when no LLM is available."""
    templates: list[dict[str, str]] = []

    if focus in ("all", "tolerancing"):
        templates.extend([
            {
                "priority": "IMPORTANT",
                "category": "tolerancing",
                "issue": "Review tolerance stack-up for critical assemblies",
                "recommendation": "Perform 1D or 3D tolerance stack analysis on critical dimension chains to verify clearances and fits.",
                "impact": "high",
                "effort": "medium",
            },
            {
                "priority": "IMPORTANT",
                "category": "tolerancing",
                "issue": "Consider GD&T instead of ± dimensions for critical features",
                "recommendation": "Replace ± position dimensions with GD&T position tolerance for holes and mating features. This provides clearer functional intent and bonus tolerance at MMC.",
                "impact": "high",
                "effort": "medium",
            },
        ])

    if focus in ("all", "manufacturability"):
        templates.extend([
            {
                "priority": "IMPORTANT",
                "category": "manufacturability",
                "issue": "Minimize internal sharp corners",
                "recommendation": "Add fillet radii to all internal corners (min = tool radius for CNC, material thickness for sheet metal). Sharp internal corners require EDM and increase cost significantly.",
                "impact": "medium",
                "effort": "low",
            },
            {
                "priority": "NICE_TO_HAVE",
                "category": "manufacturability",
                "issue": "Review wall thickness uniformity",
                "recommendation": "Ensure wall thickness variations do not exceed 25% to prevent warping, uneven cooling, and stress concentration.",
                "impact": "medium",
                "effort": "low",
            },
        ])

    if focus in ("all", "annotation"):
        templates.extend([
            {
                "priority": "IMPORTANT",
                "category": "annotation",
                "issue": "Verify all critical dimensions are present",
                "recommendation": "Cross-check that every functional dimension is explicitly called out. Missing dimensions force manufacturers to assume, leading to rejects.",
                "impact": "high",
                "effort": "low",
            },
            {
                "priority": "NICE_TO_HAVE",
                "category": "annotation",
                "issue": "Add surface finish specifications to mating surfaces",
                "recommendation": "Specify Ra values on all functional surfaces (bearing seats, seal surfaces, sliding interfaces). Unspecified finishes lead to inconsistent quality.",
                "impact": "medium",
                "effort": "low",
            },
        ])

    if focus in ("all", "view_layout"):
        templates.extend([
            {
                "priority": "NICE_TO_HAVE",
                "category": "view_layout",
                "issue": "Consider adding section or detail views for complex features",
                "recommendation": "If there are internal features or small details not clearly visible in standard orthographic views, add section views or detail views with appropriate scale.",
                "impact": "medium",
                "effort": "low",
            },
        ])

    if focus in ("all", "cost"):
        templates.extend([
            {
                "priority": "CRITICAL",
                "category": "cost",
                "issue": "Review tight tolerances for cost impact",
                "recommendation": "Tolerances tighter than ±0.025 mm significantly increase CNC machining cost. Verify that tight tolerances are functionally required; loosen where possible.",
                "impact": "high",
                "effort": "medium",
            },
        ])

    if not templates:
        return (
            f"[MOCK - no LLM API key] Design Improvement Recommendations\n"
            f"Focus: {focus} | Urgency: {urgency}\n\n"
            f"No template recommendations available for this combination.\n"
            f"Set OPENAI_API_KEY for AI-powered analysis based on your drawing.\n\n"
            f"Analysis text received ({len(analysis_text)} chars) would be processed "
            f"by the LLM to generate specific recommendations."
        )

    # Filter by urgency
    if urgency != "all":
        templates = [t for t in templates if t["priority"] == urgency.upper()]

    parts = [
        f"[MOCK - no LLM API key] Design Improvement Recommendations",
        f"Focus: {focus} | Urgency: {urgency}",
        f"Analysis text: {len(analysis_text)} chars received\n",
    ]

    priority_order = {"CRITICAL": 0, "IMPORTANT": 1, "NICE_TO_HAVE": 2}
    templates.sort(key=lambda t: priority_order.get(t["priority"], 99))

    for i, t in enumerate(templates, 1):
        parts.append(f"[{i}] Priority: {t['priority']} | Category: {t['category']}")
        parts.append(f"    Issue: {t['issue']}")
        parts.append(f"    Recommendation: {t['recommendation']}")
        parts.append(f"    Impact: {t['impact']} | Effort: {t['effort']}")
        parts.append("")

    return "\n".join(parts)
