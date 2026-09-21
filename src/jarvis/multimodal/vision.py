from __future__ import annotations

"""Vision Processing Adapter (Milestone M4, spec §92 / §131.7 / §131.13).

Provides versioned `ProviderAdapter` implementation for visual perception:
- `VisionModelAdapter`: Local / remote vision model (e.g. CLIP / Moondream)
  behind capability contracts:
  - `vision.describe` (v1.0.0): General scene, diagram, and screenshot description.
  - `vision.analyze` (v1.0.0): Query-conditioned visual question answering, OCR, and object detection.

Invariants:
1. Provider Seam: Implements `ProviderAdapter` Protocol from `jarvis.kernel.registry`.
2. Hermetic by Default: Pluggable execution runner seam with deterministic default.
3. Fail-Closed Error Mapping: Any engine or image format failure maps to `ProviderTransportError`.
"""

import base64
from pathlib import Path
from typing import Any, Callable

from jarvis.kernel.model_gateway import ProviderTransportError
from jarvis.kernel.registry import ProviderAdapter


class VisionModelAdapter:
    """ProviderAdapter for local/remote visual perception (e.g. Moondream, CLIP)."""

    provider_id = "vision.adapter"
    supported_contracts = {
        "vision.describe": "1.0.0",
        "vision.analyze": "1.0.0",
    }

    def __init__(
        self,
        *,
        model_name: str = "moondream2",
        runner: Callable[[bytes, str, str | None], dict[str, Any]] | None = None,
    ) -> None:
        self.model_name = model_name
        self._runner = runner or self._default_runner

    def _default_runner(
        self, image_bytes: bytes, contract_id: str, prompt: str | None
    ) -> dict[str, Any]:
        """Default deterministic mock/test runner when no external engine is bound."""
        if not image_bytes:
            raise ProviderTransportError("empty image payload received for vision analysis")

        p = prompt or "Describe the image."
        return {
            "description": f"Visual analysis of {len(image_bytes)} bytes: {p}",
            "objects": [
                {"label": "ui_window", "confidence": 0.95, "box": [10, 10, 200, 200]},
                {"label": "button", "confidence": 0.88, "box": [50, 150, 120, 180]},
            ],
            "text_detected": "Sample Detected Text",
            "model": self.model_name,
            "contract": contract_id,
        }

    async def invoke(
        self, contract_id: str, version: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        if contract_id not in self.supported_contracts:
            raise ProviderTransportError(
                f"adapter '{self.provider_id}' does not support contract '{contract_id}' "
                f"(supported: {list(self.supported_contracts.keys())})"
            )

        image_bytes = args.get("image_bytes")
        image_path = args.get("image_path")
        prompt = args.get("prompt") or args.get("query")

        if image_path is not None:
            p = Path(image_path)
            if not p.is_file():
                raise ProviderTransportError(f"image file not found: {image_path}")
            try:
                image_bytes = p.read_bytes()
            except Exception as exc:
                raise ProviderTransportError(f"failed to read image file '{image_path}': {exc}") from exc
        elif isinstance(image_bytes, str):
            try:
                image_bytes = base64.b64decode(image_bytes)
            except Exception as exc:
                raise ProviderTransportError(f"invalid base64 image payload: {exc}") from exc
        elif not isinstance(image_bytes, (bytes, bytearray)):
            raise ProviderTransportError(
                "vision analysis requires 'image_bytes' (bytes/base64) or 'image_path'"
            )

        try:
            return self._runner(bytes(image_bytes), contract_id, prompt)
        except ProviderTransportError:
            raise
        except Exception as exc:
            raise ProviderTransportError(f"Vision model analysis failed: {exc}") from exc

    def health_check(self) -> bool:
        """Returns True if the vision runner is operational."""
        try:
            res = self._runner(b"\x89PNG\r\n\x1a\n", "vision.describe", "ping")
            return bool(res and "description" in res)
        except Exception:
            return False


__all__ = [
    "VisionModelAdapter",
]
