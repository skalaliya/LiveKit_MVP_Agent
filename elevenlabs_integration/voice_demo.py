#!/usr/bin/env python3
"""
🎙️ ElevenLabs Voice Agent Demo
Working demo that handles API limitations gracefully
"""

import asyncio
import os
import sys
from pathlib import Path

# Add paths
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent / "src"))


async def test_basic_tts():
    """Test basic TTS functionality."""
    
    print("🎙️ Testing ElevenLabs TTS")
    print("=" * 40)
    
    # Get API key
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("ELEVENLABS_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"')
                    break
    
    if not api_key:
        print("❌ No API key found")
        return False
    
    print(f"✅ API Key: {api_key[:10]}...")
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            headers = {"xi-api-key": api_key}
            
            # Try TTS with a known voice ID (Rachel - default voice)
            voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
            
            print("\n🗣️ Testing TTS with Rachel voice...")
            
            tts_data = {
                "text": "Hello! This is your voice agent speaking. I'm using ElevenLabs for high-quality speech synthesis!",
                "model_id": "eleven_flash_v2_5",  # Your optimized model
            }
            
            async with session.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers=headers,
                json=tts_data
            ) as response:
                
                if response.status == 200:
                    audio_data = await response.read()
                    
                    # Save audio
                    output_file = "voice_agent_test.mp3"
                    with open(output_file, "wb") as f:
                        f.write(audio_data)
                    
                    print(f"✅ Generated: {output_file} ({len(audio_data):,} bytes)")
                    print(f"🎵 Play with: open {output_file}")
                    return True
                    
                else:
                    error_text = await response.text()
                    print(f"❌ TTS Error: {response.status}")
                    print(f"Response: {error_text}")
                    return False
                    
    except ImportError:
        print("❌ aiohttp not installed. Installing...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp"])
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def demo_conversation_with_tts():
    """Demo a conversation with TTS output."""
    
    print("\n🤖 Voice Agent Conversation Demo")
    print("=" * 50)
    print("This simulates talking to your voice agent:")
    print("- You type messages")
    print("- Agent responds with text + generates audio")
    print("=" * 50)
    
    conversation = [
        {
            "user": "Hello, can you help me practice French?",
            "agent": "Bonjour! I'd be happy to help you practice French. What would you like to work on today?"
        },
        {
            "user": "How do I say 'good morning' in French?",
            "agent": "Good morning in French is 'Bonjour' (pronounced bon-ZHOOR). Try saying it!"
        },
        {
            "user": "Bonjour!",
            "agent": "Excellent! Your pronunciation sounds great. Let's try another phrase: 'Comment allez-vous?' which means 'How are you?'"
        }
    ]
    
    # Get API key for TTS
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("ELEVENLABS_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"')
                    break
    
    tts_available = api_key is not None
    
    for i, exchange in enumerate(conversation, 1):
        print(f"\n--- Exchange {i} ---")
        print(f"👤 You: {exchange['user']}")
        
        # Simulate thinking
        await asyncio.sleep(0.5)
        
        print(f"🤖 Agent: {exchange['agent']}")
        
        # Generate TTS if available
        if tts_available:
            try:
                import aiohttp
                
                async with aiohttp.ClientSession() as session:
                    headers = {"xi-api-key": api_key}
                    voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel
                    
                    tts_data = {
                        "text": exchange['agent'],
                        "model_id": "eleven_flash_v2_5"
                    }
                    
                    async with session.post(
                        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                        headers=headers,
                        json=tts_data
                    ) as response:
                        
                        if response.status == 200:
                            audio_data = await response.read()
                            audio_file = f"conversation_{i}.mp3"
                            
                            with open(audio_file, "wb") as f:
                                f.write(audio_data)
                            
                            print(f"   🔊 Audio saved: {audio_file}")
                        else:
                            print(f"   ⚠️ TTS failed: {response.status}")
                            
            except Exception as e:
                print(f"   ⚠️ TTS error: {e}")
        else:
            print("   🔊 [TTS would generate audio here]")
        
        # Pause between exchanges
        await asyncio.sleep(1)


async def show_capabilities():
    """Show what the voice agent can do."""
    
    print("\n🚀 Your Voice Agent Capabilities")
    print("=" * 50)
    
    capabilities = [
        "🎙️ High-quality speech synthesis (ElevenLabs TTS)",
        "🎯 Speech recognition (ElevenLabs STT)", 
        "🧠 Local AI reasoning (Ollama LLM)",
        "🌍 Bilingual support (English + French)",
        "⚡ Real-time audio streaming (LiveKit)",
        "💰 Cost-optimized models (eleven_flash_v2_5)",
        "🎭 Multiple voice options",
        "📱 WebRTC browser support"
    ]
    
    for capability in capabilities:
        print(f"  {capability}")
        await asyncio.sleep(0.2)
    
    print("\n📋 Available Commands:")
    commands = [
        "make talk          # Interactive text chat",
        "make run           # Full voice agent with WebRTC", 
        "make test-elevenlabs # Test ElevenLabs integration",
        "make start-ollama   # Start local LLM server"
    ]
    
    for command in commands:
        print(f"  {command}")


def main_menu():
    """Show the main menu."""
    
    print("\n" + "="*60)
    print("🎙️ ELEVENLABS VOICE AGENT DEMO")
    print("="*60)
    print()
    print("Choose what you'd like to test:")
    print("1. 🗣️  Test TTS (Text-to-Speech)")
    print("2. 🤖 Demo Conversation with Voice")
    print("3. 📋 Show Agent Capabilities")
    print("4. 🚀 All Tests")
    print("0. 🚪 Exit")
    print()


async def run_demo():
    """Run the interactive demo."""
    
    while True:
        main_menu()
        
        try:
            choice = input("Enter your choice (0-4): ").strip()
            
            if choice == "0":
                print("👋 Goodbye!")
                break
            elif choice == "1":
                await test_basic_tts()
            elif choice == "2":
                await demo_conversation_with_tts()
            elif choice == "3":
                await show_capabilities()
            elif choice == "4":
                await test_basic_tts()
                await demo_conversation_with_tts()
                await show_capabilities()
            else:
                print("❌ Invalid choice. Please try again.")
                
            input("\nPress Enter to continue...")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(run_demo())