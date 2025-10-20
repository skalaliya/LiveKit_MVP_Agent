#!/bin/bash
# Bootstrap script for livekit_mvp_agent
# This script installs dependencies, downloads models, and sets up voices

set -e

echo "🚀 Bootstrapping LiveKit MVP Agent..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    print_error "uv is not installed. Please install it first:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install dependencies
print_status "Installing Python dependencies..."
uv sync --all-extras

# Check if Docker is running
if ! docker info &> /dev/null; then
    print_warning "Docker is not running. Please start Docker and run 'make start-ollama' manually."
else
    # Start Ollama
    print_status "Starting Ollama via Docker Compose..."
    docker compose up -d ollama 2>/dev/null || docker compose --profile cpu up -d ollama-cpu

    # Wait for Ollama to be ready
    print_status "Waiting for Ollama to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/version > /dev/null; then
            print_status "Ollama is ready!"
            break
        fi
        sleep 1
        if [ $i -eq 30 ]; then
            print_warning "Ollama may not be ready yet. You can check with: curl http://localhost:11434/api/version"
        fi
    done

    # Pull default LLM model
    print_status "Pulling default LLM model (this may take a while)..."
    LLM_MODEL=${LLM_MODEL:-"llama3.1:8b-instruct-q4_K_M"}
    docker compose exec ollama ollama pull "$LLM_MODEL" || print_warning "Failed to pull model $LLM_MODEL. You can try manually later."
fi

# Create necessary directories
print_status "Creating directories..."
mkdir -p ~/.local/share/voices
mkdir -p logs

# Setup voice configuration
print_status "Setting up voice configuration..."
VOICES_DIR="$HOME/.local/share/voices"

# Create voices.yaml with default configuration
cat > config/voices.yaml << EOF
# Voice configuration for TTS systems
voices:
  kokoro:
    en-US-kokoro:
      path: "${VOICES_DIR}/kokoro/en-US.wav"
      language: "en"
      gender: "neutral"
    fr-FR-kokoro:
      path: "${VOICES_DIR}/kokoro/fr-FR.wav"
      language: "fr"
      gender: "neutral"
  
  piper:
    en-US-lessac-medium:
      path: "${VOICES_DIR}/piper/en_US-lessac-medium.onnx"
      language: "en"
      gender: "male"
    fr-FR-siwis-medium:
      path: "${VOICES_DIR}/piper/fr_FR-siwis-medium.onnx"
      language: "fr"
      gender: "female"

# Default voice selection
default_voices:
  en: "en-US-kokoro"
  fr: "fr-FR-kokoro"
EOF

# Download Whisper model (will be cached)
print_status "Pre-caching Whisper model..."
uv run python -c "
import faster_whisper
try:
    model = faster_whisper.WhisperModel('medium', device='cpu', compute_type='int8')
    print('✅ Whisper model cached successfully')
except Exception as e:
    print(f'⚠️  Whisper model download failed: {e}')
"

# Copy example config if settings.toml doesn't exist
if [ ! -f config/settings.toml ]; then
    print_status "Creating default settings.toml..."
    cp config/settings.example.toml config/settings.toml
fi

# TODO: Download TTS voices (optional)
print_status "TTS Voice setup:"
echo "  - Kokoro TTS: Install manually if desired (pip install kokoro-tts)"
echo "  - Piper TTS: Install manually if desired (pip install piper-tts)"
echo "  - NoOp TTS: Available as fallback (console output)"

print_status "Bootstrap complete! 🎉"
echo ""
echo "Next steps:"
echo "1. Copy and edit environment: cp .env.example .env"
echo "2. Configure LiveKit credentials in .env"
echo "3. Run the agent: make run"
echo "4. Test with: scripts/verify.sh"