"""
ElevenLabs Integration Pipeline

Main pipeline that integrates ElevenLabs STT/TTS with existing LLM.
Combines the best of both worlds: ElevenLabs audio processing + local LLM.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, AsyncGenerator
import os
from dataclasses import dataclass

# Import from main project
import sys
sys.path.append('../src')
from livekit_mvp_agent.config import get_settings
from livekit_mvp_agent.adapters.llm_ollama import OllamaLLM
from livekit_mvp_agent.adapters.vad_silero import SileroVAD
from livekit_mvp_agent.utils.audio import AudioProcessor

# ElevenLabs adapters
from .config import ElevenLabsConfig, get_recommended_voice, get_model_for_use_case
from .stt_adapter import ElevenLabsSTTAdapter
from .tts_adapter import ElevenLabsTTSAdapter

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """Context for ongoing conversation."""
    messages: list = None
    current_language: str = "en"
    user_preferences: dict = None
    
    def __post_init__(self):
        if self.messages is None:
            self.messages = []
        if self.user_preferences is None:
            self.user_preferences = {}


class ElevenLabsPipeline:
    """
    Enhanced voice agent pipeline using ElevenLabs for audio + local LLM.
    
    This pipeline provides:
    - High-quality STT via ElevenLabs
    - Local LLM processing via Ollama  
    - High-quality TTS via ElevenLabs
    - Voice Activity Detection
    - Bilingual conversation support
    """
    
    def __init__(self, elevenlabs_config: ElevenLabsConfig, use_existing_llm: bool = True):
        """
        Initialize the ElevenLabs pipeline.
        
        Args:
            elevenlabs_config: ElevenLabs configuration
            use_existing_llm: Whether to use existing Ollama LLM setup
        """
        self.config = elevenlabs_config
        self.use_existing_llm = use_existing_llm
        
        # Load main project settings
        self.main_settings = get_settings()
        
        # Components
        self.stt: Optional[ElevenLabsSTTAdapter] = None
        self.tts: Optional[ElevenLabsTTSAdapter] = None
        self.llm: Optional[OllamaLLM] = None
        self.vad: Optional[SileroVAD] = None
        self.audio_processor: Optional[AudioProcessor] = None
        
        # State
        self.is_running = False
        self.conversation = ConversationContext()
        
    async def initialize(self) -> None:
        """Initialize all pipeline components."""
        logger.info("Initializing ElevenLabs pipeline...")
        
        try:
            # Initialize STT
            self.stt = ElevenLabsSTTAdapter(
                api_key=self.config.stt.api_key,
                model=self.config.stt.model,
                language=self.config.stt.language,
                timeout=self.config.stt.timeout
            )
            await self.stt.initialize()
            
            # Initialize TTS
            self.tts = ElevenLabsTTSAdapter(
                api_key=self.config.tts.api_key,
                voice_id=self.config.tts.voice_id,
                model=self.config.tts.model,
                voice_settings=self.config.tts.voice_settings,
                timeout=self.config.tts.timeout
            )
            await self.tts.initialize()
            
            # Initialize LLM (reuse existing setup)
            if self.use_existing_llm:
                self.llm = OllamaLLM(
                    model=self.main_settings.llm_model,
                    base_url=self.main_settings.llm_base_url,
                    temperature=self.main_settings.llm_temperature,
                    max_tokens=self.main_settings.llm_max_tokens,
                    timeout=self.main_settings.llm_timeout_seconds
                )
                await self.llm.initialize()
                
            # Initialize VAD
            self.vad = SileroVAD(
                sample_rate=self.main_settings.sample_rate,
                threshold=self.main_settings.vad_threshold
            )
            await self.vad.initialize()
            
            # Initialize audio processor
            self.audio_processor = AudioProcessor(
                sample_rate=self.main_settings.sample_rate,
                channels=self.main_settings.channels,
                chunk_size=self.main_settings.chunk_size
            )
            
            logger.info("ElevenLabs pipeline initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}")
            raise
            
    async def cleanup(self) -> None:
        """Clean up all resources."""
        logger.info("Cleaning up ElevenLabs pipeline...")
        
        cleanup_tasks = []
        
        if self.stt:
            cleanup_tasks.append(self.stt.cleanup())
        if self.tts:
            cleanup_tasks.append(self.tts.cleanup())
        if self.llm:
            cleanup_tasks.append(self.llm.cleanup())
        if self.vad:
            cleanup_tasks.append(self.vad.cleanup())
            
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
        self.is_running = False
        logger.info("Pipeline cleanup completed")
        
    async def process_audio_stream(
        self, 
        audio_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[bytes, None]:
        """
        Process incoming audio stream and yield response audio.
        
        Args:
            audio_stream: Incoming audio chunks
            
        Yields:
            Response audio chunks
        """
        if not all([self.stt, self.tts, self.llm, self.vad]):
            raise RuntimeError("Pipeline not properly initialized")
            
        self.is_running = True
        
        try:
            # Buffer for accumulating speech
            speech_buffer = bytearray()
            is_speaking = False
            silence_count = 0
            
            async for audio_chunk in audio_stream:
                if not self.is_running:
                    break
                    
                # Process audio chunk
                processed_audio = self.audio_processor.process_chunk(audio_chunk)
                
                # Voice Activity Detection
                has_speech = await self.vad.is_speech(processed_audio)
                
                if has_speech:
                    speech_buffer.extend(processed_audio)
                    is_speaking = True
                    silence_count = 0
                else:
                    silence_count += 1
                    
                # If we have speech and then silence, process the utterance
                if is_speaking and silence_count > 5:  # ~500ms of silence
                    if len(speech_buffer) > 1024:  # Minimum speech length
                        # Process the speech
                        response_audio = await self._process_speech_chunk(bytes(speech_buffer))
                        if response_audio:
                            yield response_audio
                            
                    # Reset for next utterance
                    speech_buffer.clear()
                    is_speaking = False
                    silence_count = 0
                    
        except Exception as e:
            logger.error(f"Error in audio stream processing: {e}")
        finally:
            self.is_running = False
            
    async def _process_speech_chunk(self, audio_data: bytes) -> Optional[bytes]:
        """
        Process a single speech chunk through the full pipeline.
        
        Args:
            audio_data: Audio data containing speech
            
        Returns:
            Response audio data or None
        """
        try:
            # Step 1: Speech-to-Text
            logger.info("Processing speech with ElevenLabs STT...")
            stt_result = await self.stt.transcribe_audio(audio_data)
            
            if not stt_result.get("success") or not stt_result.get("text", "").strip():
                logger.warning("No text transcribed from audio")
                return None
                
            user_text = stt_result["text"]
            detected_language = stt_result.get("language", "en")
            confidence = stt_result.get("confidence", 0.0)
            
            logger.info(f"Transcribed ({confidence:.2f}): '{user_text}' [lang: {detected_language}]")
            
            # Update conversation context
            self.conversation.current_language = detected_language
            self.conversation.messages.append({
                "role": "user",
                "content": user_text,
                "language": detected_language,
                "confidence": confidence
            })
            
            # Step 2: LLM Processing
            logger.info("Processing with local LLM...")
            
            # Build conversation context for LLM
            system_prompt = self._build_system_prompt(detected_language)
            
            llm_response = await self.llm.generate_response(
                messages=self.conversation.messages,
                system_prompt=system_prompt
            )
            
            if not llm_response.get("success") or not llm_response.get("content", "").strip():
                logger.warning("No response from LLM")
                return None
                
            assistant_text = llm_response["content"]
            logger.info(f"LLM responded: '{assistant_text[:100]}...'")
            
            # Add to conversation
            self.conversation.messages.append({
                "role": "assistant", 
                "content": assistant_text,
                "language": detected_language
            })
            
            # Step 3: Text-to-Speech
            logger.info("Synthesizing speech with ElevenLabs TTS...")
            
            # Select appropriate voice for language
            voice_id = await self._select_voice_for_language(detected_language)
            
            response_audio = await self.tts.synthesize_speech(
                text=assistant_text,
                voice_id=voice_id,
                language=detected_language
            )
            
            logger.info(f"Generated {len(response_audio)} bytes of response audio")
            return response_audio
            
        except Exception as e:
            logger.error(f"Error processing speech chunk: {e}")
            return None
            
    def _build_system_prompt(self, language: str) -> str:
        """Build system prompt based on detected language."""
        if language.startswith("fr"):
            return """Tu es un assistant vocal intelligent et amical. 
            Réponds en français de manière naturelle et conversationnelle. 
            Garde tes réponses concises mais utiles."""
        else:
            return """You are a friendly and intelligent voice assistant.
            Respond naturally and conversationally in English.
            Keep your responses concise but helpful."""
            
    async def _select_voice_for_language(self, language: str) -> Optional[str]:
        """Select appropriate voice based on detected language."""
        try:
            # Use configured voice if set
            if self.config.tts.voice_id:
                return self.config.tts.voice_id
                
            # Get recommended voice for language
            voice_id = get_recommended_voice(language, "female")  # Default to female
            
            if voice_id:
                return voice_id
                
            # Fallback: get any available voice for the language
            available_voices = await self.tts.get_voices(language)
            if available_voices:
                return available_voices[0]["voice_id"]
                
            # Final fallback: use any available voice
            all_voices = await self.tts.get_voices()
            if all_voices:
                return all_voices[0]["voice_id"]
                
            return None
            
        except Exception as e:
            logger.error(f"Error selecting voice: {e}")
            return None
            
    async def process_text(self, text: str, language: str = "auto") -> Optional[bytes]:
        """
        Process text directly (for testing or text-only mode).
        
        Args:
            text: Input text
            language: Language hint
            
        Returns:
            Response audio data
        """
        try:
            # Add to conversation
            self.conversation.messages.append({
                "role": "user",
                "content": text,
                "language": language
            })
            
            # Process with LLM
            system_prompt = self._build_system_prompt(language)
            llm_response = await self.llm.generate_response(
                messages=self.conversation.messages,
                system_prompt=system_prompt
            )
            
            if llm_response.get("success"):
                assistant_text = llm_response["content"]
                
                # Add to conversation
                self.conversation.messages.append({
                    "role": "assistant",
                    "content": assistant_text,
                    "language": language
                })
                
                # Synthesize response
                voice_id = await self._select_voice_for_language(language)
                return await self.tts.synthesize_speech(
                    text=assistant_text,
                    voice_id=voice_id,
                    language=language
                )
                
            return None
            
        except Exception as e:
            logger.error(f"Error processing text: {e}")
            return None