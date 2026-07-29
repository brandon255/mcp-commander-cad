"""VLM Vision Client for engineering drawing analysis.

Wraps OpenAI and Anthropic vision API calls to provide a unified interface
for sending drawing images to vision-language models and receiving structured
analysis responses. Falls back to mock responses when no API key is available.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class VisionClient:
    """Unified VLM client supporting OpenAI and Anthropic vision models.

    Auto-detects provider from environment variables (OPENAI_API_KEY or
    ANTHROPIC_API_KEY).  When neither is set, all calls return mock responses
    prefixed with ``[MOCK - no VLM API key]``.

    Args:
        provider: ``"openai"`` or ``"anthropic"``.  ``None`` auto-detects.
        model: Model name to use.  Defaults to ``gpt-4o`` (OpenAI) or
            ``claude-sonnet-4-20250514`` (Anthropic).
        api_key: API key.  Falls back to the matching env-var.
        max_tokens: Maximum tokens in the VLM response.
        temperature: Sampling temperature (low for deterministic analysis).
    """

    DEFAULT_OPENAI_MODEL = "gpt-4o"
    DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> None:
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Resolve provider ---------------------------------------------------
        if provider is not None:
            self.provider = provider.lower()
        elif os.getenv("OPENAI_API_KEY"):
            self.provider = "openai"
        elif os.getenv("ANTHROPIC_API_KEY"):
            self.provider = "anthropic"
        else:
            self.provider = "mock"

        # Resolve model ------------------------------------------------------
        if model is not None:
            self.model = model
        elif self.provider == "openai":
            self.model = self.DEFAULT_OPENAI_MODEL
        elif self.provider == "anthropic":
            self.model = self.DEFAULT_ANTHROPIC_MODEL
        else:
            self.model = "mock"

        # Resolve API key ----------------------------------------------------
        if self.provider == "openai":
            self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        elif self.provider == "anthropic":
            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        else:
            self.api_key = ""

        # Lazy-loaded SDK clients --------------------------------------------
        self._openai_client: Any = None
        self._anthropic_client: Any = None

    # ------------------------------------------------------------------
    # Image helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _encode_image(image_path: str) -> tuple[str, str]:
        """Load an image, resize if needed, and return ``(base64, media_type)``.

        Images larger than 1568 px on any side are downscaled so they stay
        within typical VLM token budgets while preserving legibility.
        """
        from PIL import Image

        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        img = Image.open(path).convert("RGB")
        MAX_DIM = 1568
        if img.width > MAX_DIM or img.height > MAX_DIM:
            img.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)

        ext = path.suffix.lower()
        media_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/png",
            ".bmp": "image/png",
            ".tif": "image/png",
            ".tiff": "image/png",
        }
        media_type = media_map.get(ext, "image/png")

        buf = io.BytesIO()
        img.save(buf, format=media_type.split("/")[1].upper() if media_type != "image/jpeg" else "JPEG")
        return base64.b64encode(buf.getvalue()).decode("utf-8"), media_type

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_image(self, image_path: str, prompt: str) -> str:
        """Analyze an image file using the configured VLM provider.

        Args:
            image_path: Absolute or relative path to the image file.
            prompt: The analysis prompt sent to the vision model.

        Returns:
            The model's text response, or a mock placeholder when no key
            is configured.
        """
        if self.provider == "mock":
            return self._mock_response(prompt)

        b64, media_type = self._encode_image(image_path)

        if self.provider == "openai":
            return self._call_openai(b64, media_type, prompt)
        else:
            return self._call_anthropic(b64, media_type, prompt)

    def analyze_image_base64(self, base64_data: str, prompt: str) -> str:
        """Analyze an already base64-encoded image.

        Args:
            base64_data: Raw base64-encoded image bytes (no ``data:`` prefix).
            prompt: The analysis prompt sent to the vision model.

        Returns:
            The model's text response, or a mock placeholder.
        """
        if self.provider == "mock":
            return self._mock_response(prompt)

        if self.provider == "openai":
            return self._call_openai(base64_data, "image/png", prompt)
        else:
            return self._call_anthropic(base64_data, "image/png", prompt)

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    def _call_openai(self, b64: str, media_type: str, prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError("openai package is required. Run: pip install openai") from exc

        if self._openai_client is None:
            self._openai_client = OpenAI(api_key=self.api_key)

        response = self._openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{media_type};base64,{b64}"},
                        },
                    ],
                }
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""

    def _call_anthropic(self, b64: str, media_type: str, prompt: str) -> str:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise ImportError("anthropic package is required. Run: pip install anthropic") from exc

        if self._anthropic_client is None:
            self._anthropic_client = Anthropic(api_key=self.api_key)

        response = self._anthropic_client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": media_type, "data": b64},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    # ------------------------------------------------------------------
    # Mock fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _mock_response(prompt: str) -> str:
        return (
            "[MOCK - no VLM API key] "
            f"Provider: mock | Prompt received ({len(prompt)} chars). "
            "Set OPENAI_API_KEY or ANTHROPIC_API_KEY to enable real vision analysis."
        )

    # ------------------------------------------------------------------
    # Prompt helpers
    # ------------------------------------------------------------------

    @staticmethod
    def engineering_drawing_prompt(
        focus: str = "all",
        detail_level: str = "standard",
    ) -> str:
        """Build a system prompt tailored to engineering drawing analysis.

        Args:
            focus: Area to focus on — ``"all"``, ``"dimensions"``, ``"views"``,
                ``"annotations"``, ``"title_block"``, or ``"gdnt"``.
            detail_level: ``"brief"``, ``"standard"``, or ``"detailed"``.
        """
        focus_map: dict[str, str] = {
            "all": "Provide a comprehensive analysis of all aspects.",
            "dimensions": "Focus specifically on all dimension values, tolerance annotations, and GD&T symbols.",
            "views": "Focus on identifying all views present and their arrangement.",
            "annotations": "Focus on text notes, callouts, surface finish marks, and weld symbols.",
            "title_block": "Focus on extracting every field from the title block.",
            "gdnt": "Focus on all GD&T feature control frames, datums, and tolerance zones.",
        }

        detail_map: dict[str, str] = {
            "brief": "Respond concisely in 3-5 bullet points.",
            "standard": "Provide a well-structured analysis with clear sections.",
            "detailed": "Provide an exhaustive analysis with every visible detail.",
        }

        return (
            "You are an expert mechanical engineer analyzing an engineering drawing.\n\n"
            "Carefully examine the drawing and identify:\n"
            "1. **Drawing type** — part drawing, assembly, schematic, etc.\n"
            "2. **Views** — front, top, right-side, isometric, section (label cutting plane), detail (magnification), auxiliary.\n"
            "3. **Dimensions** — linear, angular, radial, diametric, with tolerances and units.\n"
            "4. **Annotations** — notes, surface finish (Ra), weld symbols, material callouts.\n"
            "5. **Title block** — title, drawing number, revision, scale, material, drawn-by, date, units, default tolerance.\n"
            "6. **GD&T symbols** — feature control frames, datums, tolerance zone shapes.\n"
            "7. **Overall assessment** — completeness, clarity, potential issues.\n\n"
            f"{focus_map.get(focus, focus_map['all'])}\n"
            f"{detail_map.get(detail_level, detail_map['standard'])}\n\n"
            "Be precise. If something is not visible, say 'not visible' rather than guessing.\n"
            "Return your analysis as structured text with clear headings."
        )
