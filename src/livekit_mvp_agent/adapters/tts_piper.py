"""
Piper TTS Adapter for fallback text-to-speech
"""

import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List, Dict
import numpy as np

try:
    import piper_tts
    PIPER_TTS_AVAILABLE = True
except ImportError:
    PIPER_TTS_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False


class PiperTTS:
    """
    Piper TTS adapter supporting both Python API and CLI fallback
    
    Features:
    - Python piper-tts library (preferred)
    - CLI piper executable (fallback)
    - Multiple voice models
    - EN/FR language support
    """
    
    def __init__(
        self,
        model_dir: Optional[str] = None,
        voice: str = "en_US-lessac-medium",
        sample_rate: int = 22050,
    ):
        self.model_dir = Path(model_dir) if model_dir else Path.home() / ".local/share/voices/piper"
        self.voice = voice
        self.sample_rate = sample_rate
        self.logger = logging.getLogger(__name__)
        
        # TTS instances
        self.piper_model = None
        self.initialized = False
        self.use_cli = False
        
        # Voice configurations
        self._voice_configs = self._load_voice_configs()
    
    async def initialize(self) -> None:
        """Initialize Piper TTS"""
        if self.initialized:
            return
        
        self.logger.info("Initializing Piper TTS...")
        
        # Try Python library first
        if PIPER_TTS_AVAILABLE:
            try:
                await self._initialize_python_api()
                self.logger.info("Piper TTS (Python) initialized successfully")
                self.initialized = True
                return
            except Exception as e:
                self.logger.warning(f"Failed to initialize Piper Python API: {e}")
        
        # Fall back to CLI
        try:
            await self._initialize_cli()
            self.logger.info("Piper TTS (CLI) initialized successfully")
            self.use_cli = True
            self.initialized = True
        except Exception as e:
            self.logger.error(f"Failed to initialize Piper CLI: {e}")
            raise
    
    async def _initialize_python_api(self) -> None:
        """Initialize Python piper-tts library"""
        # TODO: Implement when piper-tts Python library is available
        # This is a placeholder implementation
        self.logger.info("Piper Python API would be initialized here")
        # self.piper_model = piper_tts.PiperTTS(model_path=self._get_model_path())
    
    async def _initialize_cli(self) -> None:
        """Initialize CLI-based Piper"""
        # Check if piper executable is available
        try:
            result = await asyncio.create_subprocess_exec(
                "piper", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                version = stdout.decode().strip()
                self.logger.info(f"Found Piper CLI: {version}")
            else:
                raise RuntimeError("Piper CLI not found or not working")
                
        except FileNotFoundError:
            raise RuntimeError("Piper executable not found in PATH")
    
    async def synthesize(
        self, 
        text: str, 
        language: str = "en",
        voice: Optional[str] = None
    ) -> Optional[np.ndarray]:
        """
        Synthesize speech from text
        
        Args:
            text: Text to synthesize
            language: Language code (en/fr)
            voice: Voice ID (optional)
            
        Returns:
            Audio samples as numpy array or None if failed
        """
        if not text.strip():
            return None
        
        if not self.initialized:
            await self.initialize()
        
        # Choose voice based on language
        chosen_voice = voice or self._choose_voice_for_language(language)
        
        try:
            if self.use_cli:
                return await self._synthesize_cli(text, chosen_voice)
            else:
                return await self._synthesize_python(text, chosen_voice)
                
        except Exception as e:
            self.logger.error(f"Piper synthesis failed: {e}", exc_info=True)
            return None
    
    async def _synthesize_python(self, text: str, voice: str) -> Optional[np.ndarray]:
        """Synthesize using Python API"""
        # TODO: Implement when Python library is available
        self.logger.debug("Python API synthesis not yet implemented")
        return None
    
    async def _synthesize_cli(self, text: str, voice: str) -> Optional[np.ndarray]:
        """Synthesize using CLI"""
        if not SOUNDFILE_AVAILABLE:
            self.logger.error("soundfile is required for CLI synthesis")
            return None
        
        try:
            # Get model path
            model_path = self._get_model_path(voice)
            if not model_path.exists():
                self.logger.error(f"Model file not found: {model_path}")
                return None
            
            # Create temporary file for output
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                output_path = tmp_file.name
            
            try:
                # Run piper CLI
                cmd = [
                    "piper",
                    "--model", str(model_path),
                    "--output_file", output_path,
                ]
                
                # Add config file if available
                config_path = model_path.with_suffix(model_path.suffix + ".json")
                if config_path.exists():
                    cmd.extend(["--config", str(config_path)])
                
                # Run synthesis
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate(input=text.encode('utf-8'))
                
                if process.returncode != 0:
                    self.logger.error(f"Piper CLI failed: {stderr.decode()}")
                    return None
                
                # Read generated audio
                audio_data, sr = sf.read(output_path)
                
                # Convert to float32 and ensure correct sample rate
                audio_data = audio_data.astype(np.float32)
                
                # Resample if needed (simple approach)
                if sr != self.sample_rate:
                    self.logger.warning(f"Sample rate mismatch: {sr} != {self.sample_rate}")
                    # TODO: Add proper resampling
                
                return audio_data
                
            finally:
                # Cleanup temporary file
                Path(output_path).unlink(missing_ok=True)
                
        except Exception as e:
            self.logger.error(f"CLI synthesis error: {e}", exc_info=True)
            return None
    
    def _get_model_path(self, voice: str) -> Path:
        """Get path to voice model file"""
        if voice in self._voice_configs:
            config = self._voice_configs[voice]
            return Path(config["path"]).expanduser()
        
        # Default path pattern
        return self.model_dir / f"{voice}.onnx"
    
    def _choose_voice_for_language(self, language: str) -> str:
        """Choose appropriate voice for language"""
        voice_map = {
            "en": "en_US-lessac-medium",
            "fr": "fr_FR-siwis-medium",
        }
        
        return voice_map.get(language, "en_US-lessac-medium")
    
    def _load_voice_configs(self) -> Dict[str, dict]:
        """Load voice configurations"""
        # TODO: Load from voices.yaml
        return {
            "en_US-lessac-medium": {
                "path": "~/.local/share/voices/piper/en_US-lessac-medium.onnx",
                "config": "~/.local/share/voices/piper/en_US-lessac-medium.onnx.json",
                "language": "en",
                "gender": "male",
            },
            "en_US-amy-medium": {
                "path": "~/.local/share/voices/piper/en_US-amy-medium.onnx",
                "config": "~/.local/share/voices/piper/en_US-amy-medium.onnx.json", 
                "language": "en",
                "gender": "female",
            },
            "fr_FR-siwis-medium": {
                "path": "~/.local/share/voices/piper/fr_FR-siwis-medium.onnx",
                "config": "~/.local/share/voices/piper/fr_FR-siwis-medium.onnx.json",
                "language": "fr",
                "gender": "female",
            },
        }
    
    async def list_voices(self) -> List[str]:
        """List available voices"""
        available_voices = []
        
        for voice_id, config in self._voice_configs.items():
            model_path = Path(config["path"]).expanduser()
            if model_path.exists():
                available_voices.append(voice_id)
        
        return available_voices
    
    async def download_voice(self, voice_id: str) -> bool:
        """
        Download a voice model
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            True if successful, False otherwise
        """
        # TODO: Implement voice downloading from Hugging Face
        self.logger.info(f"Voice download for {voice_id} not yet implemented")
        return False
    
    async def close(self) -> None:
        """Cleanup resources"""
        self.piper_model = None
        self.initialized = False


class MockPiperTTS:
    """Mock Piper TTS for testing"""
    
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.initialized = False
        self.sample_rate = 22050
    
    async def initialize(self) -> None:
        """Mock initialization"""
        self.logger.info("Mock Piper TTS initialized")
        self.initialized = True
    
    async def synthesize(
        self, 
        text: str, 
        language: str = "en",
        voice: Optional[str] = None
    ) -> Optional[np.ndarray]:
        """Mock synthesis - return short silence"""
        self.logger.debug(f"Mock Piper synthesis: {text[:50]}...")
        
        # Return short silent audio
        duration = min(len(text) * 0.08, 3.0)
        samples = int(duration * self.sample_rate)
        
        return np.zeros(samples, dtype=np.float32)
    
    async def list_voices(self) -> List[str]:
        """Mock voice list"""
        return ["mock-voice-en", "mock-voice-fr"]
    
    async def close(self) -> None:
        """Mock cleanup"""
        pass


# Use appropriate implementation based on availability
if not PIPER_TTS_AVAILABLE and not SOUNDFILE_AVAILABLE:
    PiperTTS = MockPiperTTS