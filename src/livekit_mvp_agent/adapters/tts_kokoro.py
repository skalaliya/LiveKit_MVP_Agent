"""
Kokoro TTS Adapter with fallback to NoOp
"""

import asyncio
import logging
from typing import Optional, Union
import numpy as np

try:
    import kokoro_tts
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False

from .tts_piper import PiperTTS


class KokoroTTS:
    """
    Text-to-Speech adapter with Kokoro as primary and Piper as fallback
    
    Features:
    - High-quality Kokoro TTS (if available)
    - Piper TTS fallback
    - NoOp TTS as final fallback
    - Multilingual support (EN/FR)
    """
    
    def __init__(
        self,
        primary_system: str = "kokoro",
        fallback_system: str = "piper", 
        voice: str = "en-US-kokoro",
        speed: float = 1.0,
        sample_rate: int = 24000,
    ):
        self.primary_system = primary_system
        self.fallback_system = fallback_system
        self.voice = voice
        self.speed = speed
        self.sample_rate = sample_rate
        self.logger = logging.getLogger(__name__)
        
        # TTS instances
        self.kokoro_tts: Optional[object] = None
        self.piper_tts: Optional[PiperTTS] = None
        self.initialized = False
        
        # Voice mappings
        self._voice_mappings = self._load_voice_mappings()
    
    async def initialize(self) -> None:
        """Initialize TTS systems"""
        if self.initialized:
            return
        
        self.logger.info("Initializing TTS systems...")
        
        # Try to initialize Kokoro
        if self.primary_system == "kokoro" and KOKORO_AVAILABLE:
            try:
                await self._initialize_kokoro()
                self.logger.info("Kokoro TTS initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Kokoro TTS: {e}")
        
        # Initialize Piper as fallback
        if self.fallback_system == "piper":
            try:
                self.piper_tts = PiperTTS()
                await self.piper_tts.initialize()
                self.logger.info("Piper TTS initialized as fallback")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Piper TTS: {e}")
        
        self.initialized = True
        
        # Log what's available
        available_systems = []
        if self.kokoro_tts:
            available_systems.append("Kokoro")
        if self.piper_tts and self.piper_tts.initialized:
            available_systems.append("Piper")
        available_systems.append("NoOp")
        
        self.logger.info(f"TTS systems available: {', '.join(available_systems)}")
    
    async def _initialize_kokoro(self) -> None:
        """Initialize Kokoro TTS"""
        if not KOKORO_AVAILABLE:
            raise ImportError("Kokoro TTS not available")
        
        # TODO: Initialize Kokoro TTS properly
        # This is a placeholder implementation
        self.logger.info("Kokoro TTS would be initialized here")
        # self.kokoro_tts = kokoro_tts.KokoroTTS(voice=self.voice)
    
    async def synthesize(
        self, 
        text: str, 
        language: str = "auto",
        voice: Optional[str] = None
    ) -> Optional[np.ndarray]:
        """
        Synthesize speech from text
        
        Args:
            text: Text to synthesize
            language: Language code (en/fr/auto)
            voice: Voice ID (optional, uses default)
            
        Returns:
            Audio samples as numpy array or None if failed
        """
        if not text.strip():
            return None
        
        if not self.initialized:
            await self.initialize()
        
        # Choose voice
        chosen_voice = voice or self.voice
        
        # Detect language if auto
        if language == "auto":
            language = self._detect_language(text)
        
        # Try TTS systems in order
        for system_name in [self.primary_system, self.fallback_system, "noop"]:
            try:
                audio_data = await self._synthesize_with_system(
                    text, language, chosen_voice, system_name
                )
                
                if audio_data is not None:
                    self.logger.debug(f"Synthesized with {system_name}: '{text[:50]}...'")
                    return audio_data
                    
            except Exception as e:
                self.logger.warning(f"TTS {system_name} failed: {e}")
                continue
        
        self.logger.error("All TTS systems failed")
        return None
    
    async def _synthesize_with_system(
        self, 
        text: str, 
        language: str, 
        voice: str, 
        system: str
    ) -> Optional[np.ndarray]:
        """Synthesize with specific TTS system"""
        
        if system == "kokoro" and self.kokoro_tts:
            return await self._synthesize_kokoro(text, language, voice)
        
        elif system == "piper" and self.piper_tts:
            return await self.piper_tts.synthesize(text, language, voice)
        
        elif system == "noop":
            return await self._synthesize_noop(text, language, voice)
        
        return None
    
    async def _synthesize_kokoro(
        self, 
        text: str, 
        language: str, 
        voice: str
    ) -> Optional[np.ndarray]:
        """Synthesize with Kokoro TTS"""
        # TODO: Implement actual Kokoro TTS synthesis
        # This is a placeholder that falls through to next system
        self.logger.debug("Kokoro synthesis not yet implemented")
        return None
    
    async def _synthesize_noop(
        self, 
        text: str, 
        language: str, 
        voice: str
    ) -> Optional[np.ndarray]:
        """NoOp TTS - just logs the text and returns silence"""
        self.logger.info(f"[TTS NoOp] ({language}, {voice}): {text}")
        
        # Return a short silent audio buffer
        duration = min(len(text) * 0.1, 5.0)  # Roughly 0.1s per character, max 5s
        samples = int(duration * self.sample_rate)
        
        # Generate very quiet noise instead of pure silence
        audio = np.random.normal(0, 0.001, samples).astype(np.float32)
        
        return audio
    
    def _detect_language(self, text: str) -> str:
        """
        Simple language detection based on character patterns
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code (en/fr)
        """
        # French indicators
        french_patterns = [
            "ç", "à", "é", "è", "ê", "ë", "î", "ï", "ô", "ö", "ù", "û", "ü", "ÿ",
            "qu'", "c'est", "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
            "le", "la", "les", "un", "une", "des", "du", "de la", "au", "aux"
        ]
        
        text_lower = text.lower()
        
        # Count French indicators
        french_score = sum(1 for pattern in french_patterns if pattern in text_lower)
        
        # If significant French content, classify as French
        if french_score >= 2 or any(char in text for char in "çàéèêëîïôöùûüÿ"):
            return "fr"
        
        return "en"  # Default to English
    
    def _load_voice_mappings(self) -> dict:
        """Load voice mappings from config (placeholder)"""
        return {
            "en-US-kokoro": {"system": "kokoro", "path": "en-US"},
            "fr-FR-kokoro": {"system": "kokoro", "path": "fr-FR"},
            "en-US-piper": {"system": "piper", "path": "en_US-lessac-medium"},
            "fr-FR-piper": {"system": "piper", "path": "fr_FR-siwis-medium"},
        }
    
    async def list_voices(self) -> dict:
        """List available voices"""
        voices = {}
        
        if self.kokoro_tts:
            voices["kokoro"] = ["en-US-kokoro", "fr-FR-kokoro"]
        
        if self.piper_tts:
            piper_voices = await self.piper_tts.list_voices()
            voices["piper"] = piper_voices
        
        voices["noop"] = ["noop"]
        
        return voices
    
    async def set_voice(self, voice: str) -> bool:
        """
        Set the current voice
        
        Args:
            voice: Voice ID to use
            
        Returns:
            True if voice is available, False otherwise
        """
        available_voices = await self.list_voices()
        
        for system_voices in available_voices.values():
            if voice in system_voices:
                self.voice = voice
                self.logger.info(f"Voice changed to: {voice}")
                return True
        
        self.logger.warning(f"Voice not available: {voice}")
        return False
    
    async def close(self) -> None:
        """Cleanup TTS resources"""
        if self.piper_tts:
            await self.piper_tts.close()
        
        # Cleanup Kokoro if needed
        self.kokoro_tts = None
        
        self.initialized = False


class NoOpTTS:
    """
    No-operation TTS that just logs text and returns silent audio
    Useful for testing and fallback scenarios
    """
    
    def __init__(self, sample_rate: int = 24000):
        self.sample_rate = sample_rate
        self.logger = logging.getLogger(__name__)
        self.initialized = True
    
    async def initialize(self) -> None:
        """Initialize (no-op)"""
        self.logger.info("NoOp TTS initialized")
    
    async def synthesize(
        self, 
        text: str, 
        language: str = "en",
        voice: Optional[str] = None
    ) -> Optional[np.ndarray]:
        """Log text and return silent audio"""
        self.logger.info(f"[NoOp TTS] ({language}): {text}")
        
        # Return short silent audio
        duration = min(len(text) * 0.08, 3.0)  # ~0.08s per character, max 3s
        samples = int(duration * self.sample_rate)
        
        return np.zeros(samples, dtype=np.float32)
    
    async def list_voices(self) -> list:
        """Return mock voice list"""
        return ["noop"]
    
    async def close(self) -> None:
        """Cleanup (no-op)"""
        pass