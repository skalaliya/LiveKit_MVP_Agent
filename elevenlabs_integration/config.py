"""
ElevenLabs Integration Configuration

Configuration settings for ElevenLabs STT and TTS adapters.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ElevenLabsSTTConfig:
    """Configuration for ElevenLabs STT."""
    api_key: str
    model: str = "eleven_multilingual_v2"
    language: str = "auto"
    timeout: int = 30
    
    # Advanced settings
    optimize_streaming_latency: int = 3  # 0-4, higher = lower latency
    voice_isolation: bool = True
    
    
@dataclass 
class ElevenLabsTTSConfig:
    """Configuration for ElevenLabs TTS."""
    api_key: str
    voice_id: Optional[str] = None
    model: str = "eleven_multilingual_v2"
    timeout: int = 30
    
    # Voice settings
    voice_settings: Dict[str, Any] = field(default_factory=lambda: {
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": True
    })
    
    # Output settings
    output_format: str = "mp3_44100_128"  # mp3_22050_32, mp3_44100_64, mp3_44100_96, etc.
    
    
@dataclass
class ElevenLabsConfig:
    """Combined ElevenLabs configuration."""
    api_key: str
    
    # STT Configuration
    stt: ElevenLabsSTTConfig = field(default=None)
    
    # TTS Configuration  
    tts: ElevenLabsTTSConfig = field(default=None)
    
    def __post_init__(self):
        """Initialize sub-configs with the API key if not provided."""
        if self.stt is None:
            self.stt = ElevenLabsSTTConfig(api_key=self.api_key)
        elif self.stt.api_key != self.api_key:
            self.stt.api_key = self.api_key
            
        if self.tts is None:
            self.tts = ElevenLabsTTSConfig(api_key=self.api_key)
        elif self.tts.api_key != self.api_key:
            self.tts.api_key = self.api_key


# Predefined voice configurations for different languages
VOICE_PRESETS = {
    "english": {
        "male": {
            "adam": "pNInz6obpgDQGcFmaJgB",  # Deep, mature English voice
            "sam": "yoZ06aMxZJJ28mfd3POQ",   # Young adult English voice
        },
        "female": {
            "rachel": "21m00Tcm4TlvDq8ikWAM",  # Young, pleasant English voice
            "domi": "AZnzlk1XvdvUeBnXmlld",   # Strong, confident English voice
        }
    },
    "french": {
        "male": {
            "antoine": "ErXwobaYiN019PkySvjV",  # French male voice
        },
        "female": {
            "charlotte": "XB0fDUnXU5powFXDhCwa",  # French female voice
        }
    }
}


# Model recommendations
MODEL_RECOMMENDATIONS = {
    "quality": {
        "highest": "eleven_multilingual_v2",
        "balanced": "eleven_multilingual_v1", 
        "fastest": "eleven_english_v1"  # English only
    },
    "latency": {
        "lowest": "eleven_turbo_v2",
        "balanced": "eleven_multilingual_v2",
        "quality": "eleven_multilingual_v1"
    }
}


def get_recommended_voice(language: str, gender: str = "female") -> Optional[str]:
    """
    Get recommended voice ID for language and gender.
    
    Args:
        language: Language code ('en', 'fr')
        gender: 'male' or 'female'
        
    Returns:
        Voice ID string or None
    """
    lang_key = "english" if language.startswith("en") else "french" if language.startswith("fr") else None
    
    if not lang_key or lang_key not in VOICE_PRESETS:
        return None
        
    voices = VOICE_PRESETS[lang_key].get(gender, {})
    if not voices:
        return None
        
    # Return first available voice
    return next(iter(voices.values()))


def get_model_for_use_case(use_case: str) -> str:
    """
    Get recommended model for use case.
    
    Args:
        use_case: 'quality', 'latency', 'balanced'
        
    Returns:
        Model name
    """
    if use_case in MODEL_RECOMMENDATIONS["quality"]:
        return MODEL_RECOMMENDATIONS["quality"][use_case]
    elif use_case in MODEL_RECOMMENDATIONS["latency"]:
        return MODEL_RECOMMENDATIONS["latency"][use_case]
    else:
        return "eleven_multilingual_v2"  # Default