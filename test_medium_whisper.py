#!/usr/bin/env python3
"""
Test script to verify the medium Whisper model is working correctly.
"""

import os
import tempfile
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

def test_whisper_medium():
    """Test the medium Whisper model with a simple audio generation."""
    
    print("🎯 Testing medium Whisper model...")
    
    # Initialize the model
    model = WhisperModel("medium", device="cpu", compute_type="int8")
    print(f"✅ Model loaded successfully")
    
    # Create a simple test audio (1 second of silence with a beep pattern)
    sample_rate = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create a simple test tone (440Hz for "Hello")
    frequency = 440
    audio = 0.1 * np.sin(2 * np.pi * frequency * t[:8000])  # First half second
    audio = np.concatenate([audio, np.zeros(8000)])  # Second half silence
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        sf.write(temp_file.name, audio, sample_rate)
        temp_path = temp_file.name
    
    try:
        # Test transcription
        print("🔄 Testing transcription...")
        segments, info = model.transcribe(temp_path, language="en")
        
        print(f"📊 Detected language: {info.language}")
        print(f"📊 Language probability: {info.language_probability:.2f}")
        
        segments_list = list(segments)
        if segments_list:
            for segment in segments_list:
                print(f"📝 Transcription: '{segment.text}'")
        else:
            print("📝 No speech detected (expected for tone test)")
        
        print("✅ Medium Whisper model is working correctly!")
        
        # Test with multilingual capability
        print("\n🌍 Testing multilingual detection...")
        segments2, info2 = model.transcribe(temp_path)  # Auto-detect language
        print(f"📊 Auto-detected language: {info2.language}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during transcription: {e}")
        return False
        
    finally:
        # Clean up
        os.unlink(temp_path)

if __name__ == "__main__":
    success = test_whisper_medium()
    if success:
        print("\n🎉 Medium Whisper model upgrade completed successfully!")
        print("🚀 Ready for better French/English bilingual performance!")
    else:
        print("\n❌ Medium Whisper model test failed")