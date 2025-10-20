# ElevenLabs Integration

This directory contains the ElevenLabs integration for the LiveKit MVP Agent. It provides high-quality Speech-to-Text (STT) and Text-to-Speech (TTS) capabilities using ElevenLabs API while maintaining the existing local LLM setup.

## 🎯 Features

- **High-Quality STT**: ElevenLabs speech recognition with multilingual support
- **Premium TTS**: Multiple voice options with natural speech synthesis  
- **Local LLM**: Keeps using your existing Ollama setup (€0 LLM costs)
- **Bilingual Support**: English and French conversation handling
- **Voice Selection**: Choose from multiple voice personalities and languages
- **Graceful Fallbacks**: Mock implementations for development/testing

## 🏗️ Architecture

```
ElevenLabs Pipeline:
Audio Input → ElevenLabs STT → Local LLM (Ollama) → ElevenLabs TTS → Audio Output
```

**Benefits of this hybrid approach:**
- ✅ High-quality audio processing (ElevenLabs)
- ✅ Local LLM inference (€0 cost, privacy)
- ✅ Best of both worlds

## 📦 Installation

1. **Install additional dependencies:**
   ```bash
   cd elevenlabs_integration
   pip install -r requirements.txt
   ```

2. **Set your ElevenLabs API key:**
   ```bash
   export ELEVENLABS_API_KEY='sk_0dd6b4af347097128ef0644479fd1c9dddc5983c7e3398a5'
   ```

3. **Ensure main project is set up:**
   ```bash
   cd ..  # Back to main project
   make setup
   make start-ollama
   make pull-model
   ```

## 🚀 Quick Start

### Text-to-Speech Demo
```python
import asyncio
from elevenlabs_integration.config import ElevenLabsConfig
from elevenlabs_integration.tts_adapter import ElevenLabsTTSAdapter

async def tts_demo():
    config = ElevenLabsConfig(api_key="your_api_key")
    tts = ElevenLabsTTSAdapter(api_key=config.api_key)
    
    await tts.initialize()
    
    # Synthesize speech
    audio = await tts.synthesize_speech("Hello, this is ElevenLabs TTS!")
    
    with open("output.mp3", "wb") as f:
        f.write(audio)
        
    await tts.cleanup()

asyncio.run(tts_demo())
```

### Full Pipeline Demo
```python
import asyncio
from elevenlabs_integration.config import ElevenLabsConfig
from elevenlabs_integration.pipeline import ElevenLabsPipeline

async def pipeline_demo():
    config = ElevenLabsConfig(api_key="your_api_key")
    pipeline = ElevenLabsPipeline(config, use_existing_llm=True)
    
    await pipeline.initialize()
    
    # Process text (simulates: STT → LLM → TTS)
    response_audio = await pipeline.process_text("Hello, how are you?", "en")
    
    if response_audio:
        with open("response.mp3", "wb") as f:
            f.write(response_audio)
    
    await pipeline.cleanup()

asyncio.run(pipeline_demo())
```

### Run Built-in Demos
```bash
cd elevenlabs_integration
python demo.py
```

## 🎛️ Configuration

### Basic Configuration
```python
from elevenlabs_integration.config import ElevenLabsConfig

config = ElevenLabsConfig(
    api_key="your_api_key",
    stt=ElevenLabsSTTConfig(
        model="eleven_multilingual_v2",
        language="auto"  # Auto-detect language
    ),
    tts=ElevenLabsTTSConfig(
        voice_id=None,  # Auto-select best voice
        model="eleven_multilingual_v2"
    )
)
```

### Voice Selection
```python
from elevenlabs_integration.config import get_recommended_voice

# Get recommended voice for language
voice_id = get_recommended_voice("fr", "female")  # French female voice
voice_id = get_recommended_voice("en", "male")    # English male voice
```

### Available Voices
The integration includes presets for:
- **English**: Adam (male), Rachel (female), Sam (male), Domi (female)
- **French**: Antoine (male), Charlotte (female)
- **Auto-detection**: Automatically selects best voice for detected language

## 📁 File Structure

```
elevenlabs_integration/
├── __init__.py              # Package initialization
├── config.py                # Configuration classes and presets
├── stt_adapter.py          # Speech-to-Text adapter
├── tts_adapter.py          # Text-to-Speech adapter  
├── pipeline.py             # Main integration pipeline
├── demo.py                 # Demo script
├── requirements.txt        # Additional dependencies
└── README.md              # This file
```

## 🔧 API Integration

### STT (Speech-to-Text)
- **Endpoint**: `https://api.elevenlabs.io/v1/speech-to-text`
- **Models**: `eleven_multilingual_v2`, `eleven_english_v1`
- **Languages**: Auto-detection or specific (en, fr, es, de, etc.)
- **Output**: Transcribed text with confidence scores

### TTS (Text-to-Speech)
- **Endpoint**: `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`
- **Models**: `eleven_multilingual_v2`, `eleven_turbo_v2`
- **Voices**: 25+ premium voices in multiple languages
- **Output**: High-quality MP3 audio

### Voice Management
- **List Voices**: `GET /v1/voices`
- **Voice Details**: Voice ID, name, language support, labels
- **Custom Settings**: Stability, similarity boost, style control

## 🧪 Testing

The adapters include comprehensive mock implementations for testing without API calls:

```python
# Test without API key (uses mocks)
config = ElevenLabsConfig(api_key="test")
pipeline = ElevenLabsPipeline(config)

# Will use mock implementations
await pipeline.initialize()
result = await pipeline.process_text("Test message", "en")
```

## 💰 Cost Considerations

- **ElevenLabs**: Pay-per-use for STT/TTS (high quality)
- **LLM (Ollama)**: €0 - runs locally
- **Hybrid approach**: Premium audio + free inference

**Typical costs (ElevenLabs):**
- STT: ~$0.24 per hour of audio
- TTS: ~$0.18 per 1K characters
- Free tier: 10K characters/month

## 🔄 Integration with Main Project

The ElevenLabs integration works alongside the existing LiveKit MVP Agent:

1. **Separate namespace**: No conflicts with existing code
2. **Reuses existing**: LLM setup, configuration, utilities
3. **Easy switching**: Can fall back to original adapters
4. **Good housekeeping**: Clean separation of concerns

### Using with LiveKit
```python
# In your LiveKit room handler
from elevenlabs_integration.pipeline import ElevenLabsPipeline

class ElevenLabsAgent:
    async def on_audio_received(self, audio_data):
        # Process through ElevenLabs pipeline
        response = await self.pipeline.process_speech_chunk(audio_data)
        # Send response back to room
        await self.room.send_audio(response)
```

## 🚨 Troubleshooting

### Common Issues

1. **API Key Issues**
   ```bash
   # Check API key is set
   echo $ELEVENLABS_API_KEY
   
   # Test API access
   curl -H "xi-api-key: $ELEVENLABS_API_KEY" https://api.elevenlabs.io/v1/user
   ```

2. **Import Errors**
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   
   # Check Python path
   export PYTHONPATH=$PYTHONPATH:$(pwd)/../src
   ```

3. **Audio Issues**
   ```bash
   # Install audio libraries
   pip install pydub librosa
   
   # Check audio format support
   python -c "import scipy.io.wavfile; print('Audio support OK')"
   ```

### Mock Mode
If ElevenLabs API is unavailable, adapters automatically fall back to mock implementations:
- STT returns: "Mock transcription from ElevenLabs STT adapter"
- TTS returns: Silent WAV audio
- All functions work for development/testing

## 📚 Advanced Usage

### Custom Voice Settings
```python
tts_config = ElevenLabsTTSConfig(
    api_key="your_key",
    voice_settings={
        "stability": 0.8,        # 0.0-1.0, higher = more consistent
        "similarity_boost": 0.9, # 0.0-1.0, higher = more similar to original
        "style": 0.2,           # 0.0-1.0, style exaggeration
        "use_speaker_boost": True
    }
)
```

### Language Detection
```python
# Auto-detect language in STT
stt_result = await stt.transcribe_audio(audio, language="auto")
detected_lang = stt_result["language"]

# Use detected language for TTS voice selection
voice_id = get_recommended_voice(detected_lang, "female")
```

### Streaming Audio
```python
# Stream processing (accumulates chunks)
async def process_stream():
    async for audio_chunk in audio_stream:
        async for result in stt.transcribe_stream([audio_chunk]):
            if result["text"]:
                # Process transcription...
                pass
```

## 🤝 Contributing

To extend the ElevenLabs integration:

1. **Add new voices**: Update `VOICE_PRESETS` in `config.py`
2. **Add languages**: Extend language support in adapters
3. **Add features**: Implement new ElevenLabs API features
4. **Add tests**: Create test cases for new functionality

## 📄 License

This integration follows the same MIT license as the main project.