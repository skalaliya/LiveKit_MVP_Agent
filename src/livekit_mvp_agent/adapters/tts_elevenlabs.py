from __future__ import annotations

import io
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class ElevenLabsTTS:
    """
    Minimal ElevenLabs TTS adapter.
    - Produces MP3 bytes by default (works for file/write or further decode).
    - Gracefully degrades if API key/voice is missing.
    """

    def __init__(
        self,
        api_key: Optional[str],
        voice_id: str,
        model_id: str,
        timeout_s: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.timeout_s = timeout_s
        self._client = httpx.Client(timeout=timeout_s)

    def available(self) -> bool:
        return bool(self.api_key and self.voice_id and self.model_id)

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
            "voice_settings": {
                "stability": 0.6,
                "similarity_boost": 0.8,
                "style": 0.1,
                "use_speaker_boost": True,
            },
        }

        try:
            resp = self._client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.content  # MP3 bytes
        except httpx.HTTPStatusError as e:
            logger.error("ElevenLabs HTTP error: %s - %s", e.response.status_code, e.response.text)
        except Exception as e:
            logger.exception("ElevenLabs TTS failed: %s", e)
        return b""  # fall back to silence on errors