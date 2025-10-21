# 🚀 French Tutor - Quick Start Guide

## ⚡ **Get Started in 3 Minutes**

### **1. Check Prerequisites**
```bash
# Verify Python 3.11+
python --version

# Verify dependencies installed
cd /Users/skalaliya/Documents/LiveKit_MVP_Agent
uv sync
```

### **2. Ensure Services Running**
```bash
# Start Ollama (for AI responses)
ollama serve

# In another terminal, verify model is available
ollama list  # Should show llama3.2:3b
```

### **3. Launch French Tutor**
```bash
make ui
```

That's it! The UI will open and you can start practicing French. 🇫🇷

---

## 🎯 **First Conversation**

1. Click the big **🎤 TALK** button
2. Say: "Hello, I want to learn French"
3. The AI coach will respond in French with teaching guidance
4. Try the lesson tools: 🔁 Répète, 🐌 Slower, 💡 Explain

---

## 🔧 **If Something's Not Working**

### **No AI responses?**
```bash
# Ensure Ollama is running
ollama serve

# Pull model if missing
ollama pull llama3.2:3b
```

### **No audio input?**
- Go to Settings (⚙️ button)
- Select your microphone from dropdown
- Watch the volume meter - should move when you speak

### **No TTS audio?**
- Check your `.env` file has:
```properties
ELEVENLABS_API_KEY=sk_your_key_here
ELEVENLABS_TTS_MODEL=eleven_flash_v2_5
TTS_PRIMARY=elevenlabs
```

---

## 📚 **Learn More**

- **Full guide**: See `FRENCH_TUTOR.md`
- **All commands**: See `COMMANDS.md`
- **Implementation status**: See `IMPLEMENTATION_STATUS.md`

---

## 🎓 **Try These Commands**

While talking with the coach, try:

- "Répète" - Repeat last sentence
- "Plus lentement" - Speak slower
- "Explique" - Explain grammar
- "Donne-moi un quiz" - Get a quiz
- "Translate to English" - Show translation

---

## 🆘 **Get Help**

**Issue:** UI won't launch
- Check: `uv sync` completed without errors
- Try: `make ui-debug` for detailed logs

**Issue:** High latency
- Enable streaming TTS (default)
- Close other CPU-intensive apps
- Use smaller model: llama3.2:3b instead of llama3.1:8b

**Issue:** Poor French recognition
- Whisper medium model is installed (default)
- Speak clearly and at normal pace
- Adjust VAD threshold in Settings if needed

---

**Bon courage ! 🇫🇷✨**
