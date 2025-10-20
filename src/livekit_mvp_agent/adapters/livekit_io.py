"""
LiveKit I/O Adapter for real-time audio streaming
"""

import asyncio
import logging
from typing import Optional, Callable, Any
import numpy as np

try:
    from livekit import agents, rtc
    LIVEKIT_AVAILABLE = True
except ImportError:
    LIVEKIT_AVAILABLE = False
    # Create mock classes for type hints
    class agents:
        class VoiceAssistant:
            pass
    class rtc:
        pass


class LiveKitAdapter:
    """
    Adapter for LiveKit real-time communication
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        sample_rate: int = 16000,
    ):
        if not LIVEKIT_AVAILABLE:
            raise ImportError(
                "livekit-agents is not installed. "
                "Install with: pip install livekit-agents[mcp]"
            )
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.sample_rate = sample_rate
        self.logger = logging.getLogger(__name__)
        
        # Connection state
        self.room: Optional[rtc.Room] = None
        self.audio_source: Optional[rtc.AudioSource] = None
        self.connected = False
        
        # Event handlers
        self.on_audio_received: Optional[Callable[[bytes, str], None]] = None
        self.on_participant_connected: Optional[Callable[[str], None]] = None
        self.on_participant_disconnected: Optional[Callable[[str], None]] = None
        
        # Audio processing
        self._audio_buffer = []
        self._processing_task: Optional[asyncio.Task] = None
    
    async def connect(self, url: str, room_name: str, participant_name: str = "VoiceAgent") -> None:
        """
        Connect to LiveKit room
        
        Args:
            url: LiveKit server URL
            room_name: Room name to join
            participant_name: Name for this agent
        """
        if not LIVEKIT_AVAILABLE:
            self.logger.error("LiveKit not available")
            return
        
        try:
            self.logger.info(f"Connecting to LiveKit: {url}/{room_name}")
            
            # Create room instance
            self.room = rtc.Room()
            
            # Setup event handlers
            self.room.on("participant_connected", self._on_participant_connected)
            self.room.on("participant_disconnected", self._on_participant_disconnected)
            self.room.on("track_published", self._on_track_published)
            self.room.on("track_subscribed", self._on_track_subscribed)
            
            # Connect to room
            await self.room.connect(
                url=url,
                token=self._generate_access_token(room_name, participant_name),
            )
            
            # Create audio source for output
            self.audio_source = rtc.AudioSource(
                sample_rate=self.sample_rate,
                num_channels=1,
            )
            
            # Publish audio track
            track = rtc.LocalAudioTrack.create_audio_track(
                "agent_audio", self.audio_source
            )
            options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
            await self.room.local_participant.publish_track(track, options)
            
            self.connected = True
            self.logger.info("Successfully connected to LiveKit")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to LiveKit: {e}", exc_info=True)
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from LiveKit room"""
        if self.room and self.connected:
            try:
                await self.room.disconnect()
                self.connected = False
                self.logger.info("Disconnected from LiveKit")
            except Exception as e:
                self.logger.error(f"Error disconnecting from LiveKit: {e}")
        
        if self._processing_task:
            self._processing_task.cancel()
    
    async def send_audio(self, audio_data: np.ndarray) -> None:
        """
        Send audio data to the room
        
        Args:
            audio_data: Audio samples as numpy array
        """
        if not self.connected or not self.audio_source:
            return
        
        try:
            # Convert to the format expected by LiveKit
            if audio_data.dtype != np.int16:
                # Convert to int16
                audio_data = (audio_data * 32767).astype(np.int16)
            
            # Create audio frame
            frame = rtc.AudioFrame(
                data=audio_data.tobytes(),
                sample_rate=self.sample_rate,
                num_channels=1,
                samples_per_channel=len(audio_data),
            )
            
            # Send to audio source
            await self.audio_source.capture_frame(frame)
            
        except Exception as e:
            self.logger.error(f"Error sending audio: {e}", exc_info=True)
    
    def _generate_access_token(self, room_name: str, participant_name: str) -> str:
        """Generate access token for LiveKit"""
        # TODO: Implement proper token generation
        # For now, return empty string for local development
        if not self.api_key or not self.api_secret:
            self.logger.warning("No API key/secret provided, using empty token")
            return ""
        
        try:
            from livekit import api
            token = api.AccessToken(self.api_key, self.api_secret)
            token.with_identity(participant_name)
            token.with_name(participant_name)
            token.with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                )
            )
            return token.to_jwt()
        except Exception as e:
            self.logger.error(f"Failed to generate token: {e}")
            return ""
    
    def _on_participant_connected(self, participant: rtc.RemoteParticipant) -> None:
        """Handle participant connection"""
        self.logger.info(f"Participant connected: {participant.identity}")
        if self.on_participant_connected:
            asyncio.create_task(self.on_participant_connected(participant.identity))
    
    def _on_participant_disconnected(self, participant: rtc.RemoteParticipant) -> None:
        """Handle participant disconnection"""
        self.logger.info(f"Participant disconnected: {participant.identity}")
        if self.on_participant_disconnected:
            asyncio.create_task(self.on_participant_disconnected(participant.identity))
    
    def _on_track_published(self, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant) -> None:
        """Handle track publication"""
        self.logger.debug(f"Track published: {publication.sid} by {participant.identity}")
    
    def _on_track_subscribed(
        self, 
        track: rtc.Track, 
        publication: rtc.RemoteTrackPublication, 
        participant: rtc.RemoteParticipant
    ) -> None:
        """Handle track subscription (incoming audio)"""
        if isinstance(track, rtc.RemoteAudioTrack):
            self.logger.info(f"Subscribed to audio track from {participant.identity}")
            
            # Start processing audio from this track
            self._processing_task = asyncio.create_task(
                self._process_audio_track(track, participant.identity)
            )
    
    async def _process_audio_track(self, track: rtc.RemoteAudioTrack, participant_id: str) -> None:
        """Process incoming audio from a track"""
        try:
            async for frame in track:
                if not self.connected:
                    break
                
                # Convert audio frame to bytes
                audio_data = bytes(frame.data)
                
                # Call handler if available
                if self.on_audio_received:
                    await self.on_audio_received(audio_data, participant_id)
                    
        except Exception as e:
            self.logger.error(f"Error processing audio track: {e}", exc_info=True)


class MockLiveKitAdapter:
    """
    Mock LiveKit adapter for testing and development when LiveKit is not available
    """
    
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.connected = False
        
        # Event handlers
        self.on_audio_received: Optional[Callable[[bytes, str], None]] = None
        self.on_participant_connected: Optional[Callable[[str], None]] = None
        self.on_participant_disconnected: Optional[Callable[[str], None]] = None
    
    async def connect(self, url: str, room_name: str, participant_name: str = "VoiceAgent") -> None:
        """Mock connection"""
        self.logger.info(f"Mock LiveKit connection to {url}/{room_name}")
        self.connected = True
        
        # Simulate participant connection
        if self.on_participant_connected:
            await self.on_participant_connected("mock_participant")
    
    async def disconnect(self) -> None:
        """Mock disconnection"""
        if self.connected:
            self.logger.info("Mock LiveKit disconnection")
            self.connected = False
    
    async def send_audio(self, audio_data: np.ndarray) -> None:
        """Mock audio sending"""
        self.logger.debug(f"Mock sending {len(audio_data)} audio samples")


# Use mock adapter if LiveKit is not available
if not LIVEKIT_AVAILABLE:
    LiveKitAdapter = MockLiveKitAdapter