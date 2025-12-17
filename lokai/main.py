"""
locAI - Main Entry Point
"""

import sys
import os
from pathlib import Path

# Set Hugging Face cache environment variables BEFORE importing anything
# For image models, use Q: drive if available
# DO NOT TOUCH HF_HUB_CACHE - let it use default location where voice files are
if os.path.exists("Q:\\"):
    hf_cache = "Q:\\huggingface_cache"
    os.environ.setdefault("DIFFUSERS_CACHE", os.path.join(hf_cache, "diffusers"))
    os.environ.setdefault("HF_DIFFUSERS_CACHE", os.path.join(hf_cache, "diffusers"))

# Add parent directory to path so we can import lokai
# This allows running from both the lokai/ directory and parent directory
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from PySide6.QtWidgets import QApplication
from lokai.ui.main_window import MainWindow
from lokai.ui.setup_wizard import SetupWizard
from lokai.core.config_manager import ConfigManager


def main():
    """Main entry point for locAI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("locAI")
    app.setApplicationVersion("1.0.0")

    # Load configuration
    config_manager = ConfigManager()

    # Show setup wizard on first run
    if config_manager.is_first_run():
        wizard = SetupWizard(config_manager)
        if wizard.exec():
            # User completed setup
            pass
        else:
            # User cancelled, exit
            sys.exit(0)

    # Create and show main window
    window = MainWindow(config_manager)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
