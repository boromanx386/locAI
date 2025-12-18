"""
Chat Widget for locAI.
Modern chat interface with streaming support.
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QScrollArea,
    QFrame,
    QLabel,
    QMenu,
    QMessageBox,
)
from PySide6.QtCore import Signal, Qt, QTimer, QEvent
from PySide6.QtGui import QFont, QPixmap, QMouseEvent, QContextMenuEvent, QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from lokai.core.ollama_client import OllamaClient
from lokai.core.image_processor import ImageProcessor
from lokai.ui.material_icons import MaterialIcons
import os
import subprocess
import platform


class ChatBubble(QFrame):
    """Individual chat message bubble."""

    # Signals for context menu actions
    text_selected_for_tts = Signal(str)
    text_selected_for_image = Signal(str)

    def __init__(
        self,
        message: str = "",
        is_user: bool = True,
        image_path: str = None,
        parent=None,
    ):
        """
        Initialize ChatBubble.

        Args:
            message: Message text
            is_user: True if user message, False if AI message
            image_path: Optional path to image to display
            parent: Parent widget
        """
        super().__init__(parent)
        self.is_user = is_user
        self.current_text = message
        self.image_path = image_path

        self.init_ui()

    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Add image if provided
        if self.image_path:
            self.image_label = QLabel()
            self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.image_label.setMaximumHeight(400)
            self.image_label.setMaximumWidth(500)
            self.image_label.setScaledContents(False)

            # Install event filter for double-click detection
            self.image_label.installEventFilter(self)

            # Load and display image
            if os.path.exists(self.image_path):
                pixmap = QPixmap(self.image_path)
                if not pixmap.isNull():
                    # Scale image maintaining aspect ratio
                    if pixmap.height() > 400 or pixmap.width() > 500:
                        aspect_ratio = pixmap.width() / pixmap.height()
                        if pixmap.height() > 400:
                            new_height = 400
                            new_width = int(new_height * aspect_ratio)
                            if new_width > 500:
                                new_width = 500
                                new_height = int(new_width / aspect_ratio)
                        else:
                            new_width = 500
                            new_height = int(new_width / aspect_ratio)

                        pixmap = pixmap.scaled(
                            new_width,
                            new_height,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    self.image_label.setPixmap(pixmap)
                    layout.addWidget(self.image_label)

        # Message label
        if self.current_text:
            self.label = QLabel(self.current_text)
            self.label.setWordWrap(True)
            self.label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self.label.setAlignment(
                Qt.AlignmentFlag.AlignRight
                if self.is_user
                else Qt.AlignmentFlag.AlignLeft
            )
            # Enable context menu
            self.label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.label.customContextMenuRequested.connect(
                self._show_bubble_context_menu
            )
            layout.addWidget(self.label)

        # Style based on user/AI
        if self.is_user:
            self.setStyleSheet(
                """
                QFrame {
                    background: #4A9EFF;
                    border-radius: 12px;
                    margin: 4px 60px 4px 4px;
                }
                QLabel {
                    color: white;
                    font-size: 14px;
                    padding: 4px;
                }
            """
            )
        else:
            self.setStyleSheet(
                """
                QFrame {
                    background: #2D2D2D;
                    border: 1px solid #404040;
                    border-radius: 12px;
                    margin: 4px 4px 4px 60px;
                }
                QLabel {
                    color: #E0E0E0;
                    font-size: 14px;
                    padding: 4px;
                }
            """
            )

        self.setLayout(layout)

        # Add shadow effect for depth
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        # Different shadow colors for user vs AI bubbles
        if self.is_user:
            shadow.setColor(
                QColor(74, 158, 255, 100)
            )  # Blue shadow for user (semi-transparent)
        else:
            shadow.setColor(
                QColor(0, 0, 0, 80)
            )  # Dark shadow for AI (semi-transparent black)
        self.setGraphicsEffect(shadow)

    def add_text(self, text: str):
        """Add text to bubble (for streaming)."""
        self.current_text += text
        # Create label if it doesn't exist
        if not hasattr(self, "label") or self.label is None:
            from PySide6.QtWidgets import QLabel
            from PySide6.QtCore import Qt

            self.label = QLabel(self.current_text)
            self.label.setWordWrap(True)
            self.label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self.label.setAlignment(
                Qt.AlignmentFlag.AlignRight
                if self.is_user
                else Qt.AlignmentFlag.AlignLeft
            )
            # Enable context menu
            self.label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.label.customContextMenuRequested.connect(
                self._show_bubble_context_menu
            )
            # Add to layout
            layout = self.layout()
            if layout:
                layout.addWidget(self.label)
        else:
            self.label.setText(self.current_text)

    def set_text(self, text: str):
        """Set complete text."""
        self.current_text = text
        if hasattr(self, "label") and self.label:
            self.label.setText(text)

    def _show_bubble_context_menu(self, position):
        """Show context menu for bubble text selection."""
        if not hasattr(self, "label") or not self.label:
            return

        # Create context menu
        menu = QMenu(self.label)

        # Standard text actions
        copy_action = menu.addAction("Copy")
        copy_action.setEnabled(self.label.hasSelectedText())
        copy_action.triggered.connect(self._copy_text)

        menu.addSeparator()

        select_all_action = menu.addAction("Select All")
        select_all_action.triggered.connect(self._select_all_text)

        menu.addSeparator()

        # Get selected text
        selected_text = self.label.selectedText()
        has_selection = bool(selected_text and selected_text.strip())

        # TTS option (only if text is selected)
        tts_action = menu.addAction("Read with TTS")
        tts_action.setEnabled(has_selection)
        if has_selection:
            tts_action.triggered.connect(
                lambda: self.text_selected_for_tts.emit(selected_text)
            )

        # Image generation option (only if text is selected)
        image_action = menu.addAction("Generate Image")
        image_action.setEnabled(has_selection)
        if has_selection:
            image_action.triggered.connect(
                lambda: self.text_selected_for_image.emit(selected_text)
            )

        # Show menu at cursor position
        menu.exec(self.label.mapToGlobal(position))

    def _copy_text(self):
        """Copy selected text to clipboard."""
        if hasattr(self, "label") and self.label:
            selected_text = self.label.selectedText()
            if selected_text:
                from PySide6.QtWidgets import QApplication

                clipboard = QApplication.clipboard()
                clipboard.setText(selected_text)

    def _select_all_text(self):
        """Select all text in label and copy to clipboard."""
        if hasattr(self, "label") and self.label:
            text = self.label.text()
            if text:
                from PySide6.QtWidgets import QApplication

                clipboard = QApplication.clipboard()
                clipboard.setText(text)
                # Show feedback
                self.label.setToolTip("All text copied to clipboard")

    def eventFilter(self, obj, event):
        """Event filter for image label double-click."""
        if obj == self.image_label and hasattr(self, "image_path") and self.image_path:
            if event.type() == QEvent.Type.MouseButtonDblClick:
                self.open_image_in_default_program()
                return True
        return super().eventFilter(obj, event)

    def open_image_in_default_program(self):
        """Open image in default system program."""
        if not self.image_path or not os.path.exists(self.image_path):
            return

        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(self.image_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", self.image_path], check=False)
            else:  # Linux and others
                subprocess.run(["xdg-open", self.image_path], check=False)
        except Exception as e:
            print(f"Error opening image: {e}")


class TypingIndicator(QFrame):
    """Animated typing indicator showing dots."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dots = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_dots)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)

        self.label = QLabel("Generating")
        self.label.setStyleSheet(
            """
            QLabel {
                color: #A0A0A0;
                font-size: 14px;
                font-style: italic;
            }
        """
        )
        layout.addWidget(self.label)

        self.setLayout(layout)
        self.setStyleSheet(
            """
            QFrame {
                background: #2D2D2D;
                border: 1px solid #404040;
                border-radius: 12px;
                margin: 4px 4px 4px 60px;
            }
        """
        )

        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

    def start(self):
        """Start the typing animation."""
        self.dots = 0
        self.timer.start(500)  # Update every 500ms
        self.update_dots()

    def stop(self):
        """Stop the typing animation."""
        self.timer.stop()

    def update_dots(self):
        """Update the dots animation."""
        self.dots = (self.dots + 1) % 4
        dots_text = "." * self.dots
        self.label.setText(f"Generating{dots_text}")


class ChatWidget(QWidget):
    """Main chat widget with message display and input."""

    message_sent = Signal(str, str)  # Signal(message, image_path)
    image_prompt_sent = Signal(str)  # Signal for image generation
    seed_lock_toggled = Signal(bool)  # Signal for seed lock toggle
    text_selected_for_tts = Signal(str)  # Signal when text is selected for TTS
    text_selected_for_image = Signal(
        str
    )  # Signal when text is selected for image generation

    def __init__(self, ollama_client: OllamaClient):
        """
        Initialize ChatWidget.

        Args:
            ollama_client: OllamaClient instance
        """
        super().__init__()
        self.ollama_client = ollama_client
        self.current_ai_bubble = None
        self.image_mode = False  # Toggle for image generation mode
        self.seed_locked = False  # Seed lock state
        self.typing_indicator = None  # Typing indicator widget
        
        # Image handling
        self.image_processor = ImageProcessor()
        self.last_uploaded_image = None  # Path to last uploaded image

        # Debounce timer for scroll (prevents too frequent scrolling)
        self.scroll_timer = QTimer()
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self._do_scroll)
        self.pending_scroll = False

        # Enable drag and drop
        self.setAcceptDrops(True)

        self.init_ui()

    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Messages area (scrollable)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout()
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_layout.setContentsMargins(12, 12, 12, 12)
        self.messages_layout.setSpacing(8)
        self.messages_container.setLayout(self.messages_layout)

        scroll_area.setWidget(self.messages_container)
        layout.addWidget(scroll_area, stretch=1)

        # Input area
        self.input_frame = QFrame()
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(8)

        # Image mode toggle button
        self.image_mode_btn = QPushButton()
        self.image_mode_btn.setCheckable(True)
        self.image_mode_btn.setToolTip("Toggle image generation mode")
        self.image_mode_btn.setMaximumWidth(40)
        self.image_mode_btn.setMaximumHeight(40)
        MaterialIcons.apply_to_button(
            self.image_mode_btn, MaterialIcons.CHAT_SVG, size=20, keep_text=False
        )
        self.image_mode_btn.toggled.connect(self.toggle_image_mode)
        input_layout.addWidget(self.image_mode_btn)

        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Type your message...")
        self.input_field.setMaximumHeight(100)
        self.input_field.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        # Optimize for better performance
        self.input_field.setAcceptRichText(False)  # Faster without rich text
        # Enable drag and drop for input field
        self.input_field.setAcceptDrops(True)
        input_layout.addWidget(self.input_field, stretch=1)

        # Seed lock button (only visible in image mode)
        self.seed_lock_btn = QPushButton()
        self.seed_lock_btn.setCheckable(True)
        self.seed_lock_btn.setToolTip(
            "Lock seed for reproducibility (unlocked = random)"
        )
        self.seed_lock_btn.setMaximumWidth(40)
        self.seed_lock_btn.setMaximumHeight(40)
        self.seed_lock_btn.setVisible(False)  # Hidden by default (chat mode)
        MaterialIcons.apply_to_button(
            self.seed_lock_btn, MaterialIcons.LOCK_OPEN_SVG, size=18, keep_text=False
        )
        self.seed_lock_btn.toggled.connect(self.on_seed_lock_toggled)
        input_layout.addWidget(self.seed_lock_btn)

        self.send_btn = QPushButton("Send")
        self.send_btn.setMinimumWidth(0)  # Allow shrinking
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)

        # Status indicator (for showing when LLM is generating)
        self.status_indicator = QLabel("")
        self.status_indicator.setMaximumWidth(20)
        self.status_indicator.setMaximumHeight(20)
        self.status_indicator.setVisible(False)
        input_layout.addWidget(self.status_indicator)

        self.input_frame.setLayout(input_layout)
        layout.addWidget(self.input_frame)
        
        # Set initial style for chat mode
        self._update_input_area_style()

        self.setLayout(layout)

        # Welcome message
        self.add_welcome_message()

    def add_welcome_message(self):
        """Add welcome message."""
        welcome = ChatBubble(
            "Welcome to locAI! Select a model above and start chatting.", is_user=False
        )
        # Connect bubble signals to widget signals
        welcome.text_selected_for_tts.connect(self.text_selected_for_tts.emit)
        welcome.text_selected_for_image.connect(self.text_selected_for_image.emit)
        self.messages_layout.addWidget(welcome)
        self.messages_layout.addStretch()

    def add_user_message(self, message: str, image_path: str = None):
        """Add user message to chat."""
        # If message is empty but image exists, show image-only message
        display_message = message if message else "📷 Image"
        bubble = ChatBubble(display_message, is_user=True, image_path=image_path)
        # Connect bubble signals to widget signals
        bubble.text_selected_for_tts.connect(self.text_selected_for_tts.emit)
        bubble.text_selected_for_image.connect(self.text_selected_for_image.emit)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self.scroll_to_bottom()

    def start_ai_message(self):
        """Start a new AI message (for streaming)."""
        # Show typing indicator instead of empty bubble
        if self.typing_indicator is None:
            self.typing_indicator = TypingIndicator()
            self.messages_layout.insertWidget(
                self.messages_layout.count() - 1, self.typing_indicator
            )
            self.typing_indicator.start()

        self.scroll_to_bottom()
        # Show status indicator
        self.status_indicator.setVisible(True)
        self.status_indicator.setStyleSheet(
            """
            QLabel {
                background-color: #4A9EFF;
                border-radius: 12px;
            }
        """
        )
        self.status_indicator.setToolTip("Generating response...")

    def append_ai_chunk(self, chunk: str):
        """Append chunk to current AI message (streaming)."""
        # Hide typing indicator and create bubble on first chunk
        if self.current_ai_bubble is None:
            # Remove typing indicator if it exists
            if self.typing_indicator is not None:
                self.typing_indicator.stop()
                self.messages_layout.removeWidget(self.typing_indicator)
                self.typing_indicator.deleteLater()
                self.typing_indicator = None

            # Create AI bubble
            self.current_ai_bubble = ChatBubble("", is_user=False)
            # Connect bubble signals to widget signals
            self.current_ai_bubble.text_selected_for_tts.connect(
                self.text_selected_for_tts.emit
            )
            self.current_ai_bubble.text_selected_for_image.connect(
                self.text_selected_for_image.emit
            )
            self.messages_layout.insertWidget(
                self.messages_layout.count() - 1, self.current_ai_bubble
            )

        self.current_ai_bubble.add_text(chunk)
        # Debounced scroll - only scroll every 150ms max (increased to reduce UI updates)
        self.pending_scroll = True
        if not self.scroll_timer.isActive():
            self.scroll_timer.start(150)  # Scroll max every 150ms

    def finish_ai_message(self):
        """Finish current AI message."""
        # Remove typing indicator if still visible
        if self.typing_indicator is not None:
            self.typing_indicator.stop()
            self.messages_layout.removeWidget(self.typing_indicator)
            self.typing_indicator.deleteLater()
            self.typing_indicator = None

        self.current_ai_bubble = None
        self.scroll_to_bottom()
        # Hide status indicator
        self.status_indicator.setVisible(False)

    def add_assistant_message(self, message: str):
        """Add complete assistant message (for loading saved chats)."""
        bubble = ChatBubble(message, is_user=False)
        # Connect bubble signals to widget signals
        bubble.text_selected_for_tts.connect(self.text_selected_for_tts.emit)
        bubble.text_selected_for_image.connect(self.text_selected_for_image.emit)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self.scroll_to_bottom()

    def _do_scroll(self):
        """Actually perform scroll (called by timer)."""
        if not self.pending_scroll:
            return
        self.pending_scroll = False

        scroll_area = self.findChild(QScrollArea)
        if scroll_area:
            scrollbar = scroll_area.verticalScrollBar()
            # Only scroll if near bottom (within 50px) to avoid interrupting user
            if scrollbar.maximum() - scrollbar.value() < 50:
                scrollbar.setValue(scrollbar.maximum())

    def scroll_to_bottom(self):
        """Scroll messages area to bottom (immediate, for user actions)."""
        scroll_area = self.findChild(QScrollArea)
        if scroll_area:
            scrollbar = scroll_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        self.pending_scroll = False
        self.scroll_timer.stop()

    def toggle_image_mode(self, checked: bool):
        """Toggle between chat and image generation mode."""
        self.image_mode = checked
        if checked:
            MaterialIcons.apply_to_button(
                self.image_mode_btn, MaterialIcons.IMAGE_SVG, size=20, keep_text=False
            )
            self.image_mode_btn.setToolTip(
                "Image generation mode - Click to switch to chat"
            )
            self.input_field.setPlaceholderText(
                "Describe the image you want to generate..."
            )
            # Show seed lock button in image mode
            self.seed_lock_btn.setVisible(True)
        else:
            MaterialIcons.apply_to_button(
                self.image_mode_btn, MaterialIcons.CHAT_SVG, size=20, keep_text=False
            )
            self.image_mode_btn.setToolTip(
                "Chat mode - Click to switch to image generation"
            )
            self.input_field.setPlaceholderText("Type your message...")
            # Hide seed lock button in chat mode
            self.seed_lock_btn.setVisible(False)
        
        # Update visual style based on mode
        self._update_input_area_style()
        
        # Update seed lock button style if visible
        if self.seed_lock_btn.isVisible():
            self.update_seed_lock_button()
    
    def _update_input_area_style(self):
        """Update input area style based on current mode."""
        if self.image_mode:
            # Image mode - purple/violet theme
            self.input_frame.setStyleSheet("""
                QFrame {
                    background: #2D1B3D;
                    border: 2px solid #9B59B6;
                    border-radius: 10px;
                }
            """)
            self.input_field.setStyleSheet("""
                QTextEdit {
                    background: #3D2B4D;
                    color: #E0E0E0;
                    border: 1px solid #9B59B6;
                    border-radius: 10px;
                    padding: 8px 12px;
                    font-size: 14px;
                }
                QTextEdit:focus {
                    border: 2px solid #9B59B6;
                    background: #4D3B5D;
                }
            """)
            # Update image mode button to show it's active
            self.image_mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: #9B59B6;
                    border: 2px solid #8E44AD;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #8E44AD;
                }
                QPushButton:pressed {
                    background-color: #7D3C98;
                }
            """)
            # Update Send button to purple theme
            self.send_btn.setStyleSheet("""
                QPushButton {
                    background-color: #9B59B6;
                    color: white;
                    border: none;
                    border-radius: 10px;
                    padding: 8px 16px;
                    font-weight: 500;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #8E44AD;
                }
                QPushButton:pressed {
                    background-color: #7D3C98;
                }
            """)
            # Update seed lock button - use update_seed_lock_button to handle locked/unlocked states
            # This will set purple for unlocked, red for locked
            if self.seed_lock_btn.isVisible():
                self.update_seed_lock_button()
        else:
            # Chat mode - default blue theme (explicitly reset to match theme)
            self.input_frame.setStyleSheet("""
                QFrame {
                    background: transparent;
                    border: none;
                }
            """)
            # Reset input field to default theme style
            self.input_field.setStyleSheet("""
                QTextEdit {
                    background: #2D2D2D;
                    color: #E0E0E0;
                    border: 1px solid #404040;
                    border-radius: 10px;
                    padding: 8px 12px;
                    font-size: 14px;
                }
                QTextEdit:focus {
                    border: 2px solid #4A9EFF;
                }
            """)
            # Reset image mode button to default theme style
            self.image_mode_btn.setStyleSheet("""
                QPushButton {
                    background: #4A9EFF;
                    color: white;
                    border: none;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background: #3A3A3A;
                }
                QPushButton:pressed {
                    background: #FF6B6B;
                }
            """)
            # Reset Send button to default theme style
            self.send_btn.setStyleSheet("""
                QPushButton {
                    background: #4A9EFF;
                    color: white;
                    border: none;
                    border-radius: 10px;
                    padding: 8px 16px;
                    font-weight: 500;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: #3A3A3A;
                }
                QPushButton:pressed {
                    background: #FF6B6B;
                }
            """)
            # Reset seed lock button (will be updated by update_seed_lock_button if visible)
            # But since it's hidden in chat mode, we don't need to reset it

    def on_seed_lock_toggled(self, checked: bool):
        """Handle seed lock toggle."""
        self.seed_locked = checked
        self.update_seed_lock_button()
        self.seed_lock_toggled.emit(checked)

    def update_seed_lock_button(self):
        """Update seed lock button appearance."""
        if self.seed_locked:
            MaterialIcons.apply_to_button(
                self.seed_lock_btn, MaterialIcons.LOCK_SVG, size=18, keep_text=False
            )
            self.seed_lock_btn.setToolTip(
                "Seed locked - Using same seed for all images"
            )
            # Red background when locked (same in both modes)
            self.seed_lock_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #EF5350;
                    border: 2px solid #E53935;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #E53935;
                }
                QPushButton:pressed {
                    background-color: #C62828;
                }
            """
            )
        else:
            MaterialIcons.apply_to_button(
                self.seed_lock_btn,
                MaterialIcons.LOCK_OPEN_SVG,
                size=18,
                keep_text=False,
            )
            self.seed_lock_btn.setToolTip("Seed unlocked - Random seed for each image")
            # Use purple theme in image mode, blue in chat mode
            if self.image_mode:
                self.seed_lock_btn.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #9B59B6;
                        border: none;
                        border-radius: 10px;
                    }
                    QPushButton:hover {
                        background-color: #8E44AD;
                    }
                    QPushButton:pressed {
                        background-color: #7D3C98;
                    }
                """
                )
            else:
                # Default blue theme style when unlocked in chat mode
                self.seed_lock_btn.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #4A9EFF;
                        border: none;
                        border-radius: 10px;
                    }
                    QPushButton:hover {
                        background-color: #3A3A3A;
                    }
                    QPushButton:pressed {
                        background-color: #FF6B6B;
                    }
                """
                )

    def send_message(self):
        """Send message from input field."""
        message = self.input_field.toPlainText().strip()
        if not message and not self.last_uploaded_image:
            return

        # Get image path if available
        image_path = self.last_uploaded_image

        # Clear input
        self.input_field.clear()
        
        # Clear uploaded image after sending
        self.last_uploaded_image = None

        # Emit appropriate signal based on mode
        if self.image_mode:
            self.image_prompt_sent.emit(message)
        else:
            self.message_sent.emit(message, image_path or "")

    def add_image_message(self, image_path: str, prompt: str = ""):
        """Add image message to chat."""
        bubble = ChatBubble(prompt, is_user=False, image_path=image_path)
        # Connect bubble signals to widget signals
        bubble.text_selected_for_tts.connect(self.text_selected_for_tts.emit)
        bubble.text_selected_for_image.connect(self.text_selected_for_image.emit)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self.scroll_to_bottom()

    def clear_messages(self):
        """Clear all messages."""
        while self.messages_layout.count() > 1:  # Keep stretch
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.current_ai_bubble = None
        self.add_welcome_message()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event for image drop."""
        if event.mimeData().hasUrls():
            # Check if any of the URLs is a supported image
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path and self.image_processor.is_supported_image(file_path):
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event for image upload."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path and self.image_processor.is_supported_image(file_path):
                    self.handle_image_upload(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def handle_image_upload(self, image_path: str):
        """Handle image upload from drag & drop."""
        if not os.path.exists(image_path):
            QMessageBox.warning(
                self,
                "File Not Found",
                f"Image file not found: {image_path}"
            )
            return
        
        # Get image info
        img_info = self.image_processor.get_image_info(image_path)
        if not img_info:
            QMessageBox.warning(
                self,
                "Invalid Image",
                "Could not read image file. Please ensure it's a valid image."
            )
            return
        
        # Check file size (max 50MB)
        if img_info["file_size_mb"] > 50:
            QMessageBox.warning(
                self,
                "File Too Large",
                f"Image file is too large ({img_info['file_size_mb']}MB). Maximum size is 50MB."
            )
            return
        
        # Store as last uploaded image
        self.last_uploaded_image = image_path
        
        # Show image in chat immediately
        upload_msg = f"📁 Image uploaded: {os.path.basename(image_path)} ({img_info['width']}x{img_info['height']}, {img_info['file_size_mb']}MB)"
        bubble = ChatBubble(upload_msg, is_user=True, image_path=image_path)
        bubble.text_selected_for_tts.connect(self.text_selected_for_tts.emit)
        bubble.text_selected_for_image.connect(self.text_selected_for_image.emit)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self.scroll_to_bottom()
        
        print(f"Image uploaded: {image_path} ({img_info['width']}x{img_info['height']})")
