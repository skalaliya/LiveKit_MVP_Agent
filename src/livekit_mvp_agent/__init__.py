"""
LiveKit MVP Agent - Local bilingual voice agent

A production-ready voice agent that runs entirely locally with LiveKit,
faster-whisper, Ollama, and TTS systems (Kokoro/Piper).
"""

__version__ = "0.1.0"
__author__ = "Algorythmos"
__description__ = "Local EN/FR voice agent using faster-whisper, Ollama, Kokoro/Piper, integrated with LiveKit."

from .config import Settings, get_settings

__all__ = ["Settings", "get_settings"]