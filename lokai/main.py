"""
locAI - Main Entry Point
"""

import sys
import os
from pathlib import Path

# Set Hugging Face cache environment variables BEFORE importing anything
# For all models, use Q: drive if available
# IMPORTANT: These must be set BEFORE any huggingface imports
if os.path.exists("Q:\\"):
    hf_cache = "Q:\\huggingface_cache"
    # Force set (not setdefault) to override any existing values
    os.environ["HF_HOME"] = hf_cache
    os.environ["HF_HUB_CACHE"] = hf_cache
    os.environ["TRANSFORMERS_CACHE"] = hf_cache
    os.environ["HF_DATASETS_CACHE"] = hf_cache
    os.environ["DIFFUSERS_CACHE"] = os.path.join(hf_cache, "diffusers")
    os.environ["HF_DIFFUSERS_CACHE"] = os.path.join(hf_cache, "diffusers")
    # Also set HF_HUB_DISABLE_SYMLINKS_WARNING to suppress warnings
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    print(f"[MAIN] Using Q: drive for Hugging Face cache: {hf_cache}")
    print(f"[MAIN] HF_HUB_CACHE={os.environ.get('HF_HUB_CACHE')}")
    print(f"[MAIN] DIFFUSERS_CACHE={os.environ.get('DIFFUSERS_CACHE')}")

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
