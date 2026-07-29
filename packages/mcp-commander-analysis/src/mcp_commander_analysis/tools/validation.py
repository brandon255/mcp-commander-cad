"""Design Validation MCP tools.

Registers tools for validating engineering drawings against standards
(ASME Y14.5) and checking designs for manufacturability (DFM analysis).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def register_validation_tools(mcp: Any) -> None:
    """Register all design validation tools on the given FastMCP server."""

    @mcp.tool()
    def validate_sketch_design(
        image_path: str,
        rules: str = "all",
        standard: str = "ASME",
    ) -> str:
        """Validate a sketch/drawing design against engineering standards.

        Uses VLM to visually inspect the drawing against specified validation
        rules. For each rule, returns pass/fail status, issue description, and
        a recommendation. When no VLM API key is available, returns a template
        validation report.

        Args:
            image_path: Path to the drawing/sketch image file.
            rules: Comma-separated list of validation rules to check. Options:
                "all", "constraints_complete", "no_open_profiles",
                "no_self_intersections", "proper_tolerancing", "gdnt_compliant",
                "dimension_chain_complete", "title_block_complete",
                "view_projections", "standard_compliance".
            standard: Engineering standard to validate against. One of:
                "ASME", "ISO", "DIN".

        Returns:
            Validation results with per-rule pass/fail/warning status,
            descriptions of issues, recommendations, and an overall summary.
        """
        path = Path(image_path)
        if not path.exists():
            return f"Error: Image file not found: {image_path}"

        requested = set(r.strip().lower() for r in rules.split(","))
        all_rules = {
            "constraints_complete",
            "no_open_profiles",
            "no_self_intersections",
            "proper_tolerancing",
            "gdnt_compliant",
            "dimension_chain_complete",
            "title_block_complete",
            "view_projections",
            "standard_compliance",
        }
        check_set = all_rules if "all" in requested else requested & all_rules

        # Build rule descriptions for the VLM prompt
        rule_descriptions: dict[str, str] = {
            "constraints_complete": (
                "All sketch entities are fully constrained (geometric and dimensional). "
                "No degrees of freedom remain on any entity."
            ),
            "no_open_profiles": (
                "All closed-profile sketches have no gaps or open endpoints. "
                "Open profiles are acceptable only for extruded cuts/surfaces."
            ),
            "no_self_intersections": (
                "No sketch entities cross or overlap themselves or other entities "
                "in unintended ways."
            ),
            "proper_tolerancing": (
                "All critical dimensions have appropriate tolerances. "
                "Default tolerances are noted in the title block."
            ),
            "gdnt_compliant": (
                "GD&T symbols follow the applicable standard (ASME Y14.5/ISO 1101). "
                "Feature control frames have correct structure: symbol, tolerance, datum."
            ),
            "dimension_chain_complete": (
                "All critical dimensions form a complete chain from datum/reference. "
                "No redundant or floating dimensions."
            ),
            "title_block_complete": (
                "Title block contains all required fields: title, drawing number, "
                "revision, scale, units, material, tolerances, drawn-by, date."
            ),
            "view_projections": (
                "Drawing views follow standard orthographic projection conventions. "
                "Views are properly arranged and labeled."
            ),
            "standard_compliance": (
                "Drawing follows general drafting standard conventions "
                "(line types, hatching, notation, etc.)."
            ),
        }

        try:
            import os

            has_vlm = bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
        except Exception:
            has_vlm = False

        if not has_vlm:
            # Return template validation without VLM
            lines: list[str] = [
                f"[MOCK - no VLM API key] Validation Report for: {image_path}",
                f"Standard: {standard} | Rules checked: {len(check_set)}",
                f"Note: Set OPENAI_API_KEY or ANTHROPIC_API_KEY for real visual validation.\n",
            ]
            for rule in sorted(check_set):
                lines.append(f"  [{rule}]")
                lines.append(f"    Status: UNKNOWN (no VLM available)")
                lines.append(
                    f"    Description: {rule_descriptions.get(rule, 'N/A')}"
                )
                lines.append(
                    f"    Recommendation: Run with VLM enabled to perform visual inspection."
                )
                lines.append("")
            return "\n".join(lines)

        # Real VLM validation
        try:
            from mcp_commander_analysis.api.vlm import VisionClient

            client = VisionClient()

            rules_text = "\n".join(
                f"  - {rule}: {rule_descriptions.get(rule, 'Check this rule.')}"
                for rule in sorted(check_set)
            )

            prompt = (
                f"You are an expert engineering drawing inspector validating a drawing "
                f"against {standard} standards.\n\n"
                f"Analyze this drawing and check these rules:\n{rules_text}\n\n"
                f"For each rule, respond with:\n"
                f"  1. PASS, FAIL, or WARNING\n"
                f"  2. A brief description of any issue found\n"
                f"  3. A specific recommendation to fix the issue\n\n"
                f"Be strict — flag anything that could cause manufacturing or "
                f"interpretation problems. Format as structured text."
            )

            result = client.analyze_image(str(path), prompt)

            # Append summary header
            return (
                f"Validation Report for: {image_path}\n"
                f"Standard: {standard} | Rules checked: {len(check_set)}\n"
                f"Provider: {client.provider} | Model: {client.model}\n\n"
                f"{result}"
            )

        except Exception as exc:
            logger.exception("Validation failed")
            return f"Error: Validation failed: {exc}"

    @mcp.tool()
    def check_manufacturability(
        image_path: str,
        process: str = "cnc",
        material: str = "aluminum_6061",
        detail_level: str = "standard",
    ) -> str:
        """Check a design for manufacturability (DFM analysis) from a drawing.

        Uses VLM to analyze geometry features against process-specific design
        rules and returns a DFM score with identified issues and recommendations.
        Falls back to a template analysis when no VLM API key is available.

        Args:
            image_path: Path to the drawing/design image file.
            process: Manufacturing process to check against. One of: "cnc",
                "injection_molding", "sheet_metal", "3d_printing", "casting".
            material: Material specification (e.g. "aluminum_6061",
                "steel_1045", "abs", "nylon").
            detail_level: Level of detail. One of: "brief", "standard",
                "detailed".

        Returns:
            DFM analysis including overall score (0-100), issues list with
            severity (critical/warning/info), process-specific recommendations,
            and material-specific notes.
        """
        path = Path(image_path)
        if not path.exists():
            return f"Error: Image file not found: {image_path}"

        # Process-specific DFM rules
        process_rules: dict[str, str] = {
            "cnc": (
                "CNC Machining DFM rules:\n"
                "- Minimum wall thickness: 1.5mm (aluminum), 2mm (steel)\n"
                "- Minimum internal corner fillet radius = tool radius (typically 1-3mm)\n"
                "- Deep pockets: depth ≤ 4× width for standard tooling\n"
                "- Hole depth ≤ 10× diameter (standard drilling)\n"
                "- Avoid undercuts (require 5-axis or special tooling)\n"
                "- Minimum feature size: 0.5mm\n"
                "- Thread depth: 1.5× diameter minimum\n"
                "- Draft angles not required (not a molded part)\n"
                "- Tolerance: ±0.025mm is achievable; tighter is expensive\n"
                "- Minimize setups: features accessible from fewer sides = lower cost"
            ),
            "injection_molding": (
                "Injection Molding DFM rules:\n"
                "- Draft angle: 1-2° minimum on all vertical surfaces\n"
                "- Uniform wall thickness: variation should not exceed 25%\n"
                "- Minimum wall thickness: 0.5mm (polycarbonate), 0.8mm (ABS), 1mm (nylon)\n"
                "- Maximum wall thickness: 4-5mm (avoid sink marks and long cycle times)\n"
                "- Undercuts require side actions or lifters (adds cost)\n"
                "- Corner radii: ≥ 0.5mm to reduce stress concentration\n"
                "- Rib thickness: ≤ 60% of adjacent wall thickness\n"
                "- Boss diameter: ≥ 2× wall thickness\n"
                "- Ejector pin locations must not affect cosmetic surfaces\n"
                "- Text/embossing: 0.5mm height minimum, raised text preferred"
            ),
            "sheet_metal": (
                "Sheet Metal DFM rules:\n"
                "- Minimum bend radius: equal to material thickness (mild steel), 1.5× (aluminum)\n"
                "- Bend relief: width ≥ material thickness, depth ≥ material thickness + bend radius\n"
                "- Minimum flange height: 2× material thickness + bend radius\n"
                "- Hole-to-edge distance: ≥ 1.5× material thickness from center\n"
                "- Hole-to-hole distance: ≥ 2× material thickness between centers\n"
                "- Minimum hole diameter: ≥ material thickness\n"
                "- Tab/slot width: ≥ 2× material thickness\n"
                "- Hem bend: minimum outer radius = material thickness\n"
                "- K-factor: 0.33-0.42 (air bending)\n"
                "- Avoid bent-to-bend distances less than 3× material thickness"
            ),
            "3d_printing": (
                "3D Printing (Additive Manufacturing) DFM rules:\n"
                "- Minimum wall thickness: 1.2mm (FDM), 0.5mm (SLA), 0.7mm (SLS)\n"
                "- Overhang angle: ≤ 45° from vertical without supports (FDM/SLA)\n"
                "- Minimum supported overhang angle: 60° (FDM), 80° (SLA)\n"
                "- Bridging span: ≤ 10mm unsupported (FDM)\n"
                "- Minimum feature size: 0.5mm (FDM), 0.1mm (SLA)\n"
                "- Minimum hole diameter: 2mm (FDM), 0.5mm (SLA)\n"
                "- Minimum gap/passage: 0.5mm (FDM), 0.3mm (SLA)\n"
                "- Layer height affects surface finish: 0.1-0.3mm (FDM)\n"
                "- Anisotropic strength: design for loading along layer lines\n"
                "- Support removal: design self-supporting where possible"
            ),
            "casting": (
                "Casting DFM rules:\n"
                "- Draft angle: 1-3° minimum on surfaces perpendicular to parting line\n"
                "- Minimum wall thickness: 4-5mm (sand casting), 2-3mm (die casting)\n"
                "- Uniform wall thickness: avoid sudden transitions (stress concentration)\n"
                "- Fillet radii: ≥ 1.5mm for sand casting, ≥ 0.5mm for die casting\n"
                "- Core feasibility: internal features must allow core removal\n"
                "- Parting line: minimize complexity, avoid undercuts\n"
                "- Machining allowance: 2-5mm on critical surfaces for post-machining\n"
                "- Riser/gate placement: must not interfere with function or appearance\n"
                "- Shrinkage compensation: include in critical dimensions (1-2%)\n"
                "- Surface finish: Ra 6.3-25 µm as-cast; finer requires post-machining"
            ),
        }

        try:
            import os

            has_vlm = bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
        except Exception:
            has_vlm = False

        if not has_vlm:
            rules_text = process_rules.get(process, "")
            return (
                f"[MOCK - no VLM API key] DFM Analysis for: {image_path}\n\n"
                f"Process: {process} | Material: {material}\n"
                f"Detail level: {detail_level}\n"
                f"DFM Score: N/A (requires VLM for visual analysis)\n\n"
                f"Process-specific rules that would be checked:\n{rules_text}\n\n"
                f"Set OPENAI_API_KEY or ANTHROPIC_API_KEY for real DFM analysis."
            )

        try:
            from mcp_commander_analysis.api.vlm import VisionClient

            client = VisionClient()

            prompt = (
                f"You are an expert manufacturing engineer performing a Design for "
                f"Manufacturability (DFM) analysis.\n\n"
                f"Process: {process.upper()}\n"
                f"Material: {material}\n"
                f"Detail level: {detail_level}\n\n"
                f"Analyze this drawing against these {process.upper()} DFM rules:\n"
                f"{process_rules.get(process, 'Standard manufacturing rules.')}\n\n"
                f"For your analysis, provide:\n"
                f"1. Overall DFM score (0-100)\n"
                f"2. List of issues with severity: CRITICAL, WARNING, or INFO\n"
                f"3. Specific recommendation for each issue\n"
                f"4. Estimated cost impact of each issue (high/medium/low)\n"
                f"5. Summary of recommended changes\n\n"
                f"Format as structured text with clear sections."
            )

            result = client.analyze_image(str(path), prompt)

            return (
                f"DFM Analysis for: {image_path}\n"
                f"Process: {process.upper()} | Material: {material}\n"
                f"Detail level: {detail_level}\n"
                f"Provider: {client.provider} | Model: {client.model}\n\n"
                f"{result}"
            )

        except Exception as exc:
            logger.exception("DFM analysis failed")
            return f"Error: DFM analysis failed: {exc}"
