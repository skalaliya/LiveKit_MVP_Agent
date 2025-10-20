# 🎮 Quick Command Reference

## 🚀 **Start Talking to Your Agent!**

### 🎪 **Interactive Voice Demo** (Most Fun!)
```bash
cd elevenlabs_integration
uv run python voice_demo.py
```
**What's happening:** ElevenLabs TTS + Audio generation + Mock conversations
**Perfect for:** Testing voices, generating audio files, exploring TTS

---

### 💬 **Text Chat** (Simplest)
```bash
make talk
```
**What's happening:** Simple text interface + Basic AI responses
**Perfect for:** Quick testing, no audio overhead, lightweight

---

### 🎙️ **Full Voice Agent** (Complete Experience)
```bash
make start-ollama    # Start AI brain (needs Docker)
make run            # Launch voice agent
```
**What's happening:** LiveKit WebRTC + Ollama LLM + Real-time audio
**Perfect for:** Full voice conversations, production experience

---

### 🧪 **Test Audio System**
```bash
make test-elevenlabs
```
**What's happening:** API validation + Audio generation + Config check
**Perfect for:** Verifying setup, testing API keys

---

## 🎵 **Play Generated Audio**
```bash
# Navigate to generated files
cd elevenlabs_integration
ls *.mp3

# Play any audio file
open voice_agent_test.mp3     # Latest test
open conversation_1.mp3       # French demo
open env_test_output.mp3      # Environment test
```

---

## 🛠️ **Setup Commands**
```bash
make help           # 📋 Show all commands
make setup          # 🛠️ Install everything
make clean          # 🧹 Reset/cleanup
```

---

## 🎯 **Recommended Flow**
1. **Start here:** `cd elevenlabs_integration && uv run python voice_demo.py`
2. **Then try:** `make talk` 
3. **Full experience:** `make start-ollama && make run`
4. **Test audio:** `make test-elevenlabs`

**Have fun exploring your voice agent! 🎙️✨**