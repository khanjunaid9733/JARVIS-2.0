from __future__ import annotations

"""Voice Interface Adapters (Milestone M4, spec §92 / §131.7 / §131.13).

Provides versioned `ProviderAdapter` implementations for voice cognition:
1. `WhisperSTTAdapter`: Local / remote Whisper Speech-To-Text behind capability
   contract `audio.transcribe` (v1.0.0).
2. `PiperTTSAdapter`: Local / fast Piper Text-To-Speech behind capability
   contract `audio.synthesize` (v1.0.0).

Invariants:
1. Provider Seam (ADR-001): Adapters implement `ProviderAdapter` Protocol from
   `jarvis.kernel.registry`. Neither the kernel nor cognitive logic directly imports
   the underlying engines or external audio drivers.
2. Injected Execution Seam: Audio processing engines are injected via callables/runners
   (defaulting to hermetic deterministic runners in test/development).
3. Fail-Closed Error Mapping: Any engine or transport error maps strictly to
   `ProviderTransportError`.
4. Additive: No existing kernel or orchestrator modules are modified.
"""

import base64
from pathlib import Path
from typing import Any, Callable

from jarvis.kernel.model_gateway import ProviderTransportError
from jarvis.kernel.registry import ProviderAdapter


# ---------------------------------------------------------------------------
# Whisper Speech-To-Text Adapter
# ---------------------------------------------------------------------------

class WhisperSTTAdapter:
    """ProviderAdapter for Whisper Speech-To-Text transcription (`audio.transcribe`)."""

    provider_id = "stt.whisper"
    supported_contract = "audio.transcribe"
    supported_version = "1.0.0"

    def __init__(
        self,
        *,
        model_name: str = "whisper-base",
        runner: Callable[[bytes, str, str | None], dict[str, Any]] | None = None,
    ) -> None:
        self.model_name = model_name
        self._runner = runner or self._default_runner

    def _default_runner(
        self, audio_bytes: bytes, audio_format: str, language: str | None
    ) -> dict[str, Any]:
        """Default deterministic mock/test runner when no external engine is bound."""
        if not audio_bytes:
            raise ProviderTransportError("empty audio payload received for transcription")
        # Deterministic transcription representation for hermetic environments
        text = f"[transcription from {len(audio_bytes)} bytes of {audio_format}]"
        return {
            "text": text,
            "language": language or "en",
            "duration_seconds": len(audio_bytes) / 32000.0,
            "segments": [
                {
                    "start": 0.0,
                    "end": len(audio_bytes) / 32000.0,
                    "text": text,
                }
            ],
            "model": self.model_name,
        }

    async def invoke(
        self, contract_id: str, version: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        if contract_id != self.supported_contract:
            raise ProviderTransportError(
                f"adapter '{self.provider_id}' does not support contract '{contract_id}' "
                f"(expected '{self.supported_contract}')"
            )

        # Support raw bytes, base64 string, or file path
        audio_bytes = args.get("audio_bytes")
        audio_path = args.get("audio_path")
        audio_format = args.get("format", "wav").lower()
        language = args.get("language")

        if audio_path is not None:
            p = Path(audio_path)
            if not p.is_file():
                raise ProviderTransportError(f"audio file not found: {audio_path}")
            try:
                audio_bytes = p.read_bytes()
            except Exception as exc:
                raise ProviderTransportError(f"failed to read audio file '{audio_path}': {exc}") from exc
        elif isinstance(audio_bytes, str):
            try:
                audio_bytes = base64.b64decode(audio_bytes)
            except Exception as exc:
                raise ProviderTransportError(f"invalid base64 audio payload: {exc}") from exc
        elif not isinstance(audio_bytes, (bytes, bytearray)):
            raise ProviderTransportError(
                "transcription requires 'audio_bytes' (bytes/base64) or 'audio_path'"
            )

        try:
            return self._runner(bytes(audio_bytes), audio_format, language)
        except ProviderTransportError:
            raise
        except Exception as exc:
            raise ProviderTransportError(f"Whisper STT transcription failed: {exc}") from exc

    def health_check(self) -> bool:
        """Returns True if the STT runner is operational."""
        try:
            res = self._runner(b"RIFF....WAVEfmt ", "wav", "en")
            return bool(res and "text" in res)
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Piper Text-To-Speech Adapter
# ---------------------------------------------------------------------------

class PiperTTSAdapter:
    """ProviderAdapter for Piper Text-To-Speech synthesis (`audio.synthesize`)."""

    provider_id = "tts.piper"
    supported_contract = "audio.synthesize"
    supported_version = "1.0.0"

    def __init__(
        self,
        *,
        voice: str = "en_US-lessac-medium",
        sample_rate: int = 22050,
        runner: Callable[[str, str, str], dict[str, Any]] | None = None,
    ) -> None:
        self.voice = voice
        self.sample_rate = sample_rate
        self._runner = runner or self._default_runner

    def _default_runner(
        self, text: str, voice: str, output_format: str
    ) -> dict[str, Any]:
        """Default deterministic mock/test runner when no external engine is bound."""
        if not text or not text.strip():
            raise ProviderTransportError("empty text provided for speech synthesis")

        # Deterministic mock audio bytes (header + text representation)
        simulated_audio = f"RIFF_WAVE_{voice}_{output_format}_{text}".encode("utf-8")
        return {
            "audio_bytes": simulated_audio,
            "sample_rate": self.sample_rate,
            "format": output_format,
            "voice": voice,
            "duration_seconds": len(text) * 0.05,
        }

    async def invoke(
        self, contract_id: str, version: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        if contract_id != self.supported_contract:
            raise ProviderTransportError(
                f"adapter '{self.provider_id}' does not support contract '{contract_id}' "
                f"(expected '{self.supported_contract}')"
            )

        text = args.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ProviderTransportError(
                "synthesis requires non-empty string in args['text']"
            )

        voice = args.get("voice", self.voice)
        output_format = args.get("format", "wav").lower()

        try:
            return self._runner(text, voice, output_format)
        except ProviderTransportError:
            raise
        except Exception as exc:
            raise ProviderTransportError(f"Piper TTS synthesis failed: {exc}") from exc

    def health_check(self) -> bool:
        """Returns True if the TTS runner is operational."""
        try:
            res = self._runner("ping", self.voice, "wav")
            return bool(res and "audio_bytes" in res)
        except Exception:
            return False


__all__ = [
    "PiperTTSAdapter",
    "WhisperSTTAdapter",
]
