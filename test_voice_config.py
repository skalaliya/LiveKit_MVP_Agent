#!/usr/bin/env python3
"""
Test script to verify the medium Whisper model is integrated correctly
"""

import os
import sys
import asyncio
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_voice_agent():
    """Test the voice agent with medium Whisper model"""
    
    print("🔍 Testing Voice Agent Configuration...")
    print("=" * 50)
    
    # Test environment variables
    print("📋 Environment Configuration:")
    print(f"  WHISPER_MODEL: {os.getenv('WHISPER_MODEL', 'not set')}")
    print(f"  LLM_MODEL: {os.getenv('LLM_MODEL', 'not set')}")
    print(f"  OLLAMA_BASE_URL: {os.getenv('OLLAMA_BASE_URL', 'not set')}")
    
    # Test imports
    try:
        from livekit_mvp_agent.config import AgentConfig
        print("\n✅ Config import successful")
        
        config = AgentConfig()
        print(f"✅ STT Model: {config.whisper_model}")
        print(f"✅ LLM Model: {config.llm_model}")
        print(f"✅ Ollama URL: {config.ollama_base_url}")
        
    except Exception as e:
        print(f"\n❌ Config import failed: {e}")
        return False
    
    # Test Whisper directly
    try:
        print("\n🎤 Testing Whisper Medium Model...")
        from faster_whisper import WhisperModel
        
        model = WhisperModel("medium", device="cpu", compute_type="int8")
        print("✅ Medium Whisper model loaded successfully")
        
    except Exception as e:
        print(f"❌ Whisper test failed: {e}")
        return False
    
    # Test Ollama connection
    try:
        print("\n🤖 Testing Ollama Connection...")
        import requests
        
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✅ Ollama connected, {len(models)} models available")
            for model in models:
                print(f"  - {model['name']}")
        else:
            print(f"⚠️  Ollama responded with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
    
    # Test ElevenLabs
    try:
        print("\n🔊 Testing ElevenLabs Integration...")
        
        # Load environment from .env file
        from dotenv import load_dotenv
        load_dotenv()
        
        elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
        if elevenlabs_key:
            print("✅ ElevenLabs API key found")
            
            # Test import
            sys.path.insert(0, str(Path(__file__).parent / "elevenlabs_integration"))
            from elevenlabs_client import ElevenLabsClient
            
            client = ElevenLabsClient(api_key=elevenlabs_key)
            voices = client.get_voices()
            print(f"✅ ElevenLabs connected, {len(voices)} voices available")
            
        else:
            print("⚠️  ElevenLabs API key not found in environment")
            
    except Exception as e:
        print(f"❌ ElevenLabs test failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Voice Agent Configuration Test Complete!")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_voice_agent())