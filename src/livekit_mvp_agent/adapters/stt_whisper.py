"""
Whisper STT Adapter using faster-whisper
"""

from __future__ import annotations

import asyncio
import io
import logging
from typing import Optional, Union, List, Tuple
import threading
import numpy as np

try:
    import soundfile as sf
except ImportError:
    sf = None

try:
    import faster_whisper
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False


class WhisperSTT:
    """
    Speech-to-Text adapter using faster-whisper
    
    Supports:
    - Real-time streaming transcription
    - Multilingual (EN/FR) auto-detection
    - Various model sizes and quantization levels
    - Accepts both `model` and `model_name` parameters (for compatibility)
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        *,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: str = "int8",
        sample_rate: int = 16000,
        language: Optional[str] = None,
        vad_filter: bool = True,
    ):
        if not FASTER_WHISPER_AVAILABLE:
            raise ImportError(
                "faster-whisper is not installed. "
                "Install with: pip install faster-whisper"
            )
        
        # Accept either `model` or the legacy alias `model_name`
        self.model_name = model or model_name or "base"
        self.device = device or "auto"
        self.compute_type = compute_type
        self.sample_rate = int(sample_rate)
        self.language = language if language else "auto"
        self.vad_filter = vad_filter
        self.logger = logging.getLogger(__name__)
        
        # Model instance
        self.model: Optional[faster_whisper.WhisperModel] = None
        self.initialized = False
        
        # Processing state
        self._processing_lock = asyncio.Lock()
        self._sync_lock = threading.Lock()
    
    async def initialize(self) -> None:
        """Initialize the Whisper model"""
        if self.initialized:
            return
        
        try:
            self.logger.info(f"Loading Whisper model: {self.model_name}")
            
            # Load model in executor to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                self._load_model
            )
            
            self.initialized = True
            self.logger.info("Whisper model loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Whisper: {e}", exc_info=True)
            raise
    
    def _load_model(self) -> faster_whisper.WhisperModel:
        """Load the Whisper model (runs in thread pool)"""
        return faster_whisper.WhisperModel(
            self.model_name,
            device=self.device,
            compute_type=self.compute_type,
        )
    
    def _read_audio_bytes(self, data: bytes) -> Tuple[np.ndarray, int]:
        """
        Load bytes (wav/mp3/ogg/webm if libsndfile supports) into mono float32 @ native sr.
        We'll resample on-the-fly for the model if needed.
        """
        if sf is None:
            raise ImportError("soundfile is required for audio decoding. Install with: pip install soundfile")
        
        with sf.SoundFile(io.BytesIO(data)) as f:
            audio = f.read(dtype="float32", always_2d=False)
            sr = f.samplerate
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)  # mono
        return audio, sr

    def _resample_audio(self, audio: np.ndarray, sr: int) -> Tuple[np.ndarray, int]:
        """Lightweight linear resampling to target sample rate."""
        target_sr = self.sample_rate

        if sr == target_sr:
            return audio, sr

        num_samples = len(audio)
        if num_samples == 0:
            return audio.astype(np.float32), target_sr

        duration = num_samples / sr
        target_samples = max(1, int(round(duration * target_sr)))

        # Simple linear interpolation resample; fast and dependency-free.
        source_positions = np.linspace(0.0, 1.0, num=num_samples, endpoint=False)
        target_positions = np.linspace(0.0, 1.0, num=target_samples, endpoint=False)
        resampled = np.interp(target_positions, source_positions, audio)
        return resampled.astype(np.float32), target_sr
    
    def transcribe_bytes(self, data: bytes) -> dict:
        """
        Transcribe an audio blob (synchronous) and return a dict with {text, language}.
        Used by the WebUI server.
        """
        if not self.initialized:
            # Synchronous initialization for WebUI compatibility
            self.logger.info(f"Loading Whisper model: {self.model_name}")
            self.model = faster_whisper.WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
            self.initialized = True
            self.logger.info("Whisper model loaded successfully")

        with self._sync_lock:
            audio, sr = self._read_audio_bytes(data)
            audio, sr = self._resample_audio(audio, sr)

            segments, info = self.model.transcribe(
                audio,
                language=None if self.language == "auto" else self.language,
                vad_filter=self.vad_filter,
            )
        text = "".join(seg.text for seg in segments)

        return {
            "text": text.strip(),
            "language": (info.language or "und"),
        }
    
    async def transcribe(
        self, 
        audio_data: Union[np.ndarray, bytes], 
        language: Optional[str] = None
    ) -> Optional[str]:
        """
        Transcribe audio to text
        
        Args:
            audio_data: Audio samples (numpy array or bytes)
            language: Language code (optional, overrides default)
            
        Returns:
            Transcribed text or None if no speech detected
        """
        if not self.initialized or not self.model:
            await self.initialize()
        
        async with self._processing_lock:
            try:
                # Convert audio data to numpy array if needed
                if isinstance(audio_data, bytes):
                    audio_array = np.frombuffer(audio_data, dtype=np.float32)
                else:
                    audio_array = audio_data.astype(np.float32)
                
                # Ensure audio is in the right format
                if audio_array.ndim > 1:
                    audio_array = audio_array.flatten()
                
                # Normalize audio to [-1, 1] range
                if audio_array.max() > 1.0 or audio_array.min() < -1.0:
                    audio_array = audio_array / np.max(np.abs(audio_array))
                
                # Use specified language or default
                lang = language or self.language
                
                # Transcribe in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                segments, info = await loop.run_in_executor(
                    None,
                    self._transcribe_audio,
                    audio_array,
                    lang
                )
                
                # Combine all segments
                transcript = " ".join(segment.text.strip() for segment in segments)
                
                if transcript:
                    detected_language = info.language
                    confidence = info.language_probability
                    
                    self.logger.debug(
                        f"Transcribed ({detected_language}, conf: {confidence:.2f}): {transcript}"
                    )
                    
                    return transcript.strip()
                
                return None
                
            except Exception as e:
                self.logger.error(f"Transcription error: {e}", exc_info=True)
                return None
    
    def _transcribe_audio(
        self, 
        audio_array: np.ndarray, 
        language: Optional[str]
    ) -> tuple:
        """Transcribe audio (runs in thread pool)"""
        segments, info = self.model.transcribe(
            audio_array,
            language=language,
            vad_filter=self.vad_filter,
            word_timestamps=False,  # Disable for faster processing
        )
        
        return list(segments), info
    
    async def transcribe_streaming(
        self, 
        audio_stream: asyncio.Queue, 
        callback: callable,
        language: Optional[str] = None
    ) -> None:
        """
        Transcribe streaming audio with callback for partial results
        
        Args:
            audio_stream: Queue of audio chunks
            callback: Function to call with partial/final results
            language: Language code (optional)
        """
        if not self.initialized:
            await self.initialize()
        
        audio_buffer = []
        
        try:
            while True:
                try:
                    # Get audio chunk with timeout
                    audio_chunk = await asyncio.wait_for(
                        audio_stream.get(), 
                        timeout=1.0
                    )
                    
                    if audio_chunk is None:  # End of stream signal
                        break
                    
                    # Add to buffer
                    audio_buffer.extend(audio_chunk)
                    
                    # Process when we have enough audio (e.g., 3 seconds)
                    if len(audio_buffer) >= 16000 * 3:  # 3 seconds at 16kHz
                        audio_array = np.array(audio_buffer, dtype=np.float32)
                        
                        # Transcribe
                        transcript = await self.transcribe(audio_array, language)
                        
                        if transcript:
                            # Call callback with result
                            await callback(transcript, is_final=True)
                        
                        # Keep overlap for context
                        overlap = len(audio_buffer) // 4  # 25% overlap
                        audio_buffer = audio_buffer[-overlap:]
                
                except asyncio.TimeoutError:
                    # Process current buffer if any
                    if audio_buffer:
                        audio_array = np.array(audio_buffer, dtype=np.float32)
                        transcript = await self.transcribe(audio_array, language)
                        
                        if transcript:
                            await callback(transcript, is_final=True)
                        
                        audio_buffer.clear()
                
        except Exception as e:
            self.logger.error(f"Streaming transcription error: {e}", exc_info=True)
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        # Whisper supports these languages
        return [
            "en", "fr", "de", "es", "it", "pt", "nl", "pl", "ru", "ja", "ko", "zh",
            "ar", "hi", "th", "vi", "uk", "cs", "tr", "sv", "da", "no", "fi", "hu",
            "el", "he", "ro", "bg", "hr", "sk", "sl", "et", "lv", "lt", "mt", "cy"
        ]
    
    def detect_language(self, audio_data: np.ndarray) -> tuple[str, float]:
        """
        Detect language from audio
        
        Args:
            audio_data: Audio samples
            
        Returns:
            Tuple of (language_code, confidence)
        """
        if not self.initialized or not self.model:
            return "en", 0.0
        
        try:
            # Use shorter audio for language detection
            audio_sample = audio_data[:16000 * 10]  # Max 10 seconds
            
            segments, info = self.model.transcribe(
                audio_sample,
                language=None,  # Auto-detect
                vad_filter=True,
                word_timestamps=False,
            )
            
            return info.language, info.language_probability
            
        except Exception as e:
            self.logger.error(f"Language detection error: {e}")
            return "en", 0.0


class MockWhisperSTT:
    """Mock STT for testing when faster-whisper is not available"""
    
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.initialized = False
    
    async def initialize(self) -> None:
        """Mock initialization"""
        self.logger.info("Mock Whisper STT initialized")
        self.initialized = True
    
    async def transcribe(
        self, 
        audio_data: Union[np.ndarray, bytes], 
        language: Optional[str] = None
    ) -> Optional[str]:
        """Mock transcription"""
        self.logger.debug("Mock transcription: Hello, this is a test transcription.")
        return "Hello, this is a test transcription."
    
    def get_supported_languages(self) -> List[str]:
        return ["en", "fr"]
    
    def detect_language(self, audio_data) -> tuple[str, float]:
        return "en", 0.9


# Use mock if faster-whisper is not available
if not FASTER_WHISPER_AVAILABLE:
    WhisperSTT = MockWhisperSTT
