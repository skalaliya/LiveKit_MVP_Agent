"""
Utility helpers for TTS adapters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from livekit_mvp_agent.config import Settings

DEFAULT_ELEVENLABS_VOICE = "21m00Tcm4TlvDq8ikWAM"


def resolve_elevenlabs_voice(settings: "Settings") -> str:
    """
    Resolve the ElevenLabs voice ID based on settings, learning mode, and presets.
    """
    explicit_voice = (settings.elevenlabs_voice_id or "").strip()
    if explicit_voice and explicit_voice.lower() != "auto":
        return explicit_voice

    candidates: list[str | None] = []

    if getattr(settings, "elevenlabs_learning_mode", False):
        candidates.extend(
            [
                getattr(settings, "elevenlabs_voice_fr_female", None),
                getattr(settings, "elevenlabs_voice_fr_male", None),
            ]
        )

    candidates.extend(
        [
            getattr(settings, "elevenlabs_voice_en_female", None),
            getattr(settings, "elevenlabs_voice_en_male", None),
            DEFAULT_ELEVENLABS_VOICE,
        ]
    )

    for candidate in candidates:
        if candidate:
            return candidate

    return DEFAULT_ELEVENLABS_VOICE
