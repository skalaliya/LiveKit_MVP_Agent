# 🇫🇷 French Tutor Voice App - User Guide

## 🎯 **Learn French with Interactive Voice Lessons**

The French Tutor is a production-grade desktop application that provides **real-time French conversation practice** with AI-powered coaching. Speak naturally, get instant feedback, and improve your French through immersive voice interactions.

---

## 🏗️ **Architecture & Flow**

```
🎤 Microphone → 🗣️ VAD (Silero) → 📝 STT (Whisper Medium) → 🧠 LLM (Ollama) → 🔊 Streaming TTS (ElevenLabs) → 🎧 Speakers
     ↓                ↓                    ↓                      ↓                         ↓
  Audio In      Speech Detection    Text (FR/EN)          French Response           Audio Stream (MP3→PCM)
  16kHz mono    300ms silence       Auto-detect           Teaching prompt           TTFB < 350ms
```

### **Key Features**
- **🎤 Voice Input**: Push-to-talk or auto-VAD modes
- **🗣️ Speech Recognition**: Whisper `medium` model with bilingual FR/EN support
- **🧠 AI Tutor**: Ollama LLM with specialized French teaching prompt
- **🔊 Natural Speech**: ElevenLabs streaming TTS for low-latency responses
- **⚡ Barge-in**: Stop AI mid-sentence by speaking (< 200ms latency)
- **📊 Real-time Feedback**: Volume meters, VAD status, processing indicators

---

## 🚀 **Getting Started**

### **1. Launch the UI**
```bash
make ui
```

### **2. Configure Your Setup**
- **Input**: Select your microphone
- **Output**: Choose your speakers/headphones  
- **Mode**: Auto-VAD (hands-free) or Push-to-Talk (space bar)
- **Voice**: Rachel (EN), Charlotte (FR), Antoine (FR)

### **3. Start Learning**
1. Click the big **🎤 TALK** button (or press Space)
2. Speak in English or French
3. AI coach responds in French with teaching guidance
4. Use lesson tools for specific practice modes

---

## 🎓 **How It Teaches**

### **Teaching Philosophy**
The AI coach follows these principles:

✅ **French-first responses** - Always replies in French by default  
✅ **Short, clear turns** - 1-3 sentences, then asks follow-up questions  
✅ **Gentle corrections** - Shows correct form, explains briefly  
✅ **Level-appropriate** - Matches vocabulary to A1-B2 CEFR levels  
✅ **Active practice** - Dialogue over monologues, micro-exercises  
✅ **Pronunciation help** - IPA transcriptions for new words  

### **Example Interaction**
```
👤 You: "Hello, I want to learn French."

🇫🇷 Coach: "Bonjour ! Je suis heureux de t'aider. Comment t'appelles-tu ?"
          (Hello! I'm happy to help you. What's your name?)

👤 You: "My name is Sarah."

🇫🇷 Coach: "Très bien ! En français, on dit : 'Je m'appelle Sarah.' /ʒə mapɛl saʁa/
          Répète après moi : 'Je m'appelle Sarah.'"
```

---

## 🎛️ **Lesson Tools**

Quick-access buttons for common practice modes:

| Button | Command | What It Does |
|--------|---------|--------------|
| 🔁 **Répète** | "répète" | Coach repeats last sentence |
| 🐌 **Plus lentement** | "plus lentement" | Slower pronunciation |
| 💡 **Explique** | "explique" | Explains grammar/vocabulary |
| 📝 **Quiz me** | "donne-moi un quiz" | 5-question quiz on topic |
| 🌍 **Translate** | "translate to English" | Shows English translation |

---

## ⚡ **Performance & Latency**

### **Target Metrics**
- **TTFB (Time to First Byte)**: < 350ms
- **End-to-end latency**: < 1.2s typical
- **Barge-in response**: < 200ms

### **Optimization Tips**
1. **Enable Streaming TTS** (default): Audio starts playing before text is fully generated
2. **Use Whisper Medium**: Best balance of accuracy vs. speed for FR/EN
3. **Reduce chunk size**: 320 samples (20ms) for lower latency
4. **Enable barge-in**: Stop AI immediately when you speak
5. **Local LLM**: Ollama on localhost avoids network delays

### **Latency Budget Breakdown**
```
User speaks → 20ms (audio chunk) → VAD detects → 50ms (processing)
→ STT transcribes → 150-300ms (Whisper medium)
→ LLM generates → 300-600ms (Ollama llama3.2:3b)
→ TTS streams → 100-200ms TTFB + incremental playback
= Total: 620-1170ms end-to-end
```

---

## ⚙️ **Configuration**

### **Audio Settings**
- **Sample Rate**: 16kHz (optimal for Whisper)
- **Channels**: Mono (1 channel)
- **Chunk Size**: 320 samples (20ms)
- **VAD Threshold**: 0.3-0.7 (adjustable)

### **Model Settings**
```properties
# .env configuration
WHISPER_MODEL=medium          # STT: best FR/EN quality
LLM_MODEL=llama3.2:3b         # Fast, good French support
TTS_PRIMARY=elevenlabs        # Premium streaming audio
ELEVENLABS_TTS_MODEL=eleven_flash_v2_5  # Low latency
ELEVENLABS_STREAMING=true     # Enable WebSocket streaming

# Tutor settings
TEACH_MODE=french
TARGET_LEVEL=A2               # A1, A2, B1, or B2
SPEECH_RATE=normal            # slow, normal, fast
```

### **Device Selection**
- **Input**: Click ⚙️ Settings → Audio → Select microphone
- **Output**: Choose speakers or headphones
- **Test**: Watch volume meters to verify audio input

---

## 🎹 **Keyboard Shortcuts**

| Key | Action |
|-----|--------|
| **Space** | Hold to talk (Push-to-Talk mode) |
| **⌘/Ctrl+L** | Clear transcripts |
| **⌘/Ctrl+S** | Save session to file |
| **Esc** | Stop current playback |

---

## 🔄 **Modes**

### **Auto-VAD** (Default)
- **How it works**: AI detects when you start/stop speaking
- **Best for**: Natural conversation flow
- **Settings**: Adjust VAD threshold if too sensitive/insensitive

### **Push-to-Talk**
- **How it works**: Hold Space or click TALK button while speaking
- **Best for**: Noisy environments, precise control
- **Tip**: Release button to end turn

---

## 🆚 **Fallback Strategy**

The app gracefully handles missing services:

```
TTS Priority Chain:
1️⃣ ElevenLabs Streaming (WebSocket) → ⚡ Fastest, best quality
2️⃣ ElevenLabs REST (HTTP) → 🔄 Fallback, full audio at once  
3️⃣ Piper (Local TTS) → 🏠 Offline capable, basic quality
4️⃣ NoOp (Log only) → 📝 UI still works, no audio
```

If Ollama isn't running:
- Simple responses mode (no AI coaching)
- UI remains functional for testing

If API keys missing:
- Falls back to local TTS
- Full features available when keys added

---

## 🧪 **Testing Without Audio**

Run headless tests without microphone:

```bash
# Test streaming TTS
uv run pytest tests/test_streaming_tts.py -v

# Test barge-in logic
uv run pytest tests/test_barge_in.py -v

# Test STT loop
uv run pytest tests/test_stt_loop.py -v
```

All tests use mocks and don't require API keys.

---

## 🎨 **UI Overview**

```
┌─────────────────────────────────────────────┐
│  🇫🇷 French Tutor - Mon Coach de Français  │
├─────────────────────────────────────────────┤
│ [🎤 TALK]  [Auto-VAD ✓]  [Input ▓▓▓░░]     │
│ [Status: STT✓ LLM✓ TTS✓]  [⚙️ Settings]     │
├──────────────┬──────────────────────────────┤
│  👤 You      │  🇫🇷 Coach                   │
│  (EN/FR)     │  (French)                    │
│              │                              │
│  Your speech │  Le coach répondra ici...    │
│  appears...  │                              │
│              │                              │
├──────────────┴──────────────────────────────┤
│ [🔁 Répète] [🐌 Slower] [💡 Explain] [📝 Quiz] │
└─────────────────────────────────────────────┘
```

---

## 🐛 **Troubleshooting**

### **No audio input?**
- Check microphone permissions (System Preferences → Security & Privacy)
- Select correct input device in Settings
- Verify volume meter shows activity when you speak

### **No AI responses?**
- Ensure Ollama is running: `ollama serve`
- Check model is installed: `ollama list`
- Pull if needed: `ollama pull llama3.2:3b`

### **TTS not working?**
- Verify ElevenLabs API key in `.env`
- Check key validity: `make test-elevenlabs`
- Falls back to Piper if streaming fails

### **High latency?**
- Enable streaming TTS in settings
- Use smaller LLM (llama3.2:3b vs llama3.1:8b)
- Reduce VAD silence duration (faster turn-taking)
- Check CPU usage (Whisper medium is compute-intensive)

---

## 🌐 **Switch to LiveKit** (Optional)

For multi-user or remote scenarios:

1. **Start LiveKit server:**
```bash
docker run --rm -p 7880:7880 -p 7881:7881 livekit/livekit-server --dev
```

2. **Configure .env:**
```properties
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
```

3. **Run in LiveKit mode:**
```bash
make run  # Instead of make ui
```

This enables WebRTC for remote voice sessions.

---

## 📊 **Session Export**

Save your practice sessions for review:

1. Press **⌘/Ctrl+S** during or after conversation
2. Exports to: `sessions/session_YYYY-MM-DD_HH-MM-SS.md`
3. Includes: Timestamps, full transcripts, corrections

**Example export:**
```markdown
# French Practice Session
Date: 2025-01-21 14:30:00

## Conversation
[14:30:05] You: Bonjour, comment allez-vous?
[14:30:08] Coach: Très bien, merci ! Et toi, comment vas-tu ?

## Corrections
- "vas" vs "allez": informal vs formal
```

---

## 🎯 **Next Steps**

- **Practice daily**: 10-15 minutes for best results
- **Use lesson tools**: Try all 5 tools during practice
- **Export sessions**: Review corrections offline
- **Adjust level**: Start A1, progress to B2
- **Try quiz mode**: Test your knowledge

**Bon apprentissage ! 🇫🇷✨**
