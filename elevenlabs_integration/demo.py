"""
ElevenLabs Integration Demo

Demo script showing how to use ElevenLabs STT/TTS with existing LLM.
This demonstrates the combined power of high-quality ElevenLabs audio processing
with local LLM inference.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the main project to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src"))
sys.path.append(str(Path(__file__).parent))  # Add current directory

from config import ElevenLabsConfig
from pipeline import ElevenLabsPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_text_processing():
    """Demo text-only processing (no audio input required)."""
    
    # Get API key from environment
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        logger.error("ELEVENLABS_API_KEY environment variable not set!")
        logger.info("Please set your ElevenLabs API key:")
        logger.info("export ELEVENLABS_API_KEY='sk_0dd6b4af347097128ef0644479fd1c9dddc5983c7e3398a5'")
        return
        
    try:
        # Initialize configuration
        config = ElevenLabsConfig(api_key=api_key)
        
        # Create pipeline
        pipeline = ElevenLabsPipeline(config, use_existing_llm=True)
        
        # Initialize pipeline
        logger.info("Initializing ElevenLabs pipeline...")
        await pipeline.initialize()
        
        # Test conversations
        test_inputs = [
            ("Hello, how are you today?", "en"),
            ("What's the weather like?", "en"),
            ("Bonjour, comment allez-vous?", "fr"),
            ("Quelle heure est-il?", "fr"),
        ]
        
        for text, language in test_inputs:
            logger.info(f"\n--- Processing: '{text}' [{language}] ---")
            
            # Process text through pipeline
            response_audio = await pipeline.process_text(text, language)
            
            if response_audio:
                # Save audio response
                output_file = f"response_{language}_{len(text)}.mp3"
                with open(output_file, "wb") as f:
                    f.write(response_audio)
                logger.info(f"Response saved to: {output_file}")
            else:
                logger.warning("No response generated")
                
            # Small delay between requests
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Demo failed: {e}")
    finally:
        # Cleanup
        if 'pipeline' in locals():
            await pipeline.cleanup()


async def demo_voice_selection():
    """Demo voice selection and TTS capabilities."""
    
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        logger.error("ELEVENLABS_API_KEY environment variable not set!")
        return
        
    try:
        from tts_adapter import ElevenLabsTTSAdapter
        
        # Initialize TTS adapter
        tts = ElevenLabsTTSAdapter(api_key=api_key)
        await tts.initialize()
        
        # List available voices
        voices = await tts.get_voices()
        logger.info(f"Available voices ({len(voices)}):")
        
        for voice in voices[:5]:  # Show first 5
            name = voice.get("name", "Unknown")
            voice_id = voice.get("voice_id", "")
            labels = voice.get("labels", {})
            logger.info(f"  - {name} ({voice_id[:8]}...): {labels}")
            
        # Test TTS with different voices
        test_text = "Hello, this is a test of the ElevenLabs text-to-speech system."
        
        for voice in voices[:2]:  # Test first 2 voices
            voice_name = voice.get("name", "Unknown")
            voice_id = voice.get("voice_id")
            
            logger.info(f"Testing voice: {voice_name}")
            
            audio_data = await tts.synthesize_speech(test_text, voice_id=voice_id)
            
            if audio_data:
                output_file = f"test_voice_{voice_name.lower().replace(' ', '_')}.mp3"
                with open(output_file, "wb") as f:
                    f.write(audio_data)
                logger.info(f"Voice sample saved: {output_file}")
                
        await tts.cleanup()
        
    except Exception as e:
        logger.error(f"Voice demo failed: {e}")


async def demo_stt_capabilities():
    """Demo STT capabilities (mock mode)."""
    
    api_key = os.getenv("ELEVENLABS_API_KEY") 
    if not api_key:
        logger.error("ELEVENLABS_API_KEY environment variable not set!")
        return
        
    try:
        from stt_adapter import ElevenLabsSTTAdapter
        
        # Initialize STT adapter
        stt = ElevenLabsSTTAdapter(api_key=api_key, language="auto")
        await stt.initialize()
        
        # Test with mock audio data (since we don't have real audio files)
        mock_audio = b"fake_audio_data" * 1000
        
        logger.info("Testing STT transcription...")
        result = await stt.transcribe_audio(mock_audio, language="en")
        
        logger.info(f"STT Result: {result}")
        
        # Test supported languages
        languages = stt.get_supported_languages()
        logger.info(f"Supported languages: {languages}")
        
        # Test available models
        models = stt.get_available_models()
        logger.info(f"Available models: {models}")
        
        await stt.cleanup()
        
    except Exception as e:
        logger.error(f"STT demo failed: {e}")


def print_setup_instructions():
    """Print setup instructions for the demo."""
    print("\n" + "="*60)
    print("🎙️  ELEVENLABS INTEGRATION DEMO")
    print("="*60)
    print()
    print("Setup Instructions:")
    print("1. Set your ElevenLabs API key:")
    print("   export ELEVENLABS_API_KEY='sk_0dd6b4af347097128ef0644479fd1c9dddc5983c7e3398a5'")
    print()
    print("2. Make sure the main LiveKit agent is set up:")
    print("   cd /path/to/LiveKit_MVP_Agent")
    print("   make setup")
    print()
    print("3. Start Ollama (for LLM):")
    print("   make start-ollama")
    print("   make pull-model")
    print()
    print("4. Run this demo:")
    print("   cd elevenlabs_integration")
    print("   python demo.py")
    print()
    print("Features:")
    print("✓ High-quality STT via ElevenLabs")
    print("✓ Local LLM processing via Ollama")
    print("✓ High-quality TTS via ElevenLabs")
    print("✓ Bilingual support (EN/FR)")
    print("✓ Multiple voice options")
    print("="*60)


async def main():
    """Run the demo."""
    print_setup_instructions()
    
    # Check if API key is set
    if not os.getenv("ELEVENLABS_API_KEY"):
        print("\n❌ ElevenLabs API key not found!")
        print("Please set the ELEVENLABS_API_KEY environment variable.")
        return
        
    print("\n🚀 Starting ElevenLabs integration demos...")
    
    try:
        # Demo 1: Voice selection
        print("\n📢 Demo 1: Voice Selection & TTS")
        await demo_voice_selection()
        
        # Demo 2: STT capabilities
        print("\n🎯 Demo 2: STT Capabilities")
        await demo_stt_capabilities()
        
        # Demo 3: Full text processing pipeline
        print("\n🔄 Demo 3: Full Pipeline (Text Processing)")
        await demo_text_processing()
        
        print("\n✅ All demos completed!")
        print("\nGenerated files:")
        print("- response_*.mp3 (TTS responses)")
        print("- test_voice_*.mp3 (Voice samples)")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())