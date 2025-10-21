.PHONY: help setup run clean lint typecheck test fmt start-ollama pull-model stop-ollama webui docker-build docker-up docker-down docker-logs

# Default target
help:
	@echo "Available targets:"
	@echo "  setup          - Install dependencies and initialize project"
	@echo "  run            - Run the voice agent"
	@echo "  clean          - Clean cache and temporary files"
	@echo "  lint           - Run ruff linter"
	@echo "  typecheck      - Run mypy type checker"
	@echo "  test           - Run pytest tests"
	@echo "  fmt            - Format code with ruff"
	@echo "  start-ollama   - Start Ollama via Docker Compose"
	@echo "  pull-model     - Pull LLM model (default or LLM_MODEL env var)"
	@echo "  stop-ollama    - Stop Ollama container"
	@echo "  check-config   - Check .env configuration"
	@echo "  test-elevenlabs - Test ElevenLabs integration"
	@echo "  talk           - Start interactive chat with agent"
	@echo ""
	@echo "WebUI targets:"
	@echo "  webui          - Run WebUI locally (no Docker)"
	@echo "  docker-build   - Build WebUI Docker image"
	@echo "  docker-up      - Start Ollama + WebUI with Docker"
	@echo "  docker-down    - Stop all Docker services"
	@echo "  docker-logs    - View WebUI logs"

# Environment variables
LLM_MODEL ?= llama3.1:8b-instruct-q4_K_M
WHISPER_MODEL ?= medium

# Setup and installation
setup:
	@echo "Setting up livekit_mvp_agent..."
	uv sync --all-extras
	@echo "Setup complete! Run 'make start-ollama && make pull-model' to initialize models."

# Run the application
run:
	@echo "Starting voice agent..."
	PYTHONPATH=src uv run python -m livekit_mvp_agent.app

run-offline:
	@echo "Starting voice agent (offline, no LiveKit)..."
	PYTHONPATH=src uv run python -m livekit_mvp_agent.app --no-livekit

# Development tools
lint:
	@echo "Running ruff linter..."
	uv run ruff check src/ tests/

typecheck:
	@echo "Running mypy type checker..."
	uv run mypy src/ tests/

test:
	@echo "Running tests..."
	uv run pytest tests/ -v

fmt:
	@echo "Formatting code..."
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

# Docker and model management
start-ollama:
	@echo "Starting Ollama via Docker Compose..."
	docker compose up -d ollama
	@echo "Waiting for Ollama to be ready..."
	@timeout 30 bash -c 'until curl -s http://localhost:11434/api/version > /dev/null; do sleep 1; done' || echo "Ollama may not be ready yet"

stop-ollama:
	@echo "Stopping Ollama..."
	docker compose down

pull-model:
	@echo "Pulling model: $(LLM_MODEL)"
	@if ! curl -s http://localhost:11434/api/version > /dev/null; then \
		echo "Error: Ollama is not running. Run 'make start-ollama' first."; \
		exit 1; \
	fi
	docker compose exec ollama ollama pull $(LLM_MODEL)

# Cleanup
clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf dist/
	rm -rf build/
	@echo "Cleanup complete."

# Bootstrap everything
bootstrap: setup start-ollama pull-model
	@echo "Running bootstrap script..."
	./scripts/bootstrap.sh

# Verification
verify:
	@echo "Running verification script..."
	./scripts/verify.sh

# Configuration testing
check-config:
	@echo "Checking configuration..."
	PYTHONPATH=src uv run python check_config.py

test-elevenlabs:
	@echo "Testing ElevenLabs integration..."
	PYTHONPATH=src:elevenlabs_integration uv run python test_elevenlabs_env.py

talk:
	@echo "Starting interactive chat with agent..."
	PYTHONPATH=src uv run python talk_to_agent.py

# French Tutor UI (legacy Qt - use WebUI instead)
ui:
	@echo "⚠️  Note: Qt UI has compatibility issues. Use 'make webui' or 'make docker-up' instead."
	@echo "Starting French Tutor UI..."
	PYTHONPATH=src QT_QPA_PLATFORM_PLUGIN_PATH=/Users/skalaliya/Documents/LiveKit_MVP_Agent/.venv/lib/python3.11/site-packages/PySide6/Qt/plugins uv run -q python -m livekit_mvp_agent.ui.app_ui

ui-debug:
	@echo "Starting French Tutor UI (debug mode)..."
	PYTHONPATH=src QT_QPA_PLATFORM_PLUGIN_PATH=/Users/skalaliya/Documents/LiveKit_MVP_Agent/.venv/lib/python3.11/site-packages/PySide6/Qt/plugins LOG_LEVEL=DEBUG uv run python -m livekit_mvp_agent.ui.app_ui

# French Tutor WebUI (Docker-first, browser-based)
webui:
	@echo "🌐 Starting French Tutor WebUI locally..."
	@echo "Open http://localhost:8000 in your browser"
	PYTHONPATH=src uv run uvicorn livekit_mvp_agent.webui.server:app --host 0.0.0.0 --port 8000 --reload

# Docker targets
docker-build:
	@echo "🐳 Building WebUI Docker image..."
	docker compose build webui

docker-up:
	@echo "🐳 Starting Ollama + WebUI with Docker..."
	docker compose up -d ollama webui
	@echo "⏳ Waiting for services to be ready..."
	@echo "   Ollama: http://localhost:11434"
	@echo "   WebUI:  http://localhost:8000"
	@echo ""
	@echo "💡 Next steps:"
	@echo "   1. Pull LLM: make pull-model LLM=llama3.2:3b"
	@echo "   2. Open: http://localhost:8000"

docker-down:
	@echo "🐳 Stopping all Docker services..."
	docker compose down

docker-logs:
	@echo "📋 Viewing WebUI logs (Ctrl+C to exit)..."
	docker compose logs -f webui

# Pull model with error handling
pull-model:
	@echo "📥 Pulling model: $(LLM_MODEL)"
	@if ! curl -s http://localhost:11434/api/version > /dev/null 2>&1; then \
		echo "❌ Error: Ollama is not running."; \
		echo "   Run 'make docker-up' or 'make start-ollama' first."; \
		exit 1; \
	fi
	@echo "   This may take a few minutes..."
	@curl -X POST http://localhost:11434/api/pull -d '{"name":"$(LLM_MODEL)"}' 2>/dev/null | \
		grep -o '"status":"[^"]*"' | sed 's/"status":"\(.*\)"/\1/' | tail -1 || \
		echo "✅ Model $(LLM_MODEL) pulled successfully"