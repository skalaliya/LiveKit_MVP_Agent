#!/usr/bin/env python
"""
Quick smoke-test for ElevenLabs TTS integration.
"""

from __future__ import annotations

import sys
from pathlib import Path

from livekit_mvp_agent.adapters.tts_elevenlabs import ElevenLabsTTS, TransientTTSError
from livekit_mvp_agent.config import get_settings, reset_settings
from livekit_mvp_agent.utils.tts_helpers import resolve_elevenlabs_voice


def main() -> int:
    reset_settings()
    settings = get_settings()

    if not settings.elevenlabs_api_key:
        print("ELEVENLABS_API_KEY not set; cannot run smoke test.", file=sys.stderr)
        return 1

    voice_id = resolve_elevenlabs_voice(settings)
    adapter = ElevenLabsTTS(
        api_key=settings.elevenlabs_api_key,
        voice_id=voice_id,
        model_id=settings.elevenlabs_model or settings.tts_model,
        timeout_s=float(settings.elevenlabs_tts_timeout),
        voice_settings={
            "stability": settings.elevenlabs_tts_stability,
            "similarity_boost": settings.elevenlabs_tts_similarity,
            "style": settings.elevenlabs_tts_style,
            "use_speaker_boost": settings.elevenlabs_tts_use_speaker_boost,
        },
        output_format=settings.elevenlabs_output_format,
        optimize_streaming_latency=settings.elevenlabs_opt_latency,
    )

    if not adapter.available():
        print("ElevenLabs adapter unavailable (check API key and voice id).", file=sys.stderr)
        return 1

    try:
        audio_bytes = adapter.synthesize("Bonjour, je m'appelle Sam.")
    except TransientTTSError as exc:
        print(f"Synthesis failed: {exc}", file=sys.stderr)
        return 1

    if not audio_bytes:
        print("Received empty audio from ElevenLabs.", file=sys.stderr)
        return 1

    output_path = Path("/tmp/tts_smoke.mp3")
    output_path.write_bytes(audio_bytes)
    size = output_path.stat().st_size
    if size < 3000:
        print(f"Audio too small ({size} bytes).", file=sys.stderr)
        return 1

    print(f"Smoke test wrote {output_path} ({size} bytes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
