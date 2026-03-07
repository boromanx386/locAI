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


# Button colors for themes (blue for dark/light, gray for dystopian)
_STATUS_BTN_STYLES = {
    "blue": {
        "bg": "#4A9EFF",
        "hover": "#3B82E0",
        "press": "#2F6FC7",
    },
    "gray": {
        "bg": "#3D4349",
        "hover": "#484F58",
        "press": "#4A5056",
    },
}


class StatusPanel(QFrame):
    """Panel showing Ollama status and model selection."""

    model_selected = Signal(str)
    tts_play_clicked = Signal()
    tts_pause_clicked = Signal()
    tts_stop_clicked = Signal()
    tts_voice_changed = Signal(str)
    refresh_clicked = Signal()  # Emitted when refresh button is clicked
    stop_clicked = Signal()  # Emitted when stop button is clicked
    tools_toggled = Signal(bool)  # Emitted when tools toggle is changed

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
        self._button_style = "blue"

        self.init_ui()
        self.update_status()

    def init_ui(self):
        """Initialize UI components."""
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # Status indicator
        self.status_indicator = QLabel("●")
        self.status_indicator.setFixedSize(24, 24)
        self.status_indicator.setStyleSheet(
            f"""
            QLabel {{
                color: {Theme.get_status_color(False)};
                font-size: 16px;
                font-weight: bold;
                border-radius: 12px;
                background: transparent;
            }}
            """
        )
        layout.addWidget(self.status_indicator)

        # Status text (hidden - only indicator is visible)
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # Model icon (aligned left with status)
        model_icon_label = QLabel()
        MaterialIcons.apply_to_label(model_icon_label, MaterialIcons.ROBOT_SVG, size=20)
        model_icon_label.setFixedSize(24, 24)
        model_icon_label.setToolTip("Model")
        model_icon_label.setStyleSheet(
            """
            QLabel {
                border-radius: 12px;
                background: transparent;
            }
            """
        )
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
        self.stop_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #E74C3C;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
            QPushButton:pressed {
                background-color: #A93226;
            }
            """
        )
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        layout.addWidget(self.stop_btn)

        # Tools toggle button (placed next to Stop button)
        self.tools_enabled = False
        self.tools_btn = QPushButton()
        self.tools_btn.setCheckable(True)
        # Use a construction/tools style icon for tools toggle
        MaterialIcons.apply_to_button(
            self.tools_btn, MaterialIcons.TOOLS_SVG, size=18, keep_text=False
        )
        self.tools_btn.setMaximumWidth(32)
        self.tools_btn.setMaximumHeight(32)
        self.tools_btn.clicked.connect(self._on_tools_clicked)
        layout.addWidget(self.tools_btn)

        # Semantic memory indicator (if enabled) – placed to the right of tools toggle
        self.semantic_memory_label = QLabel()
        MaterialIcons.apply_to_label(
            self.semantic_memory_label, MaterialIcons.COGNITION_2_SVG, size=20
        )
        self.semantic_memory_label.setToolTip("Semantic memory: disabled")
        self.semantic_memory_label.setVisible(False)
        layout.addWidget(self.semantic_memory_label)

        layout.addStretch()  # Push TTS controls to the right

        # TTS Voice icon
        voice_icon_label = QLabel()
        MaterialIcons.apply_to_label(
            voice_icon_label, MaterialIcons.MICROPHONE_SVG, size=20
        )
        voice_icon_label.setFixedSize(24, 24)
        voice_icon_label.setToolTip("Voice")
        voice_icon_label.setStyleSheet(
            """
            QLabel {
                border-radius: 12px;
                background: transparent;
            }
            """
        )
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

        # TTS Pause button (currently disabled/hidden – pause not supported reliably)
        self.tts_pause_btn = QPushButton()
        self.tts_pause_btn.hide()

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
        self._apply_button_style()

    def set_theme(self, theme_name: str):
        """Update button colors for theme (dystopian = gray, else = blue)."""
        self._button_style = "gray" if theme_name == "dystopian" else "blue"
        self._apply_button_style()
        self._update_tools_button_tooltip()

    def _apply_button_style(self):
        """Apply current button style to refresh, tts_play, tts_stop, and tools (when off)."""
        s = _STATUS_BTN_STYLES[self._button_style]
        sheet = f"""
            QPushButton {{
                background-color: {s["bg"]};
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {s["hover"]};
            }}
            QPushButton:pressed {{
                background-color: {s["press"]};
            }}
        """
        self.refresh_btn.setStyleSheet(sheet)
        self.tts_play_btn.setStyleSheet(sheet)
        self.tts_stop_btn.setStyleSheet(sheet)
        if not self.tools_enabled:
            self.tools_btn.setStyleSheet(sheet)

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
            f"""
            QLabel {{
                color: {color};
                font-size: 16px;
                font-weight: bold;
                border-radius: 12px;
                background: transparent;
            }}
            """
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
            f"""
            QLabel {{
                color: {color};
                font-size: 16px;
                font-weight: bold;
                border-radius: 12px;
                background: transparent;
            }}
            """
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

    def update_semantic_memory_status(self, enabled: bool, message_count: int = 0):
        """
        Update semantic memory indicator.

        Args:
            enabled: Whether semantic memory is enabled
            message_count: Number of embedded messages
        """
        if enabled:
            self.semantic_memory_label.setVisible(True)
            if message_count > 0:
                self.semantic_memory_label.setToolTip(
                    f"Semantic memory: active ({message_count} messages indexed)"
                )
            else:
                self.semantic_memory_label.setToolTip("Semantic memory: active")
        else:
            self.semantic_memory_label.setVisible(False)

    def set_tools_enabled(self, enabled: bool):
        """
        Set tools toggle state from outside (without emitting signal again).
        """
        self.tools_enabled = enabled
        # Block signals to avoid recursive updates
        self.tools_btn.blockSignals(True)
        self.tools_btn.setChecked(enabled)
        self.tools_btn.blockSignals(False)
        self._update_tools_button_tooltip()

    def _on_tools_clicked(self):
        """Handle tools toggle button click."""
        self.tools_enabled = self.tools_btn.isChecked()
        self._update_tools_button_tooltip()
        self.tools_toggled.emit(self.tools_enabled)

    def _update_tools_button_tooltip(self):
        """Update tools button tooltip based on current state."""
        if self.tools_enabled:
            self.tools_btn.setToolTip("Tools: enabled")
            # Green when tools are ON
            self.tools_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #4CAF50;
                    border: none;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #43A047;
                }
                QPushButton:pressed {
                    background-color: #388E3C;
                }
                """
            )
        else:
            self.tools_btn.setToolTip("Tools: disabled")
            self._apply_button_style()

    def refresh_models(self):
        """Refresh the list of available models (non-blocking)."""
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, self._refresh_models_async)

    def _refresh_models_async(self):
        """Actually refresh models."""
        # Get LLM and Vision models (exclude embedding models)
        models, error = self.detector.get_llm_and_vision_models()

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
        # If models list is provided, assume it's already filtered (LLM + Vision)
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

    def update_voices_for_language(self, lang_code: str = None, engine: str = "kokoro", voice_cloning_enabled: bool = False, config_manager=None):
        """Update voice combo box with voices for selected language and engine."""
        if engine == "pocket_tts":
            # Pocket TTS voices (English only)
            voices = ['alba', 'marius', 'javert', 'jean', 'fantine', 'cosette', 'eponine', 'azelma']
            
            # Add saved cloned voices if config_manager is provided
            if config_manager:
                saved_voices = config_manager.get_saved_cloned_voices()
                for saved_voice in saved_voices:
                    voice_name = saved_voice.get("name", "Unknown")
                    voices.append(voice_name)
            
            # Add "Clone Voice" option if voice cloning is enabled
            if voice_cloning_enabled:
                voices.append('Clone Voice')
        else:
            # Kokoro voices - use static list to avoid loading the model
            voices_by_language = {
                "a": [  # American English
                    "af_alloy", "af_aoede", "af_bella", "af_heart", "af_jessica",
                    "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
                    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam",
                    "am_michael", "am_onyx", "am_puck", "am_santa",
                ],
                "b": [  # British English
                    "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
                    "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
                ],
                "e": [  # Spanish
                    "ef_dora", "em_alex", "em_santa",
                ],
                "f": [  # French
                    "ff_siwis",
                ],
                "h": [  # Hindi
                    "hf_alpha", "hf_beta", "hm_omega", "hm_psi",
                ],
                "i": [  # Italian
                    "if_sara", "im_nicola",
                ],
                "j": [  # Japanese
                    "jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo",
                ],
                "p": [  # Brazilian Portuguese
                    "pf_dora", "pm_alex", "pm_santa",
                ],
                "z": [  # Mandarin Chinese
                    "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi",
                ],
            }
            voices = voices_by_language.get(lang_code or "a", voices_by_language["a"])

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
