#!/usr/bin/env python3
"""
🎙️ Simple Voice Agent Test
Test your components without complex configuration
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_ollama():
    """Test Ollama connection directly."""
    
    print("🧠 Testing Ollama LLM...")
    
    try:
        import aiohttp
        
        # Test Ollama directly
        async with aiohttp.ClientSession() as session:
            # Check server
            async with session.get("http://localhost:11434/api/version") as response:
                if response.status == 200:
                    version_data = await response.json()
                    print(f"✅ Ollama server: v{version_data['version']}")
                else:
                    print(f"❌ Ollama server error: {response.status}")
                    return False
            
            # Test model
            payload = {
                "model": "llama3.2:3b",
                "prompt": "Hello! Please respond with just one sentence about yourself.",
                "stream": False
            }
            
            async with session.post("http://localhost:11434/api/generate", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    response_text = result.get("response", "")
                    print(f"🤖 LLM Response: {response_text}")
                    return True
                else:
                    print(f"❌ LLM error: {response.status}")
                    return False
                    
    except ImportError:
        print("❌ aiohttp not available")
        return False
    except Exception as e:
        print(f"❌ Ollama test failed: {e}")
        return False


async def test_whisper():
    """Test Whisper model."""
    
    print("\n🎤 Testing Whisper STT...")
    
    try:
        from faster_whisper import WhisperModel
        
        # Use tiny model to avoid space issues
        print("Loading tiny Whisper model (39MB)...")
        model = WhisperModel("tiny", device="auto", compute_type="int8")
        
        print("✅ Whisper model loaded successfully")
        print(f"   Model: tiny (39MB)")
        print(f"   Device: {model.device}")
        print(f"   Compute type: {model.compute_type}")
        
        return True
        
    except Exception as e:
        print(f"❌ Whisper test failed: {e}")
        return False


async def test_elevenlabs():
    """Test ElevenLabs integration."""
    
    print("\n🔊 Testing ElevenLabs TTS...")
    
    # Get API key
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        # Try to load from .env
        env_file = Path(".env")
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("ELEVENLABS_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"')
                    break
    
    if not api_key:
        print("❌ No ElevenLabs API key found")
        return False
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            headers = {"xi-api-key": api_key}
            
            # Simple TTS test
            voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
            tts_data = {
                "text": "Hello! Your voice agent is working perfectly!",
                "model_id": "eleven_flash_v2_5"
            }
            
            async with session.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers=headers,
                json=tts_data
            ) as response:
                
                if response.status == 200:
                    audio_data = await response.read()
                    
                    # Save audio
                    output_file = "agent_test.mp3"
                    with open(output_file, "wb") as f:
                        f.write(audio_data)
                    
                    print(f"✅ Generated audio: {output_file} ({len(audio_data):,} bytes)")
                    return True
                else:
                    print(f"❌ TTS failed: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ ElevenLabs test failed: {e}")
        return False


async def interactive_chat():
    """Simple interactive chat."""
    
    print("\n💬 Interactive Chat")
    print("=" * 25)
    print("Chat with llama3.2:3b! Type 'quit' to exit.")
    print("-" * 25)
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    user_input = input("\n👤 You: ").strip()
                    
                    if not user_input:
                        continue
                        
                    if user_input.lower() in ['quit', 'exit', 'bye']:
                        print("👋 Goodbye!")
                        break
                    
                    print("🤖 Agent: ", end="", flush=True)
                    
                    # Send to Ollama
                    payload = {
                        "model": "llama3.2:3b",
                        "prompt": user_input,
                        "stream": False
                    }
                    
                    async with session.post("http://localhost:11434/api/generate", json=payload) as response:
                        if response.status == 200:
                            result = await response.json()
                            response_text = result.get("response", "Sorry, I couldn't respond.")
                            print(response_text)
                        else:
                            print("Sorry, I'm having trouble responding.")
                            
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                    
    except Exception as e:
        print(f"❌ Chat error: {e}")


async def main():
    """Run all tests."""
    
    print("🎙️ Voice Agent Component Test")
    print("=" * 40)
    
    results = {
        "ollama": await test_ollama(),
        "whisper": await test_whisper(), 
        "elevenlabs": await test_elevenlabs()
    }
    
    print("\n📊 Test Results:")
    print("-" * 20)
    for component, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{component.capitalize():12} {status}")
    
    working_count = sum(results.values())
    
    if working_count == 3:
        print(f"\n🎉 All {working_count}/3 components working!")
        
        # Offer interactive chat
        try:
            choice = input("\nTry interactive chat? (y/n): ").lower()
            if choice in ['y', 'yes']:
                await interactive_chat()
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            
    elif working_count >= 1:
        print(f"\n⚠️  {working_count}/3 components working")
        print("Your voice agent has partial functionality!")
        
        if results["ollama"]:
            try:
                choice = input("\nTry chat with working LLM? (y/n): ").lower()
                if choice in ['y', 'yes']:
                    await interactive_chat()
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
    else:
        print("\n❌ No components working")
    
    print("\n📋 Alternative ways to test:")
    print("1. 🎪 Voice demo: cd elevenlabs_integration && uv run python voice_demo.py")
    print("2. 💬 Simple chat: make talk")
    print("3. 🧪 Audio test: make test-elevenlabs")


if __name__ == "__main__":
    asyncio.run(main())