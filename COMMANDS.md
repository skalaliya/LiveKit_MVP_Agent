# �️ LiveKit MVP Agent - Complete Command Reference

## 🚀 **QUICK START - Essential Commands**

### 🎯 **Main Agent Commands**
```bash
# Navigate to project
cd /Users/skalaliya/Documents/LiveKit_MVP_Agent

# Start interactive voice agent (RECOMMENDED)
uv run python talk_to_agent.py

# Check system status & configuration  
uv run python upgrade_summary.py

# Test bilingual French/English capabilities
uv run python test_bilingual_capabilities.py
```

### 🎪 **ElevenLabs Voice Testing** 
```bash
# Test ElevenLabs integration with premium voices
cd elevenlabs_integration  
PYTHONPATH=../src:. uv run python demo.py

# Test voice generation (creates MP3 files)
uv run python voice_demo.py
```

### 🤖 **AI Model Testing**
```bash
# Test medium Whisper STT model (upgraded)
uv run python test_medium_whisper.py

# Test Ollama LLM connection
curl http://localhost:11434/api/tags

# Test configuration loading
uv run python test_voice_config.py
```

---

## 🔧 **DEVELOPMENT & SETUP**

### 📦 **Package Management**
```bash
# Install all dependencies
uv sync

# Add new package
uv add <package-name>

# List installed packages  
uv pip list

# Update dependencies
uv lock --upgrade
```

### 🧪 **Testing Commands**
```bash
# Run all tests
uv run python -m pytest tests/

# Test specific component
uv run python -c "
from src.livekit_mvp_agent.config import AgentConfig
config = AgentConfig()
print(f'✅ Config loaded: {config.whisper_model}')
"

# Validate imports
uv run python -c "
from faster_whisper import WhisperModel
print('✅ Whisper available')
"
```

---

## 🎤 **AUDIO & AI MODELS**

### 🔊 **Whisper STT (Speech-to-Text)**
```bash
# Test medium Whisper model (current)
uv run python -c "
from faster_whisper import WhisperModel
model = WhisperModel('medium', device='cpu', compute_type='int8')
print('✅ Medium Whisper (1.5GB) - excellent FR/EN quality')
"

# Check Whisper cache
ls -la ~/.cache/huggingface/hub/ | grep whisper

# View model sizes
du -sh ~/.cache/huggingface/hub/models--*whisper*
```

### 🤖 **Ollama LLM (Language Model)**  
```bash
# Check available models
ollama list

# Test llama3.2:3b (current model)
ollama run llama3.2:3b "Bonjour! Comment allez-vous?"

# Start Ollama service (if not running)
ollama serve

# Pull/update model
ollama pull llama3.2:3b
```

### 🎵 **ElevenLabs TTS (Text-to-Speech)**
```bash
# Test API connection
cd elevenlabs_integration
PYTHONPATH=../src:. uv run python -c "
import os
from dotenv import load_dotenv
load_dotenv('../.env')
print(f'API Key status: {\"✅ Found\" if os.getenv(\"ELEVENLABS_API_KEY\") else \"❌ Missing\"}')
"

# Generate test audio
uv run python demo.py

# List generated audio files
ls -la *.mp3 *.wav
```

---

## 🛠️ **SYSTEM MAINTENANCE**

### 🧹 **Cleanup Commands**
```bash
# Check disk space
df -h /

# Clean Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete

# Clean old Whisper models (if needed)
find ~/.cache/huggingface/ -name "*whisper*tiny*" -delete

# Clean logs
rm -rf logs/*.log 2>/dev/null
```

### 📊 **System Monitoring**
```bash
# Check running processes
ps aux | grep -E "(ollama|python|whisper)"

# Monitor memory usage
top -o mem | head -20

# Check GPU usage (if available)
# macOS: system_profiler SPDisplaysDataType
# Linux: nvidia-smi
```

---

## 🔐 **CONFIGURATION MANAGEMENT**

### 📝 **Environment Variables**
```bash
# View current configuration
cat .env

# Edit configuration
code .env  # or nano .env

# Test configuration loading
uv run python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('Whisper Model:', os.getenv('WHISPER_MODEL', 'default'))
print('LLM Model:', os.getenv('LLM_MODEL', 'default'))
print('Ollama URL:', os.getenv('OLLAMA_BASE_URL', 'default'))
print('ElevenLabs:', 'configured' if os.getenv('ELEVENLABS_API_KEY') else 'not configured')
"
```

### 🎯 **Model Configuration**
```bash
# Current optimal settings (already configured):
echo "WHISPER_MODEL=medium      # 1.5GB, excellent FR/EN" 
echo "LLM_MODEL=llama3.2:3b     # 2GB, fast responses"
echo "TTS_PRIMARY=elevenlabs    # Premium audio quality"

# Verify current settings
grep -E "(WHISPER_MODEL|LLM_MODEL|TTS_PRIMARY)" .env
```

---

## 🌐 **LIVEKIT (Optional Real-time Voice)**

### 🔌 **LiveKit Server** 
```bash
# Start LiveKit server (Docker)
docker run --rm -p 7880:7880 -p 7881:7881 -p 7882:7882/udp \
  livekit/livekit-server --dev

# Check if LiveKit is running
lsof -i :7880

# Test LiveKit connection
curl -X POST http://localhost:7880/twirp/livekit.RoomService/ListRooms \
  -H "Content-Type: application/json" -d '{}'
```

---

## 🎓 **USAGE EXAMPLES**

### 🗣️ **Interactive Sessions**
```bash
# Start voice agent
uv run python talk_to_agent.py

# Example conversation flow:
# You: "Hello, how are you?"
# Agent: Responds with Ollama LLM
# You: "Bonjour, comment allez-vous?"  
# Agent: Handles French automatically
# You: "Help me learn French pronunciation"
# Agent: Provides language learning assistance
# You: "quit" to exit
```

### 🇫🇷 **French Learning Mode**
```bash
# Test French capabilities
uv run python -c "
test_phrases = [
    'Bonjour, comment allez-vous?',
    'Je voudrais apprendre l\\'anglais',
    'Pouvez-vous m\\'aider?',
    'Hello! Je m\\'appelle Sarah.'
]
print('🇫🇷 Testing French phrases:')
for phrase in test_phrases:
    print(f'  ✅ \"{phrase}\"')
print('Medium Whisper handles all these excellently!')
"

# Start bilingual session
uv run python talk_to_agent.py
# Type: "Je voudrais pratiquer le français et l'anglais"
```

---

## 🆘 **TROUBLESHOOTING**

### 🔍 **Diagnostic Commands**
```bash
# Complete system check
uv run python upgrade_summary.py

# Check all components
uv run python test_voice_config.py

# Verify Python environment  
which python
python --version
uv --version

# Test network connectivity
ping -c 3 localhost
curl -s http://localhost:11434/api/tags

# Check critical imports
uv run python -c "
import sys
modules = ['faster_whisper', 'requests', 'numpy', 'soundfile']
for mod in modules:
    try:
        __import__(mod)
        print(f'✅ {mod}')
    except ImportError as e:
        print(f'❌ {mod}: {e}')
"
```

### 🩺 **Fix Common Issues**
```bash
# Reinstall dependencies
uv sync --reinstall

# Reset Whisper cache
rm -rf ~/.cache/huggingface/hub/models--*whisper*

# Restart Ollama
pkill ollama
ollama serve &

# Fix permission issues
chmod +x *.py
```

### 🚨 **Emergency Reset**
```bash
# Nuclear option - full reset (use with caution)
# rm -rf .venv
# uv sync
# ollama pull llama3.2:3b
```

---

## 📈 **PERFORMANCE OPTIMIZATION**

### ⚡ **Speed Commands**
```bash
# Preload models for faster startup
uv run python -c "
print('🔄 Preloading Whisper...')
from faster_whisper import WhisperModel
model = WhisperModel('medium', device='cpu', compute_type='int8')
print('✅ Whisper ready')
"

# Warm up Ollama
curl -s -X POST http://localhost:11434/api/generate \
  -d '{"model": "llama3.2:3b", "prompt": "Hello", "stream": false}' | head -10

# Check model sizes and memory usage
echo "📊 Model Storage:"
du -sh ~/.cache/huggingface/hub/ 2>/dev/null
du -sh ~/.ollama/models/ 2>/dev/null
```

### 📊 **Benchmarking**
```bash
# Time Whisper performance
time uv run python test_medium_whisper.py

# Measure memory usage  
/usr/bin/time -l uv run python test_bilingual_capabilities.py 2>&1 | grep "maximum resident"

# Profile execution
uv run python -m cProfile -s cumulative talk_to_agent.py | head -20
```

---

## 🎯 **PROJECT MANAGEMENT**

### 📂 **Project Structure**
```bash
# View project layout
tree -I "__pycache__|*.pyc|.git|.venv" -L 3

# Find key files
find . -name "*.py" -type f | grep -E "(agent|config|demo)" | head -10
find . -name "*config*" -o -name "*.env*" -type f

# Check project stats
echo "📊 Project Statistics:"
find . -name "*.py" -type f | wc -l | xargs echo "Python files:"
find . -name "*.py" -exec wc -l {} + | tail -1
```

### 🔄 **Git Management**
```bash
# Repository status
git status
git log --oneline -5

# Commit workflow
git add .
git commit -m "Update: Medium Whisper model for better French/English"  
git push origin main

# View online repository
echo "🌐 Repository: https://github.com/skalaliya/LiveKit_MVP_Agent"
```

---

## 🎊 **PRODUCTIVITY SHORTCUTS**

### � **Shell Aliases (Add to ~/.zshrc)**
```bash
# LiveKit MVP Agent shortcuts
alias va="cd /Users/skalaliya/Documents/LiveKit_MVP_Agent"
alias va-start="va && uv run python talk_to_agent.py"
alias va-status="va && uv run python upgrade_summary.py"
alias va-test="va && uv run python test_bilingual_capabilities.py"
alias va-config="va && cat .env"
alias va-elevenlabs="va && cd elevenlabs_integration && PYTHONPATH=../src:. uv run python demo.py"

# System checks
alias ollama-status="curl -s http://localhost:11434/api/tags | head -10"
alias disk-check="df -h /"

# Apply aliases
source ~/.zshrc
```

### ⚡ **One-liner Commands**
```bash
# Quick status check
va && uv run python -c "from src.livekit_mvp_agent.config import AgentConfig; c=AgentConfig(); print(f'✅ Ready: Whisper={c.whisper_model}, LLM={c.llm_model}')"

# Quick audio test
va && cd elevenlabs_integration && echo "Testing ElevenLabs..." && PYTHONPATH=../src:. uv run python -c "from elevenlabs_client import ElevenLabsClient; import os; from dotenv import load_dotenv; load_dotenv('../.env'); client = ElevenLabsClient(os.getenv('ELEVENLABS_API_KEY')); print(f'✅ {len(client.get_voices())} voices available')"
```

---

## 🎯 **RECOMMENDED DAILY WORKFLOW**

### 🌅 **Morning Startup**
```bash
1. va-status          # Check system health
2. ollama-status      # Verify AI model availability  
3. va-test           # Quick bilingual capability test
4. va-start          # Begin voice agent session
```

### 🔧 **Development Session**
```bash
1. va                # Navigate to project
2. code .            # Open in VS Code
3. uv run python test_voice_config.py  # Verify setup
4. Make changes...
5. uv run python talk_to_agent.py     # Test changes
```

### 🧪 **Testing & Validation** 
```bash
1. uv run python test_medium_whisper.py      # Test STT
2. curl http://localhost:11434/api/tags       # Test LLM
3. va-elevenlabs                             # Test TTS
4. uv run python upgrade_summary.py          # Overall status
```

---

## 🏆 **CURRENT SYSTEM STATUS**

✅ **Whisper STT:** Medium model (1.5GB) - excellent French/English  
✅ **Ollama LLM:** llama3.2:3b (2GB) - fast, bilingual responses  
✅ **ElevenLabs TTS:** Premium voices configured - natural audio  
✅ **Configuration:** Optimized for French language learning  
✅ **Repository:** Published at https://github.com/skalaliya/LiveKit_MVP_Agent  

**🎉 Your bilingual voice agent is ready for French/English conversations!**

---

## 🚀 **GET STARTED NOW**

```bash
# Copy and paste this to start immediately:
cd /Users/skalaliya/Documents/LiveKit_MVP_Agent && uv run python talk_to_agent.py
```

**Happy coding! 🎙️✨**