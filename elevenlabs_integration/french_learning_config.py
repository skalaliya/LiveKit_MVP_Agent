"""
ElevenLabs French Learning Configuration

Optimized settings for French language learning with cost-effectiveness in mind.
Uses the best balance of quality, cost, and multilingual support.
"""

from dataclasses import dataclass
from .config import ElevenLabsConfig, ElevenLabsSTTConfig, ElevenLabsTTSConfig


@dataclass
class FrenchLearningConfig(ElevenLabsConfig):
    """Optimized configuration for French language learning."""
    
    def __post_init__(self):
        """Initialize with French learning optimizations."""
        super().__post_init__()
        
        # Override with learning-optimized settings
        self.stt = ElevenLabsSTTConfig(
            api_key=self.api_key,
            model="scribe_v1",  # UPDATED: Best STT with 99 languages + timestamps
            language="auto",  # Auto-detect FR/EN switching
            timeout=30
        )
        
        self.tts = ElevenLabsTTSConfig(
            api_key=self.api_key,
            model="eleven_flash_v2_5",  # UPDATED: Best value for French learning
            voice_id=None,  # Will auto-select based on language
            timeout=30,
            voice_settings={
                "stability": 0.6,        # Slightly higher for clear pronunciation
                "similarity_boost": 0.8, # Higher for consistent accent
                "style": 0.1,           # Slight style for naturalness
                "use_speaker_boost": True
            }
        )


# French Learning Voice Mappings
FRENCH_LEARNING_VOICES = {
    "french": {
        "female": {
            "primary": "XB0fDUnXU5powFXDhCwa",  # Charlotte - clear French
            "description": "Clear female French pronunciation, ideal for learning"
        },
        "male": {
            "primary": "ErXwobaYiN019PkySvjV",   # Antoine - native French
            "description": "Native male French speaker, good for listening practice"
        }
    },
    "english": {
        "female": {
            "primary": "21m00Tcm4TlvDq8ikWAM",  # Rachel - clear English
            "description": "Clear English for comparison and bilingual practice"
        },
        "male": {
            "primary": "pNInz6obpgDQGcFmaJgB",   # Adam - mature English
            "description": "Deep, clear English for contrast learning"
        }
    }
}


# Model recommendations by use case
LEARNING_MODEL_RECOMMENDATIONS = {
    "pronunciation_practice": {
        "model": "eleven_multilingual_v2",
        "reason": "Clear, consistent pronunciation for repetition exercises"
    },
    "conversation_practice": {
        "model": "eleven_multilingual_v2", 
        "reason": "Natural conversation flow with emotional nuance"
    },
    "budget_learning": {
        "model": "eleven_turbo_v2_5",
        "reason": "50% lower cost, still good quality for practice"
    },
    "premium_experience": {
        "model": "eleven_multilingual_v2",
        "reason": "Best balance of quality and multilingual support"
    }
}


def get_french_learning_voice(language: str, gender: str = "female", use_case: str = "general") -> str:
    """
    Get optimized voice for French learning.
    
    Args:
        language: 'french' or 'english'  
        gender: 'female' or 'male'
        use_case: 'general', 'pronunciation', 'conversation'
        
    Returns:
        Voice ID optimized for learning
    """
    if language.lower().startswith('fr'):
        lang_key = 'french'
    else:
        lang_key = 'english'
        
    voices = FRENCH_LEARNING_VOICES.get(lang_key, {})
    gender_voices = voices.get(gender, voices.get('female', {}))
    
    return gender_voices.get('primary')


def get_learning_model(use_case: str = "conversation_practice") -> str:
    """
    Get recommended model for specific learning use case.
    
    Args:
        use_case: Type of learning activity
        
    Returns:
        Model name
    """
    recommendation = LEARNING_MODEL_RECOMMENDATIONS.get(
        use_case, 
        LEARNING_MODEL_RECOMMENDATIONS["conversation_practice"]
    )
    return recommendation["model"]


def get_cost_estimate(characters: int, model: str = "eleven_multilingual_v2") -> dict:
    """
    Estimate costs for French learning sessions.
    
    Args:
        characters: Number of characters to synthesize
        model: Model to use
        
    Returns:
        Cost breakdown
    """
    # Approximate pricing (as of 2024)
    pricing = {
        "eleven_multilingual_v2": 0.18,     # $0.18 per 1K chars
        "eleven_turbo_v2_5": 0.09,          # 50% lower (estimated)
        "eleven_flash_v2_5": 0.09,          # Similar to turbo
    }
    
    price_per_1k = pricing.get(model, 0.18)
    cost = (characters / 1000) * price_per_1k
    
    return {
        "characters": characters,
        "model": model,
        "cost_usd": round(cost, 4),
        "price_per_1k_chars": price_per_1k,
        "estimated_minutes": characters // 150,  # ~150 chars per minute of speech
    }


# Sample French learning prompts for different levels
FRENCH_LEARNING_PROMPTS = {
    "beginner": {
        "greeting": "Bonjour! Je suis votre assistant pour apprendre le français. Commençons par les bases.",
        "pronunciation": "Répétez après moi: 'Bonjour, comment allez-vous?'",
        "vocabulary": "Apprenons quelques mots nouveaux aujourd'hui."
    },
    "intermediate": {
        "conversation": "Parlons de vos hobbies en français. Que faites-vous pendant votre temps libre?",
        "grammar": "Pratiquons les temps verbaux. Conjuguez le verbe 'être' au présent.",
        "correction": "C'est presque correct! La bonne prononciation est..."
    },
    "advanced": {
        "discussion": "Discutons d'un sujet complexe. Que pensez-vous de la culture française?",
        "nuance": "Explorons les nuances de cette expression française.",
        "fluency": "Votre français s'améliore! Continuons avec des phrases plus complexes."
    }
}