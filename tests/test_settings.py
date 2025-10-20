"""
Test configuration loading and validation
"""

import pytest
import tempfile
from pathlib import Path

from livekit_mvp_agent.config import Settings, get_settings, reset_settings, load_toml_config


class TestSettings:
    """Test Settings class"""
    
    def test_default_settings(self):
        """Test default settings creation"""
        settings = Settings()
        
        assert settings.sample_rate == 16000
        assert settings.whisper_model == "medium"
        assert settings.llm_model == "llama3.1:8b-instruct-q4_K_M"
        assert settings.tts_primary == "kokoro"
        assert settings.vad_threshold == 0.5
    
    def test_environment_override(self, monkeypatch):
        """Test environment variable override"""
        monkeypatch.setenv("WHISPER_MODEL", "large")
        monkeypatch.setenv("VAD_THRESHOLD", "0.7")
        
        settings = Settings()
        
        assert settings.whisper_model == "large"
        assert settings.vad_threshold == 0.7
    
    def test_nested_config_structures(self):
        """Test nested configuration structures"""
        settings = Settings()
        
        assert hasattr(settings, "audio")
        assert hasattr(settings, "stt")
        assert hasattr(settings, "llm")
        assert hasattr(settings, "tts")
        
        assert settings.audio.sample_rate == 16000
        assert settings.stt.model == "medium"


class TestConfigLoading:
    """Test configuration file loading"""
    
    def test_load_toml_config(self):
        """Test TOML config loading"""
        config_content = """
[audio]
sample_rate = 48000
channels = 2

[stt]
model = "large"
device = "cuda"

[llm]
model = "custom-model"
temperature = 0.9
"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            f.flush()
            
            config = load_toml_config(f.name)
            
            assert config["audio"]["sample_rate"] == 48000
            assert config["audio"]["channels"] == 2
            assert config["stt"]["model"] == "large"
            assert config["llm"]["temperature"] == 0.9
        
        Path(f.name).unlink()  # Cleanup
    
    def test_load_nonexistent_config(self):
        """Test loading non-existent config file"""
        config = load_toml_config("nonexistent.toml")
        assert config == {}
    
    def test_get_settings_singleton(self):
        """Test settings singleton behavior"""
        reset_settings()  # Ensure clean state
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
    
    def test_get_settings_with_config_file(self):
        """Test settings loading with config file"""
        config_content = """
[audio]
sample_rate = 24000

[stt]
model = "small"
"""
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            f.flush()
            
            reset_settings()  # Ensure clean state
            settings = get_settings(config_file=f.name)
            
            assert settings.audio.sample_rate == 24000
            assert settings.stt.model == "small"
        
        Path(f.name).unlink()  # Cleanup


class TestConfigValidation:
    """Test configuration validation"""
    
    def test_required_livekit_settings(self):
        """Test LiveKit required settings"""
        settings = Settings()
        
        # Should have default values
        assert settings.livekit_url == "ws://localhost:7880"
        assert settings.livekit_room_name == "voice-agent-room"
    
    def test_audio_settings_validation(self):
        """Test audio settings are reasonable"""
        settings = Settings()
        
        assert 8000 <= settings.sample_rate <= 48000
        assert 1 <= settings.channels <= 2
        assert settings.chunk_size > 0
    
    def test_model_settings_validation(self):
        """Test model settings have valid defaults"""
        settings = Settings()
        
        # Whisper models
        valid_whisper_models = [
            "tiny", "tiny.en", "base", "base.en", 
            "small", "small.en", "medium", "medium.en",
            "large-v1", "large-v2", "large-v3"
        ]
        assert any(model in settings.whisper_model for model in ["tiny", "base", "small", "medium", "large"])
        
        # LLM models should be reasonable
        assert settings.llm_model
        assert settings.llm_fallback
        
        # TTS settings
        assert settings.tts_primary in ["kokoro", "piper", "noop"]
    
    def test_threshold_ranges(self):
        """Test threshold values are in valid ranges"""
        settings = Settings()
        
        assert 0.0 <= settings.vad_threshold <= 1.0
        assert 0.0 <= settings.llm_temperature <= 2.0
        assert settings.llm_max_tokens > 0