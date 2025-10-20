"""
Test VAD functionality
"""

import pytest
import numpy as np

from livekit_mvp_agent.adapters.vad_silero import SileroVAD
from livekit_mvp_agent.utils.audio import create_test_tone, create_white_noise


class TestSileroVAD:
    """Test Silero VAD functionality"""
    
    @pytest.fixture
    def vad(self):
        """Create VAD instance for testing"""
        return SileroVAD(threshold=0.5)
    
    def test_vad_initialization(self, vad):
        """Test VAD initialization"""
        assert vad.threshold == 0.5
        assert vad.sample_rate == 16000
        # Note: May use mock implementation if Silero not available
    
    def test_silence_detection(self, vad):
        """Test silence detection"""
        # Create silent audio (very low amplitude)
        silent_audio = np.zeros(1600, dtype=np.float32)  # 0.1 seconds of silence
        
        result = vad.is_speech(silent_audio)
        
        # Should detect as non-speech (silence)
        assert result is False
    
    def test_speech_detection_with_tone(self, vad):
        """Test speech detection with test tone"""
        # Create a test tone (should be detected as speech)
        tone_audio = create_test_tone(
            frequency=440.0,
            duration=0.5,
            sample_rate=16000,
            amplitude=0.5
        )
        
        result = vad.is_speech(tone_audio)
        
        # Should detect as speech (depending on implementation)
        # Note: Mock VAD uses energy detection, so tone should register
        assert isinstance(result, bool)
    
    def test_noise_detection(self, vad):
        """Test detection with white noise"""
        # Create white noise
        noise_audio = create_white_noise(
            duration=0.5,
            sample_rate=16000,
            amplitude=0.2
        )
        
        result = vad.is_speech(noise_audio)
        
        # Result depends on VAD implementation and threshold
        assert isinstance(result, bool)
    
    def test_streaming_processing(self, vad):
        """Test streaming VAD processing"""
        # Create test audio chunk
        audio_chunk = create_test_tone(
            frequency=220.0,
            duration=0.1,
            sample_rate=16000,
            amplitude=0.3
        )
        
        result = vad.process_streaming(audio_chunk)
        
        # Should return structured result
        assert isinstance(result, dict)
        assert "is_speech" in result
        assert "timestamp" in result
        assert isinstance(result["is_speech"], bool)
        assert isinstance(result["timestamp"], (int, float))
    
    def test_empty_audio(self, vad):
        """Test with empty audio"""
        empty_audio = np.array([], dtype=np.float32)
        
        result = vad.is_speech(empty_audio)
        
        # Should handle empty audio gracefully
        assert result is False
    
    def test_bytes_input(self, vad):
        """Test with bytes input"""
        # Create test audio as int16 bytes
        audio_array = create_test_tone(duration=0.1, amplitude=0.5)
        audio_int16 = (audio_array * 32767).astype(np.int16)
        audio_bytes = audio_int16.tobytes()
        
        result = vad.is_speech(audio_bytes)
        
        assert isinstance(result, bool)
    
    def test_state_reset(self, vad):
        """Test VAD state reset"""
        # Process some audio first
        audio = create_test_tone(duration=0.1)
        vad.process_streaming(audio)
        
        # Reset state
        vad.reset_state()
        
        # Should not raise any errors
        assert True  # If we get here, reset worked
    
    def test_threshold_update(self, vad):
        """Test threshold updating"""
        original_threshold = vad.threshold
        
        # Update threshold
        new_threshold = 0.8
        vad.set_threshold(new_threshold)
        
        assert vad.threshold == new_threshold
        assert vad.threshold != original_threshold
    
    def test_invalid_threshold(self, vad):
        """Test invalid threshold handling"""
        original_threshold = vad.threshold
        
        # Try invalid thresholds
        vad.set_threshold(-0.1)  # Too low
        assert vad.threshold == original_threshold
        
        vad.set_threshold(1.5)   # Too high
        assert vad.threshold == original_threshold
    
    def test_different_audio_lengths(self, vad):
        """Test with different audio lengths"""
        # Very short audio
        short_audio = create_test_tone(duration=0.01)  # 10ms
        result_short = vad.is_speech(short_audio)
        assert isinstance(result_short, bool)
        
        # Medium audio
        medium_audio = create_test_tone(duration=0.5)   # 500ms
        result_medium = vad.is_speech(medium_audio)
        assert isinstance(result_medium, bool)
        
        # Long audio
        long_audio = create_test_tone(duration=2.0)     # 2s
        result_long = vad.is_speech(long_audio)
        assert isinstance(result_long, bool)


class TestVADIntegration:
    """Test VAD integration scenarios"""
    
    def test_continuous_speech_detection(self):
        """Test continuous speech detection scenario"""
        vad = SileroVAD(threshold=0.3)
        
        # Simulate speech followed by silence
        speech_segment = create_test_tone(duration=1.0, amplitude=0.5)
        silence_segment = np.zeros(int(0.5 * 16000), dtype=np.float32)
        
        # Test speech segment
        speech_result = vad.is_speech(speech_segment)
        
        # Test silence segment
        silence_result = vad.is_speech(silence_segment)
        
        # Speech should be detected, silence should not
        # (Though this depends on the VAD implementation)
        assert isinstance(speech_result, bool)
        assert isinstance(silence_result, bool)
    
    def test_mixed_audio_stream(self):
        """Test with mixed audio content"""
        vad = SileroVAD()
        
        # Create mixed content: tone + noise + silence
        tone = create_test_tone(duration=0.2, amplitude=0.4)
        noise = create_white_noise(duration=0.2, amplitude=0.1)
        silence = np.zeros(int(0.2 * 16000), dtype=np.float32)
        
        # Process each segment
        results = []
        for segment in [tone, noise, silence]:
            result = vad.process_streaming(segment)
            results.append(result)
        
        # Should get valid results for each
        assert len(results) == 3
        assert all("is_speech" in result for result in results)
    
    def test_vad_performance_with_large_audio(self):
        """Test VAD performance with larger audio files"""
        vad = SileroVAD()
        
        # Create 5 seconds of audio
        large_audio = create_test_tone(duration=5.0, amplitude=0.3)
        
        # Should process without errors
        result = vad.is_speech(large_audio)
        assert isinstance(result, bool)
        
        # Test chunked processing
        chunk_size = 1600  # 0.1 seconds
        chunk_results = []
        
        for i in range(0, len(large_audio), chunk_size):
            chunk = large_audio[i:i+chunk_size]
            chunk_result = vad.is_speech(chunk)
            chunk_results.append(chunk_result)
        
        # Should get results for all chunks
        assert len(chunk_results) > 0
        assert all(isinstance(result, bool) for result in chunk_results)