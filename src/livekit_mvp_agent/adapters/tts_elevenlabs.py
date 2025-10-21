from __future__ import annotations

import io
import logging
from typing import Optional, Dict, Any, ClassVar

import httpx

logger = logging.getLogger(__name__)


class TransientTTSError(RuntimeError):
    """Raised when ElevenLabs returns a transient error and a fallback should be attempted."""


class ElevenLabsTTS:
    """
    Minimal ElevenLabs TTS adapter.
    - Produces MP3 bytes by default (works for file/write or further decode).
    - Gracefully degrades if API key/voice is missing.
    """
    _deprecated_warned: ClassVar[bool] = False

    def __init__(
        self,
        api_key: Optional[str],
        voice_id: str,
        model_id: Optional[str] = None,
        timeout_s: float = 30.0,
        *,
        voice_settings: Optional[Dict[str, Any]] = None,
        output_format: str = "mp3_22050_32",
        optimize_streaming_latency: int = 4,
        stability: float = 0.6,
        similarity_boost: float = 0.8,
        style: float = 0.1,
        use_speaker_boost: bool = True,
    ) -> None:
        if model_id is None:
            model_id = self._resolve_default_model()
            if not getattr(self.__class__, "_deprecated_warned", False):
                logger.warning(
                    "ElevenLabsTTS instantiated without model_id; defaulting to '%s'. "
                    "Please supply model_id explicitly.",
                    model_id,
                )
                self.__class__._deprecated_warned = True  # type: ignore[attr-defined]

        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.timeout_s = timeout_s
        self.output_format = output_format
        latency = int(optimize_streaming_latency)
        self.optimize_streaming_latency = max(0, min(4, latency))

        self.voice_settings = (
            voice_settings.copy()
            if voice_settings is not None
            else {
                "stability": float(stability),
                "similarity_boost": float(similarity_boost),
                "style": float(style),
                "use_speaker_boost": bool(use_speaker_boost),
            }
        )
        self._client = httpx.Client(timeout=timeout_s)

    def available(self) -> bool:
        return bool(self.api_key and self.voice_id and self.model_id)

    @classmethod
    def _resolve_default_model(cls) -> str:
        try:
            from livekit_mvp_agent.config import get_settings

            return getattr(get_settings(), "tts_model", "eleven_flash_v2_5")
        except Exception:
            return "eleven_flash_v2_5"

    def synthesize(self, text: str) -> bytes:
        if not self.available():
            logger.warning("ElevenLabs TTS not available (missing API key, voice_id or model_id).")
            return b""  # NoOp

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": self.model_id,  # e.g., eleven_flash_v2_5
            "voice_settings": self.voice_settings,
            "output_format": self.output_format,
            "optimize_streaming_latency": self.optimize_streaming_latency,
        }

        try:
            resp = self._client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.content  # MP3 bytes
        except httpx.HTTPStatusError as e:
            logger.error(
                "ElevenLabs HTTP %s: %s",
                e.response.status_code,
                e.response.text.strip() if e.response is not None else e,
            )
            raise TransientTTSError(f"HTTP {e.response.status_code}") from e
        except Exception as e:  # pragma: no cover - unexpected transport errors
            logger.error("ElevenLabs TTS failed: %s", e)
            raise TransientTTSError("transport error") from e
