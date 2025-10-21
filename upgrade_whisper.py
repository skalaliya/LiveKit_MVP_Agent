#!/usr/bin/env python3
"""
🎤 Download Whisper Medium Model
Perfect for bilingual EN/FR with great quality
"""

import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def download_medium_whisper():
    """Download and test Whisper medium model."""
    
    print("🎤 Upgrading to Whisper Medium Model")
    print("=" * 50)
    print("Model: medium (~769MB)")
    print("Quality: ⭐⭐⭐⭐⭐ (Excellent)")
    print("Speed: ~2-3× realtime") 
    print("Languages: 99 supported (optimized for EN/FR)")
    print("Best balance for bilingual conversations!")
    print("=" * 50)
    
    try:
        from faster_whisper import WhisperModel
        
        print("📥 Downloading Whisper medium model...")
        print("   Size: ~769MB")
        print("   This may take a few minutes...")
        
        # Initialize the model (this triggers download)
        model = WhisperModel(
            "medium",
            device="auto", 
            compute_type="int8"
        )
        
        print("✅ Model downloaded and loaded successfully!")
        
        # Get model info
        print(f"✅ Model: medium")
        print(f"✅ Device: {model.device}")
        print(f"✅ Compute type: {model.compute_type}")
        
        print("\n🎯 Medium Model Features:")
        print("   • Excellent accuracy for EN/FR")
        print("   • 2-3× realtime processing")
        print("   • Great balance of speed/quality")
        print("   • Perfect for voice conversations")
        
        print("\n🎉 Ready for premium voice agent experience!")
        return True
        
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        return False

def check_disk_space():
    """Check if we have enough disk space."""
    import shutil
    
    free_bytes = shutil.disk_usage('/').free
    free_gb = free_bytes / (1024**3)
    
    print(f"💾 Available disk space: {free_gb:.1f} GB")
    
    if free_gb < 1.0:
        print("⚠️ Warning: Less than 1GB free space")
        print("   Medium model needs ~769MB")
        return False
    else:
        print("✅ Sufficient space for medium model")
        return True

def main():
    """Run the upgrade."""
    
    print("🚀 Whisper Model Upgrade")
    print("From: tiny (39MB) → medium (769MB)")
    print()
    
    # Check disk space
    if not check_disk_space():
        print("❌ Insufficient disk space. Please free up space first.")
        return
    
    # Download model
    success = download_medium_whisper()
    
    if success:
        print("\n" + "="*60)
        print("🎉 SUCCESS! Whisper Medium Model Ready!")
        print("="*60)
        print("📋 Next steps:")
        print("1. 💬 Test improved chat: make talk")
        print("2. 🎙️ Try voice agent: make run")
        print("3. 🧪 Test audio quality: make test-elevenlabs")
        print("4. 🎪 Voice demos: cd elevenlabs_integration && uv run python voice_demo.py")
        print("\n🎤 Your voice agent now has excellent STT quality!")
        
        # Clean up this script
        try:
            os.remove(__file__)
            print("🧹 Cleanup: Removed download script")
        except:
            pass
    else:
        print("\n❌ Download failed. You can try again or use the tiny model.")

if __name__ == "__main__":
    main()