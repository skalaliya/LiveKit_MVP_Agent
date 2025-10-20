#!/usr/bin/env python3
"""
French Learning Demo with Cost-Effective ElevenLabs Integration

This demo shows how to use ElevenLabs for French language learning
with the most cost-effective model choices and optimized settings.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env" 
load_dotenv(env_path)

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src"))
sys.path.append(str(project_root))

async def demo_french_learning():
    """Demo French learning with cost-effective ElevenLabs setup."""
    
    print("🇫🇷 French Learning with ElevenLabs - Cost-Effective Setup")
    print("=" * 65)
    
    # Import our configurations
    from elevenlabs_integration.french_learning_config import (
        FrenchLearningConfig, 
        get_french_learning_voice,
        get_learning_model,
        get_cost_estimate,
        FRENCH_LEARNING_PROMPTS
    )
    from elevenlabs_integration.tts_adapter import ElevenLabsTTSAdapter
    
    # Get API key from environment
    api_key = os.getenv('ELEVENLABS_API_KEY')
    
    if not api_key:
        print("❌ ELEVENLABS_API_KEY not found!")
        print("   Please set it in your .env file")
        return False
    
    print(f"✅ API Key loaded: {api_key[:10]}...")
    
    # Create French learning configuration
    config = FrenchLearningConfig(api_key=api_key)
    
    print(f"\n🎯 Learning Configuration:")
    print(f"   STT Model: {config.stt.model}")
    print(f"   TTS Model: {config.tts.model}")
    print(f"   Language Detection: {config.stt.language}")
    
    # Initialize TTS with learning settings
    tts = ElevenLabsTTSAdapter(
        api_key=config.tts.api_key,
        model=config.tts.model,
        voice_settings=config.tts.voice_settings,
        timeout=config.tts.timeout
    )
    
    await tts.initialize()
    
    # Learning scenarios with cost estimates
    learning_scenarios = [
        {
            "level": "beginner",
            "text": FRENCH_LEARNING_PROMPTS["beginner"]["greeting"],
            "language": "french",
            "gender": "female"
        },
        {
            "level": "beginner", 
            "text": "Hello! Let's learn French together. We'll start with basic pronunciation.",
            "language": "english",
            "gender": "female"
        },
        {
            "level": "intermediate",
            "text": FRENCH_LEARNING_PROMPTS["intermediate"]["conversation"],
            "language": "french", 
            "gender": "male"
        },
        {
            "level": "advanced",
            "text": FRENCH_LEARNING_PROMPTS["advanced"]["discussion"],
            "language": "french",
            "gender": "female"
        }
    ]
    
    total_characters = 0
    
    print(f"\n🎓 French Learning Scenarios:")
    print("-" * 45)
    
    for i, scenario in enumerate(learning_scenarios, 1):
        print(f"\n{i}. {scenario['level'].title()} Level - {scenario['language'].title()}")
        
        # Get optimized voice for this scenario
        voice_id = get_french_learning_voice(
            scenario['language'], 
            scenario['gender']
        )
        
        text = scenario['text']
        print(f"   Text: '{text[:50]}...'")
        print(f"   Voice: {scenario['gender']} {scenario['language']} ({voice_id[:8] if voice_id else 'auto'}...)")
        
        # Generate speech
        audio_data = await tts.synthesize_speech(
            text=text,
            voice_id=voice_id,
            language=scenario['language'][:2]
        )
        
        # Save audio file
        filename = f"french_learning_{scenario['level']}_{scenario['language']}.mp3"
        with open(filename, "wb") as f:
            f.write(audio_data)
        
        chars = len(text)
        total_characters += chars
        
        print(f"   ✅ Generated: {filename} ({len(audio_data):,} bytes, {chars} chars)")
    
    # Cost analysis
    print(f"\n💰 Cost Analysis:")
    print("-" * 20)
    
    # Compare models
    models_to_compare = ["eleven_multilingual_v2", "eleven_turbo_v2_5"]
    
    for model in models_to_compare:
        cost_info = get_cost_estimate(total_characters, model)
        print(f"\n📊 {model}:")
        print(f"   Characters: {cost_info['characters']:,}")
        print(f"   Estimated Cost: ${cost_info['cost_usd']:.4f}")
        print(f"   Price per 1K: ${cost_info['price_per_1k_chars']:.3f}")
        print(f"   Speech Time: ~{cost_info['estimated_minutes']} minutes")
    
    # Recommendations
    print(f"\n🎯 Recommendations for French Learning:")
    print("-" * 40)
    
    recommended_model = get_learning_model("conversation_practice")
    budget_model = get_learning_model("budget_learning")
    
    print(f"✅ **Recommended**: {recommended_model}")
    print(f"   - Best balance of quality and cost")
    print(f"   - Clear pronunciation for learning")
    print(f"   - Multilingual support (FR/EN)")
    
    print(f"\n💡 **Budget Option**: {budget_model}")
    print(f"   - 50% lower cost")
    print(f"   - Still good quality for practice")
    print(f"   - Perfect for high-volume learning")
    
    print(f"\n🎭 **Voice Strategy**:")
    print(f"   - French Female (Charlotte): Clear pronunciation learning")
    print(f"   - French Male (Antoine): Listening comprehension variety") 
    print(f"   - English Female (Rachel): Bilingual comparison")
    
    await tts.cleanup()
    return True


async def demo_learning_conversation():
    """Demo a full French learning conversation."""
    
    print(f"\n🗣️ French Learning Conversation Demo")
    print("=" * 40)
    
    from elevenlabs_integration.pipeline import ElevenLabsPipeline
    from elevenlabs_integration.french_learning_config import FrenchLearningConfig
    
    api_key = os.getenv('ELEVENLABS_API_KEY')
    
    if not api_key:
        print("❌ Need API key for conversation demo")
        return False
    
    # Create learning-optimized pipeline
    config = FrenchLearningConfig(api_key=api_key)
    pipeline = ElevenLabsPipeline(config, use_existing_llm=True)
    
    try:
        await pipeline.initialize()
        
        # Learning conversation scenarios
        learning_exchanges = [
            ("Hello, I want to learn French", "en"),
            ("Bonjour, comment allez-vous?", "fr"),
            ("What does 'comment allez-vous' mean?", "en"),
            ("Pouvez-vous répéter lentement?", "fr"),
        ]
        
        print("🎓 Learning Conversation:")
        
        for i, (text, lang) in enumerate(learning_exchanges, 1):
            print(f"\n{i}. Student ({lang.upper()}): '{text}'")
            
            # Process through learning pipeline
            response_audio = await pipeline.process_text(text, lang)
            
            if response_audio:
                output_file = f"conversation_step_{i}_{lang}.mp3"
                with open(output_file, "wb") as f:
                    f.write(response_audio)
                print(f"   ✅ Teacher response saved: {output_file}")
            
            # Small delay for realistic conversation
            await asyncio.sleep(0.5)
            
        await pipeline.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Conversation demo failed: {e}")
        return False


def show_model_recommendations():
    """Show detailed model recommendations for French learning."""
    
    print(f"\n📋 ElevenLabs Model Recommendations for French Learning")
    print("=" * 60)
    
    models = {
        "eleven_multilingual_v2": {
            "cost": "$$",
            "quality": "⭐⭐⭐⭐⭐",
            "languages": "29 languages including FR/EN",
            "best_for": "Complete French learning experience",
            "pros": ["Excellent French pronunciation", "Stable quality", "Multilingual support"],
            "cons": ["Higher cost than Turbo models"]
        },
        "eleven_turbo_v2_5": {
            "cost": "$",
            "quality": "⭐⭐⭐⭐",
            "languages": "32 languages including FR/EN", 
            "best_for": "Budget-conscious French practice",
            "pros": ["50% lower cost", "Fast generation", "Good quality"],
            "cons": ["Slightly less nuanced than multilingual_v2"]
        },
        "eleven_flash_v2_5": {
            "cost": "$",
            "quality": "⭐⭐⭐",
            "languages": "32 languages",
            "best_for": "High-volume vocabulary practice",
            "pros": ["Ultra-fast", "Very low cost", "Good for repetition"],
            "cons": ["Less emotional range", "Basic pronunciation"]
        }
    }
    
    for model_name, info in models.items():
        print(f"\n🎯 **{model_name}**")
        print(f"   Cost: {info['cost']} | Quality: {info['quality']}")
        print(f"   Languages: {info['languages']}")
        print(f"   Best for: {info['best_for']}")
        print(f"   Pros: {', '.join(info['pros'])}")
        print(f"   Cons: {', '.join(info['cons'])}")
    
    print(f"\n💡 **Our Recommendation for French Learning:**")
    print(f"   🥇 Primary: **eleven_multilingual_v2**")
    print(f"      - Best balance of quality and cost")
    print(f"      - Excellent for pronunciation learning") 
    print(f"      - Clear French accent and intonation")
    print(f"   ")
    print(f"   🥈 Budget: **eleven_turbo_v2_5**")
    print(f"      - 50% cost savings")
    print(f"      - Perfect for practice sessions")
    print(f"      - Good quality for conversation practice")


if __name__ == "__main__":
    print("🇫🇷 ElevenLabs French Learning Demo")
    print("Optimized for cost-effective language learning")
    
    async def run_all_demos():
        print("\n🚀 Running French Learning Demos...")
        
        # Show recommendations first
        show_model_recommendations()
        
        # Run TTS demo
        tts_success = await demo_french_learning()
        
        # Run conversation demo
        conversation_success = await demo_learning_conversation()
        
        print(f"\n🎯 Demo Results:")
        print(f"   TTS Learning Demo: {'✅ PASSED' if tts_success else '❌ FAILED'}")
        print(f"   Conversation Demo: {'✅ PASSED' if conversation_success else '❌ FAILED'}")
        
        if tts_success:
            print(f"\n🎵 Generated Learning Files:")
            print(f"   - french_learning_*.mp3 (pronunciation examples)")
            if conversation_success:
                print(f"   - conversation_step_*.mp3 (learning dialogue)")
        
        print(f"\n🎓 Ready for French Learning!")
        print(f"   Model: eleven_multilingual_v2 (recommended)")
        print(f"   Voices: Charlotte (FR-F), Antoine (FR-M), Rachel (EN-F)")
        print(f"   Cost: ~$0.18 per 1K characters")
        
    asyncio.run(run_all_demos())