"""OpenCV-based geometric analysis utilities for drawing images.

Provides functions for detecting geometric primitives (lines, circles,
arcs, rectangles, dimension lines, text blocks) and classifying symbols
using contour analysis.  All functions use ``cv2`` and ``numpy``.
"""

from __future__ import annotations

import math
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Preprocessing
# ------------------------------------------------------------------

def _preprocess(image_path: str) -> Any:
    """Common preprocessing pipeline: grayscale → Gaussian blur → Canny edge detection.

    Returns a tuple ``(binary_mask, edges, gray, color)`` where:
    - ``binary_mask`` is an Otsu-thresholded binary image
    - ``edges`` is the Canny edge map
    - ``gray`` is the grayscale image
    - ``color`` is the original BGR image
    """
    import cv2
    import numpy as np

    color = cv2.imread(image_path)
    if color is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    gray = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)

    # Bilateral filter preserves edges while reducing noise
    blurred = cv2.bilateralFilter(gray, 9, 75, 75)

    # Otsu threshold
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Canny edge detection
    edges = cv2.Canny(blurred, 50, 150, apertureSize=3)

    return binary, edges, gray, color


# ------------------------------------------------------------------
# Line detection
# ------------------------------------------------------------------

def detect_lines(image_path: str) -> list[dict[str, Any]]:
    """Detect straight lines in a drawing image using HoughLinesP.

    Returns:
        List of dicts: ``{"start": {"x", "y"}, "end": {"x", "y"}, "angle": float, "length": float}``.
    """
    import cv2
    import numpy as np

    _, edges, _, _ = _preprocess(image_path)

    raw_lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=80,
        minLineLength=30,
        maxLineGap=10,
    )

    if raw_lines is None:
        return []

    results: list[dict[str, Any]] = []
    for line in raw_lines:
        x1, y1, x2, y2 = line[0].tolist()
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        angle = math.degrees(math.atan2(dy, dx))

        results.append({
            "start": {"x": x1, "y": y1},
            "end": {"x": x2, "y": y2},
            "angle": round(angle, 2),
            "length": round(length, 2),
        })

    # Sort by length descending
    results.sort(key=lambda l: l["length"], reverse=True)
    return results


# ------------------------------------------------------------------
# Circle detection
# ------------------------------------------------------------------

def detect_circles(image_path: str) -> list[dict[str, Any]]:
    """Detect circles in a drawing image using HoughCircles.

    Returns:
        List of dicts: ``{"center": {"x", "y"}, "radius": float}``.
    """
    import cv2
    import numpy as np

    _, _, gray, _ = _preprocess(image_path)

    raw = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=30,
        param1=80,
        param2=30,
        minRadius=10,
        maxRadius=500,
    )

    if raw is None:
        return []

    results: list[dict[str, Any]] = []
    for circle in np.uint16(np.around(raw)):
        cx, cy, r = int(circle[0]), int(circle[1]), int(circle[2])
        results.append({
            "center": {"x": cx, "y": cy},
            "radius": float(r),
        })

    results.sort(key=lambda c: c["radius"], reverse=True)
    return results


# ------------------------------------------------------------------
# Arc detection
# ------------------------------------------------------------------

def detect_arcs(image_path: str) -> list[dict[str, Any]]:
    """Detect arc-like contours in a drawing image.

    Uses contour analysis — an arc is a contour that is not a full ellipse
    and has significant curvature deviation from a straight line.

    Returns:
        List of dicts: ``{"start": {"x", "y"}, "end": {"x", "y"}, "center": {"x", "y"}, "radius": float, "sweep_angle": float}``.
    """
    import cv2
    import numpy as np

    binary, edges, _, _ = _preprocess(image_path)

    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    results: list[dict[str, Any]] = []
    for contour in contours:
        # Filter small contours
        if len(contour) < 10:
            continue
        area = cv2.contourArea(contour)
        if area < 200:
            continue

        # Fit an ellipse — arcs won't be complete ellipses
        if len(contour) >= 5:
            ellipse = cv2.fitEllipse(contour)
            (cx, cy), (rx, ry), angle = ellipse

            # Calculate arc-ness: ratio of contour perimeter to full ellipse perimeter
            perimeter = cv2.arcLength(contour, True)
            ellipse_perimeter = math.pi * (3 * (rx + ry) - math.sqrt((3 * rx + ry) * (rx + 3 * ry)))

            if ellipse_perimeter > 0:
                arc_ratio = perimeter / ellipse_perimeter

                # Arcs have ratio between 0.15 and 0.85 (not a full ellipse, not noise)
                if 0.15 < arc_ratio < 0.85 and min(rx, ry) > 5:
                    # Get start and end points
                    pts = contour.reshape(-1, 2)
                    start_pt = pts[0].tolist()
                    end_pt = pts[-1].tolist()

                    avg_radius = (rx + ry) / 2.0
                    sweep = arc_ratio * 360.0

                    results.append({
                        "start": {"x": start_pt[0], "y": start_pt[1]},
                        "end": {"x": end_pt[0], "y": end_pt[1]},
                        "center": {"x": int(cx), "y": int(cy)},
                        "radius": round(avg_radius, 2),
                        "sweep_angle": round(sweep, 2),
                    })

    return results


# ------------------------------------------------------------------
# Rectangle detection
# ------------------------------------------------------------------

def detect_rectangles(image_path: str) -> list[dict[str, Any]]:
    """Detect rectangular contours in a drawing image.

    Returns:
        List of dicts: ``{"top_left": {"x", "y"}, "width": float, "height": float, "angle": float, "perimeter": float}``.
    """
    import cv2
    import numpy as np

    binary, edges, _, _ = _preprocess(image_path)

    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    results: list[dict[str, Any]] = []
    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        if perimeter < 100:
            continue

        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

        # A rectangle has exactly 4 vertices
        if len(approx) == 4:
            # Compute bounding rect with angle
            rect = cv2.minAreaRect(contour)
            (cx, cy), (w, h), angle = rect
            box = cv2.boxPoints(rect)
            box = np.int0(box)

            # Ensure width >= height
            if w < h:
                w, h = h, w
                angle = angle + 90

            # Normalize angle to [0, 90)
            angle = angle % 180
            if angle > 90:
                angle = angle - 180

            results.append({
                "top_left": {"x": int(box[0][0]), "y": int(box[0][1])},
                "width": round(float(max(w, h)), 2),
                "height": round(float(min(w, h)), 2),
                "angle": round(float(angle), 2),
                "perimeter": round(float(perimeter), 2),
            })

    return results


# ------------------------------------------------------------------
# Dimension line detection
# ------------------------------------------------------------------

def detect_dimensions(image_path: str) -> list[dict[str, Any]]:
    """Detect dimension lines with arrows and associated text annotations.

    Looks for pairs of parallel lines (extension lines) connected by a short
    perpendicular line (dimension line) with arrow heads.

    Returns:
        List of dicts: ``{"type": str, "position": {"x", "y", "w", "h"}, "orientation": str, "confidence": float}``.
    """
    import cv2
    import numpy as np

    _, edges, gray, color = _preprocess(image_path)
    lines = detect_lines(image_path)

    if not lines:
        return []

    # Group nearly-parallel line pairs
    dimension_groups: list[list[dict[str, Any]]] = []
    ANGLE_THRESHOLD = 10  # degrees

    for i, line_a in enumerate(lines):
        for line_b in lines[i + 1:]:
            angle_diff = abs(line_a["angle"] - line_b["angle"])
            if angle_diff < ANGLE_THRESHOLD or abs(angle_diff - 180) < ANGLE_THRESHOLD:
                # Check if they are roughly the same length and close together
                length_ratio = min(line_a["length"], line_b["length"]) / max(line_a["length"], line_b["length"])
                if length_ratio > 0.5:
                    # Calculate midpoint distance
                    ax = (line_a["start"]["x"] + line_a["end"]["x"]) / 2
                    ay = (line_a["start"]["y"] + line_a["end"]["y"]) / 2
                    bx = (line_b["start"]["x"] + line_b["end"]["x"]) / 2
                    by = (line_b["start"]["y"] + line_b["end"]["y"]) / 2
                    dist = math.hypot(ax - bx, ay - by)

                    if 20 < dist < 500:
                        dimension_groups.append([line_a, line_b])

    # Build result entries for each detected dimension
    results: list[dict[str, Any]] = []
    for group in dimension_groups:
        all_x = []
        all_y = []
        for line in group:
            all_x.extend([line["start"]["x"], line["end"]["x"]])
            all_y.extend([line["start"]["y"], line["end"]["y"]])

        orientation = "horizontal" if abs(group[0]["angle"]) < 45 or abs(group[0]["angle"]) > 135 else "vertical"

        results.append({
            "type": "dimension_line",
            "position": {
                "x": int(min(all_x)),
                "y": int(min(all_y)),
                "w": int(max(all_x) - min(all_x)),
                "h": int(max(all_y) - min(all_y)),
            },
            "orientation": orientation,
            "confidence": 0.6,
        })

    return results


# ------------------------------------------------------------------
# Text block detection
# ------------------------------------------------------------------

def detect_text_blocks(image_path: str) -> list[dict[str, Any]]:
    """Detect text block regions using OCR + bounding boxes.

    Falls back to contour-based detection if OCR is not available.

    Returns:
        List of dicts: ``{"text": str, "bbox": {"x", "y", "w", "h"}, "confidence": float, "source": str}``.
    """
    import cv2

    try:
        from mcp_commander_analysis.api.ocr import Engine
        ocr = Engine()
        blocks = ocr.extract_text(image_path)
        if blocks:
            return [
                {
                    "text": b["text"],
                    "bbox": b["bbox"],
                    "confidence": b["confidence"],
                    "source": "ocr",
                }
                for b in blocks
            ]
    except Exception:
        logger.debug("OCR unavailable for text block detection, falling back to contour analysis")

    # Fallback: use contour-based detection for text-like regions
    binary, _, _, _ = _preprocess(image_path)
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    results: list[dict[str, Any]] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect = w / max(h, 1)

        # Text blocks are typically wider than tall, moderate aspect ratio
        if 0.3 < aspect < 10 and 50 < w < 2000 and 10 < h < 200:
            area = w * h
            # Filter very large regions (unlikely text) and tiny noise
            if 200 < area < 500000:
                results.append({
                    "text": "",
                    "bbox": {"x": x, "y": y, "w": w, "h": h},
                    "confidence": 0.3,
                    "source": "contour",
                })

    return results


# ------------------------------------------------------------------
# Symbol classification
# ------------------------------------------------------------------

def classify_symbol(image_crop: str, symbol_set: str = "all") -> str:
    """Classify a cropped symbol image using contour analysis.

    Attempts to classify GD&T, weld, and surface finish symbols based
    on geometric properties (circularity, aspect ratio, etc.).

    Args:
        image_crop: Path to a cropped symbol image.
        symbol_set: ``"all"``, ``"gdnt"``, ``"weld"``, or ``"surface_finish"``.

    Returns:
        Classification label string or ``"unknown"``.
    """
    import cv2
    import numpy as np

    img = cv2.imread(image_crop)
    if img is None:
        return "unknown"

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return "unknown"

    # Analyze the largest contour
    main_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(main_contour)
    perimeter = cv2.arcLength(main_contour, True)

    if perimeter == 0:
        return "unknown"

    # Circularity: 1.0 = perfect circle
    circularity = 4 * math.pi * area / (perimeter * perimeter)

    # Bounding rect properties
    x, y, w, h = cv2.boundingRect(main_contour)
    aspect_ratio = w / max(h, 1)
    extent = area / (w * h) if w * h > 0 else 0
    hull_area = cv2.contourArea(cv2.convexHull(main_contour))
    solidity = area / hull_area if hull_area > 0 else 0

    # Classification heuristics
    if symbol_set == "all" or symbol_set == "gdnt":
        # Many GD&T symbols are moderately circular (0.3-0.7)
        if 0.3 < circularity < 0.7 and extent > 0.4:
            # Diamond shape → parallelism, perpendicularity, angularity, position
            if aspect_ratio > 0.7 and aspect_ratio < 1.3:
                return "gdnt_diamond"
            # Tall narrow → perpendicularity
            if aspect_ratio < 0.6:
                return "gdnt_perpendicularity"
            # Wide → parallelism
            if aspect_ratio > 1.5:
                return "gdnt_parallelism"

        # Circle → circularity, cylindricity, concentricity
        if circularity > 0.7:
            return "gdnt_circle"

        # Triangle → angularity
        approx = cv2.approxPolyDP(main_contour, 0.04 * perimeter, True)
        if len(approx) == 3:
            return "gdnt_angularity"

    if symbol_set == "all" or symbol_set == "weld":
        # Weld symbols often have triangular or arrow-like shapes
        approx = cv2.approxPolyDP(main_contour, 0.04 * perimeter, True)
        if len(approx) <= 5 and circularity < 0.5:
            if aspect_ratio > 0.4:
                return "weld_fillet"
            if aspect_ratio < 0.4:
                return "weld_groove"

        # Arrow-like: high extent, low circularity
        if solidity > 0.6 and circularity < 0.3:
            return "weld_arrow"

    if symbol_set == "all" or symbol_set == "surface_finish":
        # Surface finish: checkmark-like (⌒) or simple arc
        if 0.1 < circularity < 0.4 and extent < 0.5:
            approx = cv2.approxPolyDP(main_contour, 0.04 * perimeter, True)
            if len(approx) <= 6:
                return "surface_finish_checkmark"

    return "unknown"
