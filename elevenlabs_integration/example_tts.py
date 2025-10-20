#!/usr/bin/env python3
"""
Simple ElevenLabs TTS Example

Quick example showing how to use ElevenLabs for text-to-speech
while keeping the existing LLM setup.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src"))

async def simple_tts_example():
    """Simple TTS example that creates speech from text."""
    
    print("🎙️ ElevenLabs TTS Example")
    print("=" * 40)
    
    # Import the TTS adapter
    from elevenlabs_integration.tts_adapter import ElevenLabsTTSAdapter
    
    # Get API key (or use mock mode)
    api_key = os.getenv("ELEVENLABS_API_KEY", "mock_key")
    
    # Initialize TTS
    tts = ElevenLabsTTSAdapter(api_key=api_key)
    await tts.initialize()
    
    # Test messages
    messages = [
        "Hello! This is a test of the ElevenLabs text-to-speech system.",
        "Bonjour! Ceci est un test du système de synthèse vocale ElevenLabs.",
        "The weather today is sunny with a chance of cloud computing.",
        "Would you like to hear more examples of artificial voice synthesis?"
    ]
    
    for i, text in enumerate(messages, 1):
        print(f"\n{i}. Synthesizing: '{text[:50]}...'")
        
        # Generate speech
        audio_data = await tts.synthesize_speech(text)
        
        # Save to file
        filename = f"speech_example_{i}.mp3"
        with open(filename, "wb") as f:
            f.write(audio_data)
            
        print(f"   ✅ Saved: {filename} ({len(audio_data):,} bytes)")
    
    # Show available voices (if API key works)
    print(f"\n🎭 Available voices:")
    voices = await tts.get_voices()
    
    for voice in voices[:5]:  # Show first 5
        name = voice.get("name", "Unknown")
        voice_id = voice.get("voice_id", "")[:8]
        print(f"   - {name} ({voice_id}...)")
        
    await tts.cleanup()
    
    print(f"\n✅ Generated {len(messages)} speech files!")
    print("🎧 Play them with any audio player.")


async def tts_with_different_voices():
    """Example showing different voice selection."""
    
    print("\n🎭 Voice Selection Example")
    print("=" * 40)
    
    from elevenlabs_integration.tts_adapter import ElevenLabsTTSAdapter
    from elevenlabs_integration.config import get_recommended_voice
    
    api_key = os.getenv("ELEVENLABS_API_KEY", "mock_key")
    tts = ElevenLabsTTSAdapter(api_key=api_key)
    await tts.initialize()
    
    # Test with different voice recommendations
    test_cases = [
        ("Hello, I'm speaking in English!", "en", "female"),
        ("Hello, I'm a male English speaker!", "en", "male"), 
        ("Bonjour, je parle français!", "fr", "female"),
        ("Bonjour, je suis un homme français!", "fr", "male")
    ]
    
    for i, (text, lang, gender) in enumerate(test_cases, 1):
        print(f"\n{i}. {lang.upper()} {gender}: '{text}'")
        
        # Get recommended voice
        voice_id = get_recommended_voice(lang, gender)
        print(f"   Recommended voice: {voice_id}")
        
        # Synthesize with specific voice
        audio_data = await tts.synthesize_speech(text, voice_id=voice_id)
        
        filename = f"voice_{lang}_{gender}_{i}.mp3"
        with open(filename, "wb") as f:
            f.write(audio_data)
            
        print(f"   ✅ Saved: {filename}")
    
    await tts.cleanup()


if __name__ == "__main__":
    print("🚀 Starting ElevenLabs TTS Examples...")
    
    # Set API key if you have one
    if not os.getenv("ELEVENLABS_API_KEY"):
        print("\n💡 Tip: Set ELEVENLABS_API_KEY for live audio generation")
        print("   export ELEVENLABS_API_KEY='sk_0dd6b4af347097128ef0644479fd1c9dddc5983c7e3398a5'")
        print("   (Mock mode will be used instead)")
    
    # Run examples
    asyncio.run(simple_tts_example())
    asyncio.run(tts_with_different_voices())
    
    print("\n🎉 Examples completed!")
    print("📂 Check the generated .mp3 files in this directory.")