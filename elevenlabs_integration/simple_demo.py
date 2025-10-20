#!/usr/bin/env python3
"""
🎙️ Simple ElevenLabs Demo
Test ElevenLabs TTS/STT without complex imports
"""

import asyncio
import os
import sys
from pathlib import Path

# Add paths
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent / "src"))


async def test_elevenlabs_tts():
    """Test ElevenLabs TTS with your API key."""
    
    print("🎙️ ElevenLabs TTS Demo")
    print("=" * 40)
    
    # Get API key from environment or .env
    api_key = os.getenv("ELEVENLABS_API_KEY")
    
    if not api_key:
        # Try to load from .env file
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("ELEVENLABS_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"')
                    break
    
    if not api_key:
        print("❌ No ElevenLabs API key found!")
        print("Set ELEVENLABS_API_KEY environment variable or check .env file")
        return
    
    print(f"✅ Found API key: {api_key[:10]}...")
    
    try:
        # Test with simple HTTP request
        import aiohttp
        
        # Test API connection
        async with aiohttp.ClientSession() as session:
            headers = {"xi-api-key": api_key}
            
            # Get voices
            print("\n🎭 Fetching available voices...")
            async with session.get(
                "https://api.elevenlabs.io/v1/voices",
                headers=headers
            ) as response:
                if response.status == 200:
                    voices_data = await response.json()
                    voices = voices_data.get("voices", [])
                    print(f"✅ Found {len(voices)} voices")
                    
                    # Show first few voices
                    for i, voice in enumerate(voices[:3]):
                        name = voice.get("name", "Unknown")
                        voice_id = voice.get("voice_id", "")
                        print(f"  {i+1}. {name} ({voice_id[:8]}...)")
                        
                    # Test TTS with first voice
                    if voices:
                        voice_id = voices[0]["voice_id"]
                        voice_name = voices[0]["name"]
                        
                        print(f"\n🗣️ Testing TTS with voice: {voice_name}")
                        
                        tts_data = {
                            "text": "Hello! This is a test of ElevenLabs text-to-speech. Your agent is working perfectly!",
                            "model_id": "eleven_flash_v2_5",  # Your optimized model
                            "voice_settings": {
                                "stability": 0.6,
                                "similarity_boost": 0.8,
                                "style": 0.1,
                                "use_speaker_boost": True
                            }
                        }
                        
                        async with session.post(
                            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                            headers=headers,
                            json=tts_data
                        ) as tts_response:
                            if tts_response.status == 200:
                                audio_data = await tts_response.read()
                                
                                # Save audio file
                                output_file = "elevenlabs_test.mp3"
                                with open(output_file, "wb") as f:
                                    f.write(audio_data)
                                
                                print(f"✅ Generated audio: {output_file} ({len(audio_data):,} bytes)")
                                print(f"🎵 Play it with: open {output_file}")
                                
                            else:
                                error = await tts_response.text()
                                print(f"❌ TTS failed: {tts_response.status} - {error}")
                                
                else:
                    error = await response.text()
                    print(f"❌ API Error: {response.status} - {error}")
                    
    except ImportError:
        print("❌ aiohttp not available. Installing...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp"])
        print("Please run the demo again.")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_conversation():
    """Test a simple conversation flow."""
    
    print("\n🤖 Conversation Demo")
    print("=" * 40)
    
    # Simple conversation test
    messages = [
        "Hello, how are you today?",
        "What's the weather like?", 
        "Tell me a joke",
        "Goodbye!"
    ]
    
    for message in messages:
        print(f"\n👤 User: {message}")
        
        # Simulate processing
        await asyncio.sleep(0.5)
        
        # Simple responses (in real mode, this would use LLM)
        responses = {
            "hello": "Hello! I'm doing great, thank you for asking. How can I help you today?",
            "weather": "I don't have access to real-time weather data, but I hope it's beautiful where you are!",
            "joke": "Why don't scientists trust atoms? Because they make up everything!",
            "goodbye": "Goodbye! It was nice talking with you. Have a wonderful day!"
        }
        
        # Find best response
        message_lower = message.lower()
        response = "That's interesting! Tell me more."  # Default
        
        for key, resp in responses.items():
            if key in message_lower:
                response = resp
                break
                
        print(f"🤖 Agent: {response}")
        
        # In real mode, this would also generate TTS audio
        print("   🔊 [Audio would be generated here with ElevenLabs TTS]")


def print_instructions():
    """Print usage instructions."""
    print("\n" + "="*60)
    print("🎙️ ELEVENLABS SIMPLE DEMO")
    print("="*60)
    print()
    print("This demo tests your ElevenLabs integration:")
    print("✓ Connects to ElevenLabs API")
    print("✓ Lists available voices")
    print("✓ Generates test audio")
    print("✓ Shows conversation flow")
    print()
    print("Your API key is loaded from .env file automatically!")
    print("="*60)


async def main():
    """Run the simple demo."""
    print_instructions()
    
    try:
        # Test ElevenLabs TTS
        await test_elevenlabs_tts()
        
        # Test conversation flow
        await test_conversation()
        
        print("\n🎉 Demo completed successfully!")
        print("\nNext steps:")
        print("1. Check the generated audio file: elevenlabs_test.mp3")
        print("2. Try the full agent: make run")
        print("3. Use the interactive chat: make talk")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())