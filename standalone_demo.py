#!/usr/bin/env python3
"""
🎙️ Standalone Voice Agent Demo
Test your voice agent without LiveKit server
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_voice_pipeline():
    """Test the voice processing pipeline directly."""
    
    print("🎙️ Standalone Voice Agent Test")
    print("=" * 50)
    print("Testing without LiveKit server...")
    print()
    
    try:
        # Import voice components
        from livekit_mvp_agent.config import Settings
        from livekit_mvp_agent.adapters.llm_ollama import OllamaLLM
        from livekit_mvp_agent.adapters.stt_whisper import WhisperSTT
        
        print("📋 Loading configuration...")
        settings = Settings()
        print(f"✅ LLM Model: {settings.llm.model}")
        print(f"✅ Whisper Model: {settings.stt.model}")
        print(f"✅ TTS Primary: {settings.tts.primary}")
        
        # Test Ollama connection
        print("\n🧠 Testing Ollama LLM...")
        ollama = OllamaLLM(
            base_url=settings.ollama.base_url,
            model=settings.llm.model,
            temperature=settings.llm.temperature
        )
        
        await ollama.initialize()
        
        # Test LLM response
        response = await ollama.generate_response("Hello! How are you today?")
        print(f"🤖 LLM Response: {response}")
        
        # Test Whisper STT
        print("\n🎤 Testing Whisper STT...")
        whisper = WhisperSTT(
            model_name=settings.stt.model,
            device=settings.stt.device
        )
        
        await whisper.initialize()
        print("✅ Whisper model loaded successfully")
        
        # Test with fake audio (just to verify model works)
        fake_audio = b"fake_audio_data" * 1000
        try:
            result = await whisper.transcribe(fake_audio)
            print(f"🎯 STT Test: {result}")
        except Exception as e:
            print(f"⚠️ STT test with fake audio: {e} (expected)")
        
        # Cleanup
        await ollama.cleanup()
        await whisper.cleanup()
        
        print("\n✅ All components working!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def interactive_chat():
    """Interactive chat with the LLM."""
    
    print("\n💬 Interactive Chat Mode")
    print("=" * 30)
    print("Chat with your AI agent! Type 'quit' to exit.")
    
    try:
        from livekit_mvp_agent.config import Settings
        from livekit_mvp_agent.adapters.llm_ollama import OllamaLLM
        
        settings = Settings()
        ollama = OllamaLLM(
            base_url=settings.ollama.base_url,
            model=settings.llm.model,
            temperature=settings.llm.temperature
        )
        
        await ollama.initialize()
        print(f"🤖 Connected to {settings.llm.model}")
        print("-" * 30)
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("👋 Goodbye!")
                    break
                
                print("🤖 Agent: ", end="", flush=True)
                response = await ollama.generate_response(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
                
        await ollama.cleanup()
        
    except Exception as e:
        print(f"❌ Chat error: {e}")


def main():
    """Run the standalone demo."""
    
    print("🚀 Starting Standalone Voice Agent Demo...")
    
    # Check if we're in the right directory
    if not Path("src").exists():
        print("❌ Please run from the project root directory")
        return
    
    async def run_demo():
        # Test components
        success = await test_voice_pipeline()
        
        if success:
            print("\n🎉 All systems working!")
            
            # Ask if user wants to chat
            try:
                chat_choice = input("\nWould you like to try interactive chat? (y/n): ").lower()
                if chat_choice in ['y', 'yes']:
                    await interactive_chat()
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
        else:
            print("\n❌ Some components failed. Check the errors above.")
            
        print("\n📋 Other ways to use your agent:")
        print("1. 💬 Text chat: make talk")
        print("2. 🎪 Voice demo: cd elevenlabs_integration && uv run python voice_demo.py") 
        print("3. 🧪 Audio test: make test-elevenlabs")
    
    # Run the demo
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()