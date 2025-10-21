"""
UI package for French Tutor Voice App
"""

from .app_ui import FrenchTutorUI, main
from .audio_io import (
    AudioConfig,
    AudioDevice,
    AudioInputStream,
    AudioOutputStream,
    VolumeMeter,
)

__all__ = [
    "FrenchTutorUI",
    "main",
    "AudioConfig",
    "AudioDevice",
    "AudioInputStream",
    "AudioOutputStream",
    "VolumeMeter",
]
