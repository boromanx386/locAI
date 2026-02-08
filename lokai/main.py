"""
locAI - Main Entry Point
"""

import sys
import os
from pathlib import Path

# Add parent directory to path so we can import lokai (before HF env so we can use paths)
# This allows running from both the lokai/ directory and parent directory
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from lokai.core.paths import default_hf_cache_root

# Set Hugging Face cache BEFORE any huggingface imports. LOCAI_HF_CACHE overrides; else default (e.g. Q:\ if exists).
hf_cache = os.environ.get("LOCAI_HF_CACHE") or default_hf_cache_root()
if hf_cache:
    os.environ["HF_HOME"] = hf_cache
    os.environ["HF_HUB_CACHE"] = hf_cache
    os.environ["TRANSFORMERS_CACHE"] = hf_cache
    os.environ["HF_DATASETS_CACHE"] = hf_cache
    os.environ["DIFFUSERS_CACHE"] = os.path.join(hf_cache, "diffusers")
    os.environ["HF_DIFFUSERS_CACHE"] = os.path.join(hf_cache, "diffusers")
    print(f"[MAIN] Hugging Face cache: {hf_cache}")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "300")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

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
