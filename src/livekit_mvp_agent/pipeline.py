"""
Voice Agent Pipeline - Main orchestration of the voice agent components
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .config import Settings
from .adapters.livekit_io import LiveKitAdapter
from .adapters.stt_whisper import WhisperSTT
from .adapters.llm_ollama import OllamaLLM
from .adapters.tts_kokoro import KokoroTTS
from .adapters.vad_silero import SileroVAD
from .utils.audio import AudioProcessor
from .utils.timing import PerformanceTimer


@dataclass
class ConversationContext:
    """Context for ongoing conversation"""
    participant_id: str
    language: str = "auto"
    conversation_history: list = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []


class VoiceAgentPipeline:
    """
    Main voice agent pipeline that orchestrates all components
    
    Flow:
    Audio Input → VAD → STT → LLM → TTS → Audio Output
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Components
        self.livekit: Optional[LiveKitAdapter] = None
        self.stt: Optional[WhisperSTT] = None
        self.llm: Optional[OllamaLLM] = None
        self.tts: Optional[KokoroTTS] = None
        self.vad: Optional[SileroVAD] = None
        self.audio_processor: Optional[AudioProcessor] = None
        
        # State
        self.running = False
        self.contexts: Dict[str, ConversationContext] = {}
        self.performance_timer = PerformanceTimer()
        
        # Audio buffers
        self.audio_buffer = []
        self.processing_lock = asyncio.Lock()
    
    async def start(self) -> None:
        """Initialize and start all components"""
        self.logger.info("Starting Voice Agent Pipeline...")
        
        try:
            # Initialize components
            await self._initialize_components()
            
            # Setup LiveKit event handlers
            if self.livekit:
                await self._setup_livekit_handlers()
            
            self.running = True
            self.logger.info("Voice Agent Pipeline started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start pipeline: {e}", exc_info=True)
            raise
    
    async def stop(self) -> None:
        """Stop all components and cleanup"""
        self.logger.info("Stopping Voice Agent Pipeline...")
        
        self.running = False
        
        # Stop components
        if self.livekit:
            await self.livekit.disconnect()
        
        # Cleanup
        self.contexts.clear()
        self.audio_buffer.clear()
        
        self.logger.info("Voice Agent Pipeline stopped")
    
    async def run(self) -> None:
        """Main run loop"""
        if not self.running:
            raise RuntimeError("Pipeline not started")
        
        self.logger.info("Voice Agent Pipeline running...")
        
        try:
            # Connect to LiveKit
            if self.livekit:
                await self.livekit.connect(
                    self.settings.livekit_url,
                    self.settings.livekit_room_name,
                    self.settings.livekit_participant_name
                )
            
            # Keep running until stopped
            while self.running:
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            self.logger.info("Pipeline cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Pipeline error: {e}", exc_info=True)
            raise
    
    async def _initialize_components(self) -> None:
        """Initialize all pipeline components"""
        
        # Audio processor
        self.audio_processor = AudioProcessor(
            sample_rate=self.settings.sample_rate,
            channels=self.settings.channels,
            chunk_size=self.settings.chunk_size
        )
        
        # VAD
        self.vad = SileroVAD(
            threshold=self.settings.vad_threshold,
            min_silence_duration=self.settings.vad_min_silence_duration,
            speech_pad=self.settings.vad_speech_pad
        )
        
        # STT
        self.stt = WhisperSTT(
            model=self.settings.whisper_model,
            device=self.settings.whisper_device,
            compute_type=self.settings.whisper_compute_type
        )
        await self.stt.initialize()
        
        # LLM
        self.llm = OllamaLLM(
            base_url=self.settings.ollama_base_url,
            model=self.settings.llm_model,
            fallback_model=self.settings.llm_fallback,
            temperature=self.settings.llm_temperature,
            max_tokens=self.settings.llm_max_tokens
        )
        await self.llm.initialize()
        
        # TTS
        self.tts = KokoroTTS(
            primary_system=self.settings.tts_primary,
            fallback_system=self.settings.tts_fallback,
            voice=self.settings.tts_voice,
            speed=self.settings.tts_speed
        )
        await self.tts.initialize()
        
        # LiveKit (if not in dry-run mode)
        if self.settings.livekit_api_key and self.settings.livekit_api_secret:
            self.livekit = LiveKitAdapter(
                api_key=self.settings.livekit_api_key,
                api_secret=self.settings.livekit_api_secret,
                sample_rate=self.settings.sample_rate
            )
        else:
            self.logger.warning("LiveKit credentials not provided, running in local mode")
    
    async def _setup_livekit_handlers(self) -> None:
        """Setup LiveKit event handlers"""
        if not self.livekit:
            return
        
        # Audio input handler
        self.livekit.on_audio_received = self._handle_audio_input
        
        # Participant events
        self.livekit.on_participant_connected = self._handle_participant_connected
        self.livekit.on_participant_disconnected = self._handle_participant_disconnected
    
    async def _handle_audio_input(self, audio_data: bytes, participant_id: str) -> None:
        """Handle incoming audio from LiveKit"""
        if not self.running:
            return
        
        async with self.processing_lock:
            try:
                # Convert audio data
                audio_array = self.audio_processor.bytes_to_array(audio_data)
                
                # VAD check
                if not self.vad.is_speech(audio_array):
                    return
                
                # Add to buffer
                self.audio_buffer.extend(audio_array)
                
                # Process when we have enough audio
                if len(self.audio_buffer) >= self.settings.sample_rate * 2:  # 2 seconds
                    await self._process_audio_buffer(participant_id)
                
            except Exception as e:
                self.logger.error(f"Error handling audio input: {e}", exc_info=True)
    
    async def _process_audio_buffer(self, participant_id: str) -> None:
        """Process accumulated audio buffer"""
        if not self.audio_buffer:
            return
        
        with self.performance_timer.measure("full_pipeline"):
            try:
                # Get or create conversation context
                context = self.contexts.get(participant_id)
                if not context:
                    context = ConversationContext(participant_id=participant_id)
                    self.contexts[participant_id] = context
                
                # STT: Convert speech to text
                with self.performance_timer.measure("stt"):
                    transcript = await self.stt.transcribe(self.audio_buffer)
                
                if not transcript or not transcript.strip():
                    self.audio_buffer.clear()
                    return
                
                self.logger.info(f"Transcribed: {transcript}")
                
                # Update conversation context
                context.conversation_history.append({
                    "role": "user",
                    "content": transcript
                })
                
                # LLM: Generate response
                with self.performance_timer.measure("llm"):
                    response = await self.llm.chat(
                        messages=context.conversation_history[-10:]  # Keep last 10 messages
                    )
                
                if response:
                    self.logger.info(f"LLM response: {response}")
                    context.conversation_history.append({
                        "role": "assistant", 
                        "content": response
                    })
                    
                    # TTS: Convert response to speech
                    with self.performance_timer.measure("tts"):
                        audio_response = await self.tts.synthesize(
                            text=response,
                            language=context.language
                        )
                    
                    # Send audio response back
                    if audio_response and self.livekit:
                        await self.livekit.send_audio(audio_response)
                
                # Clear buffer
                self.audio_buffer.clear()
                
                # Log performance
                timings = self.performance_timer.get_last_timings()
                self.logger.debug(f"Pipeline timings: {timings}")
                
            except Exception as e:
                self.logger.error(f"Error processing audio buffer: {e}", exc_info=True)
                self.audio_buffer.clear()
    
    async def _handle_participant_connected(self, participant_id: str) -> None:
        """Handle new participant connection"""
        self.logger.info(f"Participant connected: {participant_id}")
        
        # Create conversation context
        self.contexts[participant_id] = ConversationContext(
            participant_id=participant_id
        )
        
        # Send welcome message (optional)
        if self.tts and self.livekit:
            welcome_text = "Hello! I'm your voice assistant. How can I help you today?"
            audio_data = await self.tts.synthesize(welcome_text, "en")
            if audio_data:
                await self.livekit.send_audio(audio_data)
    
    async def _handle_participant_disconnected(self, participant_id: str) -> None:
        """Handle participant disconnection"""
        self.logger.info(f"Participant disconnected: {participant_id}")
        
        # Cleanup context
        if participant_id in self.contexts:
            del self.contexts[participant_id]
    
    def get_status(self) -> Dict[str, Any]:
        """Get pipeline status information"""
        return {
            "running": self.running,
            "active_participants": len(self.contexts),
            "components": {
                "livekit": self.livekit is not None,
                "stt": self.stt is not None,
                "llm": self.llm is not None,
                "tts": self.tts is not None,
                "vad": self.vad is not None,
            },
            "performance": self.performance_timer.get_summary(),
        }