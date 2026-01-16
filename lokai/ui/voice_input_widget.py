"""
Voice Input Widget for locAI.
Real-time voice input with audio visualization and transcription display.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTextEdit,
    QProgressBar,
    QSizePolicy,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor, QPainter, QPainterPath, QBrush, QPen, QLinearGradient, QRadialGradient
from lokai.ui.material_icons import MaterialIcons
from lokai.ui.asr_worker import ASRWorker
from lokai.core.asr_engine import ASREngine
from lokai.core.config_manager import ConfigManager


class AudioLevelIndicator(QWidget):
    """Circular audio level indicator widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio_level = 0.0  # 0.0 to 1.0
        self.is_listening = False
        self.setFixedSize(60, 60)

    def set_audio_level(self, level: float):
        """Set audio level (0.0 to 1.0)."""
        self.audio_level = max(0.0, min(1.0, level))
        self.update()

    def set_listening(self, listening: bool):
        """Set listening state."""
        self.is_listening = listening
        self.update()

    def paintEvent(self, event):
        """Custom paint event."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = self.rect().center()
        radius = min(self.width(), self.height()) / 2 - 5

        # Background circle
        painter.setPen(QPen(QColor(100, 100, 100, 100), 2))
        painter.setBrush(QBrush(QColor(50, 50, 50, 50)))
        painter.drawEllipse(center, radius, radius)

        if self.is_listening:
            # Active listening indicator
            level_radius = radius * (0.3 + self.audio_level * 0.7)

            # Gradient for audio level
            gradient = QRadialGradient(center, level_radius)
            if self.audio_level > 0.5:
                # High level - red to orange
                gradient.setColorAt(0, QColor(255, 100, 100, 200))
                gradient.setColorAt(1, QColor(255, 150, 100, 100))
            else:
                # Low level - green to yellow
                gradient.setColorAt(0, QColor(100, 255, 100, 200))
                gradient.setColorAt(1, QColor(255, 255, 100, 100))

            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, level_radius, level_radius)

        # Center microphone icon area
        icon_radius = radius * 0.4
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.setBrush(QBrush(QColor(70, 70, 70, 150)))
        painter.drawEllipse(center, icon_radius, icon_radius)

        # Simple microphone symbol
        mic_height = icon_radius * 0.6
        mic_width = icon_radius * 0.3
        mic_rect = QPainterPath()
        mic_rect.addRoundedRect(
            center.x() - mic_width/2,
            center.y() - mic_height/2,
            mic_width,
            mic_height,
            2, 2
        )
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
        painter.drawPath(mic_rect)


class VoiceInputWidget(QWidget):
    """Voice input widget with real-time audio visualization."""

    voice_input_started = Signal()
    voice_input_stopped = Signal()
    transcription_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        Initialize VoiceInputWidget.

        Args:
            config_manager: ConfigManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = config_manager

        # ASR components
        self.asr_engine = None
        self.asr_worker = None

        # State
        self.is_listening = False
        self.current_transcription = ""
        self.accumulated_transcription = []  # Collect multiple chunks

        # Initialize UI
        self.init_ui()
        self.init_asr()

        # Update timer for smooth animations
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(50)  # 20 FPS

    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Top row: microphone button and status
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        # Voice input button
        self.voice_btn = QPushButton()
        self.voice_btn.setFixedSize(50, 50)
        self.voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        MaterialIcons.apply_to_button(
            self.voice_btn,
            MaterialIcons.MIC_SVG,
            size=24,
            keep_text=False
        )
        self.voice_btn.clicked.connect(self.toggle_voice_input)

        # Add shadow effect
        btn_shadow = QGraphicsDropShadowEffect()
        btn_shadow.setBlurRadius(15)
        btn_shadow.setXOffset(0)
        btn_shadow.setYOffset(2)
        btn_shadow.setColor(QColor(52, 152, 219, 150))
        self.voice_btn.setGraphicsEffect(btn_shadow)

        # Set initial style
        self.update_button_style()

        # Audio level indicator
        self.audio_indicator = AudioLevelIndicator()

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #BDC3C7;
                font-size: 14px;
                font-weight: 500;
            }
        """)

        top_layout.addWidget(self.voice_btn)
        top_layout.addWidget(self.audio_indicator)
        top_layout.addWidget(self.status_label, stretch=1)
        top_layout.addStretch()

        # Transcription display
        self.transcription_edit = QTextEdit()
        self.transcription_edit.setPlaceholderText("Voice transcription will appear here...")
        self.transcription_edit.setMaximumHeight(80)
        self.transcription_edit.setStyleSheet("""
            QTextEdit {
                background-color: rgba(44, 62, 80, 0.8);
                border: 1px solid rgba(52, 152, 219, 0.3);
                border-radius: 8px;
                color: #ECF0F1;
                font-size: 13px;
                padding: 8px;
            }
            QTextEdit:focus {
                border: 1px solid rgba(52, 152, 219, 0.6);
            }
        """)

        layout.addLayout(top_layout)
        layout.addWidget(self.transcription_edit)

        self.setLayout(layout)

        # Overall styling
        self.setStyleSheet("""
            VoiceInputWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(44, 62, 80, 0.9),
                    stop:1 rgba(33, 47, 61, 0.9));
                border: 1px solid rgba(52, 152, 219, 0.3);
                border-radius: 12px;
            }
        """)

        # Add shadow effect to entire widget
        widget_shadow = QGraphicsDropShadowEffect()
        widget_shadow.setBlurRadius(20)
        widget_shadow.setXOffset(0)
        widget_shadow.setYOffset(4)
        widget_shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(widget_shadow)

    def init_asr(self):
        """Initialize ASR components."""
        try:
            # Initialize ASR engine
            # Use asr.storage_path if set, otherwise fallback to models.storage_path
            storage_path = self.config_manager.get("asr.storage_path")
            if not storage_path:
                storage_path = self.config_manager.get("models.storage_path")
            self.asr_engine = ASREngine(storage_path)

            if not self.asr_engine.is_available():
                self.status_label.setText("ASR not available")
                self.voice_btn.setEnabled(False)
                return

            # Initialize ASR worker
            self.asr_worker = ASRWorker(self.asr_engine, self.config_manager)

            # Connect signals
            self.asr_worker.transcription_ready.connect(self.on_transcription_ready)
            self.asr_worker.partial_transcription.connect(self.on_partial_transcription)
            self.asr_worker.error_occurred.connect(self.on_asr_error)
            self.asr_worker.listening_started.connect(self.on_listening_started)
            self.asr_worker.listening_stopped.connect(self.on_listening_stopped)
            self.asr_worker.audio_level_updated.connect(self.on_audio_level_updated)

            self.status_label.setText("ASR ready")

        except Exception as e:
            print(f"Error initializing ASR: {e}")
            self.status_label.setText("ASR initialization failed")
            self.voice_btn.setEnabled(False)

    def update_button_style(self):
        """Update voice button style based on state."""
        if self.is_listening:
            # Listening state - red/pulsing
            self.voice_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E74C3C;
                    border: 2px solid #C0392B;
                    border-radius: 25px;
                }
                QPushButton:hover {
                    background-color: #FF6B6B;
                    border: 2px solid #E74C3C;
                }
            """)
        else:
            # Ready state - blue
            self.voice_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498DB;
                    border: 2px solid #2980B9;
                    border-radius: 25px;
                }
                QPushButton:hover {
                    background-color: #5DADE2;
                    border: 2px solid #3498DB;
                }
            """)

    def toggle_voice_input(self):
        """Toggle voice input on/off."""
        if self.is_listening:
            self.stop_voice_input()
        else:
            self.start_voice_input()

    def start_voice_input(self):
        """Start voice input."""
        if not self.asr_worker:
            self.error_occurred.emit("ASR not initialized")
            return

        try:
            self.is_listening = True
            self.update_button_style()
            self.status_label.setText("Listening...")
            self.audio_indicator.set_listening(True)
            self.current_transcription = ""
            self.transcription_edit.clear()

            self.asr_worker.start_listening()
            self.voice_input_started.emit()

        except Exception as e:
            self.error_occurred.emit(f"Failed to start voice input: {e}")
            self.is_listening = False
            self.update_button_style()

    def stop_voice_input(self):
        """Stop voice input."""
        if not self.asr_worker:
            return

        try:
            self.is_listening = False
            self.update_button_style()
            self.status_label.setText("Processing...")
            self.audio_indicator.set_listening(False)

            self.asr_worker.stop_listening()
            self.voice_input_stopped.emit()
            
            # Emit final transcription if we have accumulated text
            # This ensures transcription is sent even if on_transcription_ready
            # was called while is_listening was still True
            if self.accumulated_transcription:
                final_text = " ".join(self.accumulated_transcription)
                print(f"[STOP] Emitting final accumulated transcription: '{final_text}'")
                if final_text.strip():
                    self.transcription_ready.emit(final_text)
                self.accumulated_transcription = []

        except Exception as e:
            self.error_occurred.emit(f"Failed to stop voice input: {e}")

    def on_transcription_ready(self, text: str):
        """Handle completed transcription."""
        # Accumulate transcription chunks
        if text and text.strip():
            self.accumulated_transcription.append(text.strip())
        
        full_text = " ".join(self.accumulated_transcription)
        self.current_transcription = full_text
        self.transcription_edit.setPlainText(full_text)
        
        if self.is_listening:
            # Still listening - show accumulated text but don't emit yet
            self.status_label.setText("Listening...")
            print(f"Accumulated so far: {full_text}")
        else:
            # Stopped - emit final transcription to chat
            self.status_label.setText("Ready")
            print(f"[WIDGET] Final transcription: {full_text}")
            if full_text.strip():
                print(f"[WIDGET] >>> Emitting transcription_ready signal with: '{full_text}'")
                self.transcription_ready.emit(full_text)
                print(f"[WIDGET] >>> Signal emitted!")
            else:
                print(f"[WIDGET] >>> NOT emitting - text is empty")
            # Clear for next session
            self.accumulated_transcription = []

    def on_partial_transcription(self, text: str):
        """Handle partial transcription during listening."""
        self.transcription_edit.setPlainText(text)
        self.status_label.setText("Listening...")

    def on_asr_error(self, error: str):
        """Handle ASR errors."""
        self.status_label.setText("Error")
        self.error_occurred.emit(error)

    def on_listening_started(self):
        """Handle listening started."""
        self.is_listening = True
        self.accumulated_transcription = []  # Clear previous transcriptions
        self.transcription_edit.clear()
        self.status_label.setText("Listening...")
        self.audio_indicator.set_listening(True)

    def on_listening_stopped(self):
        """Handle listening stopped."""
        self.is_listening = False
        self.audio_indicator.set_listening(False)
        self.status_label.setText("Ready")

    def on_audio_level_updated(self, level: float):
        """Handle audio level updates."""
        self.audio_indicator.set_audio_level(level)

    def update_ui(self):
        """Update UI elements."""
        # Could add smooth animations here if needed
        pass

    def transcribe_file(self, file_path: str):
        """Transcribe audio from file."""
        if self.asr_worker:
            self.asr_worker.transcribe_file(file_path)

    def cleanup(self):
        """Cleanup resources."""
        if self.update_timer:
            self.update_timer.stop()

        if self.asr_worker:
            self.asr_worker.cleanup()

        if self.asr_engine:
            try:
                self.asr_engine.clear_gpu_memory()
            except:
                pass