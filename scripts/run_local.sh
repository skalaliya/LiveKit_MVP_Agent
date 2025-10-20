#!/bin/bash
# Launch script for LiveKit MVP Agent
# Starts Ollama and the voice agent

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning "No .env file found. Copying from .env.example..."
    cp .env.example .env
    print_warning "Please edit .env with your LiveKit credentials before running."
fi

# Start Ollama if not running
print_status "Checking Ollama status..."
if ! curl -s http://localhost:11434/api/version > /dev/null; then
    print_status "Starting Ollama..."
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    # Try GPU first, fallback to CPU
    docker compose up -d ollama 2>/dev/null || docker compose --profile cpu up -d ollama-cpu
    
    # Wait for Ollama
    print_status "Waiting for Ollama to be ready..."
    for i in {1..60}; do
        if curl -s http://localhost:11434/api/version > /dev/null; then
            print_status "Ollama is ready!"
            break
        fi
        sleep 1
        if [ $i -eq 60 ]; then
            print_error "Ollama failed to start within 60 seconds."
            exit 1
        fi
    done
else
    print_status "Ollama is already running."
fi

# Check if required model is available
LLM_MODEL=${LLM_MODEL:-"llama3.1:8b-instruct-q4_K_M"}
print_status "Checking if model $LLM_MODEL is available..."

if ! docker compose exec ollama ollama list | grep -q "$LLM_MODEL"; then
    print_status "Model $LLM_MODEL not found. Pulling it now..."
    docker compose exec ollama ollama pull "$LLM_MODEL"
fi

# Start the agent
print_status "Starting LiveKit MVP Agent..."
echo "Press Ctrl+C to stop the agent"
echo "----------------------------------------"

# Load environment and start
export $(cat .env | grep -v '^#' | xargs)
uv run -m livekit_mvp_agent.app "$@"