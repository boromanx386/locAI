"""
Global keyboard shortcuts for locAI.
Allows reading selected text from anywhere in Windows and sending to TTS/Image generator.
"""

import sys
import time
from typing import Optional, Callable

try:
    import keyboard

    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    print("Warning: keyboard library not available. Install with: pip install keyboard")

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QObject, Signal, QThread

    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False


class GlobalShortcutHandler(QObject):
    """Handles global keyboard shortcuts for text selection."""

    text_selected_for_tts = Signal(str)
    text_selected_for_image = Signal(str)

    def __init__(self, parent=None, tts_hotkey: str = "f9", image_hotkey: str = "f10"):
        super().__init__(parent)
        self.tts_callback: Optional[Callable[[str], None]] = None
        self.image_callback: Optional[Callable[[str], None]] = None
        self.enabled = False
        # Hotkeys are configurable (defaults: F9 for TTS, F10 for image)
        self.tts_hotkey = tts_hotkey.lower() if tts_hotkey else "f9"
        self.image_hotkey = image_hotkey.lower() if image_hotkey else "f10"

    def set_callbacks(
        self, tts_callback: Callable[[str], None], image_callback: Callable[[str], None]
    ):
        """Set callbacks for TTS and image generation."""
        self.tts_callback = tts_callback
        self.image_callback = image_callback

    def enable(self):
        """Enable global shortcuts."""
        if not KEYBOARD_AVAILABLE:
            print("Cannot enable global shortcuts: keyboard library not available")
            return False

        if self.enabled:
            return True

        try:
            # Register global shortcuts using configured keys
            keyboard.add_hotkey(self.tts_hotkey, self._handle_tts_shortcut)
            keyboard.add_hotkey(self.image_hotkey, self._handle_image_shortcut)

            self.enabled = True
            print(
                f"Global shortcuts enabled: {self.tts_hotkey.upper()} (TTS), "
                f"{self.image_hotkey.upper()} (Image)"
            )
            return True
        except Exception as e:
            print(f"Error enabling global shortcuts: {e}")
            return False

    def disable(self):
        """Disable global shortcuts."""
        if not self.enabled:
            return

        try:
            keyboard.unhook_all()
            self.enabled = False
            print("Global shortcuts disabled")
        except Exception as e:
            print(f"Error disabling global shortcuts: {e}")

    def update_hotkeys(self, tts_hotkey: str, image_hotkey: str, enabled: bool):
        """
        Reconfigure hotkeys and (re)enable or disable them.

        Args:
            tts_hotkey: Key for TTS (e.g. 'f9')
            image_hotkey: Key for image generation (e.g. 'f10')
            enabled: Whether shortcuts should be enabled
        """
        # Normalize and store new keys
        if tts_hotkey:
            self.tts_hotkey = tts_hotkey.lower()
        if image_hotkey:
            self.image_hotkey = image_hotkey.lower()

        # Always disable current hooks first
        if self.enabled:
            self.disable()

        # Re-enable only if requested
        if enabled:
            self.enable()

    def _get_selected_text(self) -> Optional[str]:
        """
        Get currently selected text by simulating Ctrl+C.
        Returns the text from clipboard, or None if failed.
        """
        if not PYSIDE_AVAILABLE:
            return None

        try:
            # Save current clipboard content
            app = QApplication.instance()
            if not app:
                return None

            clipboard = app.clipboard()
            original_text = clipboard.text()

            # Simulate Ctrl+C to copy selected text
            # Use write() instead of send() for better compatibility
            keyboard.press_and_release("ctrl+c")

            # Wait a bit for clipboard to update (longer delay for reliability)
            time.sleep(0.2)

            # Get new clipboard content
            selected_text = clipboard.text()

            # If we got text and it's different from original, return it
            if (
                selected_text
                and selected_text.strip()
                and selected_text != original_text
            ):
                return selected_text.strip()

            # Try one more time with longer delay if first attempt failed
            if not selected_text or selected_text == original_text:
                time.sleep(0.2)
                selected_text = clipboard.text()
                if (
                    selected_text
                    and selected_text.strip()
                    and selected_text != original_text
                ):
                    return selected_text.strip()

            return None
        except Exception as e:
            print(f"Error getting selected text: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _handle_tts_shortcut(self):
        """Handle Ctrl+Shift+T shortcut for TTS."""
        if not self.enabled:
            return

        text = self._get_selected_text()
        if text:
            print(f"Global shortcut: TTS requested for text: {text[:50]}...")
            if self.tts_callback:
                self.tts_callback(text)
            else:
                self.text_selected_for_tts.emit(text)
        else:
            print("No text selected for TTS")

    def _handle_image_shortcut(self):
        """Handle Ctrl+Shift+I shortcut for image generation."""
        if not self.enabled:
            return

        text = self._get_selected_text()
        if text:
            print(
                f"Global shortcut: Image generation requested for text: {text[:50]}..."
            )
            if self.image_callback:
                self.image_callback(text)
            else:
                self.text_selected_for_image.emit(text)
        else:
            print("No text selected for image generation")
