"""OCR Engine for engineering drawing text extraction.

Wraps **Tesseract** (via ``pytesseract``) and **RapidOCR**
(via ``rapidocr_onnxruntime``) for extracting text from engineering drawings.
Includes an OpenCV-based preprocessing pipeline (grayscale → Otsu threshold →
morphological denoise) to improve accuracy on noisy technical drawings.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Engine:
    """Unified OCR engine supporting Tesseract and RapidOCR backends.

    Each method returns a list of dicts with keys ``text``, ``confidence``,
    and ``bbox`` (``{x, y, w, h}``).

    Args:
        engine_type: ``"tesseract"`` or ``"rapidocr"``.
        lang: Language code for Tesseract (e.g. ``"eng"``).
        confidence_threshold: Discard results below this threshold.
    """

    def __init__(
        self,
        engine_type: str = "tesseract",
        lang: str = "eng",
        confidence_threshold: float = 0.3,
    ) -> None:
        self.engine_type = engine_type
        self.lang = lang
        self.confidence_threshold = confidence_threshold

        self._tesseract_available = self._check_tesseract()
        self._rapidocr_available = self._check_rapidocr()
        self._rapidocr_engine: Any = None

    # ------------------------------------------------------------------
    # Availability checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_tesseract() -> bool:
        try:
            import pytesseract  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _check_rapidocr() -> bool:
        try:
            from rapidocr_onnxruntime import RapidOCR  # noqa: F401
            return True
        except ImportError:
            return False

    @property
    def available(self) -> bool:
        if self.engine_type == "tesseract":
            return self._tesseract_available
        return self._rapidocr_available

    @property
    def active_engine(self) -> str:
        """Return the name of the actually usable engine (falls back)."""
        if self.engine_type == "tesseract" and self._tesseract_available:
            return "tesseract"
        if self.engine_type == "rapidocr" and self._rapidocr_available:
            return "rapidocr"
        if self._tesseract_available:
            return "tesseract"
        if self._rapidocr_available:
            return "rapidocr"
        return "none"

    # ------------------------------------------------------------------
    # Image preprocessing
    # ------------------------------------------------------------------

    @staticmethod
    def _preprocess(image_path: str) -> Any:
        """Apply preprocessing pipeline: grayscale → Otsu threshold → morphological denoise.

        Returns an OpenCV ``Mat`` ready for OCR.
        """
        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {image_path}")

        # 1. Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2. Otsu binarization
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 3. Morphological denoise — remove small noise, connect broken chars
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        denoised = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        return denoised

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_text(
        self,
        image_path: str,
        lang: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Run OCR on an image and return text blocks with bounding boxes.

        Args:
            image_path: Path to the drawing image file.
            lang: Override language.  Defaults to the instance's ``lang``.

        Returns:
            List of ``{"text": str, "confidence": float, "bbox": {"x": int, "y": int, "w": int, "h": int}}``.
            Returns an empty list if no engine is available.
        """
        lang = lang or self.lang
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        engine = self.active_engine
        if engine == "none":
            logger.warning("No OCR engine available (install pytesseract or rapidocr-onnxruntime)")
            return []

        if engine == "tesseract":
            return self._extract_tesseract(image_path, lang)
        else:
            return self._extract_rapidocr(image_path)

    def extract_text_regions(self, image_path: str) -> list[dict[str, Any]]:
        """Extract text and group blocks by spatial proximity into regions.

        Groups nearby text blocks into logical regions (e.g. a dimension value
        with its tolerance on a drawing).

        Returns:
            List of ``{"region_id": int, "texts": [str, ...], "bbox": {"x", "y", "w", "h"}, "confidence": float}``.
        """
        blocks = self.extract_text(image_path)
        if not blocks:
            return []

        import cv2
        import numpy as np

        # Sort blocks by vertical position then horizontal
        blocks.sort(key=lambda b: (b["bbox"]["y"], b["bbox"]["x"]))

        # Group blocks that are spatially close (within 50 px)
        regions: list[dict[str, Any]] = []
        current_region: list[dict[str, Any]] = [blocks[0]]

        PROXIMITY_THRESHOLD = 50  # pixels

        for block in blocks[1:]:
            prev = current_region[-1]
            dx = abs(block["bbox"]["x"] - prev["bbox"]["x"])
            dy = abs(block["bbox"]["y"] - prev["bbox"]["y"])

            if max(dx, dy) < PROXIMITY_THRESHOLD:
                current_region.append(block)
            else:
                regions.append(self._merge_region(current_region, len(regions)))
                current_region = [block]

        regions.append(self._merge_region(current_region, len(regions)))
        return regions

    # ------------------------------------------------------------------
    # Engine-specific implementations
    # ------------------------------------------------------------------

    def _extract_tesseract(
        self,
        image_path: str,
        lang: str,
    ) -> list[dict[str, Any]]:
        import pytesseract
        from PIL import Image

        img = Image.open(image_path)

        # Use sparse-text mode (psm 11) best for engineering drawings
        data = pytesseract.image_to_data(
            img,
            lang=lang,
            output_type=pytesseract.Output.DICT,
            config="--psm 11 --oem 3",
        )

        blocks: list[dict[str, Any]] = []
        n = len(data["text"])
        for i in range(n):
            text = data["text"][i].strip()
            if not text:
                continue
            try:
                conf = float(data["conf"][i]) / 100.0  # Tesseract 0-100
            except (ValueError, TypeError):
                conf = 0.0
            if conf < self.confidence_threshold:
                continue
            blocks.append({
                "text": text,
                "confidence": round(conf, 3),
                "bbox": {
                    "x": int(data["left"][i]),
                    "y": int(data["top"][i]),
                    "w": int(data["width"][i]),
                    "h": int(data["height"][i]),
                },
            })
        return blocks

    def _extract_rapidocr(self, image_path: str) -> list[dict[str, Any]]:
        from rapidocr_onnxruntime import RapidOCR

        if self._rapidocr_engine is None:
            self._rapidocr_engine = RapidOCR()

        result, _ = self._rapidocr_engine(image_path)
        blocks: list[dict[str, Any]] = []

        if not result:
            return blocks

        for item in result:
            # RapidOCR returns (bbox_points, text, confidence)
            bbox_points, text, conf = item
            xs = [p[0] for p in bbox_points]
            ys = [p[1] for p in bbox_points]

            x = int(min(xs))
            y = int(min(ys))
            w = int(max(xs) - min(xs))
            h = int(max(ys) - min(ys))

            if conf < self.confidence_threshold:
                continue

            blocks.append({
                "text": text.strip(),
                "confidence": round(float(conf), 3),
                "bbox": {"x": x, "y": y, "w": w, "h": h},
            })
        return blocks

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_region(blocks: list[dict[str, Any]], region_id: int) -> dict[str, Any]:
        """Merge a list of text blocks into a single region dict."""
        if not blocks:
            return {"region_id": region_id, "texts": [], "bbox": {"x": 0, "y": 0, "w": 0, "h": 0}, "confidence": 0.0}

        min_x = min(b["bbox"]["x"] for b in blocks)
        min_y = min(b["bbox"]["y"] for b in blocks)
        max_x = max(b["bbox"]["x"] + b["bbox"]["w"] for b in blocks)
        max_y = max(b["bbox"]["y"] + b["bbox"]["h"] for b in blocks)
        avg_conf = sum(b["confidence"] for b in blocks) / len(blocks)

        return {
            "region_id": region_id,
            "texts": [b["text"] for b in blocks],
            "bbox": {
                "x": min_x,
                "y": min_y,
                "w": max_x - min_x,
                "h": max_y - min_y,
            },
            "confidence": round(avg_conf, 3),
        }
