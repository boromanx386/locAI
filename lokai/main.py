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
from lokai.core.config_manager import ConfigManager


def apply_hf_cache_env(hf_cache: str | None) -> None:
    """Set Hugging Face cache env vars before any HF imports. Call with path from config or default."""
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


def get_hf_cache_path(config_manager: ConfigManager) -> str | None:
    """Resolve HF cache path: env LOCAI_HF_CACHE, then config models.storage_path, then default suggestion."""
    path = os.environ.get("LOCAI_HF_CACHE")
    if path:
        return path
    path = config_manager.get("models.storage_path")
    if path:
        return path
    return default_hf_cache_root()


def main():
    """Main entry point for locAI application."""
    # Load config first (no Hugging Face imports yet)
    config_manager = ConfigManager()

    # HF cache: on first run we don't have a path yet; set default or leave to wizard
    if not config_manager.is_first_run():
        hf_cache = get_hf_cache_path(config_manager)
        apply_hf_cache_env(hf_cache)
    else:
        # Optional: set a fallback so imports don't break; wizard will save user choice and we re-apply below
        apply_hf_cache_env(os.environ.get("LOCAI_HF_CACHE") or default_hf_cache_root())

    from PySide6.QtWidgets import QApplication
    from lokai.ui.main_window import MainWindow
    from lokai.ui.setup_wizard import SetupWizard

    app = QApplication(sys.argv)
    app.setApplicationName("locAI")
    app.setApplicationVersion("1.0.0")

    # Show setup wizard on first run
    if config_manager.is_first_run():
        wizard = SetupWizard(config_manager)
        if wizard.exec():
            # Config is saved with user's Hugging Face folder. Restart so HF env
            # is set from config before any HF/TTS imports (e.g. Kokoro).
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            sys.exit(0)

    # Create and show main window
    window = MainWindow(config_manager)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
