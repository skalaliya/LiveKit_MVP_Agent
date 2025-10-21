#!/usr/bin/env python3
"""
Direct launcher for French Tutor UI
Bypasses module import issues
"""

import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Set Qt plugin path before importing
if sys.platform == "darwin":
    venv_path = project_root / ".venv" / "lib" / "python3.11" / "site-packages"
    qt_plugins = venv_path / "PySide6" / "Qt" / "plugins"
    if qt_plugins.exists():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(qt_plugins)

# Now import and run
from livekit_mvp_agent.ui.app_ui import main

if __name__ == "__main__":
    main()
