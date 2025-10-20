#!/usr/bin/env python3
"""
🎙️ Interactive Voice Agent Demo
Simple CLI to talk to your voice agent using text input/output
"""

import os
import asyncio
import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "elevenlabs_integration"))

async def main():
    print("🎙️ Welcome to your Voice Agent!")
    print("=" * 50)
    print("Type your messages and get AI responses.")
    print("Commands:")
    print("  'quit' or 'exit' - Exit the demo")
    print("  'voice' - Switch to voice mode (if available)")
    print("  'help' - Show this help")
    print("=" * 50)
    
    # Try to import and initialize the agent
    try:
        from livekit_mvp_agent.pipeline import VoicePipeline
        from livekit_mvp_agent.config import AgentConfig
        
        config = AgentConfig()
        pipeline = VoicePipeline(config)
        
        print(f"✅ Agent loaded with LLM: {config.llm.model}")
        print(f"✅ STT Model: {config.stt.model}")
        print(f"✅ TTS Model: {config.tts.model}")
        
    except Exception as e:
        print(f"⚠️  Could not load full pipeline: {e}")
        print("📝 Running in simple chat mode...")
        pipeline = None
    
    print("\n🚀 Agent ready! Start chatting:")
    print("-" * 30)
    
    conversation_history = []
    
    while True:
        try:
            # Get user input
            user_input = input("\n👤 You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye!")
                break
                
            if user_input.lower() == 'help':
                print("\n📖 Available commands:")
                print("  - Type any message to chat with the AI")
                print("  - 'quit'/'exit' - Exit")
                print("  - 'clear' - Clear conversation history")
                print("  - 'status' - Show agent status")
                continue
                
            if user_input.lower() == 'clear':
                conversation_history = []
                print("🧹 Conversation history cleared!")
                continue
                
            if user_input.lower() == 'status':
                print(f"\n📊 Agent Status:")
                print(f"  Pipeline loaded: {'✅ Yes' if pipeline else '❌ No'}")
                print(f"  Conversation length: {len(conversation_history)} messages")
                continue
            
            # Add to conversation history
            conversation_history.append({"role": "user", "content": user_input})
            
            # Get AI response
            print("🤖 Agent: ", end="", flush=True)
            
            if pipeline:
                try:
                    # Try to use the full pipeline
                    response = await pipeline.process_text(user_input, conversation_history)
                    print(response)
                    conversation_history.append({"role": "assistant", "content": response})
                except Exception as e:
                    print(f"Error with pipeline: {e}")
                    print("Falling back to simple response...")
                    response = generate_simple_response(user_input)
                    print(response)
            else:
                # Simple fallback response
                response = generate_simple_response(user_input)
                print(response)
                conversation_history.append({"role": "assistant", "content": response})
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Type 'help' for available commands.")

def generate_simple_response(user_input: str) -> str:
    """Generate a simple response when full pipeline isn't available"""
    responses = {
        "hello": "Hello! I'm your voice agent. How can I help you today?",
        "hi": "Hi there! What would you like to chat about?",
        "how are you": "I'm doing great! Ready to assist you with anything you need.",
        "what can you do": "I can help with conversations, answer questions, and in full mode I can process voice input/output!",
        "test": "Test successful! I'm responding to your message.",
    }
    
    user_lower = user_input.lower()
    for key, response in responses.items():
        if key in user_lower:
            return response
    
    # Default response
    return f"I heard you say: '{user_input}'. In full mode, I would process this through the LLM pipeline!"

if __name__ == "__main__":
    asyncio.run(main())