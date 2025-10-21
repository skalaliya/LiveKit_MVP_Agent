#!/bin/bash
# Wrapper script to launch French Tutor UI with proper Qt plugin path

export PYTHONPATH=src
export QT_QPA_PLATFORM_PLUGIN_PATH="/Users/skalaliya/Documents/LiveKit_MVP_Agent/.venv/lib/python3.11/site-packages/PySide6/Qt/plugins"

cd "$(dirname "$0")"
.venv/bin/python -m livekit_mvp_agent.ui.app_ui
