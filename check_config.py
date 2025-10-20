#!/usr/bin/env python3
"""
Environment Configuration Test Script

This script verifies that all environment variables are properly configured
and shows how to access them in your applications.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

def load_env_config():
    """Load and display environment configuration."""
    
    # Load .env file
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded configuration from: {env_path}")
    else:
        print("⚠️  No .env file found, using system environment variables only")
    
    print("\n" + "="*60)
    print("🔧 CONFIGURATION SUMMARY")
    print("="*60)
    
    # LiveKit Configuration
    print("\n📡 LiveKit Configuration:")
    print(f"   URL: {os.getenv('LIVEKIT_URL', 'NOT SET')}")
    print(f"   API Key: {mask_key(os.getenv('LIVEKIT_API_KEY', 'NOT SET'))}")
    print(f"   API Secret: {mask_key(os.getenv('LIVEKIT_API_SECRET', 'NOT SET'))}")
    print(f"   Room Name: {os.getenv('LIVEKIT_ROOM_NAME', 'NOT SET')}")
    
    # ElevenLabs Configuration
    print("\n🎙️ ElevenLabs Configuration:")
    elevenlabs_key = os.getenv('ELEVENLABS_API_KEY', 'NOT SET')
    if elevenlabs_key != 'NOT SET':
        print(f"   API Key: {mask_key(elevenlabs_key)} ✅")
        print(f"   STT Model: {os.getenv('ELEVENLABS_STT_MODEL', 'eleven_multilingual_v2')}")
        print(f"   TTS Model: {os.getenv('ELEVENLABS_TTS_MODEL', 'eleven_multilingual_v2')}")
        print(f"   Voice ID: {os.getenv('ELEVENLABS_TTS_VOICE_ID', 'auto')}")
    else:
        print(f"   API Key: {elevenlabs_key} ❌")
        print("   Note: ElevenLabs integration will use mock mode")
    
    # Whisper Configuration
    print("\n🗣️ Whisper STT Configuration:")
    print(f"   Model: {os.getenv('WHISPER_MODEL', 'medium')}")
    print(f"   Device: {os.getenv('WHISPER_DEVICE', 'auto')}")
    print(f"   Compute Type: {os.getenv('WHISPER_COMPUTE_TYPE', 'int8')}")
    
    # LLM Configuration
    print("\n🧠 LLM Configuration (Ollama):")
    print(f"   Base URL: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")
    print(f"   Model: {os.getenv('LLM_MODEL', 'llama3.1:8b-instruct-q4_K_M')}")
    print(f"   Fallback: {os.getenv('LLM_FALLBACK', 'mistral:7b-instruct-q4_K_M')}")
    print(f"   Temperature: {os.getenv('LLM_TEMPERATURE', '0.7')}")
    
    # TTS Configuration
    print("\n🔊 TTS Configuration:")
    print(f"   Primary: {os.getenv('TTS_PRIMARY', 'kokoro')}")
    print(f"   Fallback: {os.getenv('TTS_FALLBACK', 'piper')}")
    print(f"   Voice: {os.getenv('TTS_VOICE', 'en-US-kokoro')}")
    
    # Audio Configuration
    print("\n🎵 Audio Configuration:")
    print(f"   Sample Rate: {os.getenv('SAMPLE_RATE', '16000')} Hz")
    print(f"   Channels: {os.getenv('CHANNELS', '1')}")
    print(f"   Chunk Size: {os.getenv('CHUNK_SIZE', '1024')}")
    
    # Voice Presets
    print("\n🎭 ElevenLabs Voice Presets:")
    voice_presets = {
        'EN Female': os.getenv('ELEVENLABS_VOICE_EN_FEMALE'),
        'EN Male': os.getenv('ELEVENLABS_VOICE_EN_MALE'),
        'FR Female': os.getenv('ELEVENLABS_VOICE_FR_FEMALE'),
        'FR Male': os.getenv('ELEVENLABS_VOICE_FR_MALE'),
    }
    
    for name, voice_id in voice_presets.items():
        if voice_id:
            print(f"   {name}: {voice_id[:8]}... ✅")
        else:
            print(f"   {name}: Not configured (using auto-select)")


def mask_key(key):
    """Mask API keys for security."""
    if key == 'NOT SET' or key == 'your_api_key_here' or key == 'your_elevenlabs_api_key_here':
        return key
    if len(key) > 8:
        return f"{key[:8]}...{key[-4:]}"
    return "***"


def check_config_health():
    """Check configuration health and provide recommendations."""
    
    print("\n" + "="*60)
    print("🏥 CONFIGURATION HEALTH CHECK")
    print("="*60)
    
    issues = []
    recommendations = []
    
    # Check ElevenLabs
    elevenlabs_key = os.getenv('ELEVENLABS_API_KEY', '')
    if not elevenlabs_key or elevenlabs_key in ['NOT SET', 'your_elevenlabs_api_key_here']:
        issues.append("ElevenLabs API key not configured")
        recommendations.append("Set ELEVENLABS_API_KEY for premium audio quality")
    elif not elevenlabs_key.startswith('sk_'):
        issues.append("ElevenLabs API key format incorrect")
        recommendations.append("API key should start with 'sk_'")
    
    # Check LiveKit
    livekit_key = os.getenv('LIVEKIT_API_KEY', '')
    if not livekit_key or livekit_key in ['NOT SET', 'your_api_key_here']:
        issues.append("LiveKit API key not configured")
        recommendations.append("Set LiveKit credentials for real-time streaming")
    
    # Check Ollama
    ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    if 'localhost' in ollama_url:
        recommendations.append("Make sure Ollama is running: make start-ollama")
    
    # Report results
    if not issues:
        print("✅ All critical configurations look good!")
    else:
        print(f"⚠️  Found {len(issues)} configuration issues:")
        for issue in issues:
            print(f"   - {issue}")
    
    if recommendations:
        print(f"\n💡 Recommendations ({len(recommendations)}):")
        for rec in recommendations:
            print(f"   - {rec}")
    
    return len(issues) == 0


def show_usage_examples():
    """Show code examples for using these environment variables."""
    
    print("\n" + "="*60)
    print("📚 USAGE EXAMPLES")
    print("="*60)
    
    print("""
# Basic Environment Access
import os
elevenlabs_key = os.getenv('ELEVENLABS_API_KEY')
livekit_url = os.getenv('LIVEKIT_URL', 'ws://localhost:7880')

# ElevenLabs Integration
from elevenlabs_integration.config import ElevenLabsConfig
config = ElevenLabsConfig(api_key=os.getenv('ELEVENLABS_API_KEY'))

# Voice Selection
from elevenlabs_integration.config import get_recommended_voice
voice_id = (os.getenv('ELEVENLABS_VOICE_EN_FEMALE') or 
           get_recommended_voice('en', 'female'))

# TTS with Environment Settings
from elevenlabs_integration.tts_adapter import ElevenLabsTTSAdapter
tts = ElevenLabsTTSAdapter(
    api_key=os.getenv('ELEVENLABS_API_KEY'),
    model=os.getenv('ELEVENLABS_TTS_MODEL', 'eleven_multilingual_v2'),
    voice_id=os.getenv('ELEVENLABS_TTS_VOICE_ID')
)

# Main Project Configuration (uses .env automatically)
from livekit_mvp_agent.config import get_settings  
settings = get_settings()  # Loads from .env automatically
""")


if __name__ == "__main__":
    print("🔍 Environment Configuration Checker")
    print("This script checks your .env file and environment variables")
    
    try:
        load_env_config()
        is_healthy = check_config_health()
        show_usage_examples()
        
        if is_healthy:
            print(f"\n🎉 Configuration is ready! You can now:")
            print("   - Run the main agent: make run")
            print("   - Test ElevenLabs: cd elevenlabs_integration && python example_tts.py")
            print("   - Run full demo: cd elevenlabs_integration && python demo.py")
        else:
            print(f"\n🔧 Please fix the configuration issues above before proceeding.")
            
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("   Make sure you're in the project directory and dependencies are installed")
        print("   Run: make setup")
    except Exception as e:
        print(f"\n❌ Error: {e}")