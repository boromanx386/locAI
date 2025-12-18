"""
Status Panel for locAI.
Displays Ollama status and model selection.
"""

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QFrame,
)
from PySide6.QtCore import Signal, Qt
from lokai.core.ollama_detector import OllamaDetector
from lokai.core.ollama_client import OllamaClient
from lokai.ui.theme import Theme
from lokai.ui.material_icons import MaterialIcons


class StatusPanel(QFrame):
    """Panel showing Ollama status and model selection."""

    model_selected = Signal(str)
    tts_play_clicked = Signal()
    tts_pause_clicked = Signal()
    tts_stop_clicked = Signal()
    tts_voice_changed = Signal(str)
    refresh_clicked = Signal()  # Emitted when refresh button is clicked
    stop_clicked = Signal()  # Emitted when stop button is clicked

    def __init__(self, detector: OllamaDetector, client: OllamaClient):
        """
        Initialize StatusPanel.

        Args:
            detector: OllamaDetector instance
            client: OllamaClient instance
        """
        super().__init__()
        self.detector = detector
        self.client = client

        self.init_ui()
        self.update_status()

    def init_ui(self):
        """Initialize UI components."""
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # Status indicator
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet(
            f"color: {Theme.get_status_color(False)}; font-size: 16px; font-weight: bold;"
        )
        layout.addWidget(self.status_indicator)

        # Status text
        self.status_label = QLabel("Checking Ollama...")
        self.status_label.setStyleSheet("font-weight: 500;")
        layout.addWidget(self.status_label)

        # Model icon (aligned left with status)
        model_icon_label = QLabel()
        MaterialIcons.apply_to_label(model_icon_label, MaterialIcons.ROBOT_SVG, size=20)
        model_icon_label.setToolTip("Model")
        layout.addWidget(model_icon_label)

        # Model selector (aligned left with status)
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(0)  # Allow shrinking
        self.model_combo.setMaximumWidth(300)
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        layout.addWidget(self.model_combo)

        # Refresh button (icon only, smaller)
        self.refresh_btn = QPushButton()
        MaterialIcons.apply_to_button(
            self.refresh_btn, MaterialIcons.REFRESH_SVG, size=18, keep_text=False
        )
        self.refresh_btn.setToolTip("Refresh model list")
        self.refresh_btn.setMaximumWidth(32)
        self.refresh_btn.setMaximumHeight(32)
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        layout.addWidget(self.refresh_btn)

        # Stop button (icon only, smaller)
        self.stop_btn = QPushButton()
        MaterialIcons.apply_to_button(
            self.stop_btn, MaterialIcons.STOP_SVG, size=18, keep_text=False
        )
        self.stop_btn.setToolTip("Stop all operations (Ollama & Image Generation)")
        self.stop_btn.setMaximumWidth(32)
        self.stop_btn.setMaximumHeight(32)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        layout.addWidget(self.stop_btn)

        layout.addStretch()  # Push TTS controls to the right

        # TTS Voice icon
        voice_icon_label = QLabel()
        MaterialIcons.apply_to_label(
            voice_icon_label, MaterialIcons.MICROPHONE_SVG, size=20
        )
        voice_icon_label.setToolTip("Voice")
        layout.addWidget(voice_icon_label)

        # TTS Voice dropdown
        self.tts_voice_combo = QComboBox()
        self.tts_voice_combo.setMinimumWidth(0)  # Allow shrinking
        self.tts_voice_combo.setMaximumWidth(150)
        # Will be populated based on language from config
        # Default voices for American English (only confirmed available)
        self.tts_voice_combo.addItems(
            [
                "af_heart",
                "af_bella",
                "af_sam",
                "af_sky",
                "af_spring",
            ]
        )
        self.tts_voice_combo.setCurrentText("af_heart")
        self.tts_voice_combo.currentTextChanged.connect(self.on_tts_voice_changed)
        layout.addWidget(self.tts_voice_combo)

        # TTS Controls (after voice dropdown)
        # TTS Play button
        self.tts_play_btn = QPushButton()
        MaterialIcons.apply_to_button(
            self.tts_play_btn, MaterialIcons.PLAY_SVG, size=18, keep_text=False
        )
        self.tts_play_btn.setToolTip("Play TTS")
        self.tts_play_btn.setMaximumWidth(32)
        self.tts_play_btn.setMaximumHeight(32)
        self.tts_play_btn.clicked.connect(self.on_tts_play)
        layout.addWidget(self.tts_play_btn)

        # TTS Pause button
        self.tts_pause_btn = QPushButton()
        MaterialIcons.apply_to_button(
            self.tts_pause_btn, MaterialIcons.PAUSE_SVG, size=18, keep_text=False
        )
        self.tts_pause_btn.setToolTip("Pause TTS")
        self.tts_pause_btn.setMaximumWidth(32)
        self.tts_pause_btn.setMaximumHeight(32)
        self.tts_pause_btn.setEnabled(False)
        self.tts_pause_btn.clicked.connect(self.on_tts_pause)
        layout.addWidget(self.tts_pause_btn)

        # TTS Stop button
        self.tts_stop_btn = QPushButton()
        MaterialIcons.apply_to_button(
            self.tts_stop_btn, MaterialIcons.STOP_SVG, size=18, keep_text=False
        )
        self.tts_stop_btn.setToolTip("Stop TTS")
        self.tts_stop_btn.setMaximumWidth(32)
        self.tts_stop_btn.setMaximumHeight(32)
        self.tts_stop_btn.setEnabled(False)
        self.tts_stop_btn.clicked.connect(self.on_tts_stop)
        layout.addWidget(self.tts_stop_btn)

        self.setLayout(layout)
        self.setFrameStyle(QFrame.Shape.StyledPanel)

    def update_status(self):
        """Update Ollama status display (non-blocking)."""
        from PySide6.QtCore import QTimer

        # Delay check to avoid blocking UI
        QTimer.singleShot(100, self._update_status_async)

    def _update_status_async(self):
        """Actually update status."""
        is_running, error = self.detector.check_ollama_running()

        if is_running:
            self.set_online()
        else:
            self.set_offline(error)

    def set_online(self):
        """Set status to online."""
        color = Theme.get_status_color(True)
        self.status_indicator.setStyleSheet(
            f"color: {color}; font-size: 16px; font-weight: bold;"
        )
        self.status_label.setText("Ollama Online")
        self.status_label.setStyleSheet("font-weight: 500; color: #51CF66;")
        self.refresh_btn.setEnabled(True)

        # Update models (non-blocking)
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, self._refresh_models_async)

    def set_offline(self, error: str = None):
        """Set status to offline."""
        color = Theme.get_status_color(False)
        self.status_indicator.setStyleSheet(
            f"color: {color}; font-size: 16px; font-weight: bold;"
        )
        if error:
            self.status_label.setText(f"Ollama Offline - {error}")
        else:
            self.status_label.setText("Ollama Offline")
        self.status_label.setStyleSheet("font-weight: 500; color: #EF5350;")
        self.model_combo.clear()
        self.model_combo.addItem("No models available")
        self.model_combo.setEnabled(False)
        self.refresh_btn.setEnabled(False)

    def _on_refresh_clicked(self):
        """Handle refresh button click - emit signal and refresh models."""
        self.refresh_clicked.emit()
        self.refresh_models()

    def _on_stop_clicked(self):
        """Handle stop button click - emit signal."""
        self.stop_clicked.emit()

    def refresh_models(self):
        """Refresh the list of available models (non-blocking)."""
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, self._refresh_models_async)

    def _refresh_models_async(self):
        """Actually refresh models."""
        models, error = self.detector.get_installed_models()

        if error:
            self.set_offline(error)
            return

        if not models:
            self.model_combo.clear()
            self.model_combo.addItem("No models installed")
            self.model_combo.setEnabled(False)
            return

        # Update combo box
        current_selection = self.model_combo.currentText()
        self.model_combo.clear()
        self.model_combo.addItems(models)
        self.model_combo.setEnabled(True)

        # Restore selection if still available
        if current_selection in models:
            index = self.model_combo.findText(current_selection)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)

    def update_models(self, models: list):
        """Update model list (called externally)."""
        if not models:
            self.model_combo.clear()
            self.model_combo.addItem("No models installed")
            self.model_combo.setEnabled(False)
            return

        current_selection = self.model_combo.currentText()
        self.model_combo.clear()
        self.model_combo.addItems(models)
        self.model_combo.setEnabled(True)

        if current_selection in models:
            index = self.model_combo.findText(current_selection)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)

    def get_selected_model(self) -> str:
        """Get currently selected model name."""
        model = self.model_combo.currentText()
        if model and model not in ["No models available", "No models installed"]:
            return model
        return None

    def on_model_changed(self, model_name: str):
        """Handle model selection change."""
        if model_name and model_name not in [
            "No models available",
            "No models installed",
        ]:
            self.model_selected.emit(model_name)

    def on_tts_play(self):
        """Handle TTS play button click."""
        self.tts_play_clicked.emit()
        self.tts_play_btn.setEnabled(False)
        self.tts_pause_btn.setEnabled(True)
        self.tts_stop_btn.setEnabled(True)

    def on_tts_pause(self):
        """Handle TTS pause button click."""
        self.tts_pause_clicked.emit()
        self.tts_play_btn.setEnabled(True)
        self.tts_pause_btn.setEnabled(False)

    def on_tts_stop(self):
        """Handle TTS stop button click."""
        self.tts_stop_clicked.emit()
        self.tts_play_btn.setEnabled(True)
        self.tts_pause_btn.setEnabled(False)
        self.tts_stop_btn.setEnabled(False)

    def update_voices_for_language(self, lang_code: str):
        """Update voice combo box with voices for selected language."""
        from lokai.core.tts_engine import TTSEngine

        # Create temporary engine to get voices
        temp_engine = TTSEngine(lang_code=lang_code)
        voices = temp_engine.get_voices_for_language(lang_code)

        # Save current selection if it exists in new list
        current_voice = self.tts_voice_combo.currentText()

        # Update combo box
        self.tts_voice_combo.clear()
        self.tts_voice_combo.addItems(voices)

        # Restore selection if still available
        if current_voice in voices:
            index = self.tts_voice_combo.findText(current_voice)
            if index >= 0:
                self.tts_voice_combo.setCurrentIndex(index)
        else:
            # Select first voice if previous not available
            if voices:
                self.tts_voice_combo.setCurrentIndex(0)
                # Emit signal with new voice (but block signal to avoid recursion)
                self.tts_voice_combo.blockSignals(True)
                self.tts_voice_combo.setCurrentIndex(0)
                self.tts_voice_combo.blockSignals(False)
                self.on_tts_voice_changed(voices[0])

    def on_tts_voice_changed(self, voice: str):
        """Handle TTS voice selection change."""
        self.tts_voice_changed.emit(voice)

    def set_tts_playing(self, is_playing: bool):
        """Update TTS button states based on playing status."""
        self.tts_play_btn.setEnabled(not is_playing)
        self.tts_pause_btn.setEnabled(is_playing)
        self.tts_stop_btn.setEnabled(is_playing)
