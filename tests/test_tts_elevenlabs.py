import os

import pytest

from livekit_mvp_agent.adapters.tts_elevenlabs import ElevenLabsTTS, TransientTTSError
from livekit_mvp_agent.config import get_settings, reset_settings
from livekit_mvp_agent.utils.tts_helpers import resolve_elevenlabs_voice


@pytest.mark.skipif(
    not os.getenv("ELEVENLABS_API_KEY"),
    reason="ELEVENLABS_API_KEY not configured",
)
def test_elevenlabs_synthesize_basic() -> None:
    reset_settings()
    settings = get_settings()

    adapter = ElevenLabsTTS(
        api_key=settings.elevenlabs_api_key,
        voice_id=resolve_elevenlabs_voice(settings),
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

    assert adapter.available(), "ElevenLabs adapter should be available"

    try:
        audio = adapter.synthesize("bonjour")
    except TransientTTSError as exc:  # pragma: no cover - depends on service availability
        pytest.skip(f"Transient ElevenLabs error: {exc}")

    assert audio, "Expected non-empty audio payload"
    assert len(audio) > 1000
    assert audio.startswith(b"ID3") or audio[:2] == b"\xff\xfb"
