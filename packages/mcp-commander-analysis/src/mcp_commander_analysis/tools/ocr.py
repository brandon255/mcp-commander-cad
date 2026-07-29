"""OCR Dimension Extraction MCP tools.

Registers tools that extract dimension values, tolerances, and GD&T symbols
from engineering drawing images using OCR engines (Tesseract / RapidOCR)
with engineering-aware post-processing.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dimension regex patterns used for filtering OCR text
# ---------------------------------------------------------------------------

_DIM_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Bilateral tolerance: 50±0.1
    (re.compile(r"^([\d.]+)\s*[±]\s*([\d.]+)$"), "bilateral"),
    # Diametric with tolerance: Ø25±0.05
    (re.compile(r"^[ØøDd]\s*([\d.]+)\s*[±]\s*([\d.]+)$"), "diametric_bilateral"),
    # Plain diametric: Ø25
    (re.compile(r"^[ØøDd]\s*([\d.]+)\s*$"), "diametric"),
    # Radial: R10
    (re.compile(r"^[Rr]\s*([\d.]+)\s*$"), "radial"),
    # Angular: 45°, 45 deg
    (re.compile(r"^([\d.]+)\s*[°]\s*$"), "angular"),
    # Thread: M8x1.25
    (re.compile(r"^[Mm]\s*([\d.]+)\s*[x×]\s*([\d.]+)\s*$"), "thread"),
    # Fit class: 25 H7, Ø25H7/g6
    (re.compile(r"^[ØøDd]?\s*([\d.]+)\s*([HhGgPp]\d+(?:/[a-z]\d+)?)\s*$"), "fit"),
    # Plain linear: 50, 50.5
    (re.compile(r"^([\d.]+)\s*$"), "linear"),
]


def _classify_text(text: str) -> dict[str, Any] | None:
    """Try to classify OCR text as a dimension, GD&T, or surface finish entry."""
    text = text.strip()
    if not text or len(text) > 30:
        return None

    # Check dimension patterns
    for pattern, dim_type in _DIM_PATTERNS:
        m = pattern.match(text)
        if m:
            groups = m.groups()
            result: dict[str, Any] = {
                "raw_text": text,
                "type": dim_type,
            }
            if len(groups) >= 1:
                try:
                    result["value"] = float(groups[0])
                except ValueError:
                    pass
            if len(groups) >= 2:
                try:
                    result["tolerance"] = float(groups[1])
                except ValueError:
                    result["tolerance"] = groups[1]
            return result

    # GD&T detection
    gdt_keywords = re.compile(
        r"(flatness|straightness|circularity|cylindricity|"
        r"profile.of.line|profile.of.surface|"
        r"perpendicularity|angularity|parallelism|"
        r"position|concentricity|symmetry|"
        r"circular.runout|total.runout)",
        re.IGNORECASE,
    )
    if gdt_keywords.search(text):
        return {"raw_text": text, "type": "gdnt"}

    # Surface finish detection
    if re.search(r"(Ra|Rz|Rt|√)\s*[\d.]", text, re.IGNORECASE):
        return {"raw_text": text, "type": "surface_finish"}

    return None


def register_ocr_tools(mcp: Any) -> None:
    """Register all OCR dimension extraction tools on the given FastMCP server."""

    @mcp.tool()
    def extract_dimensions_from_image(
        image_path: str,
        include_tolerances: bool = True,
        include_gdnt: bool = True,
        ocr_engine: str = "tesseract",
    ) -> str:
        """Extract dimension values, tolerances, and GD&T symbols from a drawing.

        Uses OCR (Tesseract or RapidOCR) to find all text in the drawing,
        then filters and classifies dimension patterns, tolerance annotations,
        and GD&T symbols using regex-based engineering drawing awareness.

        Args:
            image_path: Path to the drawing image file.
            include_tolerances: Whether to include tolerance information in results.
            include_gdnt: Whether to include GD&T symbols in results.
            ocr_engine: OCR engine to use. One of: "tesseract", "rapidocr".

        Returns:
            Structured list of extracted dimensions with values, tolerances,
            types (linear/angular/radial/diametric), positions, and units.
            Also includes GD&T symbols and surface finish callouts if detected.
        """
        path = Path(image_path)
        if not path.exists():
            return f"Error: Image file not found: {image_path}"

        try:
            from mcp_commander_analysis.api.ocr import Engine

            engine = Engine(engine_type=ocr_engine)
            blocks = engine.extract_text(str(path))

            if not blocks:
                return (
                    f"No text detected in image: {image_path}\n"
                    f"OCR engine used: {engine.active_engine}\n"
                    f"Tip: Ensure the image has sufficient resolution and contrast."
                )

            # Classify each OCR text block
            dimensions: list[dict[str, Any]] = []
            gdnt_symbols: list[dict[str, Any]] = []
            surface_finishes: list[dict[str, Any]] = []
            other_text: list[dict[str, Any]] = []

            for block in blocks:
                classified = _classify_text(block["text"])
                if classified is None:
                    if len(block["text"]) > 2:
                        other_text.append({
                            "text": block["text"],
                            "confidence": block["confidence"],
                            "bbox": block["bbox"],
                        })
                    continue

                entry = {
                    **classified,
                    "confidence": block["confidence"],
                    "bbox": block["bbox"],
                }

                dtype = classified.get("type", "")

                if dtype in ("gdnt",) and include_gdnt:
                    gdnt_symbols.append(entry)
                elif dtype == "surface_finish":
                    surface_finishes.append(entry)
                elif include_tolerances:
                    dimensions.append(entry)
                elif dtype in ("linear", "diametric", "radial", "angular", "thread", "fit"):
                    # Strip tolerance info if not requested
                    entry.pop("tolerance", None)
                    dimensions.append(entry)

            # Cross-reference with dimension lines from vision module
            try:
                from mcp_commander_analysis.api.vision import detect_dimensions

                dim_lines = detect_dimensions(str(path))
            except Exception:
                dim_lines = []

            # Build response
            parts: list[str] = []
            parts.append(f"Dimension Extraction Results for: {image_path}")
            parts.append(f"OCR engine: {engine.active_engine}")
            parts.append(f"Total text blocks detected: {len(blocks)}")
            parts.append(f"Classified dimensions: {len(dimensions)}")
            parts.append(f"GD&T symbols: {len(gdnt_symbols)}")
            parts.append(f"Surface finishes: {len(surface_finishes)}")
            parts.append(f"Dimension lines (vision): {len(dim_lines)}")

            if dimensions:
                parts.append("\n--- Dimensions ---")
                for d in dimensions:
                    line = f"  • {d['raw_text']}"
                    if "value" in d:
                        line += f" | value={d['value']}"
                    if "tolerance" in d:
                        line += f" | tol=±{d['tolerance']}"
                    if "type" in d:
                        line += f" | type={d['type']}"
                    parts.append(line)

            if gdnt_symbols:
                parts.append("\n--- GD&T Symbols ---")
                for g in gdnt_symbols:
                    parts.append(f"  • {g['raw_text']} (confidence: {g['confidence']:.0%})")

            if surface_finishes:
                parts.append("\n--- Surface Finishes ---")
                for s in surface_finishes:
                    parts.append(f"  • {s['raw_text']}")

            return "\n".join(parts)

        except Exception as exc:
            logger.exception("Dimension extraction failed")
            return f"Error: Dimension extraction failed: {exc}"
