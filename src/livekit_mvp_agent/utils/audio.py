"""
Audio processing utilities
"""

import logging
from typing import Union, Tuple, Optional
import numpy as np

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False


class AudioProcessor:
    """
    Audio processing utilities for format conversion and manipulation
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        dtype: np.dtype = np.float32,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.dtype = dtype
        self.logger = logging.getLogger(__name__)
    
    def bytes_to_array(
        self, 
        audio_bytes: bytes, 
        source_dtype: np.dtype = np.int16
    ) -> np.ndarray:
        """
        Convert audio bytes to numpy array
        
        Args:
            audio_bytes: Raw audio bytes
            source_dtype: Data type of source audio
            
        Returns:
            Numpy array of audio samples
        """
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_bytes, dtype=source_dtype)
            
            # Convert to target dtype
            if source_dtype == np.int16:
                # Convert int16 to float32 in range [-1, 1]
                audio_array = audio_array.astype(np.float32) / 32768.0
            elif source_dtype == np.int32:
                # Convert int32 to float32
                audio_array = audio_array.astype(np.float32) / 2147483648.0
            else:
                # Assume already float
                audio_array = audio_array.astype(self.dtype)
            
            # Handle multi-channel audio
            if self.channels == 1 and len(audio_array.shape) > 1:
                # Convert to mono by averaging channels
                audio_array = np.mean(audio_array, axis=1)
            elif self.channels > 1 and len(audio_array.shape) == 1:
                # Convert mono to multi-channel by duplicating
                audio_array = np.tile(audio_array.reshape(-1, 1), (1, self.channels))
            
            return audio_array.astype(self.dtype)
            
        except Exception as e:
            self.logger.error(f"Error converting bytes to array: {e}")
            return np.array([], dtype=self.dtype)
    
    def array_to_bytes(
        self, 
        audio_array: np.ndarray, 
        target_dtype: np.dtype = np.int16
    ) -> bytes:
        """
        Convert numpy array to audio bytes
        
        Args:
            audio_array: Audio samples as numpy array
            target_dtype: Target data type for output
            
        Returns:
            Audio data as bytes
        """
        try:
            # Ensure correct shape
            if audio_array.ndim > 2:
                audio_array = audio_array.flatten()
            
            # Convert to target dtype
            if target_dtype == np.int16:
                # Convert float32 to int16
                audio_array = np.clip(audio_array, -1.0, 1.0)
                audio_array = (audio_array * 32767).astype(np.int16)
            elif target_dtype == np.int32:
                # Convert float32 to int32
                audio_array = np.clip(audio_array, -1.0, 1.0)
                audio_array = (audio_array * 2147483647).astype(np.int32)
            else:
                audio_array = audio_array.astype(target_dtype)
            
            return audio_array.tobytes()
            
        except Exception as e:
            self.logger.error(f"Error converting array to bytes: {e}")
            return b""
    
    def resample(
        self, 
        audio_data: np.ndarray, 
        source_rate: int, 
        target_rate: int
    ) -> np.ndarray:
        """
        Resample audio data (simple linear interpolation)
        
        Args:
            audio_data: Input audio samples
            source_rate: Source sample rate
            target_rate: Target sample rate
            
        Returns:
            Resampled audio data
        """
        if source_rate == target_rate:
            return audio_data
        
        try:
            # Calculate resampling ratio
            ratio = target_rate / source_rate
            
            # Calculate new length
            new_length = int(len(audio_data) * ratio)
            
            # Simple linear interpolation resampling
            old_indices = np.linspace(0, len(audio_data) - 1, new_length)
            new_audio = np.interp(old_indices, np.arange(len(audio_data)), audio_data)
            
            return new_audio.astype(self.dtype)
            
        except Exception as e:
            self.logger.error(f"Resampling error: {e}")
            return audio_data
    
    def normalize(
        self, 
        audio_data: np.ndarray, 
        target_level: float = -20.0
    ) -> np.ndarray:
        """
        Normalize audio to target RMS level (in dB)
        
        Args:
            audio_data: Input audio samples
            target_level: Target RMS level in dB
            
        Returns:
            Normalized audio data
        """
        try:
            if len(audio_data) == 0:
                return audio_data
            
            # Calculate current RMS
            rms = np.sqrt(np.mean(audio_data ** 2))
            
            if rms == 0:
                return audio_data
            
            # Convert target level from dB to linear
            target_rms = 10 ** (target_level / 20)
            
            # Calculate scaling factor
            scale_factor = target_rms / rms
            
            # Apply scaling
            normalized = audio_data * scale_factor
            
            # Clip to prevent clipping
            normalized = np.clip(normalized, -1.0, 1.0)
            
            return normalized.astype(self.dtype)
            
        except Exception as e:
            self.logger.error(f"Normalization error: {e}")
            return audio_data
    
    def apply_gain(self, audio_data: np.ndarray, gain_db: float) -> np.ndarray:
        """
        Apply gain to audio data
        
        Args:
            audio_data: Input audio samples
            gain_db: Gain in decibels
            
        Returns:
            Audio with gain applied
        """
        try:
            # Convert dB to linear scale
            gain_linear = 10 ** (gain_db / 20)
            
            # Apply gain
            gained_audio = audio_data * gain_linear
            
            # Clip to prevent overflow
            gained_audio = np.clip(gained_audio, -1.0, 1.0)
            
            return gained_audio.astype(self.dtype)
            
        except Exception as e:
            self.logger.error(f"Gain application error: {e}")
            return audio_data
    
    def detect_silence(
        self, 
        audio_data: np.ndarray, 
        threshold_db: float = -40.0,
        min_duration: float = 0.1
    ) -> list:
        """
        Detect silent segments in audio
        
        Args:
            audio_data: Input audio samples
            threshold_db: Silence threshold in dB
            min_duration: Minimum duration for silence detection
            
        Returns:
            List of (start_sample, end_sample) tuples for silent segments
        """
        try:
            if len(audio_data) == 0:
                return []
            
            # Convert threshold to linear scale
            threshold_linear = 10 ** (threshold_db / 20)
            
            # Calculate frame size for minimum duration
            frame_size = int(min_duration * self.sample_rate)
            
            silent_segments = []
            i = 0
            
            while i < len(audio_data):
                # Get frame
                end_idx = min(i + frame_size, len(audio_data))
                frame = audio_data[i:end_idx]
                
                # Calculate RMS of frame
                rms = np.sqrt(np.mean(frame ** 2))
                
                if rms < threshold_linear:
                    # Start of silent segment
                    start = i
                    
                    # Extend while silent
                    while i < len(audio_data):
                        end_idx = min(i + frame_size, len(audio_data))
                        frame = audio_data[i:end_idx]
                        rms = np.sqrt(np.mean(frame ** 2))
                        
                        if rms >= threshold_linear:
                            break
                        
                        i += frame_size // 2  # Overlap frames
                    
                    silent_segments.append((start, i))
                else:
                    i += frame_size // 2  # Overlap frames
            
            return silent_segments
            
        except Exception as e:
            self.logger.error(f"Silence detection error: {e}")
            return []
    
    def trim_silence(
        self, 
        audio_data: np.ndarray, 
        threshold_db: float = -40.0
    ) -> np.ndarray:
        """
        Trim silence from beginning and end of audio
        
        Args:
            audio_data: Input audio samples
            threshold_db: Silence threshold in dB
            
        Returns:
            Trimmed audio data
        """
        try:
            if len(audio_data) == 0:
                return audio_data
            
            # Convert threshold to linear scale
            threshold_linear = 10 ** (threshold_db / 20)
            
            # Find start of audio content
            start_idx = 0
            for i in range(len(audio_data)):
                if abs(audio_data[i]) > threshold_linear:
                    start_idx = i
                    break
            
            # Find end of audio content
            end_idx = len(audio_data)
            for i in range(len(audio_data) - 1, -1, -1):
                if abs(audio_data[i]) > threshold_linear:
                    end_idx = i + 1
                    break
            
            return audio_data[start_idx:end_idx]
            
        except Exception as e:
            self.logger.error(f"Silence trimming error: {e}")
            return audio_data
    
    def save_audio(
        self, 
        audio_data: np.ndarray, 
        filename: str, 
        sample_rate: Optional[int] = None
    ) -> bool:
        """
        Save audio data to file
        
        Args:
            audio_data: Audio samples to save
            filename: Output filename
            sample_rate: Sample rate (uses instance default if None)
            
        Returns:
            True if successful, False otherwise
        """
        if not SOUNDFILE_AVAILABLE:
            self.logger.error("soundfile library not available for saving audio")
            return False
        
        try:
            sr = sample_rate or self.sample_rate
            sf.write(filename, audio_data, sr)
            self.logger.info(f"Audio saved to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving audio to {filename}: {e}")
            return False
    
    def load_audio(
        self, 
        filename: str, 
        target_sr: Optional[int] = None
    ) -> Tuple[np.ndarray, int]:
        """
        Load audio from file
        
        Args:
            filename: Input filename
            target_sr: Target sample rate (resamples if different)
            
        Returns:
            Tuple of (audio_data, sample_rate)
        """
        if not SOUNDFILE_AVAILABLE:
            self.logger.error("soundfile library not available for loading audio")
            return np.array([]), 0
        
        try:
            audio_data, sample_rate = sf.read(filename)
            
            # Convert to target sample rate if specified
            if target_sr and target_sr != sample_rate:
                audio_data = self.resample(audio_data, sample_rate, target_sr)
                sample_rate = target_sr
            
            # Ensure correct dtype
            audio_data = audio_data.astype(self.dtype)
            
            self.logger.info(f"Audio loaded from {filename}: {len(audio_data)} samples at {sample_rate}Hz")
            return audio_data, sample_rate
            
        except Exception as e:
            self.logger.error(f"Error loading audio from {filename}: {e}")
            return np.array([]), 0
    
    def get_audio_info(self, audio_data: np.ndarray) -> dict:
        """
        Get information about audio data
        
        Args:
            audio_data: Audio samples
            
        Returns:
            Dictionary with audio information
        """
        try:
            if len(audio_data) == 0:
                return {
                    "length": 0,
                    "duration": 0.0,
                    "rms": 0.0,
                    "peak": 0.0,
                    "dynamic_range": 0.0,
                }
            
            # Basic info
            length = len(audio_data)
            duration = length / self.sample_rate
            
            # Audio levels
            rms = np.sqrt(np.mean(audio_data ** 2))
            peak = np.max(np.abs(audio_data))
            
            # Dynamic range (approximate)
            dynamic_range = 20 * np.log10(peak / (rms + 1e-10))
            
            return {
                "length": length,
                "duration": duration,
                "sample_rate": self.sample_rate,
                "channels": self.channels,
                "rms": rms,
                "rms_db": 20 * np.log10(rms + 1e-10),
                "peak": peak,
                "peak_db": 20 * np.log10(peak + 1e-10),
                "dynamic_range_db": dynamic_range,
                "dtype": str(audio_data.dtype),
            }
            
        except Exception as e:
            self.logger.error(f"Error getting audio info: {e}")
            return {}


def create_test_tone(
    frequency: float = 440.0,
    duration: float = 1.0,
    sample_rate: int = 16000,
    amplitude: float = 0.5
) -> np.ndarray:
    """
    Create a test tone
    
    Args:
        frequency: Tone frequency in Hz
        duration: Duration in seconds
        sample_rate: Sample rate
        amplitude: Amplitude (0.0 to 1.0)
        
    Returns:
        Test tone as numpy array
    """
    t = np.linspace(0, duration, int(duration * sample_rate), False)
    tone = amplitude * np.sin(2 * np.pi * frequency * t)
    return tone.astype(np.float32)


def create_white_noise(
    duration: float = 1.0,
    sample_rate: int = 16000,
    amplitude: float = 0.1
) -> np.ndarray:
    """
    Create white noise
    
    Args:
        duration: Duration in seconds
        sample_rate: Sample rate
        amplitude: Amplitude (0.0 to 1.0)
        
    Returns:
        White noise as numpy array
    """
    length = int(duration * sample_rate)
    noise = amplitude * np.random.randn(length)
    return noise.astype(np.float32)