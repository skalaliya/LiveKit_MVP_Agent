"""
Configuration management for LiveKit MVP Agent
"""

import os
import toml
from pathlib import Path
from typing import Optional, Union
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AudioConfig(BaseModel):
    """Audio processing configuration"""
    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")
    channels: int = Field(default=1, description="Number of audio channels")
    chunk_size: int = Field(default=1024, description="Audio chunk size for processing")
    buffer_size: int = Field(default=4096, description="Audio buffer size")


class STTConfig(BaseModel):
    """Speech-to-Text configuration"""
    model: str = Field(default="medium", description="Whisper model name")
    device: str = Field(default="auto", description="Device for inference")
    compute_type: str = Field(default="int8", description="Compute precision type")
    language: str = Field(default="auto", description="Language code or 'auto'")
    vad_filter: bool = Field(default=True, description="Enable VAD filtering")
    vad_threshold: float = Field(default=0.5, description="VAD threshold")


class LLMConfig(BaseModel):
    """Large Language Model configuration"""
    base_url: str = Field(default="http://localhost:11434", description="Ollama base URL")
    model: str = Field(default="llama3.1:8b-instruct-q4_K_M", description="Primary LLM model")
    fallback_model: str = Field(default="mistral:7b-instruct-q4_K_M", description="Fallback LLM model")
    temperature: float = Field(default=0.7, description="Sampling temperature")
    max_tokens: int = Field(default=512, description="Maximum response tokens")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")


class TTSConfig(BaseModel):
    """Text-to-Speech configuration"""
    primary: str = Field(default="kokoro", description="Primary TTS system")
    fallback: str = Field(default="piper", description="Fallback TTS system")
    voice: str = Field(default="en-US-kokoro", description="Voice ID")
    speed: float = Field(default=1.0, description="Speech speed multiplier")
    quality: str = Field(default="medium", description="Audio quality setting")


class VADConfig(BaseModel):
    """Voice Activity Detection configuration"""
    threshold: float = Field(default=0.5, description="VAD threshold")
    min_silence_duration: float = Field(default=0.5, description="Minimum silence duration")
    speech_pad: float = Field(default=0.2, description="Speech padding duration")
    frame_size: int = Field(default=512, description="VAD frame size")


class LiveKitConfig(BaseModel):
    """LiveKit configuration"""
    url: str = Field(default="ws://localhost:7880", description="LiveKit server URL")
    room_name: str = Field(default="voice-agent-room", description="Room name")
    participant_name: str = Field(default="VoiceAgent", description="Participant name")
    auto_subscribe: bool = Field(default=True, description="Auto-subscribe to tracks")
    auto_publish: bool = Field(default=True, description="Auto-publish tracks")


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    file: Optional[str] = Field(default="logs/agent.log", description="Log file path")
    max_bytes: int = Field(default=10485760, description="Max log file size")
    backup_count: int = Field(default=5, description="Number of backup files")


class SystemConfig(BaseModel):
    """System configuration"""
    max_concurrent_requests: int = Field(default=5, description="Max concurrent requests")
    request_timeout: float = Field(default=30.0, description="Request timeout")
    retry_attempts: int = Field(default=3, description="Retry attempts")
    retry_delay: float = Field(default=1.0, description="Retry delay")


class PerformanceConfig(BaseModel):
    """Performance configuration"""
    use_gpu: bool = Field(default=True, description="Enable GPU acceleration")
    max_memory_usage: str = Field(default="2GB", description="Maximum memory usage")
    prefetch_models: bool = Field(default=True, description="Prefetch models")
    cache_size: int = Field(default=1000, description="Cache size")


class Settings(BaseSettings):
    """Main application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Direct environment variables
    livekit_url: str = Field(default="ws://localhost:7880", env="LIVEKIT_URL")
    livekit_api_key: Optional[str] = Field(default=None, env="LIVEKIT_API_KEY")
    livekit_api_secret: Optional[str] = Field(default=None, env="LIVEKIT_API_SECRET")
    livekit_room_name: str = Field(default="voice-agent-room", env="LIVEKIT_ROOM_NAME")
    livekit_participant_name: str = Field(default="VoiceAgent", env="LIVEKIT_PARTICIPANT_NAME")
    
    # Whisper STT
    whisper_model: str = Field(default="medium", env="WHISPER_MODEL")
    whisper_device: str = Field(default="auto", env="WHISPER_DEVICE")
    whisper_compute_type: str = Field(default="int8", env="WHISPER_COMPUTE_TYPE")
    
    # Ollama LLM
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    llm_model: str = Field(default="llama3.1:8b-instruct-q4_K_M", env="LLM_MODEL")
    llm_fallback: str = Field(default="mistral:7b-instruct-q4_K_M", env="LLM_FALLBACK")
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=512, env="LLM_MAX_TOKENS")
    
    # TTS
    tts_primary: str = Field(default="kokoro", env="TTS_PRIMARY")
    tts_fallback: str = Field(default="piper", env="TTS_FALLBACK")
    tts_voice: str = Field(default="en-US-kokoro", env="TTS_VOICE")
    tts_speed: float = Field(default=1.0, env="TTS_SPEED")
    
    # VAD
    vad_threshold: float = Field(default=0.5, env="VAD_THRESHOLD")
    vad_min_silence_duration: float = Field(default=0.5, env="VAD_MIN_SILENCE_DURATION")
    vad_speech_pad: float = Field(default=0.2, env="VAD_SPEECH_PAD")
    
    # Audio
    sample_rate: int = Field(default=16000, env="SAMPLE_RATE")
    channels: int = Field(default=1, env="CHANNELS")
    chunk_size: int = Field(default=1024, env="CHUNK_SIZE")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # Development
    debug: bool = Field(default=False, env="DEBUG")
    verbose: bool = Field(default=False, env="VERBOSE")
    
    # Configuration sections (loaded from TOML)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    stt: STTConfig = Field(default_factory=STTConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    vad: VADConfig = Field(default_factory=VADConfig)
    livekit: LiveKitConfig = Field(default_factory=LiveKitConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)


def load_toml_config(config_path: Union[str, Path]) -> dict:
    """Load configuration from TOML file"""
    config_path = Path(config_path)
    if not config_path.exists():
        return {}
    
    try:
        return toml.load(config_path)
    except Exception as e:
        raise ValueError(f"Failed to load TOML config from {config_path}: {e}")


def merge_configs(base_config: dict, override_config: dict) -> dict:
    """Merge configuration dictionaries recursively"""
    result = base_config.copy()
    
    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result


_settings_instance: Optional[Settings] = None


def get_settings(config_file: Optional[Union[str, Path]] = None) -> Settings:
    """
    Get application settings (singleton pattern)
    
    Args:
        config_file: Optional path to TOML config file
        
    Returns:
        Settings instance
    """
    global _settings_instance
    
    if _settings_instance is not None:
        return _settings_instance
    
    # Default config paths
    config_paths = [
        Path("config/settings.toml"),
        Path("config/settings.example.toml"),
    ]
    
    if config_file:
        config_paths.insert(0, Path(config_file))
    
    # Load TOML configuration
    toml_config = {}
    for path in config_paths:
        if path.exists():
            toml_config = load_toml_config(path)
            break
    
    # Create settings with TOML config
    if toml_config:
        # Extract nested configurations
        audio_config = toml_config.get("audio", {})
        stt_config = toml_config.get("stt", {})
        llm_config = toml_config.get("llm", {})
        tts_config = toml_config.get("tts", {})
        vad_config = toml_config.get("vad", {})
        livekit_config = toml_config.get("livekit", {})
        logging_config = toml_config.get("logging", {})
        system_config = toml_config.get("system", {})
        performance_config = toml_config.get("performance", {})
        
        # Create settings with nested configs
        _settings_instance = Settings(
            audio=AudioConfig(**audio_config),
            stt=STTConfig(**stt_config),
            llm=LLMConfig(**llm_config),
            tts=TTSConfig(**tts_config),
            vad=VADConfig(**vad_config),
            livekit=LiveKitConfig(**livekit_config),
            logging=LoggingConfig(**logging_config),
            system=SystemConfig(**system_config),
            performance=PerformanceConfig(**performance_config),
        )
    else:
        _settings_instance = Settings()
    
    return _settings_instance


def reset_settings() -> None:
    """Reset settings instance (useful for testing)"""
    global _settings_instance
    _settings_instance = None