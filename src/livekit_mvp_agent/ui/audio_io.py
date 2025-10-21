"""
Cross-platform audio I/O for French Tutor Voice App
Handles microphone capture and speaker playback with jitter buffering
"""

from __future__ import annotations

import logging
import queue
import threading
from collections import deque
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """Audio configuration"""
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = "float32"
    chunk_size: int = 320  # 20ms at 16kHz
    buffer_size: int = 10  # ~200ms jitter buffer


class VolumeMeter:
    """Simple RMS volume meter with smoothing"""
    
    def __init__(self, smoothing: float = 0.3):
        self.smoothing = smoothing
        self._level = 0.0
    
    def update(self, audio_data: np.ndarray) -> float:
        """Update meter with new audio frame, return smoothed RMS level (0-1)"""
        rms = np.sqrt(np.mean(audio_data ** 2))
        self._level = self.smoothing * rms + (1 - self.smoothing) * self._level
        return self._level
    
    @property
    def level(self) -> float:
        """Current smoothed level"""
        return self._level


class AudioInputStream:
    """Microphone input stream with volume metering"""
    
    def __init__(
        self,
        config: AudioConfig,
        callback: Callable[[np.ndarray, float], None],
        device: Optional[int] = None,
    ):
        self.config = config
        self.callback = callback
        self.device = device
        self.meter = VolumeMeter()
        self.stream: Optional[sd.InputStream] = None
        self._running = False
        
    def start(self) -> None:
        """Start audio capture"""
        if self._running:
            return
            
        logger.info(f"Starting audio input (device={self.device})")
        
        def audio_callback(indata, frames, time, status):
            if status:
                logger.warning(f"Input status: {status}")
            
            # Convert to float32 if needed
            audio = np.array(indata[:, 0], dtype=np.float32)
            
            # Clamp peaks
            audio = np.clip(audio, -1.0, 1.0)
            
            # Update volume meter
            level = self.meter.update(audio)
            
            # Call user callback with audio and level
            try:
                self.callback(audio, level)
            except Exception as e:
                logger.error(f"Audio callback error: {e}")
        
        self.stream = sd.InputStream(
            device=self.device,
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype=self.config.dtype,
            blocksize=self.config.chunk_size,
            callback=audio_callback,
        )
        self.stream.start()
        self._running = True
    
    def stop(self) -> None:
        """Stop audio capture"""
        if not self._running:
            return
            
        logger.info("Stopping audio input")
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self._running = False
    
    @property
    def is_running(self) -> bool:
        return self._running


class AudioOutputStream:
    """Speaker output stream with jitter buffer"""
    
    def __init__(
        self,
        config: AudioConfig,
        device: Optional[int] = None,
    ):
        self.config = config
        self.device = device
        self.stream: Optional[sd.OutputStream] = None
        self._buffer = queue.Queue(maxsize=config.buffer_size)
        self._running = False
        self._playing = False
        self._cancelled = False
        self._lock = threading.Lock()
        
    def start(self) -> None:
        """Start audio playback"""
        if self._running:
            return
            
        logger.info(f"Starting audio output (device={self.device})")
        
        def audio_callback(outdata, frames, time, status):
            if status:
                logger.warning(f"Output status: {status}")
            
            # Check if cancelled
            with self._lock:
                if self._cancelled:
                    outdata.fill(0)
                    return
            
            # Get audio from buffer
            try:
                audio = self._buffer.get_nowait()
                outdata[:] = audio.reshape(-1, 1)
                self._playing = True
            except queue.Empty:
                outdata.fill(0)
                self._playing = False
        
        self.stream = sd.OutputStream(
            device=self.device,
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype=self.config.dtype,
            blocksize=self.config.chunk_size,
            callback=audio_callback,
        )
        self.stream.start()
        self._running = True
    
    def write(self, audio_data: np.ndarray) -> None:
        """Write audio data to playback buffer (non-blocking)"""
        if not self._running:
            return
        
        with self._lock:
            if self._cancelled:
                return
                
        try:
            # Split into chunks if needed
            for i in range(0, len(audio_data), self.config.chunk_size):
                chunk = audio_data[i:i + self.config.chunk_size]
                
                # Pad last chunk if needed
                if len(chunk) < self.config.chunk_size:
                    chunk = np.pad(chunk, (0, self.config.chunk_size - len(chunk)))
                
                # Try to put in buffer (drop if full to prevent blocking)
                try:
                    self._buffer.put_nowait(chunk)
                except queue.Full:
                    logger.warning("Output buffer full, dropping audio")
                    break
        except Exception as e:
            logger.error(f"Error writing audio: {e}")
    
    def cancel(self) -> None:
        """Cancel current playback (for barge-in)"""
        logger.info("Cancelling audio playback")
        with self._lock:
            self._cancelled = True
            # Drain buffer
            while not self._buffer.empty():
                try:
                    self._buffer.get_nowait()
                except queue.Empty:
                    break
        
        # Reset cancel flag after draining
        threading.Timer(0.1, self._reset_cancel).start()
    
    def _reset_cancel(self) -> None:
        with self._lock:
            self._cancelled = False
    
    def stop(self) -> None:
        """Stop audio playback"""
        if not self._running:
            return
            
        logger.info("Stopping audio output")
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self._running = False
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def is_playing(self) -> bool:
        """True if actively playing audio"""
        return self._playing


class AudioDevice:
    """Audio device enumeration and selection"""
    
    @staticmethod
    def list_devices() -> list[dict]:
        """List all audio devices"""
        devices = sd.query_devices()
        return [
            {
                "index": i,
                "name": d["name"],
                "inputs": d["max_input_channels"],
                "outputs": d["max_output_channels"],
                "sample_rate": d["default_samplerate"],
            }
            for i, d in enumerate(devices)
        ]
    
    @staticmethod
    def get_default_input() -> int:
        """Get default input device index"""
        return sd.default.device[0]
    
    @staticmethod
    def get_default_output() -> int:
        """Get default output device index"""
        return sd.default.device[1]
    
    @staticmethod
    def get_device_info(device_id: int) -> dict:
        """Get device information"""
        return sd.query_devices(device_id)


# Utility functions

def normalize_audio(audio: np.ndarray, target_level: float = -3.0) -> np.ndarray:
    """Normalize audio to target dB level"""
    # Convert to dB
    rms = np.sqrt(np.mean(audio ** 2))
    if rms == 0:
        return audio
    
    current_db = 20 * np.log10(rms)
    gain_db = target_level - current_db
    gain_linear = 10 ** (gain_db / 20)
    
    return np.clip(audio * gain_linear, -1.0, 1.0)


def resample_audio(
    audio: np.ndarray,
    orig_sr: int,
    target_sr: int,
) -> np.ndarray:
    """Simple resampling using linear interpolation"""
    if orig_sr == target_sr:
        return audio
    
    # Calculate new length
    duration = len(audio) / orig_sr
    new_length = int(duration * target_sr)
    
    # Resample using numpy interpolation
    old_indices = np.arange(len(audio))
    new_indices = np.linspace(0, len(audio) - 1, new_length)
    
    return np.interp(new_indices, old_indices, audio).astype(np.float32)
