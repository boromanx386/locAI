"""
Audio Player Widget with Waveform Visualization for locAI.
Modern audio player with waveform display and playback controls.
"""

import os
import numpy as np
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSizePolicy, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, Signal, QUrl, QTimer, QPointF, QRectF, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPainter, QPen, QColor, QLinearGradient, QPainterPath, QBrush, QMouseEvent, QPalette
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from lokai.ui.material_icons import MaterialIcons

try:
    import soundfile as sf
except ImportError:
    sf = None
    print("Warning: soundfile not installed. Waveform visualization disabled.")


class WaveformWidget(QWidget):
    """Custom widget for displaying audio waveform."""
    
    seek_requested = Signal(float)  # Emit position (0.0 to 1.0) when user clicks
    
    def __init__(self, audio_path: str, parent=None):
        """
        Initialize WaveformWidget.
        
        Args:
            audio_path: Path to audio file
            parent: Parent widget
        """
        super().__init__(parent)
        self.audio_path = audio_path
        self.waveform_data = None
        self.progress = 0.0  # Current playback progress (0.0 to 1.0)
        self.hover_position = -1.0  # Mouse hover position (-1 = not hovering)
        self._hover_opacity = 0.0  # For smooth fade in/out of hover effect
        
        # Set minimum size
        self.setMinimumHeight(80)
        self.setMinimumWidth(250)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMaximumHeight(100)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Animation for hover opacity
        self._hover_animation = QPropertyAnimation(self, b"hoverOpacity")
        self._hover_animation.setDuration(150)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Load waveform data
        self._load_waveform()
    
    def get_hover_opacity(self):
        """Get hover opacity for animation."""
        return self._hover_opacity
    
    def set_hover_opacity(self, value):
        """Set hover opacity for animation."""
        self._hover_opacity = value
        self.update()
    
    hoverOpacity = Property(float, get_hover_opacity, set_hover_opacity)
        
    def _load_waveform(self):
        """Load and process waveform data from audio file."""
        if not sf or not os.path.exists(self.audio_path):
            return
            
        try:
            # Load audio file
            data, samplerate = sf.read(self.audio_path)
            
            # Convert to mono if stereo
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)
            
            # Downsample for display based on data length
            # For short audio (< 5 seconds at typical sample rates), use more samples
            # For longer audio, use fewer samples to fit in display
            samples_per_second = 100  # Target samples per second of audio
            audio_duration_seconds = len(data) / samplerate
            target_samples = int(min(3000, max(500, audio_duration_seconds * samples_per_second)))
            
            if len(data) > target_samples:
                # Use max/min pooling for better representation
                block_size = max(1, len(data) // target_samples)
                blocks = len(data) // block_size
                
                # Calculate max values for each block to preserve peaks
                max_vals = []
                for i in range(blocks):
                    start_idx = i * block_size
                    end_idx = min((i + 1) * block_size, len(data))
                    block = data[start_idx:end_idx]
                    if len(block) > 0:
                        max_vals.append(np.max(np.abs(block)))
                
                self.waveform_data = np.array(max_vals)
            else:
                self.waveform_data = np.abs(data)
            
            # Normalize to 0-1 range
            max_val = np.max(self.waveform_data)
            if max_val > 0:
                self.waveform_data = self.waveform_data / max_val
            
            # Ensure minimum height for very quiet parts
            self.waveform_data = np.maximum(self.waveform_data, 0.05)
                
        except Exception as e:
            print(f"Error loading waveform: {e}")
            import traceback
            traceback.print_exc()
            self.waveform_data = None
    
    def set_progress(self, progress: float):
        """
        Set playback progress.
        
        Args:
            progress: Progress value (0.0 to 1.0)
        """
        self.progress = max(0.0, min(1.0, progress))
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event to draw waveform."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Get widget dimensions
        width = self.width()
        height = self.height()
        center_y = height / 2
        
        # Background with gradient
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor(40, 25, 32, 200))
        gradient.setColorAt(1, QColor(30, 20, 25, 220))
        painter.fillRect(self.rect(), gradient)
        
        # Draw subtle border
        painter.setPen(QPen(QColor(231, 76, 60, 80), 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 6, 6)
        
        if self.waveform_data is None or len(self.waveform_data) == 0:
            # No waveform data - draw placeholder
            painter.setPen(QPen(QColor(150, 150, 150), 1))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Loading waveform...")
            return
        
        # Calculate bar width and spacing
        num_samples = len(self.waveform_data)
        bar_spacing = 0.5  # Reduced spacing for more continuous look
        bar_width = max(0.8, (width / num_samples) - bar_spacing)
        
        # Draw waveform bars with gradient
        for i, amplitude in enumerate(self.waveform_data):
            x = i * (bar_width + bar_spacing)
            
            # Skip if x is beyond widget width
            if x >= width:
                break
                
            bar_height = max(3, amplitude * (height * 0.80))  # 80% of widget height, minimum 3px
            
            # Determine color based on progress
            progress_x = self.progress * width
            
            if x < progress_x:
                # Played portion - gradient from bright red to orange
                bar_gradient = QLinearGradient(x, center_y - bar_height/2, x, center_y + bar_height/2)
                bar_gradient.setColorAt(0, QColor(255, 120, 120))  # Light red top
                bar_gradient.setColorAt(0.5, QColor(255, 107, 107))  # Bright red middle
                bar_gradient.setColorAt(1, QColor(255, 90, 90))  # Slightly darker red bottom
                brush = QBrush(bar_gradient)
            else:
                # Unplayed portion - gradient darker red
                bar_gradient = QLinearGradient(x, center_y - bar_height/2, x, center_y + bar_height/2)
                bar_gradient.setColorAt(0, QColor(231, 76, 60, 140))  # Top
                bar_gradient.setColorAt(0.5, QColor(192, 57, 43, 160))  # Middle
                bar_gradient.setColorAt(1, QColor(169, 50, 38, 140))  # Bottom
                brush = QBrush(bar_gradient)
            
            # Hover glow effect with animation
            if self.hover_position >= 0 and self._hover_opacity > 0:
                hover_x = self.hover_position * width
                distance = abs(x - hover_x)
                if distance < 80:  # Hover range
                    # Add glow based on proximity and animation
                    glow_intensity = int(40 * (1 - distance / 80) * self._hover_opacity)
                    
                    # Draw glow effect
                    glow_color = QColor(255, 150, 150, glow_intensity)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(glow_color)
                    glow_rect = QRectF(
                        x - 2,
                        center_y - bar_height / 2 - 4,
                        bar_width + 4,
                        bar_height + 8
                    )
                    painter.drawRoundedRect(glow_rect, 2, 2)
            
            # Draw bar with rounded corners (centered vertically)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(brush)
            bar_rect = QRectF(
                x,
                center_y - bar_height / 2,
                bar_width,
                bar_height
            )
            painter.drawRoundedRect(bar_rect, 1, 1)
        
        # Draw progress indicator with glow
        progress_x = self.progress * width
        
        # Progress line glow
        glow_gradient = QLinearGradient(progress_x - 10, 0, progress_x + 10, 0)
        glow_gradient.setColorAt(0, QColor(255, 255, 255, 0))
        glow_gradient.setColorAt(0.5, QColor(255, 255, 255, 100))
        glow_gradient.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setPen(QPen(QBrush(glow_gradient), 8))
        painter.drawLine(int(progress_x), 5, int(progress_x), height - 5)
        
        # Progress line main
        painter.setPen(QPen(QColor(255, 255, 255, 220), 2))
        painter.drawLine(int(progress_x), 0, int(progress_x), height)
        
        # Draw hover time indicator with animation
        if self.hover_position >= 0 and self._hover_opacity > 0:
            hover_x = self.hover_position * width
            
            # Hover line with fade
            line_alpha = int(120 * self._hover_opacity)
            painter.setPen(QPen(QColor(255, 255, 255, line_alpha), 1, Qt.PenStyle.DashLine))
            painter.drawLine(int(hover_x), 0, int(hover_x), height)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse click for seeking."""
        if event.button() == Qt.MouseButton.LeftButton:
            position = event.position().x() / self.width()
            self.seek_requested.emit(position)
    
    def enterEvent(self, event):
        """Handle mouse enter - start hover animation."""
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_opacity)
        self._hover_animation.setEndValue(1.0)
        self._hover_animation.start()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for hover effect."""
        self.hover_position = event.position().x() / self.width()
        self.update()
    
    def leaveEvent(self, event):
        """Handle mouse leave - animate hover out."""
        self.hover_position = -1.0
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_opacity)
        self._hover_animation.setEndValue(0.0)
        self._hover_animation.start()


class AudioPlayerWidget(QWidget):
    """Complete audio player widget with controls and waveform."""
    
    def __init__(self, audio_path: str, parent=None):
        """
        Initialize AudioPlayerWidget.
        
        Args:
            audio_path: Path to audio file
            parent: Parent widget
        """
        super().__init__(parent)
        self.audio_path = audio_path
        self.is_playing = False
        self.duration = 0  # Duration in milliseconds
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.init_ui()
        self.init_player()
        
    def init_ui(self):
        """Initialize UI components."""
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # Play/Pause button with shadow
        self.play_btn = QPushButton()
        self.play_btn.setFixedSize(44, 44)
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        MaterialIcons.apply_to_button(
            self.play_btn, 
            MaterialIcons.PLAY_SVG, 
            size=26, 
            keep_text=False
        )
        self.play_btn.clicked.connect(self.toggle_play_pause)
        
        # Add shadow effect to play button
        play_btn_shadow = QGraphicsDropShadowEffect()
        play_btn_shadow.setBlurRadius(15)
        play_btn_shadow.setXOffset(0)
        play_btn_shadow.setYOffset(2)
        play_btn_shadow.setColor(QColor(231, 76, 60, 150))
        self.play_btn.setGraphicsEffect(play_btn_shadow)
        
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                border: 2px solid #C0392B;
                border-radius: 22px;
            }
            QPushButton:hover {
                background-color: #FF6B6B;
                border: 2px solid #E74C3C;
            }
            QPushButton:pressed {
                background-color: #C0392B;
                border: 2px solid #A93226;
            }
        """)
        layout.addWidget(self.play_btn)
        
        # Waveform and time display in vertical layout
        waveform_layout = QVBoxLayout()
        waveform_layout.setSpacing(4)
        
        # Waveform widget
        self.waveform = WaveformWidget(self.audio_path)
        self.waveform.seek_requested.connect(self.seek_to_position)
        waveform_layout.addWidget(self.waveform)
        
        # Time label with better styling
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setStyleSheet("""
            QLabel {
                color: #D0D0D0;
                font-size: 12px;
                font-family: 'Segoe UI', 'Arial', monospace;
                font-weight: 500;
                padding: 2px 4px;
                background-color: rgba(0, 0, 0, 0.3);
                border-radius: 4px;
            }
        """)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        waveform_layout.addWidget(self.time_label)
        
        layout.addLayout(waveform_layout, stretch=1)
        
        self.setLayout(layout)
        
        # Apply overall styling with gradient
        self.setStyleSheet("""
            AudioPlayerWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(50, 30, 40, 0.8),
                    stop:1 rgba(35, 20, 28, 0.9));
                border: 1px solid rgba(231, 76, 60, 0.3);
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
    
    def init_player(self):
        """Initialize QMediaPlayer."""
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # Load audio file
        if os.path.exists(self.audio_path):
            self.player.setSource(QUrl.fromLocalFile(self.audio_path))
        
        # Connect signals
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        
        # Timer for updating UI (more frequent for smooth progress)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(30)  # Update every 30ms for smoother animation
    
    def toggle_play_pause(self):
        """Toggle between play and pause."""
        if self.is_playing:
            self.player.pause()
        else:
            self.player.play()
    
    def on_playback_state_changed(self, state):
        """Handle playback state changes with animation."""
        self.is_playing = (state == QMediaPlayer.PlaybackState.PlayingState)
        
        # Update button icon with smooth transition
        if self.is_playing:
            MaterialIcons.apply_to_button(
                self.play_btn, 
                MaterialIcons.PAUSE_SVG, 
                size=26, 
                keep_text=False
            )
            # Update shadow color when playing
            if self.play_btn.graphicsEffect():
                self.play_btn.graphicsEffect().setColor(QColor(255, 107, 107, 180))
        else:
            MaterialIcons.apply_to_button(
                self.play_btn, 
                MaterialIcons.PLAY_SVG, 
                size=26, 
                keep_text=False
            )
            # Restore shadow color when paused
            if self.play_btn.graphicsEffect():
                self.play_btn.graphicsEffect().setColor(QColor(231, 76, 60, 150))
    
    def on_position_changed(self, position):
        """Handle position changes during playback."""
        if self.duration > 0:
            # Ensure position doesn't exceed duration
            position = min(position, self.duration)
            progress = position / self.duration
            self.waveform.set_progress(progress)
            
            # Debug output
            # print(f"Position: {position}ms, Duration: {self.duration}ms, Progress: {progress:.2%}")
    
    def on_duration_changed(self, duration):
        """Handle duration changes when media is loaded."""
        self.duration = duration
        self.update_time_label()
        print(f"Audio duration: {duration}ms ({duration/1000:.2f}s)")
    
    def seek_to_position(self, position):
        """
        Seek to a specific position in the audio.
        
        Args:
            position: Position (0.0 to 1.0)
        """
        if self.duration > 0:
            target_ms = int(position * self.duration)
            self.player.setPosition(target_ms)
    
    def update_ui(self):
        """Update UI elements."""
        self.update_time_label()
        
        # Force progress update during playback
        if self.is_playing and self.duration > 0:
            position = self.player.position()
            progress = min(1.0, position / self.duration)
            self.waveform.set_progress(progress)
    
    def update_time_label(self):
        """Update time label with current position."""
        if self.duration > 0:
            current = self.player.position() // 1000  # Convert to seconds
            total = self.duration // 1000
            
            current_str = f"{current // 60}:{current % 60:02d}"
            total_str = f"{total // 60}:{total % 60:02d}"
            
            self.time_label.setText(f"{current_str} / {total_str}")
        else:
            self.time_label.setText("0:00 / 0:00")
    
    def on_media_status_changed(self, status):
        """Handle media status changes."""
        from PySide6.QtMultimedia import QMediaPlayer
        
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            # Reset to beginning when playback finishes
            self.player.setPosition(0)
            self.waveform.set_progress(0.0)
        elif status == QMediaPlayer.MediaStatus.LoadedMedia:
            print(f"Media loaded successfully: {self.audio_path}")
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            print(f"Invalid media: {self.audio_path}")
    
    def cleanup(self):
        """Cleanup resources."""
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()
        if hasattr(self, 'player'):
            self.player.stop()
