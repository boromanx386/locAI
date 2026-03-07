"""
Neural Filter Widget for locAI.
Displays raw model thinking logs in real-time with terminal-style aesthetic.
Theme-aware: white text in dark/light modes, green in dystopian mode.
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPlainTextEdit,
    QLabel,
    QPushButton,
    QHBoxLayout,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor


# Theme-specific colors for Neural Filter
_NEURAL_FILTER_COLORS = {
    "dark": {
        "text": "#E0E0E0",
        "background": "#1E1E1E",
        "border": "#404040",
        "title": "#4A9EFF",
        "btn_bg": "#2D2D2D",
        "btn_text": "#A0A0A0",
        "btn_hover": "#4A9EFF",
    },
    "light": {
        "text": "#212121",
        "background": "#FAFAFA",
        "border": "#E0E0E0",
        "title": "#1976D2",
        "btn_bg": "#F5F5F5",
        "btn_text": "#757575",
        "btn_hover": "#1976D2",
    },
    "dystopian": {
        "text": "#8FBC8F",
        "background": "#0D1117",
        "border": "#30363D",
        "title": "#8B949E",
        "btn_bg": "#3D4349",
        "btn_text": "#8B949E",
        "btn_hover": "#8FBC8F",
    },
}


class NeuralFilterWidget(QWidget):
    """
    Widget that displays raw thinking stream from the model in real-time.
    Terminal-style monospace display with timestamp option.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buffer = []
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.timeout.connect(self._flush_buffer)
        self._show_timestamps = False
        self._current_theme = "dark"

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        self.title_label = QLabel("NEURAL FILTER")
        header.addWidget(self.title_label)
        header.addStretch()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setMinimumHeight(28)
        self.clear_btn.setMinimumWidth(60)
        self.clear_btn.clicked.connect(self.clear)
        header.addWidget(self.clear_btn)

        layout.addLayout(header)

        self.text_view = QPlainTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setPlaceholderText(
            "Raw thinking stream will appear here when the model generates..."
        )
        layout.addWidget(self.text_view)

        self.setLayout(layout)
        self.setMinimumWidth(280)
        self.setMaximumWidth(450)

        self._apply_theme(self._current_theme)

    def set_theme(self, theme_name: str):
        """Update colors to match app theme. dark/light = white text, dystopian = green."""
        theme_name = theme_name or "dark"
        if theme_name not in _NEURAL_FILTER_COLORS:
            theme_name = "dark"
        self._current_theme = theme_name
        self._apply_theme(theme_name)

    def _apply_theme(self, theme_name: str):
        colors = _NEURAL_FILTER_COLORS.get(theme_name, _NEURAL_FILTER_COLORS["dark"])
        self.title_label.setStyleSheet(
            f"""
            color: {colors["title"]};
            font-weight: bold;
            font-size: 11px;
            letter-spacing: 2px;
        """
        )
        self.clear_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {colors["btn_bg"]};
                color: {colors["btn_text"]};
                border: 1px solid {colors["border"]};
                border-radius: 4px;
                font-size: 12px;
                padding: 4px 12px;
                min-height: 28px;
            }}
            QPushButton:hover {{
                background: {colors["border"]};
                color: {colors["btn_hover"]};
            }}
        """
        )
        self.text_view.setStyleSheet(
            f"""
            QPlainTextEdit {{
                background: {colors["background"]};
                color: {colors["text"]};
                border: 1px solid {colors["border"]};
                border-radius: 4px;
                font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
                font-size: 12px;
                padding: 8px;
            }}
        """
        )

    def append_chunk(self, text: str):
        """Append thinking chunk (throttled)."""
        if not text:
            return
        self._buffer.append(text)
        if not self._flush_timer.isActive():
            self._flush_timer.start(50)

    def _flush_buffer(self):
        """Flush buffered chunks to display."""
        if not self._buffer:
            return
        text = "".join(self._buffer)
        self._buffer.clear()

        if self._show_timestamps:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            text = f"[{ts}] {text}"

        cursor = self.text_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.text_view.setTextCursor(cursor)
        self.text_view.verticalScrollBar().setValue(
            self.text_view.verticalScrollBar().maximum()
        )

    def clear(self):
        """Clear the log display."""
        self._buffer.clear()
        self._flush_timer.stop()
        self.text_view.clear()

    def set_show_timestamps(self, show: bool):
        self._show_timestamps = show
