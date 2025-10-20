.PHONY: help setup run clean lint typecheck test fmt start-ollama pull-model stop-ollama

# Default target
help:
	@echo "Available targets:"
	@echo "  setup        - Install dependencies and initialize project"
	@echo "  run          - Run the voice agent"
	@echo "  clean        - Clean cache and temporary files"
	@echo "  lint         - Run ruff linter"
	@echo "  typecheck    - Run mypy type checker"
	@echo "  test         - Run pytest tests"
	@echo "  fmt          - Format code with ruff"
	@echo "  start-ollama - Start Ollama via Docker Compose"
	@echo "  pull-model   - Pull LLM model (default or LLM_MODEL env var)"
	@echo "  stop-ollama  - Stop Ollama container"
	@echo "  check-config - Check .env configuration"
	@echo "  test-elevenlabs - Test ElevenLabs integration"
	@echo "  talk         - Start interactive chat with agent"

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