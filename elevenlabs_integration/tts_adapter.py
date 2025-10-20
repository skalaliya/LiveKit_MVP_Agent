"""
ElevenLabs TTS (Text-to-Speech) Adapter

This adapter uses ElevenLabs API for high-quality voice synthesis.
Supports multiple voices, languages, and voice settings.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Union
import httpx
from io import BytesIO
import json

# Base adapter interface (simplified for standalone use)
class BaseTTSAdapter:
    def __init__(self):
        self.is_initialized = False
    
    async def initialize(self):
        pass
    
    async def cleanup(self):
        pass

logger = logging.getLogger(__name__)


class ElevenLabsTTSAdapter(BaseTTSAdapter):
    """ElevenLabs Text-to-Speech adapter with multiple voice options."""
    
    def __init__(
        self,
        api_key: str,
        voice_id: Optional[str] = None,
        model: str = "eleven_multilingual_v2",
        voice_settings: Optional[Dict[str, float]] = None,
        timeout: int = 30
    ):
        """
        Initialize ElevenLabs TTS adapter.
        
        Args:
            api_key: ElevenLabs API key
            voice_id: Specific voice ID (if None, uses default voice)
            model: Model to use for TTS
            voice_settings: Voice configuration (stability, similarity_boost, style)
            timeout: Request timeout in seconds
        """
        super().__init__()
        self.api_key = api_key
        self.voice_id = voice_id
        self.model = model
        self.timeout = timeout
        self.base_url = "https://api.elevenlabs.io/v1"
        self.client: Optional[httpx.AsyncClient] = None
        
        # Default voice settings
        self.voice_settings = voice_settings or {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }
        
        # Cache for voices
        self._voices_cache: Optional[List[Dict[str, Any]]] = None
        self._default_voice_id: Optional[str] = None
        
    async def initialize(self) -> None:
        """Initialize the ElevenLabs TTS client."""
        try:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "xi-api-key": self.api_key,
                    "Accept": "application/json"
                }
            )
            
            # Test connection and load voices
            response = await self.client.get(f"{self.base_url}/user")
            if response.status_code != 200:
                raise RuntimeError(f"ElevenLabs API authentication failed: {response.status_code}")
                
            # Load available voices
            await self._load_voices()
            
            # Set default voice if none specified
            if not self.voice_id and self._voices_cache:
                # Find a good default voice (prefer multilingual)
                for voice in self._voices_cache:
                    if "multilingual" in voice.get("name", "").lower() or "adam" in voice.get("name", "").lower():
                        self._default_voice_id = voice["voice_id"]
                        break
                
                # Fallback to first available voice
                if not self._default_voice_id and self._voices_cache:
                    self._default_voice_id = self._voices_cache[0]["voice_id"]
                    
            logger.info(f"ElevenLabs TTS initialized successfully with {len(self._voices_cache or [])} voices")
            self.is_initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize ElevenLabs TTS: {e}")
            # Fallback to mock for development
            self.is_initialized = False
            
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.client:
            await self.client.aclose()
            self.client = None
            
    async def _load_voices(self) -> None:
        """Load available voices from ElevenLabs."""
        if not self.client:
            return
            
        try:
            response = await self.client.get(f"{self.base_url}/voices")
            if response.status_code == 200:
                data = response.json()
                self._voices_cache = data.get("voices", [])
                logger.info(f"Loaded {len(self._voices_cache)} voices from ElevenLabs")
            else:
                logger.warning(f"Failed to load voices: {response.status_code}")
                self._voices_cache = []
        except Exception as e:
            logger.error(f"Error loading voices: {e}")
            self._voices_cache = []
            
    async def synthesize_speech(
        self, 
        text: str, 
        voice_id: Optional[str] = None,
        language: Optional[str] = None,
        **kwargs
    ) -> bytes:
        """
        Synthesize speech from text using ElevenLabs API.
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID override
            language: Language hint (used for voice selection)
            **kwargs: Additional voice settings
            
        Returns:
            Audio data as bytes (MP3 format)
        """
        if not self.is_initialized or not self.client:
            return await self._mock_synthesize(text)
            
        try:
            # Determine voice to use
            target_voice_id = voice_id or self.voice_id or self._default_voice_id
            
            if not target_voice_id:
                logger.warning("No voice ID available, using mock synthesis")
                return await self._mock_synthesize(text)
                
            # Merge voice settings
            settings = {**self.voice_settings, **kwargs}
            
            # Prepare request
            url = f"{self.base_url}/text-to-speech/{target_voice_id}"
            
            payload = {
                "text": text,
                "model_id": self.model,
                "voice_settings": settings
            }
            
            response = await self.client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info(f"Synthesized {len(text)} characters to {len(response.content)} bytes")
                return response.content
            else:
                logger.error(f"ElevenLabs TTS API error: {response.status_code} - {response.text}")
                return await self._mock_synthesize(text)
                
        except Exception as e:
            logger.error(f"ElevenLabs TTS synthesis failed: {e}")
            return await self._mock_synthesize(text)
            
    async def synthesize_stream(
        self, 
        text: str, 
        voice_id: Optional[str] = None,
        **kwargs
    ) -> bytes:
        """
        Streaming synthesis (ElevenLabs supports streaming).
        For now, falls back to regular synthesis.
        """
        # TODO: Implement streaming synthesis with ElevenLabs streaming API
        return await self.synthesize_speech(text, voice_id, **kwargs)
        
    async def _mock_synthesize(self, text: str) -> bytes:
        """Mock synthesis for development/fallback."""
        # Simulate processing delay
        await asyncio.sleep(0.5)
        
        # Return minimal WAV file (silence)
        # WAV header for 1 second of silence at 16kHz, 16-bit mono
        sample_rate = 16000
        duration = max(1, len(text) // 20)  # Rough duration estimate
        num_samples = sample_rate * duration
        
        # WAV header
        wav_header = (
            b'RIFF' +
            (36 + num_samples * 2).to_bytes(4, 'little') +
            b'WAVE' +
            b'fmt ' +
            (16).to_bytes(4, 'little') +
            (1).to_bytes(2, 'little') +   # PCM
            (1).to_bytes(2, 'little') +   # Mono
            sample_rate.to_bytes(4, 'little') +
            (sample_rate * 2).to_bytes(4, 'little') +
            (2).to_bytes(2, 'little') +
            (16).to_bytes(2, 'little') +
            b'data' +
            (num_samples * 2).to_bytes(4, 'little')
        )
        
        # Silent audio data
        audio_data = b'\x00' * (num_samples * 2)
        
        logger.info(f"Mock TTS: Generated {len(wav_header + audio_data)} bytes for '{text[:50]}...'")
        return wav_header + audio_data
        
    async def get_voices(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get available voices, optionally filtered by language.
        
        Args:
            language: Language code to filter by (optional)
            
        Returns:
            List of voice information dictionaries
        """
        if not self._voices_cache:
            await self._load_voices()
            
        voices = self._voices_cache or []
        
        if language:
            # Filter voices that support the language
            filtered_voices = []
            for voice in voices:
                voice_labels = voice.get("labels", {})
                supported_languages = voice_labels.get("language", "").split(",")
                supported_languages = [lang.strip().lower() for lang in supported_languages]
                
                if language.lower() in supported_languages or "multilingual" in supported_languages:
                    filtered_voices.append(voice)
                    
            return filtered_voices
            
        return voices
        
    async def get_voice_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a voice by name."""
        voices = await self.get_voices()
        
        for voice in voices:
            if voice.get("name", "").lower() == name.lower():
                return voice
                
        return None
        
    async def set_voice(self, voice_id: str) -> bool:
        """
        Set the active voice.
        
        Args:
            voice_id: Voice ID to set as active
            
        Returns:
            True if voice exists and was set
        """
        voices = await self.get_voices()
        
        for voice in voices:
            if voice.get("voice_id") == voice_id:
                self.voice_id = voice_id
                logger.info(f"Set active voice to: {voice.get('name')} ({voice_id})")
                return True
                
        logger.warning(f"Voice ID not found: {voice_id}")
        return False
        
    def get_supported_formats(self) -> List[str]:
        """Get supported audio formats."""
        return ["mp3", "wav", "pcm"]
        
    def get_available_models(self) -> List[str]:
        """Get available TTS models."""
        return [
            "eleven_multilingual_v2",
            "eleven_multilingual_v1", 
            "eleven_monolingual_v1",
            "eleven_english_v1"
        ]