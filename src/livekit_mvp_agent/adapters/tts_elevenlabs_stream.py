"""
ElevenLabs Streaming TTS Adapter for low-latency audio generation
Uses WebSocket API for incremental text-to-speech with immediate playback
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator, Optional

import httpx
import numpy as np
import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)


class ElevenLabsStreamingTTS:
    """
    Streaming TTS adapter using ElevenLabs WebSocket API
    - Sends text chunks as they arrive from LLM
    - Receives MP3 audio chunks for immediate playback
    - Target TTFB < 350ms
    """

    def __init__(
        self,
        api_key: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Rachel
        model_id: str = "eleven_flash_v2_5",
        language: str = "fr",  # French for tutor
        stability: float = 0.6,
        similarity_boost: float = 0.8,
        style: float = 0.1,
        use_speaker_boost: bool = True,
        timeout_s: float = 30.0,
    ):
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.language = language
        self.stability = stability
        self.similarity_boost = similarity_boost
        self.style = style
        self.use_speaker_boost = use_speaker_boost
        self.timeout_s = timeout_s
        
        self._ws: Optional[WebSocketClientProtocol] = None
        self._streaming = False
        self._stopped = False
    
    async def begin_stream(self) -> None:
        """Initialize WebSocket connection for streaming"""
        if self._streaming:
            logger.warning("Stream already active")
            return
        
        # WebSocket URL
        url = f"wss://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream-input?model_id={self.model_id}"
        
        try:
            self._ws = await websockets.connect(url, extra_headers={
                "xi-api-key": self.api_key,
            })
            
            # Send initialization message
            init_message = {
                "text": " ",  # Initial space to start stream
                "voice_settings": {
                    "stability": self.stability,
                    "similarity_boost": self.similarity_boost,
                    "style": self.style,
                    "use_speaker_boost": self.use_speaker_boost,
                },
                "generation_config": {
                    "chunk_length_schedule": [120, 160, 250, 290],  # Optimized for low latency
                },
                "xi_api_key": self.api_key,
            }
            
            await self._ws.send(json.dumps(init_message))
            self._streaming = True
            self._stopped = False
            logger.info(f"Streaming TTS started (voice={self.voice_id}, model={self.model_id})")
            
        except Exception as e:
            logger.error(f"Failed to start streaming: {e}")
            raise
    
    async def send_text_chunk(self, text: str) -> None:
        """Send a text chunk to be synthesized"""
        if not self._streaming or not self._ws:
            logger.warning("Stream not active")
            return
        
        if self._stopped:
            return
        
        try:
            message = {
                "text": text,
                "try_trigger_generation": True,  # Trigger audio generation
            }
            await self._ws.send(json.dumps(message))
            logger.debug(f"Sent text chunk: {text[:50]}...")
            
        except Exception as e:
            logger.error(f"Error sending text chunk: {e}")
    
    async def end_stream(self) -> None:
        """Signal end of text input"""
        if not self._streaming or not self._ws:
            return
        
        try:
            # Send empty string to signal end
            await self._ws.send(json.dumps({"text": ""}))
            logger.debug("Sent end-of-stream signal")
            
        except Exception as e:
            logger.error(f"Error ending stream: {e}")
    
    async def receive_audio_chunks(self) -> AsyncIterator[bytes]:
        """
        Receive audio chunks from the WebSocket
        Yields MP3 chunks that should be decoded to PCM for playback
        """
        if not self._streaming or not self._ws:
            logger.warning("Stream not active")
            return
        
        try:
            async for message in self._ws:
                if self._stopped:
                    break
                
                try:
                    data = json.loads(message)
                    
                    # Check for audio chunk
                    if "audio" in data:
                        # Base64-encoded MP3 chunk
                        import base64
                        audio_bytes = base64.b64decode(data["audio"])
                        yield audio_bytes
                    
                    # Check for completion or errors
                    if data.get("isFinal"):
                        logger.debug("Received final audio chunk")
                        break
                    
                    if "error" in data:
                        logger.error(f"Streaming error: {data['error']}")
                        break
                        
                except json.JSONDecodeError:
                    # Might be binary data
                    logger.warning("Received non-JSON message")
                    continue
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error receiving audio: {e}")
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """Stop and cleanup WebSocket connection"""
        if not self._streaming:
            return
        
        self._stopped = True
        self._streaming = False
        
        if self._ws:
            try:
                await self._ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
            self._ws = None
        
        logger.info("Streaming TTS stopped")
    
    def is_streaming(self) -> bool:
        """Check if currently streaming"""
        return self._streaming and not self._stopped


# MP3 decoder utility
def decode_mp3_to_pcm(mp3_data: bytes, sample_rate: int = 16000) -> np.ndarray:
    """
    Decode MP3 bytes to PCM float32 array
    Requires pydub and ffmpeg/libav
    """
    try:
        from pydub import AudioSegment
        import io
        
        # Load MP3
        audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))
        
        # Convert to mono and target sample rate
        audio = audio.set_channels(1)
        audio = audio.set_frame_rate(sample_rate)
        
        # Convert to numpy array
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        
        # Normalize to -1..1
        samples = samples / (2 ** 15)  # 16-bit audio
        
        return samples
        
    except ImportError:
        logger.error("pydub not installed, cannot decode MP3")
        return np.array([], dtype=np.float32)
    except Exception as e:
        logger.error(f"Error decoding MP3: {e}")
        return np.array([], dtype=np.float32)


# REST fallback adapter
class ElevenLabsRESTFallback:
    """Fallback to REST API if streaming fails"""
    
    def __init__(
        self,
        api_key: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        model_id: str = "eleven_flash_v2_5",
        timeout_s: float = 30.0,
    ):
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.timeout_s = timeout_s
        self._client = httpx.AsyncClient(timeout=timeout_s)
    
    async def synthesize(self, text: str) -> bytes:
        """Synthesize full text to MP3 (blocking until complete)"""
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        
        headers = {
            "xi-api-key": self.api_key,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        }
        
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.6,
                "similarity_boost": 0.8,
                "style": 0.1,
                "use_speaker_boost": True,
            },
        }
        
        try:
            logger.info(f"REST TTS request ({len(text)} chars)")
            resp = await self._client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            logger.info(f"REST TTS response ({len(resp.content)} bytes)")
            return resp.content
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            return b""
        except Exception as e:
            logger.error(f"REST TTS failed: {e}")
            return b""
    
    async def close(self) -> None:
        """Close HTTP client"""
        await self._client.aclose()
