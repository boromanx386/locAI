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
from PySide6.QtCore import Signal, Qt, QTimer, QEvent, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QFont,
    QPixmap,
    QMouseEvent,
    QContextMenuEvent,
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QKeyEvent,
    QTextOption,
    QDesktopServices,
)
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QSizePolicy
import re
from lokai.core.ollama_client import OllamaClient
from lokai.core.image_processor import ImageProcessor
from lokai.core.config_manager import ConfigManager
from lokai.ui.material_icons import MaterialIcons
from lokai.ui.attachments import (
    is_allowed_attachment,
    format_file_size,
    is_probably_binary,
)
import os
import subprocess
import platform


class ChatInputField(QTextEdit):
    """Custom QTextEdit that handles Enter for send and Shift+Enter for new line.
    Does not accept file drops; drop is on the input frame so the cursor stays ok."""

    send_requested = Signal()  # Signal emitted when Enter is pressed (without Shift)
    mode_change_requested = Signal()  # Signal emitted when Shift+Tab is pressed

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events."""
        # If Shift+Tab is pressed, cycle mode
        if (
            event.key() == Qt.Key.Key_Backtab
            and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.mode_change_requested.emit()
            event.accept()
            return

        # If Enter is pressed without Shift, send message
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Shift+Enter: insert new line (default behavior)
                super().keyPressEvent(event)
            else:
                # Enter alone: send message
                self.send_requested.emit()
                event.accept()
        else:
            # All other keys: default behavior
            super().keyPressEvent(event)

    # No dragEnterEvent/dropEvent: file drop is on the input frame (parent) so cursor does not break


class ChatBubbleTextEdit(QTextEdit):
    """Custom QTextEdit for chat bubbles that prevents scrolling."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._update_height_callback = None
        # Enable mouse tracking for real-time cursor updates
        self.setMouseTracking(True)
        # Set default cursor to arrow on viewport (not I-beam for text selection)
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        # Install event filter on viewport to control cursor
        self.viewport().installEventFilter(self)

    def set_update_height_callback(self, callback):
        """Set callback to update height when widget resizes."""
        self._update_height_callback = callback

    def resizeEvent(self, event):
        """Handle resize events to update text height."""
        super().resizeEvent(event)
        # Update height when widget is resized (e.g., window resize)
        if self._update_height_callback:
            QTimer.singleShot(10, self._update_height_callback)

    def wheelEvent(self, event):
        """Block wheel events to prevent scrolling."""
        # Ignore wheel events - don't scroll
        event.ignore()
        # Pass to parent to allow chat area scrolling
        if self.parent():
            self.parent().wheelEvent(event)

    def scrollContentsBy(self, dx, dy):
        """Prevent programmatic scrolling."""
        # Don't scroll - keep text at top
        pass

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events - allow text selection but prevent scrolling keys."""
        # Block keys that would cause scrolling
        if event.key() in (
            Qt.Key.Key_Up,
            Qt.Key.Key_Down,
            Qt.Key.Key_PageUp,
            Qt.Key.Key_PageDown,
            Qt.Key.Key_Home,
            Qt.Key.Key_End,
        ):
            # Ignore scrolling keys - don't process them
            event.ignore()
            return

        # Allow all other keys (text selection, copy, etc.)
        super().keyPressEvent(event)

        # After any key press, ensure we're at the top
        QTimer.singleShot(0, lambda: self.verticalScrollBar().setValue(0))

    def eventFilter(self, obj, event):
        """Event filter to control cursor on viewport."""
        if obj == self.viewport() and event.type() == QEvent.Type.MouseMove:
            # Check if over a link
            try:
                pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
            except:
                pos = event.pos()
            anchor = self.anchorAt(pos)
            if anchor:
                self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        return super().eventFilter(obj, event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move events to change cursor based on link position."""
        # Call super first, then override cursor
        super().mouseMoveEvent(event)
        # Use pos() for compatibility (PySide6/Qt6)
        try:
            pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        except:
            pos = event.pos()
        anchor = self.anchorAt(pos)
        if anchor:
            # Show pointing hand cursor over links
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            # Show arrow cursor (not I-beam) when not over links
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events to open links."""
        # Check if clicked position is on a link
        # Use pos() for compatibility (PySide6/Qt6)
        try:
            pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        except:
            pos = event.pos()
        anchor = self.anchorAt(pos)
        if anchor:
            # Open link in default browser
            QDesktopServices.openUrl(QUrl(anchor))
            event.accept()
            return
        
        # Otherwise, use default behavior (text selection)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click to copy code block (like Ollama app)."""
        # Default behavior (no special handling – right-click menu handles code copy)
        super().mouseDoubleClickEvent(event)


class ChatBubble(QFrame):
    """Individual chat message bubble."""

    # Signals for context menu actions
    text_selected_for_tts = Signal(str)
    text_selected_for_image = Signal(str)
    text_selected_for_audio = Signal(str)
    image_selected_for_video = Signal(str)  # image_path
    # Manual semantic memory (RAG) actions
    remember_selected_text = Signal(str, str, int)  # text, role, message_index
    remember_message = Signal(str, str, int)  # full_text, role, message_index
    memory_stats_requested = Signal()

    def __init__(
        self,
        message: str = "",
        is_user: bool = True,
        image_path: str = None,
        audio_path: str = None,
        message_index: int = -1,
        parent=None,
    ):
        """
        Initialize ChatBubble.

        Args:
            message: Message text
            is_user: True if user message, False if AI message
            image_path: Optional path to image to display
            audio_path: Optional path to audio file to display with waveform
            parent: Parent widget
        """
        super().__init__(parent)
        self.is_user = is_user
        self.current_text = message
        self.image_path = image_path
        self.audio_path = audio_path
        self.message_index = message_index
        self.message_role = "user" if is_user else "assistant"
        # Throttle streaming UI updates (timer created when label exists in add_text)
        self._stream_refresh_timer = None

        self.init_ui()

    def set_message_metadata(self, *, role: str = None, message_index: int = None):
        """Attach metadata so context menu actions know what they refer to."""
        if role is not None:
            self.message_role = role
        if message_index is not None:
            self.message_index = message_index

    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Add audio player if provided
        if self.audio_path:
            from lokai.ui.audio_player_widget import AudioPlayerWidget
            self.audio_player = AudioPlayerWidget(self.audio_path)
            layout.addWidget(self.audio_player)
        else:
            self.audio_player = None

        # Add image if provided
        if self.image_path:
            self.image_label = QLabel()
            self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.image_label.setMaximumHeight(400)
            self.image_label.setMaximumWidth(500)
            self.image_label.setScaledContents(False)

            # Install event filter for double-click and right-click detection
            self.image_label.installEventFilter(self)
            # Enable context menu for right-click
            self.image_label.setContextMenuPolicy(
                Qt.ContextMenuPolicy.CustomContextMenu
            )
            self.image_label.customContextMenuRequested.connect(
                self._show_image_context_menu
            )

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

        # Message label (using QTextEdit for markdown support)
        if self.current_text:
            self.label = ChatBubbleTextEdit()
            self.label.setReadOnly(True)
            self.label.setHtml(self._format_markdown(self.current_text))
            self.label.setWordWrapMode(
                QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere
            )
            self.label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
                | Qt.TextInteractionFlag.LinksAccessibleByMouse
                | Qt.TextInteractionFlag.LinksAccessibleByKeyboard
            )
            # Set alignment
            if self.is_user:
                self.label.setAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
                )
            else:
                self.label.setAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                )
            # Remove borders and background for seamless look
            self.label.setFrameShape(QTextEdit.Shape.NoFrame)
            self.label.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.label.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            # Prevent scrolling - keep text at top
            self.label.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            # Set size policy to allow auto-resizing
            self.label.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
            )
            # Auto-resize to content - update height based on document
            self.label.document().contentsChanged.connect(self._update_text_height)
            # Set callback for resize events
            self.label.set_update_height_callback(self._update_text_height)
            # Initial update
            QTimer.singleShot(50, self._update_text_height)
            # Ensure text stays at top (no scrolling)
            QTimer.singleShot(100, lambda: self.label.verticalScrollBar().setValue(0))
            # Enable context menu
            self.label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.label.customContextMenuRequested.connect(
                self._show_bubble_context_menu
            )
            # Store reference to bubble in label for code block detection
            self.label._parent_bubble = self
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
                QTextEdit {
                    color: white;
                    font-size: 14px;
                    padding: 4px 4px 8px 4px;
                    background: transparent;
                    border: none;
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
                QTextEdit {
                    color: #E0E0E0;
                    font-size: 14px;
                    padding: 4px 4px 8px 4px;
                    background: transparent;
                    border: none;
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

    def _update_text_height(self):
        """Update QTextEdit height to match content exactly."""
        if not hasattr(self, "label") or not self.label:
            return

        doc = self.label.document()
        # Set text width to match widget width for proper wrapping
        text_width = self.label.viewport().width()
        if text_width > 0:
            doc.setTextWidth(text_width)

        # Get document height after wrapping
        doc_height = doc.size().height()

        # If document height is 0 or very small, try again after a short delay
        if doc_height < 5:
            QTimer.singleShot(10, self._update_text_height)
            return

        # Add padding for descenders (g, j, q, p, y) - extra bottom padding
        # Base padding + extra for descenders
        new_height = int(doc_height) + 16  # Increased from 10 to 16 for descenders

        # Use setMinimumHeight and setMaximumHeight instead of setFixedHeight
        # This allows the widget to grow/shrink naturally
        self.label.setMinimumHeight(new_height)
        self.label.setMaximumHeight(new_height)

        # Ensure text stays at top (no scrolling) after height update
        QTimer.singleShot(10, lambda: self.label.verticalScrollBar().setValue(0))

    def _format_markdown(self, text: str) -> str:
        """
        Convert markdown to HTML for display.

        Args:
            text: Markdown text

        Returns:
            HTML formatted text
        """
        if not text:
            return ""

        # Link color: visible on user (blue) vs assistant (dark) bubble
        link_color = "#FFFFFF" if self.is_user else "#4A9EFF"

        # Escape HTML first
        html = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Bold: **text** -> <b>text</b> (do this first)
        html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)

        # Italic: *text* -> <i>text</i> (only single asterisks that aren't part of **)
        # Match single asterisks that aren't adjacent to other asterisks
        html = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", html)

        # Code blocks: ```code``` -> <pre><code>code</code></pre>
        html = re.sub(
            r"```([\s\S]*?)```",
            r'<pre style="background: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px; overflow-x: auto;"><code>\1</code></pre>',
            html,
        )

        # Inline code: `code` -> <code>code</code>
        html = re.sub(
            r"`([^`]+?)`",
            r'<code style="background: rgba(0,0,0,0.2); padding: 2px 4px; border-radius: 3px; font-family: monospace;">\1</code>',
            html,
        )

        # Links: [text](url) -> <a href="url">text</a> (markdown format)
        # IMPORTANT: Only allow http/https URLs to avoid javascript:/file:/data: XSS vectors.
        def _replace_markdown_link(match: re.Match) -> str:
            link_text = match.group(1)
            url = (match.group(2) or "").strip()

            # Only allow http/https URLs, and reject ones containing quotes to keep href safe
            url_lower = url.lower()
            if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
                return link_text
            if '"' in url or "'" in url:
                return link_text

            return (
                f'<a href="{url}" '
                f'style="color: {link_color}; text-decoration: underline;">'
                f"{link_text}</a>"
            )

        html = re.sub(r"\[([^\]]+?)\]\(([^\)]+?)\)", _replace_markdown_link, html)

        # Plain URLs: http://... or https://... -> <a href="url">url</a>
        # Only match URLs that aren't already inside <a> tags.
        # Use a greedy match for the URL and then strip trailing punctuation
        # like '.', ',', ')', '!' which models sometimes append.
        def _replace_plain_url(match: re.Match) -> str:
            url = match.group(1)
            # Strip common trailing punctuation that is usually not part of URL
            while url and url[-1] in ".,!?)":
                url = url[:-1]
            return (
                f'<a href="{url}" '
                f'style="color: {link_color}; text-decoration: underline;">'
                f"{url}</a>"
            )

        html = re.sub(
            r'(?<!href=")(?<!>)(https?://[^\s<>"{}|\\^`\[\]]+)(?![^<]*</a>)',
            _replace_plain_url,
            html,
        )

        # Headers
        html = re.sub(
            r"^### (.+)$",
            r'<h3 style="margin: 8px 0 4px 0; font-size: 1.1em;">\1</h3>',
            html,
            flags=re.MULTILINE,
        )
        html = re.sub(
            r"^## (.+)$",
            r'<h2 style="margin: 10px 0 6px 0; font-size: 1.2em;">\1</h2>',
            html,
            flags=re.MULTILINE,
        )
        html = re.sub(
            r"^# (.+)$",
            r'<h1 style="margin: 12px 0 8px 0; font-size: 1.3em;">\1</h1>',
            html,
            flags=re.MULTILINE,
        )

        # Line breaks
        html = html.replace("\n", "<br>")

        return html

    def add_text(self, text: str):
        """Add text to bubble (for streaming). Throttles setHtml to avoid UI freeze on long responses."""
        self.current_text += text
        # Create label if it doesn't exist
        if not hasattr(self, "label") or self.label is None:
            from PySide6.QtCore import Qt
            from PySide6.QtGui import QTextOption

            self.label = ChatBubbleTextEdit()
            self.label.setReadOnly(True)
            self.label.setHtml(self._format_markdown(self.current_text))
            self.label.setWordWrapMode(
                QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere
            )
            self.label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
                | Qt.TextInteractionFlag.LinksAccessibleByMouse
                | Qt.TextInteractionFlag.LinksAccessibleByKeyboard
            )
            if self.is_user:
                self.label.setAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
                )
            else:
                self.label.setAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                )
            self.label.setFrameShape(QTextEdit.Shape.NoFrame)
            self.label.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.label.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            # Set size policy to allow auto-resizing
            self.label.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
            )
            # Auto-resize to content - update height based on document
            self.label.document().contentsChanged.connect(self._update_text_height)
            # Set callback for resize events
            self.label.set_update_height_callback(self._update_text_height)
            # Initial update
            QTimer.singleShot(50, self._update_text_height)
            # Ensure text stays at top (no scrolling)
            QTimer.singleShot(100, lambda: self.label.verticalScrollBar().setValue(0))
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
            # Throttle: refresh at most every 50ms to avoid blocking UI on long streams
            if self._stream_refresh_timer is None:
                self._stream_refresh_timer = QTimer(self)
                self._stream_refresh_timer.setSingleShot(True)
                self._stream_refresh_timer.timeout.connect(self._flush_stream_display)
            if not self._stream_refresh_timer.isActive():
                self._stream_refresh_timer.start(50)
    def _flush_stream_display(self):
        """Apply current_text to label (throttled streaming refresh)."""
        if not hasattr(self, "label") or self.label is None:
            return
        self.label.setHtml(self._format_markdown(self.current_text))
        QTimer.singleShot(0, self._update_text_height)
        QTimer.singleShot(10, lambda: self.label.verticalScrollBar().setValue(0))

    def flush_display(self):
        """Flush pending streaming content to label immediately (call when stream ends)."""
        if self._stream_refresh_timer is not None and self._stream_refresh_timer.isActive():
            self._stream_refresh_timer.stop()
        self._flush_stream_display()

    def set_text(self, text: str):
        """Set complete text."""
        self.current_text = text
        if hasattr(self, "label") and self.label:
            self.label.setHtml(self._format_markdown(text))
            # Update height after setting new content
            QTimer.singleShot(0, self._update_text_height)

    def _show_bubble_context_menu(self, position):
        """Show context menu for bubble text selection."""
        if not hasattr(self, "label") or not self.label:
            return

        # Create context menu
        menu = QMenu(self.label)

        # Standard text actions
        # For QTextEdit, check if text is selected using textCursor
        cursor = self.label.textCursor()
        has_selection = cursor.hasSelection()

        copy_action = menu.addAction("Copy")
        copy_action.setEnabled(has_selection)
        copy_action.triggered.connect(self._copy_text)

        menu.addSeparator()

        select_all_action = menu.addAction("Select All")
        select_all_action.triggered.connect(self._select_all_text)

        menu.addSeparator()

        # Get selected text
        if has_selection:
            selected_text = cursor.selectedText()
        else:
            selected_text = ""

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

        # Audio generation option (only if text is selected)
        audio_action = menu.addAction("Generate Audio")
        audio_action.setEnabled(has_selection)
        if has_selection:
            audio_action.triggered.connect(
                lambda: self.text_selected_for_audio.emit(selected_text)
            )

        menu.addSeparator()

        # Check if message contains code blocks
        code_blocks = self._extract_code_blocks()
        if code_blocks:
            if len(code_blocks) == 1:
                # Single block – one flat action
                block = code_blocks[0]
                copy_code_action = menu.addAction("Copy code block")
                copy_code_action.triggered.connect(
                    lambda _checked=False, b=block: self._copy_code_block(b["code"])
                )
            else:
                # Multiple blocks – submenu with one action per block
                copy_menu = menu.addMenu("Copy code block")
                for idx, block in enumerate(code_blocks, start=1):
                    lang = block["language"] or "code"
                    action = copy_menu.addAction(f"Block {idx} ({lang})")
                    action.triggered.connect(
                        lambda _checked=False, b=block: self._copy_code_block(b["code"])
                    )

        # Manual semantic memory (RAG) actions
        menu.addSeparator()
        remember_selection_action = menu.addAction("Remember selection")
        remember_selection_action.setEnabled(has_selection)
        if has_selection:
            remember_selection_action.triggered.connect(
                lambda: self.remember_selected_text.emit(
                    selected_text, self.message_role, self.message_index
                )
            )

        remember_message_action = menu.addAction("Remember whole message")
        full_plain_text = self.label.toPlainText() if hasattr(self, "label") and self.label else ""
        remember_message_action.setEnabled(bool(full_plain_text and full_plain_text.strip()))
        if full_plain_text and full_plain_text.strip():
            remember_message_action.triggered.connect(
                lambda: self.remember_message.emit(
                    full_plain_text.strip(), self.message_role, self.message_index
                )
            )

        memory_stats_action = menu.addAction("Memory stats")
        memory_stats_action.triggered.connect(lambda: self.memory_stats_requested.emit())

        # Show menu at cursor position
        menu.exec(self.label.mapToGlobal(position))

    def _copy_text(self):
        """Copy selected text to clipboard."""
        if hasattr(self, "label") and self.label:
            # For QTextEdit, use textCursor to get selected text
            cursor = self.label.textCursor()
            if cursor.hasSelection():
                selected_text = cursor.selectedText()
                from PySide6.QtWidgets import QApplication

                clipboard = QApplication.clipboard()
                clipboard.setText(selected_text)

    def _select_all_text(self):
        """Select all text in label and copy to clipboard."""
        if hasattr(self, "label") and self.label:
            # For QTextEdit, use toPlainText() to get text without HTML
            text = self.label.toPlainText()
            if text:
                from PySide6.QtWidgets import QApplication

                clipboard = QApplication.clipboard()
                clipboard.setText(text)
                # Show feedback
                self.label.setToolTip("All text copied to clipboard")

    def _extract_code_blocks(self) -> list:
        """
        Extract all code blocks from message text.
        
        Returns:
            List of dicts with 'language' and 'code'
        """
        if not hasattr(self, "label") or not self.label:
            return []
        
        # Get original markdown text
        full_text = self.current_text if hasattr(self, "current_text") else self.label.toPlainText()
        if not full_text:
            return []
        
        # Find all code blocks: ```language\ncode\n``` or ```\ncode\n```
        pattern = r'```(\w+)?\n(.*?)```'
        code_blocks: list[dict] = []
        for match in re.finditer(pattern, full_text, re.DOTALL):
            language = (match.group(1) or "").strip()
            code_content = match.group(2).strip()
            if code_content:
                code_blocks.append(
                    {
                        "language": language,
                        "code": code_content,
                    }
                )
        
        return code_blocks

    def _copy_code_block(self, code_content: str):
        """Copy code block content to clipboard."""
        if not code_content:
            return
        
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(code_content)
        
        # Show brief feedback
        if hasattr(self, "label") and self.label:
            self.label.setToolTip("Code block copied to clipboard")
            QTimer.singleShot(2000, lambda: self.label.setToolTip("") if hasattr(self, "label") and self.label else None)

    def _show_image_context_menu(self, position):
        """Show context menu for image (right-click)."""
        if not hasattr(self, "image_path") or not self.image_path:
            return

        menu = QMenu(self.image_label)

        # Open image action
        open_action = menu.addAction("Open Image")
        open_action.triggered.connect(self.open_image_in_default_program)

        menu.addSeparator()

        # Generate video action
        video_action = menu.addAction("Generate Video")
        video_action.triggered.connect(
            lambda: self.image_selected_for_video.emit(self.image_path)
        )

        # Show menu at cursor position
        menu.exec(self.image_label.mapToGlobal(position))

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
    
    def __del__(self):
        """Cleanup resources when bubble is destroyed."""
        # Clean up audio player if it exists
        if hasattr(self, 'audio_player') and self.audio_player is not None:
            try:
                self.audio_player.cleanup()
            except Exception as e:
                print(f"Error cleaning up audio player: {e}")


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
    image_prompt_sent = Signal(str, str)  # Signal(prompt, init_image_path)
    audio_prompt_sent = Signal(str)  # Signal for audio generation
    seed_lock_toggled = Signal(bool)  # Signal for seed lock toggle
    seed_increase_requested = Signal()  # Signal to increase seed
    seed_decrease_requested = Signal()  # Signal to decrease seed
    text_selected_for_tts = Signal(str)  # Signal when text is selected for TTS
    text_selected_for_image = Signal(
        str
    )  # Signal when text is selected for image generation
    text_selected_for_audio = Signal(
        str
    )  # Signal when text is selected for audio generation
    image_selected_for_video = Signal(
        str
    )  # Signal when image is selected for video generation
    # Manual semantic memory (RAG)
    remember_selected_text = Signal(str, str, int)  # text, role, message_index
    remember_message = Signal(str, str, int)  # full_text, role, message_index
    memory_stats_requested = Signal()

    def __init__(
        self, ollama_client: OllamaClient, config_manager: ConfigManager = None
    ):
        """
        Initialize ChatWidget.

        Args:
            ollama_client: OllamaClient instance
            config_manager: ConfigManager instance (optional, for prompts)
        """
        super().__init__()
        self.ollama_client = ollama_client
        self.config_manager = config_manager
        self.current_ai_bubble = None
        self.image_mode = False  # Toggle for image generation mode
        self.audio_mode = False  # Toggle for audio generation mode
        self.seed_locked = False  # Seed lock state
        
        # Auto-stop timer for voice input (30 seconds)
        self.voice_auto_stop_timer = QTimer()
        self.voice_auto_stop_timer.setSingleShot(True)
        self.voice_auto_stop_timer.timeout.connect(self._auto_stop_voice_input)
        self.typing_indicator = None  # Typing indicator widget

        # Image handling
        self.image_processor = ImageProcessor()
        self.last_uploaded_image = None  # Path to last uploaded image

        # Pending file attachments (text/code): list of {path, name, size}
        self.pending_attachments: list[dict] = []
        self._attachment_chips: dict[str, QWidget] = {}  # path -> chip widget

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
        input_frame_v = QVBoxLayout()
        input_frame_v.setContentsMargins(0, 0, 0, 0)
        input_frame_v.setSpacing(4)

        # Attachments row (chips above input) – hidden when empty
        self.attachments_container = QWidget()
        self.attachments_container.setFixedHeight(44)
        self.attachments_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.attachments_layout = QHBoxLayout()
        self.attachments_layout.setContentsMargins(12, 4, 12, 0)
        self.attachments_layout.setSpacing(6)
        self.attachments_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.attachments_layout.addStretch(1)  # at end so chips stay left
        self.attachments_container.setLayout(self.attachments_layout)
        self.attachments_container.hide()
        input_frame_v.addWidget(self.attachments_container)

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(8)

        # Mode toggle button (chat -> image -> audio -> chat)
        self.image_mode_btn = QPushButton()
        self.image_mode_btn.setCheckable(False)  # Not checkable, uses clicked instead
        self.image_mode_btn.setToolTip(
            "Chat mode - Click to switch to image generation"
        )
        self.image_mode_btn.setMaximumWidth(40)
        self.image_mode_btn.setMaximumHeight(40)
        MaterialIcons.apply_to_button(
            self.image_mode_btn, MaterialIcons.CHAT_SVG, size=20, keep_text=False
        )
        self.image_mode_btn.clicked.connect(self.cycle_mode)
        input_layout.addWidget(self.image_mode_btn)

        self.input_field = ChatInputField()
        self.input_field.setPlaceholderText("Type your message...")
        self.input_field.setMaximumHeight(100)
        self.input_field.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        # Optimize for better performance
        self.input_field.setAcceptRichText(False)  # Faster without rich text
        # No drop on input field: drop handled in eventFilter so cursor never breaks
        self.input_field.setAcceptDrops(False)
        self.input_field.installEventFilter(self)
        # Connect Enter key to send message
        self.input_field.send_requested.connect(self.send_message)
        # Connect Shift+Tab to cycle mode
        self.input_field.mode_change_requested.connect(self.cycle_mode)
        input_layout.addWidget(self.input_field, stretch=1)

        # Voice input button (STT) - placed before prompt button
        self.voice_btn = QPushButton()
        self.voice_btn.setToolTip("Voice input (Speech-to-Text)")
        self.voice_btn.setMaximumWidth(32)
        self.voice_btn.setMaximumHeight(32)
        MaterialIcons.apply_to_button(
            self.voice_btn, MaterialIcons.MIC_SVG, size=16, keep_text=False
        )
        self.voice_btn.clicked.connect(self.toggle_voice_input)
        
        # Add shadow effect for pulsing animation
        self.voice_btn_shadow = QGraphicsDropShadowEffect()
        self.voice_btn_shadow.setBlurRadius(10)
        self.voice_btn_shadow.setXOffset(0)
        self.voice_btn_shadow.setYOffset(0)
        self.voice_btn_shadow.setColor(QColor(231, 76, 60, 0))  # Red, invisible when not active
        self.voice_btn.setGraphicsEffect(self.voice_btn_shadow)
        
        # Simple pulsing animation - animate blur radius for visible pulsing effect
        self.voice_btn_animation = QPropertyAnimation(self.voice_btn_shadow, b"blurRadius")
        self.voice_btn_animation.setDuration(500)
        self.voice_btn_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.voice_btn_animation.setLoopCount(-1)
        
        input_layout.addWidget(self.voice_btn)

        # Prompt template button
        self.prompt_btn = QPushButton()
        self.prompt_btn.setToolTip("Insert prompt template")
        self.prompt_btn.setMaximumWidth(32)
        self.prompt_btn.setMaximumHeight(32)
        MaterialIcons.apply_to_button(
            self.prompt_btn, MaterialIcons.BOOK_SVG, size=16, keep_text=False
        )
        self.prompt_btn.clicked.connect(self.show_prompt_menu)
        input_layout.addWidget(self.prompt_btn)

        # Seed controls container (vertical: plus, lock, minus)
        seed_widget = QWidget()
        seed_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        seed_widget.setAutoFillBackground(False)
        seed_layout = QVBoxLayout()
        seed_layout.setContentsMargins(0, 0, 0, 0)
        seed_layout.setSpacing(2)

        # Plus button - transparent QLabel
        self.seed_plus_btn = QLabel()
        self.seed_plus_btn.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True
        )
        self.seed_plus_btn.setAutoFillBackground(False)
        plus_pixmap = MaterialIcons.svg_to_icon(
            MaterialIcons.ADD_SVG, size=12, color="white"
        ).pixmap(12, 12)
        self.seed_plus_btn.setPixmap(plus_pixmap)
        self.seed_plus_btn.setFixedSize(16, 16)
        self.seed_plus_btn.setToolTip("Increase seed")
        self.seed_plus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.seed_plus_btn.hide()
        self.seed_plus_btn.setStyleSheet("background: transparent; border: none;")
        self.seed_plus_btn.mousePressEvent = (
            lambda e: self.seed_increase_requested.emit()
        )
        seed_layout.addWidget(
            self.seed_plus_btn, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        # Seed lock button
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
        seed_layout.addWidget(
            self.seed_lock_btn, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        # Minus button - transparent QLabel
        self.seed_minus_btn = QLabel()
        self.seed_minus_btn.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True
        )
        self.seed_minus_btn.setAutoFillBackground(False)
        minus_pixmap = MaterialIcons.svg_to_icon(
            MaterialIcons.REMOVE_SVG, size=12, color="white"
        ).pixmap(12, 12)
        self.seed_minus_btn.setPixmap(minus_pixmap)
        self.seed_minus_btn.setFixedSize(16, 16)
        self.seed_minus_btn.setToolTip("Decrease seed")
        self.seed_minus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.seed_minus_btn.hide()
        self.seed_minus_btn.setStyleSheet("background: transparent; border: none;")
        self.seed_minus_btn.mousePressEvent = (
            lambda e: self.seed_decrease_requested.emit()
        )
        seed_layout.addWidget(
            self.seed_minus_btn, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        seed_widget.setLayout(seed_layout)
        input_layout.addWidget(seed_widget)

        self.send_btn = QPushButton("Send")
        self.send_btn.setMinimumWidth(0)  # Allow shrinking
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)

        # Status indicator (for showing when LLM is generating)
        self.status_indicator = QLabel("")
        self.status_indicator.setMaximumHeight(24)
        self.status_indicator.setVisible(False)
        self.status_indicator.setStyleSheet("""
            QLabel {
                background-color: rgba(74, 158, 255, 0.2);
                border: 1px solid rgba(74, 158, 255, 0.5);
                border-radius: 12px;
                padding: 4px 10px;
                color: #4A9EFF;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        input_layout.addWidget(self.status_indicator)

        input_frame_v.addLayout(input_layout)
        self.input_frame.setLayout(input_frame_v)
        # Accept file drops on the frame (not on input field) so cursor stays ok
        self.input_frame.setAcceptDrops(True)
        self.input_frame.installEventFilter(self)
        layout.addWidget(self.input_frame)

        # Voice input widget (initially hidden)
        self.voice_input_widget = None
        self._init_voice_input()

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
        welcome.text_selected_for_audio.connect(self.text_selected_for_audio.emit)
        welcome.memory_stats_requested.connect(self.memory_stats_requested.emit)
        self.messages_layout.addWidget(welcome)
        self.messages_layout.addStretch()

    def add_user_message(self, message: str, image_path: str = None, message_index: int = -1):
        """Add user message to chat."""
        # If message is empty but image exists, show image-only message
        display_message = message if message else "📷 Image"
        bubble = ChatBubble(
            display_message, is_user=True, image_path=image_path, message_index=message_index
        )
        # Connect bubble signals to widget signals
        bubble.text_selected_for_tts.connect(self.text_selected_for_tts.emit)
        bubble.text_selected_for_image.connect(self.text_selected_for_image.emit)
        bubble.text_selected_for_audio.connect(self.text_selected_for_audio.emit)
        bubble.remember_selected_text.connect(self.remember_selected_text.emit)
        bubble.remember_message.connect(self.remember_message.emit)
        bubble.memory_stats_requested.connect(self.memory_stats_requested.emit)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self.scroll_to_bottom()

    def start_ai_message(self, model_name: str = None):
        """Start a new AI message (for streaming).
        
        Args:
            model_name: Optional name of the model being used
        """
        # Show typing indicator instead of empty bubble
        if self.typing_indicator is None:
            self.typing_indicator = TypingIndicator()
            self.messages_layout.insertWidget(
                self.messages_layout.count() - 1, self.typing_indicator
            )
            self.typing_indicator.start()

        self.scroll_to_bottom()
        # Show status indicator
        if model_name:
            self.status_indicator.setText(f"⚡ {model_name}")
            self.status_indicator.setToolTip(f"Generating response with {model_name}...")
        else:
            self.status_indicator.setText("⚡ Generating...")
            self.status_indicator.setToolTip("Generating response...")
        self.status_indicator.setVisible(True)

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
            self.current_ai_bubble = ChatBubble("", is_user=False, message_index=-1)
            # Connect bubble signals to widget signals
            self.current_ai_bubble.text_selected_for_tts.connect(
                self.text_selected_for_tts.emit
            )
            self.current_ai_bubble.text_selected_for_image.connect(
                self.text_selected_for_image.emit
            )
            self.current_ai_bubble.text_selected_for_audio.connect(
                self.text_selected_for_audio.emit
            )
            self.current_ai_bubble.remember_selected_text.connect(
                self.remember_selected_text.emit
            )
            self.current_ai_bubble.remember_message.connect(self.remember_message.emit)
            self.current_ai_bubble.memory_stats_requested.connect(
                self.memory_stats_requested.emit
            )
            self.messages_layout.insertWidget(
                self.messages_layout.count() - 1, self.current_ai_bubble
            )

        self.current_ai_bubble.add_text(chunk)
        # Debounced scroll - only scroll every 150ms max (increased to reduce UI updates)
        self.pending_scroll = True
        if not self.scroll_timer.isActive():
            self.scroll_timer.start(150)  # Scroll max every 150ms

    def update_tool_status(self, tool_name: str):
        """Update status indicator to show tool being executed."""
        if not tool_name:
            return
        # Format tool name nicely (e.g. "search_web" -> "Search web")
        display_name = tool_name.replace("_", " ").title()
        self.status_indicator.setText(f"🔧 {display_name}")
        self.status_indicator.setToolTip(f"Executing {display_name}...")
        self.status_indicator.setVisible(True)
        print(f"[UI] Status updated to: 🔧 {display_name}")

    def set_current_ai_bubble_metadata(self, *, role: str, message_index: int):
        """Attach metadata (role/index) to the currently streaming AI bubble."""
        if self.current_ai_bubble is not None and hasattr(
            self.current_ai_bubble, "set_message_metadata"
        ):
            self.current_ai_bubble.set_message_metadata(
                role=role, message_index=message_index
            )

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
        # Restore input focus and cursor visibility (fixes cursor sometimes stuck / not blinking)
        QTimer.singleShot(50, self._ensure_input_cursor_visible)

    def _ensure_input_cursor_visible(self):
        """Refocus input and force cursor/viewport repaint so cursor is visible and blinking."""
        if not hasattr(self, "input_field") or not self.input_field:
            return
        self.input_field.setFocus()
        self.input_field.ensureCursorVisible()
        self.input_field.viewport().update()

    def add_assistant_message(self, message: str, message_index: int = -1):
        """Add complete assistant message (for loading saved chats)."""
        bubble = ChatBubble(message, is_user=False, message_index=message_index)
        # Connect bubble signals to widget signals
        bubble.text_selected_for_tts.connect(self.text_selected_for_tts.emit)
        bubble.text_selected_for_image.connect(self.text_selected_for_image.emit)
        bubble.text_selected_for_audio.connect(self.text_selected_for_audio.emit)
        bubble.remember_selected_text.connect(self.remember_selected_text.emit)
        bubble.remember_message.connect(self.remember_message.emit)
        bubble.memory_stats_requested.connect(self.memory_stats_requested.emit)
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

    def cycle_mode(self):
        """Cycle between chat -> image -> audio -> chat modes."""
        if not self.image_mode and not self.audio_mode:
            # Currently in chat mode, switch to image mode
            self.image_mode = True
            self.audio_mode = False
            MaterialIcons.apply_to_button(
                self.image_mode_btn, MaterialIcons.IMAGE_SVG, size=20, keep_text=False
            )
            self.image_mode_btn.setToolTip(
                "Image generation mode - Click to switch to audio generation"
            )
            self.input_field.setPlaceholderText(
                "Describe the image you want to generate..."
            )
            self.seed_lock_btn.setVisible(True)
            self.seed_plus_btn.setVisible(self.seed_locked)
            self.seed_minus_btn.setVisible(self.seed_locked)
        elif self.image_mode and not self.audio_mode:
            # Currently in image mode, switch to audio mode
            self.image_mode = False
            self.audio_mode = True
            MaterialIcons.apply_to_button(
                self.image_mode_btn, MaterialIcons.AUDIO_SVG, size=20, keep_text=False
            )
            self.image_mode_btn.setToolTip(
                "Audio generation mode - Click to switch to chat"
            )
            self.input_field.setPlaceholderText(
                "Describe the audio you want to generate..."
            )
            self.seed_lock_btn.setVisible(True)
            self.seed_plus_btn.setVisible(self.seed_locked)
            self.seed_minus_btn.setVisible(self.seed_locked)
        else:  # audio_mode is True
            # Currently in audio mode, switch to chat mode
            self.image_mode = False
            self.audio_mode = False
            MaterialIcons.apply_to_button(
                self.image_mode_btn, MaterialIcons.CHAT_SVG, size=20, keep_text=False
            )
            self.image_mode_btn.setToolTip(
                "Chat mode - Click to switch to image generation"
            )
            self.input_field.setPlaceholderText("Type your message...")
            self.seed_lock_btn.setVisible(False)
            self.seed_plus_btn.hide()
            self.seed_minus_btn.hide()

        # Update visual style based on mode
        self._update_input_area_style()

        # Update seed lock button style if visible
        if self.seed_lock_btn.isVisible():
            self.update_seed_lock_button()

    def _update_input_area_style(self):
        """Update input area style based on current mode."""
        if self.audio_mode:
            # Audio mode - red theme
            self.input_frame.setStyleSheet(
                """
                QFrame {
                    background: #3D1B1B;
                    border: 2px solid #E74C3C;
                    border-radius: 10px;
                }
            """
            )
            self.input_field.setStyleSheet(
                """
                QTextEdit {
                    background: #4D2B2B;
                    color: #E0E0E0;
                    border: 1px solid #E74C3C;
                    border-radius: 10px;
                    padding: 8px 12px;
                    font-size: 14px;
                }
                QTextEdit:focus {
                    border: 2px solid #E74C3C;
                    background: #5D3B3B;
                }
            """
            )
            # Update mode button to show audio mode is active
            self.image_mode_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #E74C3C;
                    border: 2px solid #C0392B;
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
            # Update Send button to red theme
            self.send_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #E74C3C;
                    color: white;
                    border: none;
                    border-radius: 10px;
                    padding: 8px 16px;
                    font-weight: 500;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #C0392B;
                }
                QPushButton:pressed {
                    background-color: #A93226;
                }
            """
            )
            # Update prompt button to red theme
            self.prompt_btn.setStyleSheet(
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
            # Update voice button to red theme
            self.voice_btn.setStyleSheet(
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
            # Update seed lock button - use update_seed_lock_button to handle locked/unlocked states
            if self.seed_lock_btn.isVisible():
                self.update_seed_lock_button()
        elif self.image_mode:
            # Image mode - purple/violet theme
            self.input_frame.setStyleSheet(
                """
                QFrame {
                    background: #2D1B3D;
                    border: 2px solid #9B59B6;
                    border-radius: 10px;
                }
            """
            )
            self.input_field.setStyleSheet(
                """
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
            """
            )
            # Update mode button to show image mode is active
            self.image_mode_btn.setStyleSheet(
                """
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
            """
            )
            # Update Send button to purple theme
            self.send_btn.setStyleSheet(
                """
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
            """
            )
            # Update prompt button to purple theme
            self.prompt_btn.setStyleSheet(
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
            # Update voice button to purple theme
            self.voice_btn.setStyleSheet(
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
            # Update seed lock button - use update_seed_lock_button to handle locked/unlocked states
            # This will set purple for unlocked, red for locked
            if self.seed_lock_btn.isVisible():
                self.update_seed_lock_button()
        else:
            # Chat mode - default blue theme (explicitly reset to match theme)
            self.input_frame.setStyleSheet(
                """
                QFrame {
                    background: transparent;
                    border: none;
                }
            """
            )
            # Reset input field to default theme style
            self.input_field.setStyleSheet(
                """
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
            """
            )
            # Reset mode button to default theme style (chat mode)
            # Use blue theme with slightly darker hover, not global gray.
            self.image_mode_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #4A9EFF;
                    color: white;
                    border: none;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #3B82E0;
                }
                QPushButton:pressed {
                    background-color: #2F6FC7;
                }
            """
            )
            # Reset Send button to default blue theme style
            self.send_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #4A9EFF;
                    color: white;
                    border: none;
                    border-radius: 10px;
                    padding: 8px 16px;
                    font-weight: 500;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #3B82E0;
                }
                QPushButton:pressed {
                    background-color: #2F6FC7;
                }
            """
            )
            # Reset prompt button to default blue theme style
            self.prompt_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #4A9EFF;
                    border: none;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #3B82E0;
                }
                QPushButton:pressed {
                    background-color: #2F6FC7;
                }
            """
            )
            # Reset voice button to default blue theme style  
            self.voice_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #4A9EFF;
                    border: none;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #3B82E0;
                }
                QPushButton:pressed {
                    background-color: #2F6FC7;
                }
            """
            )
            # Reset seed lock button (will be updated by update_seed_lock_button if visible)
            # But since it's hidden in chat mode, we don't need to reset it

    def on_seed_lock_toggled(self, checked: bool):
        """Handle seed lock toggle."""
        self.seed_locked = checked
        self.update_seed_lock_button()
        # Show/hide plus/minus when lock is toggled
        if checked and (self.image_mode or self.audio_mode):
            self.seed_plus_btn.show()
            self.seed_minus_btn.show()
        else:
            self.seed_plus_btn.hide()
            self.seed_minus_btn.hide()
        self.seed_lock_toggled.emit(checked)

    def update_seed_lock_button(self):
        """Update seed lock button appearance."""
        if self.seed_locked:
            MaterialIcons.apply_to_button(
                self.seed_lock_btn, MaterialIcons.LOCK_SVG, size=18, keep_text=False
            )
            tooltip_text = "Seed locked - Using same seed"
            if self.audio_mode:
                tooltip_text += " for audio"
            elif self.image_mode:
                tooltip_text += " for images"
            self.seed_lock_btn.setToolTip(tooltip_text)
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
            tooltip_text = "Seed unlocked - Random seed"
            if self.audio_mode:
                tooltip_text += " for each audio"
            elif self.image_mode:
                tooltip_text += " for each image"
            else:
                tooltip_text += " for each generation"
            self.seed_lock_btn.setToolTip(tooltip_text)
            # Use purple theme in image mode, red in audio mode, blue in chat mode
            if self.audio_mode:
                self.seed_lock_btn.setStyleSheet(
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
            elif self.image_mode:
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
                        background-color: #3B82E0;
                    }
                    QPushButton:pressed {
                        background-color: #2F6FC7;
                    }
                """
                )

    def set_send_enabled(self, enabled: bool):
        """Enable or disable send button."""
        self.send_btn.setEnabled(enabled)

    def show_prompt_menu(self):
        """Show prompt selection menu."""
        from PySide6.QtWidgets import QMenu

        if not self.config_manager:
            return

        menu = QMenu(self)

        prompts = self.config_manager.get_prompts()
        if not prompts:
            action = menu.addAction("No prompts available")
            action.setEnabled(False)
        else:
            for prompt in prompts:
                action = menu.addAction(prompt.get("name", "Unnamed"))
                action.setData(prompt.get("text", ""))
                action.triggered.connect(
                    lambda checked, text=prompt.get("text", ""): self.insert_prompt(
                        text
                    )
                )

        # Show menu below button
        button_pos = self.prompt_btn.mapToGlobal(self.prompt_btn.rect().bottomLeft())
        menu.exec(button_pos)

    def insert_prompt(self, text: str):
        """Insert prompt text into input field."""
        if not text:
            return

        current_text = self.input_field.toPlainText()
        if current_text.strip():
            # If there's existing text, add prompt on new line
            self.input_field.setPlainText(f"{current_text}\n{text}")
        else:
            # Replace empty input
            self.input_field.setPlainText(text)
        self.input_field.setFocus()

    def send_message(self):
        """Send message from input field."""
        message = self.input_field.toPlainText().strip()
        has_content = bool(message or self.last_uploaded_image)
        has_attach_only = (
            not self.audio_mode and not self.image_mode and bool(self.pending_attachments)
        )
        if not has_content and not has_attach_only:
            return

        # Get image path if available
        image_path = self.last_uploaded_image

        # Clear input and restore cursor visibility (avoids cursor "freeze" after send)
        self.input_field.clear()
        self._ensure_input_cursor_visible()

        # Clear uploaded image after sending
        self.last_uploaded_image = None

        # Emit appropriate signal based on mode
        if self.audio_mode:
            self.audio_prompt_sent.emit(message)
        elif self.image_mode:
            self.image_prompt_sent.emit(message, image_path or "")
        else:
            self.message_sent.emit(message, image_path or "")

    def add_image_message(self, image_path: str, prompt: str = ""):
        """Add image message to chat."""
        bubble = ChatBubble(prompt, is_user=False, image_path=image_path)
        # Connect bubble signals to widget signals
        bubble.text_selected_for_tts.connect(self.text_selected_for_tts.emit)
        bubble.text_selected_for_image.connect(self.text_selected_for_image.emit)
        bubble.text_selected_for_audio.connect(self.text_selected_for_audio.emit)
        bubble.image_selected_for_video.connect(self.image_selected_for_video.emit)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self.scroll_to_bottom()

    def add_video_message(self, video_path: str, prompt: str = ""):
        """Add video message to chat."""
        # Create bubble with video link
        bubble = ChatBubble(prompt or "Generated video", is_user=False)

        # Add video link
        video_label = QLabel(
            f'<a href="file:///{video_path.replace(chr(92), "/")}">Open Video: {os.path.basename(video_path)}</a>'
        )
        video_label.setOpenExternalLinks(True)
        video_label.setStyleSheet(
            "color: #4A9EFF; text-decoration: underline; padding: 8px;"
        )

        layout = bubble.layout()
        if layout:
            layout.insertWidget(0, video_label)

        # Connect bubble signals
        bubble.text_selected_for_tts.connect(self.text_selected_for_tts.emit)
        bubble.text_selected_for_image.connect(self.text_selected_for_image.emit)
        bubble.text_selected_for_audio.connect(self.text_selected_for_audio.emit)

        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self.scroll_to_bottom()

    def add_audio_message(self, audio_path: str, prompt: str = ""):
        """Add audio message to chat with waveform player."""
        # Create bubble with audio player
        bubble = ChatBubble(
            prompt or "Generated audio", 
            is_user=False, 
            audio_path=audio_path
        )

        # Connect bubble signals
        bubble.text_selected_for_tts.connect(self.text_selected_for_tts.emit)
        bubble.text_selected_for_image.connect(self.text_selected_for_image.emit)
        bubble.text_selected_for_audio.connect(self.text_selected_for_audio.emit)

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

    def eventFilter(self, obj, event):
        """Handle file drop on input_frame or input_field so drop never runs in input (cursor stays ok)."""
        if obj == self.input_frame or obj == self.input_field:
            if event.type() == QEvent.Type.DragEnter:
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Type.Drop:
                if event.mimeData().hasUrls():
                    paths = []
                    for url in event.mimeData().urls():
                        path = url.toLocalFile()
                        if path and path.strip() and os.path.isfile(path):
                            paths.append(path)
                    if paths:
                        self._on_files_dropped(paths)
                        event.acceptProposedAction()
                    return True
        return super().eventFilter(obj, event)

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
                self, "File Not Found", f"Image file not found: {image_path}"
            )
            return

        # Get image info
        img_info = self.image_processor.get_image_info(image_path)
        if not img_info:
            QMessageBox.warning(
                self,
                "Invalid Image",
                "Could not read image file. Please ensure it's a valid image.",
            )
            return

        # Check file size (max 50MB)
        if img_info["file_size_mb"] > 50:
            QMessageBox.warning(
                self,
                "File Too Large",
                f"Image file is too large ({img_info['file_size_mb']}MB). Maximum size is 50MB.",
            )
            return

        # Store as last uploaded image
        self.last_uploaded_image = image_path

        # Show image in chat immediately
        upload_msg = f"📁 Image uploaded: {os.path.basename(image_path)} ({img_info['width']}x{img_info['height']}, {img_info['file_size_mb']}MB)"
        bubble = ChatBubble(upload_msg, is_user=True, image_path=image_path)
        bubble.text_selected_for_tts.connect(self.text_selected_for_tts.emit)
        bubble.text_selected_for_image.connect(self.text_selected_for_image.emit)
        bubble.text_selected_for_audio.connect(self.text_selected_for_audio.emit)
        bubble.remember_selected_text.connect(self.remember_selected_text.emit)
        bubble.remember_message.connect(self.remember_message.emit)
        bubble.memory_stats_requested.connect(self.memory_stats_requested.emit)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self.scroll_to_bottom()

        print(
            f"Image uploaded: {image_path} ({img_info['width']}x{img_info['height']})"
        )

    def _on_files_dropped(self, paths: list):
        """Route dropped files: images -> handle_image_upload, others -> add_attachments."""
        if not paths:
            return
        images = [p for p in paths if self.image_processor.is_supported_image(p)]
        if images:
            self.handle_image_upload(images[0])
            return
        enabled = True
        if self.config_manager:
            enabled = self.config_manager.get("chat.attachments.enabled", True)
        if not enabled:
            return
        self.add_attachments(paths)

    def _make_attachment_chip(self, path: str, name: str, size_bytes: int) -> QWidget:
        """Build a chip widget: filename + size + remove button."""
        chip = QFrame()
        chip.setFixedHeight(36)
        chip.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        chip.setStyleSheet("""
            QFrame {
                background: rgba(74, 158, 255, 0.2);
                border: 1px solid rgba(74, 158, 255, 0.5);
                border-radius: 8px;
                padding: 2px 6px;
            }
        """)
        chip_layout = QHBoxLayout()
        chip_layout.setContentsMargins(6, 2, 4, 2)
        chip_layout.setSpacing(4)
        label = QLabel(f"📎 {name} ({format_file_size(size_bytes)})")
        label.setStyleSheet("color: #E0E0E0; font-size: 12px;")
        label.setToolTip(path)
        label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        chip_layout.addWidget(label, 1)
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(22, 22)
        remove_btn.setStyleSheet("""
            QPushButton {
                background: rgba(120, 120, 120, 0.4);
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.3);
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #FF6B6B;
                color: #FFFFFF;
            }
        """)
        remove_btn.setToolTip("Remove attachment")
        remove_btn.clicked.connect(lambda: self._remove_attachment(path))
        chip_layout.addWidget(remove_btn, 0)
        chip.setLayout(chip_layout)
        return chip

    def _remove_attachment(self, path: str):
        """Remove one attachment by path and hide container if empty."""
        for i, att in enumerate(self.pending_attachments):
            if att["path"] == path:
                self.pending_attachments.pop(i)
                break
        w = self._attachment_chips.pop(path, None)
        if w:
            self.attachments_layout.removeWidget(w)
            w.deleteLater()
        if not self.pending_attachments:
            self.attachments_container.hide()

    def add_attachments(self, paths: list):
        """Add file paths as pending attachments; show chips above input."""
        max_files = 5
        if self.config_manager:
            max_files = self.config_manager.get("chat.attachments.max_files", 5)
        max_file_size_bytes = 10 * 1024 * 1024  # 10 MB
        skipped = []
        for p in paths:
            if len(self.pending_attachments) >= max_files:
                skipped.append(f"{os.path.basename(p)} (max {max_files} files)")
                continue
            if not os.path.isfile(p):
                continue
            if not is_allowed_attachment(p):
                skipped.append(f"{os.path.basename(p)} (unsupported type)")
                continue
            if any(a["path"] == p for a in self.pending_attachments):
                continue
            try:
                size = os.path.getsize(p)
            except OSError:
                skipped.append(f"{os.path.basename(p)} (cannot read)")
                continue
            if size > max_file_size_bytes:
                skipped.append(
                    f"{os.path.basename(p)} (too large, max {max_file_size_bytes // (1024*1024)} MB)"
                )
                continue
            if is_probably_binary(p):
                skipped.append(f"{os.path.basename(p)} (binary)")
                continue
            name = os.path.basename(p)
            self.pending_attachments.append({"path": p, "name": name, "size": size})
            chip = self._make_attachment_chip(p, name, size)
            # insert before the stretch so chips stay left and don't fill the row
            self.attachments_layout.insertWidget(self.attachments_layout.count() - 1, chip)
            self._attachment_chips[p] = chip
        if skipped:
            QMessageBox.warning(
                self,
                "Some files skipped",
                "Skipped:\n" + "\n".join(skipped[:10])
                + ("\n..." if len(skipped) > 10 else ""),
            )
        if self.pending_attachments:
            self.attachments_container.show()

    def consume_attachments(self) -> list[dict]:
        """Return and clear pending attachments (next-message-only)."""
        out = list(self.pending_attachments)
        for path in list(self._attachment_chips.keys()):
            w = self._attachment_chips.pop(path)
            self.attachments_layout.removeWidget(w)
            w.deleteLater()
        self.pending_attachments.clear()
        self.attachments_container.hide()
        return out

    def _init_voice_input(self):
        """Initialize voice input widget."""
        try:
            from lokai.ui.voice_input_widget import VoiceInputWidget
            from lokai.core.config_manager import ConfigManager

            config_manager = ConfigManager()
            self.voice_input_widget = VoiceInputWidget(config_manager)

            # Connect signals
            self.voice_input_widget.transcription_ready.connect(self._on_voice_transcription)
            self.voice_input_widget.error_occurred.connect(self._on_voice_error)
            self.voice_input_widget.voice_input_started.connect(self._on_voice_started)
            self.voice_input_widget.voice_input_stopped.connect(self._on_voice_stopped)

            # Initially hide voice input widget
            self.voice_input_widget.hide()

        except Exception as e:
            print(f"Error initializing voice input: {e}")
            self.voice_input_widget = None

    def toggle_voice_input(self):
        """Toggle voice input (directly start/stop ASR without showing widget)."""
        if self.voice_input_widget is None:
            return

        # Check if currently listening
        if hasattr(self.voice_input_widget, 'is_listening') and self.voice_input_widget.is_listening:
            # Stop listening
            self.voice_input_widget.stop_voice_input()
            # Reset voice button icon
            MaterialIcons.apply_to_button(
                self.voice_btn, MaterialIcons.MIC_SVG, size=16, keep_text=False
            )
        else:
            # Start listening directly (no widget shown)
            self.voice_input_widget.start_voice_input()
            # Update voice button icon to indicate active
            MaterialIcons.apply_to_button(
                self.voice_btn, MaterialIcons.MIC_OFF_SVG, size=16, keep_text=False
                )

    def _on_voice_transcription(self, text: str):
        """Handle voice transcription ready. Inserts text at current cursor position in chat input."""
        if not text.strip():
            return
        cursor = self.input_field.textCursor()
        insert_text = text.strip()
        # Add space before if cursor is mid-text and previous character is not whitespace
        pos = cursor.position()
        if pos > 0:
            current = self.input_field.toPlainText()
            if current and pos <= len(current) and not current[pos - 1].isspace():
                insert_text = " " + insert_text
        cursor.insertText(insert_text)
        self.input_field.setTextCursor(cursor)
        self.input_field.setFocus()
        self._ensure_input_cursor_visible()

        # Auto-send disabled - user must press Enter or Send button to confirm
        auto_send = False
        if auto_send:
            self.send_message()

    def _on_voice_error(self, error: str):
        """Handle voice input error."""
        print(f"Voice input error: {error}")
        # Could show error message to user

    def _on_voice_started(self):
        """Handle voice input started."""
        print("Voice input started")
        # Update mic button to indicate active listening
        MaterialIcons.apply_to_button(
            self.voice_btn, MaterialIcons.MIC_OFF_SVG, size=16, keep_text=False
        )
        # Set shadow to bright red (always red, regardless of mode)
        self.voice_btn_shadow.setColor(QColor(255, 0, 0, 255))  # Bright red - full opacity
        # Start pulsing animation - large range for maximum visibility
        self.voice_btn_animation.setStartValue(15)
        self.voice_btn_animation.setEndValue(35)
        self.voice_btn_animation.start()
        
        # Start auto-stop timer (30 seconds)
        self.voice_auto_stop_timer.start(30000)  # 30 seconds

    def _on_voice_stopped(self):
        """Handle voice input stopped."""
        print("Voice input stopped")
        # Stop auto-stop timer if running
        if self.voice_auto_stop_timer.isActive():
            self.voice_auto_stop_timer.stop()
        
        # Reset mic button to normal state
        MaterialIcons.apply_to_button(
            self.voice_btn, MaterialIcons.MIC_SVG, size=16, keep_text=False
        )
        # Stop pulsing animation
        self.voice_btn_animation.stop()
        self.voice_btn_shadow.setBlurRadius(10)
        self.voice_btn_shadow.setColor(QColor(231, 76, 60, 0))  # Reset to invisible
    
    def _auto_stop_voice_input(self):
        """Automatically stop voice input after 30 seconds."""
        if self.voice_input_widget and hasattr(self.voice_input_widget, 'is_listening'):
            if self.voice_input_widget.is_listening:
                print("Auto-stopping voice input after 30 seconds")
                self.voice_input_widget.stop_voice_input()