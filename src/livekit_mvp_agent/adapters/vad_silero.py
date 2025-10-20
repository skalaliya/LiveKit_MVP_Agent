"""
Silero VAD Adapter for Voice Activity Detection
"""

import logging
from typing import Union, Optional
import numpy as np

try:
    import torch
    import silero_vad
    SILERO_AVAILABLE = True
except ImportError:
    SILERO_AVAILABLE = False


class SileroVAD:
    """
    Voice Activity Detection using Silero VAD
    
    Features:
    - Real-time voice activity detection
    - Configurable threshold
    - Efficient processing
    - Low latency
    """
    
    def __init__(
        self,
        threshold: float = 0.5,
        min_silence_duration: float = 0.5,
        speech_pad: float = 0.2,
        sample_rate: int = 16000,
        frame_size: int = 512,
    ):
        if not SILERO_AVAILABLE:
            self.logger = logging.getLogger(__name__)
            self.logger.warning("Silero VAD not available, using mock implementation")
            self._use_mock = True
        else:
            self._use_mock = False
        
        self.threshold = threshold
        self.min_silence_duration = min_silence_duration
        self.speech_pad = speech_pad
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.logger = logging.getLogger(__name__)
        
        # VAD model
        self.model = None
        self.initialized = False
        
        # State tracking
        self._speech_start = None
        self._last_speech_time = 0
        self._audio_buffer = []
    
    def __post_init__(self):
        """Initialize after object creation"""
        if not self._use_mock:
            self._initialize_model()
    
    def _initialize_model(self) -> None:
        """Initialize Silero VAD model"""
        if self._use_mock:
            return
        
        try:
            self.logger.info("Loading Silero VAD model...")
            
            # Load the pre-trained model
            self.model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            
            # Set model to evaluation mode
            self.model.eval()
            
            self.initialized = True
            self.logger.info("Silero VAD model loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Silero VAD: {e}")
            self._use_mock = True
    
    def is_speech(self, audio_data: Union[np.ndarray, bytes]) -> bool:
        """
        Detect if audio contains speech
        
        Args:
            audio_data: Audio samples (numpy array or bytes)
            
        Returns:
            True if speech is detected, False otherwise
        """
        if self._use_mock:
            return self._mock_is_speech(audio_data)
        
        if not self.initialized:
            self._initialize_model()
            if not self.initialized:
                return self._mock_is_speech(audio_data)
        
        try:
            # Convert to numpy array if needed
            if isinstance(audio_data, bytes):
                audio_array = np.frombuffer(audio_data, dtype=np.float32)
            else:
                audio_array = audio_data.astype(np.float32)
            
            # Ensure correct shape
            if audio_array.ndim > 1:
                audio_array = audio_array.flatten()
            
            # Resample if needed (Silero VAD expects 16kHz)
            if len(audio_array) == 0:
                return False
            
            # Convert to tensor
            audio_tensor = torch.from_numpy(audio_array)
            
            # Get VAD prediction
            with torch.no_grad():
                speech_prob = self.model(audio_tensor, self.sample_rate).item()
            
            # Apply threshold
            is_speech = speech_prob > self.threshold
            
            self.logger.debug(f"VAD: speech_prob={speech_prob:.3f}, is_speech={is_speech}")
            
            return is_speech
            
        except Exception as e:
            self.logger.error(f"VAD error: {e}", exc_info=True)
            return False
    
    def _mock_is_speech(self, audio_data: Union[np.ndarray, bytes]) -> bool:
        """Mock speech detection for fallback"""
        # Simple energy-based detection
        try:
            if isinstance(audio_data, bytes):
                audio_array = np.frombuffer(audio_data, dtype=np.float32)
            else:
                audio_array = audio_data.astype(np.float32)
            
            if len(audio_array) == 0:
                return False
            
            # Calculate RMS energy
            rms_energy = np.sqrt(np.mean(audio_array ** 2))
            
            # Use a simple threshold (this is very basic)
            energy_threshold = 0.01  # Adjust as needed
            is_speech = rms_energy > energy_threshold
            
            self.logger.debug(f"Mock VAD: energy={rms_energy:.4f}, is_speech={is_speech}")
            
            return is_speech
            
        except Exception as e:
            self.logger.error(f"Mock VAD error: {e}")
            return False
    
    def process_streaming(self, audio_chunk: np.ndarray) -> dict:
        """
        Process streaming audio and return VAD state
        
        Args:
            audio_chunk: Audio samples
            
        Returns:
            Dictionary with VAD state information
        """
        is_speech = self.is_speech(audio_chunk)
        current_time = len(self._audio_buffer) / self.sample_rate
        
        # Update buffer
        self._audio_buffer.extend(audio_chunk)
        
        # Keep buffer size manageable (e.g., last 10 seconds)
        max_buffer_size = self.sample_rate * 10
        if len(self._audio_buffer) > max_buffer_size:
            self._audio_buffer = self._audio_buffer[-max_buffer_size:]
        
        result = {
            "is_speech": is_speech,
            "timestamp": current_time,
            "speech_probability": None,  # Could add this if using Silero
        }
        
        # Track speech segments
        if is_speech:
            if self._speech_start is None:
                self._speech_start = current_time
                result["speech_start"] = True
            
            self._last_speech_time = current_time
            result["speech_duration"] = current_time - self._speech_start
        else:
            if self._speech_start is not None:
                # Check if we've had enough silence to end speech
                silence_duration = current_time - self._last_speech_time
                
                if silence_duration >= self.min_silence_duration:
                    result["speech_end"] = True
                    result["speech_duration"] = self._last_speech_time - self._speech_start
                    self._speech_start = None
        
        return result
    
    def reset_state(self) -> None:
        """Reset VAD state"""
        self._speech_start = None
        self._last_speech_time = 0
        self._audio_buffer.clear()
        
        self.logger.debug("VAD state reset")
    
    def get_speech_segments(
        self, 
        audio_data: np.ndarray, 
        return_seconds: bool = True
    ) -> list:
        """
        Get speech segments from audio
        
        Args:
            audio_data: Audio samples
            return_seconds: Return timestamps in seconds vs samples
            
        Returns:
            List of (start, end) tuples for speech segments
        """
        if self._use_mock:
            # Simple mock implementation
            segments = []
            chunk_size = self.sample_rate  # 1 second chunks
            
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                if self.is_speech(chunk):
                    start = i / self.sample_rate if return_seconds else i
                    end = min(i + chunk_size, len(audio_data))
                    end = end / self.sample_rate if return_seconds else end
                    segments.append((start, end))
            
            return segments
        
        # TODO: Implement proper speech segmentation with Silero VAD
        # For now, return simple segments
        return []
    
    def set_threshold(self, threshold: float) -> None:
        """
        Update VAD threshold
        
        Args:
            threshold: New threshold value (0.0 to 1.0)
        """
        if 0.0 <= threshold <= 1.0:
            self.threshold = threshold
            self.logger.info(f"VAD threshold updated to {threshold}")
        else:
            self.logger.warning(f"Invalid threshold value: {threshold}")


class MockVAD:
    """Simple mock VAD for testing"""
    
    def __init__(self, threshold: float = 0.5, **kwargs):
        self.threshold = threshold
        self.logger = logging.getLogger(__name__)
        self.initialized = True
    
    def is_speech(self, audio_data: Union[np.ndarray, bytes]) -> bool:
        """Mock speech detection"""
        try:
            if isinstance(audio_data, bytes):
                audio_array = np.frombuffer(audio_data, dtype=np.float32)
            else:
                audio_array = audio_data.astype(np.float32)
            
            if len(audio_array) == 0:
                return False
            
            # Simple energy-based detection
            energy = np.sqrt(np.mean(audio_array ** 2))
            return energy > 0.01
            
        except Exception:
            return False
    
    def process_streaming(self, audio_chunk: np.ndarray) -> dict:
        """Mock streaming processing"""
        return {
            "is_speech": self.is_speech(audio_chunk),
            "timestamp": 0.0,
        }
    
    def reset_state(self) -> None:
        """Mock reset"""
        pass
    
    def set_threshold(self, threshold: float) -> None:
        """Mock threshold setting"""
        self.threshold = threshold


# Use mock if Silero VAD is not available
if not SILERO_AVAILABLE:
    SileroVAD = MockVAD