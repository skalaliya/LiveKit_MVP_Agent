"""
Pipeline worker for French Tutor UI.

Runs the AI pipeline (VAD → STT → LLM → TTS) in a separate thread,
communicating with the main UI thread via Qt signals.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional
import numpy as np

from PySide6.QtCore import QThread, Signal, Slot

# Add project root to path
import sys
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from livekit_mvp_agent.config import get_settings
from livekit_mvp_agent.adapters.stt_whisper import WhisperSTT
from livekit_mvp_agent.adapters.llm_ollama import OllamaLLM
from livekit_mvp_agent.adapters.tts_elevenlabs_stream import ElevenLabsStreamingTTS
from livekit_mvp_agent.adapters.vad_silero import SileroVAD

logger = logging.getLogger(__name__)


class PipelineWorker(QThread):
    """
    Worker thread that processes audio through the AI pipeline.
    
    Signals:
        user_transcript: Emitted when user speech is transcribed (str)
        agent_transcript: Emitted when agent response is generated (str)
        agent_audio: Emitted when agent audio is ready to play (bytes)
        status_update: Emitted for status messages (str)
        error_occurred: Emitted when an error occurs (str)
        vad_active: Emitted when voice activity detected (bool)
    """
    
    # Qt signals for thread-safe communication
    user_transcript = Signal(str)
    agent_transcript = Signal(str)
    agent_audio = Signal(bytes)
    status_update = Signal(str)
    error_occurred = Signal(str)
    vad_active = Signal(bool)
    
    def __init__(self):
        super().__init__()
        
        self.settings = get_settings()
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Pipeline components (initialized in run())
        self.vad: Optional[SileroVAD] = None
        self.stt: Optional[WhisperSTT] = None
        self.llm: Optional[OllamaLLM] = None
        self.tts: Optional[ElevenLabsStreamingTTS] = None
        
        # Audio buffer for VAD
        self._audio_buffer = bytearray()
        self._buffer_lock = asyncio.Lock()
        
        # Conversation state
        self._conversation_history: list[dict] = []
        self._is_speaking = False
        
        logger.info("PipelineWorker initialized")
    
    def run(self):
        """Main thread execution - sets up async event loop."""
        try:
            # Create new event loop for this thread
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            # Initialize pipeline
            self._loop.run_until_complete(self._initialize_pipeline())
            
            # Run event loop
            self._running = True
            self.status_update.emit("Pipeline ready")
            logger.info("Pipeline worker running")
            
            # Keep loop running until stopped
            self._loop.run_forever()
            
        except Exception as e:
            logger.error(f"Pipeline worker error: {e}", exc_info=True)
            self.error_occurred.emit(f"Pipeline error: {str(e)}")
        finally:
            # Cleanup
            if self._loop:
                self._loop.run_until_complete(self._cleanup_pipeline())
                self._loop.close()
            logger.info("Pipeline worker stopped")
    
    async def _initialize_pipeline(self):
        """Initialize all pipeline components."""
        try:
            self.status_update.emit("Initializing VAD...")
            self.vad = SileroVAD()
            
            self.status_update.emit("Loading Whisper model...")
            self.stt = WhisperSTT(
                model_name=self.settings.whisper_model,
                device=self.settings.whisper_device,
                compute_type=self.settings.whisper_compute_type,
            )
            
            self.status_update.emit("Connecting to Ollama...")
            self.llm = OllamaLLM(
                base_url=self.settings.ollama_base_url,
                model_name=self.settings.llm_model,
            )
            
            self.status_update.emit("Connecting to ElevenLabs...")
            self.tts = ElevenLabsStreamingTTS(
                api_key=self.settings.elevenlabs_api_key,
                voice_id=self.settings.elevenlabs_voice_id,
                model_id="eleven_flash_v2_5",
            )
            
            # Add French tutor system prompt
            self._conversation_history = [
                {
                    "role": "system",
                    "content": self._get_french_tutor_prompt()
                }
            ]
            
            logger.info("Pipeline initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}", exc_info=True)
            raise
    
    async def _cleanup_pipeline(self):
        """Cleanup pipeline resources."""
        try:
            if self.tts:
                # Close any open TTS streams
                pass
            
            logger.info("Pipeline cleanup complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
    
    def _get_french_tutor_prompt(self) -> str:
        """Get the French tutor system prompt."""
        return """Tu es un professeur de français bienveillant et patient. Ta mission est d'aider les apprenants à améliorer leur français à travers des conversations naturelles.

Ton rôle:
- Parler principalement en français, avec des explications en anglais si nécessaire
- Adapter ton niveau de langue à celui de l'apprenant
- Corriger les erreurs de manière constructive et encourageante
- Donner des exemples pratiques et contextuels
- Encourager la pratique orale et écrite
- Être enthousiaste et motivant

Principes pédagogiques:
1. Commence par évaluer le niveau de l'apprenant
2. Encourage la communication avant la perfection
3. Corrige une erreur à la fois
4. Donne du contexte culturel quand c'est pertinent
5. Propose des exercices adaptés au niveau
6. Félicite les progrès, même petits

Ton style de correction:
- Note l'erreur
- Donne la forme correcte
- Explique brièvement la règle
- Donne un exemple similaire

Sois conversationnel, amical, et fais-en une expérience d'apprentissage agréable!"""
    
    @Slot(bytes)
    def process_audio(self, audio_data: bytes):
        """
        Process incoming audio from microphone.
        Called from main thread, schedules async processing.
        """
        if not self._running or not self._loop:
            return
        
        # Schedule processing in worker thread's event loop
        asyncio.run_coroutine_threadsafe(
            self._process_audio_async(audio_data),
            self._loop
        )
    
    async def _process_audio_async(self, audio_data: bytes):
        """Process audio through VAD and STT (async)."""
        try:
            # Convert bytes to numpy array (16-bit PCM, 16kHz mono)
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Run VAD
            speech_prob = self.vad.process_chunk(audio_np)
            is_speech = speech_prob > self.settings.vad_threshold
            
            # Emit VAD status
            self.vad_active.emit(is_speech)
            
            if is_speech:
                # Add to buffer
                async with self._buffer_lock:
                    self._audio_buffer.extend(audio_data)
                
                # Check if we have enough audio (e.g., 1 second = 32000 bytes)
                if len(self._audio_buffer) >= 32000:
                    # Process buffered audio
                    await self._transcribe_and_respond()
                    
        except Exception as e:
            logger.error(f"Error processing audio: {e}", exc_info=True)
            self.error_occurred.emit(f"Audio processing error: {str(e)}")
    
    async def _transcribe_and_respond(self):
        """Transcribe buffered audio and generate response."""
        try:
            # Get buffered audio
            async with self._buffer_lock:
                audio_bytes = bytes(self._audio_buffer)
                self._audio_buffer.clear()
            
            if len(audio_bytes) == 0:
                return
            
            # Convert to numpy for STT
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Transcribe
            self.status_update.emit("Transcribing...")
            user_text = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.stt.transcribe(audio_np, sample_rate=16000)
            )
            
            if not user_text or user_text.strip() == "":
                return
            
            # Emit user transcript
            self.user_transcript.emit(user_text)
            logger.info(f"User: {user_text}")
            
            # Add to conversation history
            self._conversation_history.append({
                "role": "user",
                "content": user_text
            })
            
            # Generate LLM response
            self.status_update.emit("Generating response...")
            agent_text = await self._generate_llm_response()
            
            if not agent_text:
                return
            
            # Emit agent transcript
            self.agent_transcript.emit(agent_text)
            logger.info(f"Agent: {agent_text}")
            
            # Add to conversation history
            self._conversation_history.append({
                "role": "assistant",
                "content": agent_text
            })
            
            # Generate and stream TTS
            await self._generate_and_stream_tts(agent_text)
            
        except Exception as e:
            logger.error(f"Error in transcribe_and_respond: {e}", exc_info=True)
            self.error_occurred.emit(f"Transcription error: {str(e)}")
    
    async def _generate_llm_response(self) -> str:
        """Generate LLM response from conversation history."""
        try:
            response = await self.llm.generate(
                messages=self._conversation_history,
                temperature=0.7,
                max_tokens=500,
            )
            return response.strip()
        except Exception as e:
            logger.error(f"LLM generation error: {e}", exc_info=True)
            return ""
    
    async def _generate_and_stream_tts(self, text: str):
        """Generate TTS and stream audio chunks."""
        try:
            self.status_update.emit("Generating speech...")
            self._is_speaking = True
            
            # Begin streaming
            await self.tts.begin_stream()
            
            # Send text
            await self.tts.send_text_chunk(text)
            await self.tts.end_stream()
            
            # Receive audio chunks
            async for audio_chunk in self.tts.receive_audio_chunks():
                if not self._running:
                    break
                
                # Emit audio to UI for playback
                self.agent_audio.emit(audio_chunk)
            
            self._is_speaking = False
            self.status_update.emit("Ready")
            
        except Exception as e:
            logger.error(f"TTS generation error: {e}", exc_info=True)
            self.error_occurred.emit(f"TTS error: {str(e)}")
            self._is_speaking = False
    
    @Slot()
    def cancel_speech(self):
        """Cancel ongoing speech generation (barge-in)."""
        if self._is_speaking:
            logger.info("Canceling speech (barge-in)")
            self._is_speaking = False
            self.status_update.emit("Speech cancelled")
    
    @Slot()
    def clear_history(self):
        """Clear conversation history."""
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self._clear_history_async(),
                self._loop
            )
    
    async def _clear_history_async(self):
        """Clear conversation history (async)."""
        self._conversation_history = [
            {
                "role": "system",
                "content": self._get_french_tutor_prompt()
            }
        ]
        logger.info("Conversation history cleared")
    
    def stop(self):
        """Stop the worker thread gracefully."""
        logger.info("Stopping pipeline worker...")
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.wait()  # Wait for thread to finish
