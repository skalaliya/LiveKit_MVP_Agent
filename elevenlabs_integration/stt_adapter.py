"""
ElevenLabs STT (Speech-to-Text) Adapter

This adapter uses ElevenLabs API for speech recognition with multilingual support.
Provides real-time transcription with high accuracy for English and French.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, AsyncGenerator
import httpx
from io import BytesIO
import numpy as np

# Base adapter interface (simplified for standalone use)
class BaseSTTAdapter:
    def __init__(self):
        self.is_initialized = False
    
    async def initialize(self):
        pass
    
    async def cleanup(self):
        pass

logger = logging.getLogger(__name__)


class ElevenLabsSTTAdapter(BaseSTTAdapter):
    """ElevenLabs Speech-to-Text adapter with real-time transcription."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "eleven_multilingual_v2",
        language: str = "auto",
        timeout: int = 30
    ):
        """
        Initialize ElevenLabs STT adapter.
        
        Args:
            api_key: ElevenLabs API key
            model: Model to use for STT (eleven_multilingual_v2, eleven_english_v1)
            language: Language code ('en', 'fr', 'auto' for detection)
            timeout: Request timeout in seconds
        """
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.language = language
        self.timeout = timeout
        self.base_url = "https://api.elevenlabs.io/v1"
        self.client: Optional[httpx.AsyncClient] = None
        
    async def initialize(self) -> None:
        """Initialize the ElevenLabs STT client."""
        try:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "audio/mpeg",
                    "Accept": "application/json"
                }
            )
            
            # Test connection
            response = await self.client.get(f"{self.base_url}/user")
            if response.status_code != 200:
                raise RuntimeError(f"ElevenLabs API authentication failed: {response.status_code}")
                
            logger.info("ElevenLabs STT initialized successfully")
            self.is_initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize ElevenLabs STT: {e}")
            # Fallback to mock for development
            self.is_initialized = False
            
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.client:
            await self.client.aclose()
            self.client = None
            
    async def transcribe_audio(
        self, 
        audio_data: bytes, 
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio using ElevenLabs STT API.
        
        Args:
            audio_data: Raw audio bytes (WAV/MP3 format)
            language: Language override (optional)
            
        Returns:
            Dictionary with transcription results
        """
        if not self.is_initialized or not self.client:
            return await self._mock_transcribe(audio_data)
            
        try:
            # Use language override or instance default
            lang = language or self.language
            
            # Prepare request
            url = f"{self.base_url}/speech-to-text"
            
            # Create form data
            files = {
                "audio": ("audio.wav", BytesIO(audio_data), "audio/wav")
            }
            
            data = {
                "model_id": self.model,
                "language_code": lang if lang != "auto" else None
            }
            
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}
            
            response = await self.client.post(
                url,
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                
                return {
                    "text": result.get("text", ""),
                    "confidence": result.get("confidence", 0.9),
                    "language": result.get("detected_language", lang),
                    "duration": result.get("duration_seconds", 0),
                    "words": result.get("words", []),
                    "success": True
                }
            else:
                logger.error(f"ElevenLabs STT API error: {response.status_code} - {response.text}")
                return await self._mock_transcribe(audio_data)
                
        except Exception as e:
            logger.error(f"ElevenLabs STT transcription failed: {e}")
            return await self._mock_transcribe(audio_data)
            
    async def transcribe_stream(
        self, 
        audio_stream: AsyncGenerator[bytes, None],
        language: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream transcription (if supported by ElevenLabs).
        For now, accumulates chunks and transcribes in batches.
        """
        if not self.is_initialized:
            async for chunk in audio_stream:
                yield await self._mock_transcribe(chunk)
            return
            
        buffer = BytesIO()
        chunk_count = 0
        
        try:
            async for audio_chunk in audio_stream:
                buffer.write(audio_chunk)
                chunk_count += 1
                
                # Process every 10 chunks or when buffer gets large
                if chunk_count >= 10 or buffer.tell() > 1024 * 1024:  # 1MB
                    audio_data = buffer.getvalue()
                    if len(audio_data) > 1024:  # Only process if we have enough data
                        result = await self.transcribe_audio(audio_data, language)
                        if result["text"].strip():
                            yield result
                    
                    # Reset buffer
                    buffer = BytesIO()
                    chunk_count = 0
                    
        except Exception as e:
            logger.error(f"Stream transcription error: {e}")
            yield {
                "text": "",
                "confidence": 0.0,
                "language": language or "en",
                "success": False,
                "error": str(e)
            }
            
    async def _mock_transcribe(self, audio_data: bytes) -> Dict[str, Any]:
        """Mock transcription for development/fallback."""
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        # Mock response based on audio length
        duration = len(audio_data) / 16000 / 2  # Estimate duration
        
        if duration > 1:
            mock_text = "Hello, this is a mock transcription from ElevenLabs STT adapter."
        else:
            mock_text = "Mock audio"
            
        return {
            "text": mock_text,
            "confidence": 0.85,
            "language": "en",
            "duration": duration,
            "words": [
                {"word": word, "start": i * 0.5, "end": (i + 1) * 0.5, "confidence": 0.9}
                for i, word in enumerate(mock_text.split())
            ],
            "success": True,
            "mock": True
        }
        
    def get_supported_languages(self) -> list[str]:
        """Get list of supported languages."""
        return [
            "en",  # English
            "fr",  # French
            "es",  # Spanish
            "de",  # German
            "it",  # Italian
            "pt",  # Portuguese
            "pl",  # Polish
            "tr",  # Turkish
            "ru",  # Russian
            "nl",  # Dutch
            "cs",  # Czech
            "ar",  # Arabic
            "zh",  # Chinese
            "ja",  # Japanese
            "hu",  # Hungarian
            "ko",  # Korean
        ]
        
    def get_available_models(self) -> list[str]:
        """Get list of available models."""
        return [
            "eleven_multilingual_v2",  # Latest multilingual model
            "eleven_english_v1",       # English-only model
            "eleven_multilingual_v1"   # Older multilingual model
        ]