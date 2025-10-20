#!/usr/bin/env python3
"""
Test ElevenLabs Integration with Environment Variables

This script tests the ElevenLabs integration using the API key from .env file.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env" 
load_dotenv(env_path)

# Add project paths
project_root = Path(__file__).parent
sys.path.append(str(project_root / "src"))
sys.path.append(str(project_root))

async def test_elevenlabs_with_env():
    """Test ElevenLabs integration using environment variables."""
    
    print("🎙️ Testing ElevenLabs Integration with Environment Variables")
    print("=" * 65)
    
    # Get API key from environment
    api_key = os.getenv('ELEVENLABS_API_KEY')
    
    if not api_key:
        print("❌ ELEVENLABS_API_KEY not found in environment variables")
        print("   Make sure it's set in your .env file")
        return False
    
    print(f"✅ Found API key: {api_key[:10]}...")
    
    try:
        from elevenlabs_integration.tts_adapter import ElevenLabsTTSAdapter
        
        # Initialize with environment settings
        tts = ElevenLabsTTSAdapter(
            api_key=api_key,
            model=os.getenv('ELEVENLABS_TTS_MODEL', 'eleven_multilingual_v2'),
            voice_id=os.getenv('ELEVENLABS_TTS_VOICE_ID'),  # Will be None (auto-select)
            voice_settings={
                "stability": float(os.getenv('ELEVENLABS_TTS_STABILITY', '0.5')),
                "similarity_boost": float(os.getenv('ELEVENLABS_TTS_SIMILARITY_BOOST', '0.75')),
                "style": float(os.getenv('ELEVENLABS_TTS_STYLE', '0.0')),
                "use_speaker_boost": os.getenv('ELEVENLABS_TTS_USE_SPEAKER_BOOST', 'true').lower() == 'true'
            },
            timeout=int(os.getenv('ELEVENLABS_TTS_TIMEOUT', '30'))
        )
        
        print("🚀 Initializing TTS adapter...")
        await tts.initialize()
        
        # Test synthesis
        test_text = "Hello! This is a test using environment variables from the .env file."
        
        print(f"🗣️ Synthesizing: '{test_text}'")
        audio_data = await tts.synthesize_speech(test_text)
        
        # Save result
        output_file = "env_test_output.mp3"
        with open(output_file, "wb") as f:
            f.write(audio_data)
            
        print(f"✅ Generated audio: {output_file} ({len(audio_data):,} bytes)")
        
        # Test voice listing
        print("🎭 Fetching available voices...")
        voices = await tts.get_voices()
        
        if voices:
            print(f"✅ Found {len(voices)} voices:")
            for i, voice in enumerate(voices[:3], 1):  # Show first 3
                name = voice.get("name", "Unknown")
                voice_id = voice.get("voice_id", "")
                labels = voice.get("labels", {})
                language = labels.get("language", "unknown")
                print(f"   {i}. {name} ({language}) - {voice_id[:8]}...")
        else:
            print("⚠️ No voices retrieved (using mock mode)")
        
        await tts.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_stt_with_env():
    """Test STT adapter with environment variables."""
    
    print(f"\n🎯 Testing STT with Environment Variables")
    print("=" * 45)
    
    try:
        from elevenlabs_integration.stt_adapter import ElevenLabsSTTAdapter
        
        api_key = os.getenv('ELEVENLABS_API_KEY')
        
        stt = ElevenLabsSTTAdapter(
            api_key=api_key,
            model=os.getenv('ELEVENLABS_STT_MODEL', 'eleven_multilingual_v2'),
            language=os.getenv('ELEVENLABS_STT_LANGUAGE', 'auto'),
            timeout=int(os.getenv('ELEVENLABS_STT_TIMEOUT', '30'))
        )
        
        print("🚀 Initializing STT adapter...")
        await stt.initialize()
        
        # Test transcription with mock audio
        mock_audio = b"mock_audio_data" * 500
        
        print("🎤 Testing transcription...")
        result = await stt.transcribe_audio(mock_audio, language="en")
        
        print(f"✅ STT Result:")
        print(f"   Text: '{result.get('text', 'N/A')}'")
        print(f"   Confidence: {result.get('confidence', 0):.2f}")
        print(f"   Language: {result.get('language', 'N/A')}")
        print(f"   Success: {result.get('success', False)}")
        
        await stt.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ STT test failed: {e}")
        return False


def show_env_summary():
    """Show summary of loaded environment variables."""
    
    print(f"\n📋 Environment Variables Summary")
    print("=" * 35)
    
    env_vars = {
        'ELEVENLABS_API_KEY': 'ElevenLabs API Key',
        'ELEVENLABS_TTS_MODEL': 'TTS Model',
        'ELEVENLABS_STT_MODEL': 'STT Model', 
        'ELEVENLABS_TTS_STABILITY': 'TTS Stability',
        'ELEVENLABS_TTS_SIMILARITY_BOOST': 'TTS Similarity Boost',
        'ELEVENLABS_TTS_STYLE': 'TTS Style',
        'ELEVENLABS_TTS_USE_SPEAKER_BOOST': 'Use Speaker Boost'
    }
    
    for var, description in env_vars.items():
        value = os.getenv(var)
        if value:
            if 'API_KEY' in var and len(value) > 10:
                display_value = f"{value[:8]}...{value[-4:]}"
            else:
                display_value = value
            print(f"✅ {description}: {display_value}")
        else:
            print(f"⚪ {description}: Not set (using defaults)")


if __name__ == "__main__":
    print("🧪 ElevenLabs Environment Integration Test")
    print("This script tests ElevenLabs using your .env configuration")
    
    show_env_summary()
    
    async def run_tests():
        tts_success = await test_elevenlabs_with_env()
        stt_success = await test_stt_with_env()
        
        print(f"\n🎯 Test Results:")
        print(f"   TTS Test: {'✅ PASSED' if tts_success else '❌ FAILED'}")
        print(f"   STT Test: {'✅ PASSED' if stt_success else '❌ FAILED'}")
        
        if tts_success:
            print(f"\n🎵 Audio file generated: env_test_output.mp3")
            print(f"   Play it to hear your ElevenLabs TTS configuration!")
        
        overall_success = tts_success and stt_success
        print(f"\n{'🎉 All tests passed!' if overall_success else '⚠️ Some tests failed - check configuration'}")
        
        return overall_success
        
    success = asyncio.run(run_tests())