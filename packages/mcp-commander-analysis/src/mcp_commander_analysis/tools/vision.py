"""Vision Analysis MCP tools.

Registers tools that leverage VLM (Vision Language Model) and OpenCV for
engineering drawing analysis and geometric feature recognition.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def register_vision_tools(mcp: Any) -> None:
    """Register all vision analysis tools on the given FastMCP server."""

    @mcp.tool()
    def analyze_drawing_image(
        image_path: str,
        focus: str = "all",
        detail_level: str = "standard",
    ) -> str:
        """Analyze an engineering drawing image using VLM vision.

        Sends the drawing image to a Vision Language Model (GPT-4o or Claude)
        and returns a comprehensive analysis of the drawing content. When no
        API key is available, returns a mock placeholder.

        Args:
            image_path: Path to the drawing image file (PNG, JPG, BMP, etc.).
            focus: What to focus the analysis on. One of: "all", "dimensions",
                "views", "annotations", "title_block", "gdnt".
            detail_level: Level of detail in the response. One of: "brief",
                "standard", "detailed".

        Returns:
            Comprehensive text analysis of the drawing including drawing type,
            views found, dimensions, annotations, title block info, GD&T
            symbols, materials, scale, and recommendations.
        """
        path = Path(image_path)
        if not path.exists():
            return f"Error: Image file not found: {image_path}"

        try:
            from mcp_commander_analysis.api.vlm import VisionClient

            client = VisionClient()
            prompt = VisionClient.engineering_drawing_prompt(
                focus=focus,
                detail_level=detail_level,
            )
            result = client.analyze_image(str(path), prompt)

            if client.provider == "mock":
                return (
                    f"[MOCK - no VLM API key] Drawing analysis unavailable for: {image_path}\n\n"
                    f"Set OPENAI_API_KEY or ANTHROPIC_API_KEY to enable real vision analysis.\n\n"
                    f"Requested focus: {focus} | Detail level: {detail_level}\n"
                    f"Expected analysis would include: drawing type, views, dimensions, "
                    f"annotations, title block, GD&T symbols, materials, scale, and recommendations."
                )

            return result

        except Exception as exc:
            logger.exception("Drawing analysis failed")
            return f"Error: Drawing analysis failed: {exc}"

    @mcp.tool()
    def recognize_features_in_sketch(
        image_path: str,
        feature_types: str = "all",
        output_format: str = "summary",
    ) -> str:
        """Recognize geometric features in a sketch or drawing image.

        Uses OpenCV for primitive detection (lines, circles, arcs, rectangles)
        and optionally VLM for semantic classification (fillets, slots, chamfers,
        etc.). Works even without a VLM API key using pure OpenCV detection.

        Args:
            image_path: Path to the sketch/drawing image file.
            feature_types: Comma-separated list of feature types to detect.
                Options: "lines", "circles", "arcs", "rectangles", "slots",
                "fillets", "chamfers", "patterns", "splines", "holes", or
                "all" for all types.
            output_format: Output format. One of: "summary" (human-readable),
                "detailed" (per-feature info), "json" (machine-readable).

        Returns:
            Structured feature list with types, positions, approximate
            dimensions, and counts for each feature category.
        """
        path = Path(image_path)
        if not path.exists():
            return f"Error: Image file not found: {image_path}"

        requested = set(ft.strip().lower() for ft in feature_types.split(","))
        all_types = {
            "lines", "circles", "arcs", "rectangles", "slots",
            "fillets", "chamfers", "patterns", "splines", "holes",
        }
        detect_set = all_types if "all" in requested else requested & all_types

        results: dict[str, Any] = {}

        try:
            from mcp_commander_analysis.api.vision import (
                detect_lines,
                detect_circles,
                detect_arcs,
                detect_rectangles,
            )

            # OpenCV primitive detection ---------------------------------
            if "lines" in detect_set:
                lines = detect_lines(str(path))
                results["lines"] = {"count": len(lines), "items": lines[:20]}
                if len(lines) > 20:
                    results["lines"]["truncated"] = True

            if "circles" in detect_set:
                circles = detect_circles(str(path))
                results["circles"] = {"count": len(circles), "items": circles[:20]}
                # Circles in drawings are often holes
                if circles:
                    results["holes"] = {
                        "count": len(circles),
                        "note": "Detected circles interpreted as potential holes",
                        "items": [
                            {"center": c["center"], "diameter": round(c["radius"] * 2, 2)}
                            for c in circles[:20]
                        ],
                    }

            if "arcs" in detect_set:
                arcs = detect_arcs(str(path))
                results["arcs"] = {"count": len(arcs), "items": arcs[:20]}

            if "rectangles" in detect_set:
                rects = detect_rectangles(str(path))
                results["rectangles"] = {"count": len(rects), "items": rects[:20]}
                # Interpret narrow rectangles as slots
                narrow_rects = [
                    r for r in rects
                    if r["height"] / max(r["width"], 1) < 0.4
                    or r["width"] / max(r["height"], 1) < 0.4
                ]
                if narrow_rects:
                    results["slots"] = {
                        "count": len(narrow_rects),
                        "note": "Interpreted from narrow rectangles",
                        "items": narrow_rects[:20],
                    }

            # Attempt VLM semantic classification -----------------------
            has_vlm = False
            try:
                import os
                has_vlm = bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
            except Exception:
                pass

            if has_vlm and ("fillets" in detect_set or "chamfers" in detect_set or "patterns" in detect_set):
                from mcp_commander_analysis.api.vlm import VisionClient

                client = VisionClient()
                classify_prompt = (
                    "Analyze this engineering sketch image. Identify and classify these feature types: "
                    f"{', '.join(detect_set & {'fillets', 'chamfers', 'patterns', 'splines'})}. "
                    "For each feature found, list: type, approximate location (x,y), approximate size, "
                    "and confidence. Return as structured JSON."
                )
                vlm_result = client.analyze_image(str(path), classify_prompt)
                results["vlm_classification"] = vlm_result

        except Exception as exc:
            logger.exception("Feature recognition failed")
            return f"Error: Feature recognition failed: {exc}"

        # Format output ---------------------------------------------------
        if output_format == "json":
            return json.dumps(results, indent=2, default=str)

        # Summary format
        summary_parts = [f"Feature Recognition Results for: {image_path}\n"]
        total = 0
        for ftype, data in results.items():
            if isinstance(data, dict) and "count" in data:
                count = data["count"]
                total += count
                summary_parts.append(f"  • {ftype}: {count} found")
                if "note" in data:
                    summary_parts.append(f"    ({data['note']})")
        summary_parts.append(f"\n  Total features detected: {total}")
        summary_parts.append(f"  Detection types: {', '.join(sorted(detect_set)) or 'none'}")

        if output_format == "detailed":
            for ftype, data in results.items():
                if isinstance(data, dict) and "items" in data:
                    summary_parts.append(f"\n  --- {ftype} details ---")
                    for item in data["items"]:
                        summary_parts.append(f"    {item}")

        return "\n".join(summary_parts)
