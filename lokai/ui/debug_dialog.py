"""
Debug Dialog for locAI.
Shows the current prompt that would be sent to LLM.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel,
    QGroupBox,
    QFormLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class DebugDialog(QDialog):
    """Debug dialog showing current prompt details."""

    def __init__(self, parent=None, preview_mode: bool = False):
        """
        Initialize DebugDialog.
        
        Args:
            parent: Parent widget
            preview_mode: If True, shows Send/Cancel buttons instead of Close (for preview before sending)
        """
        super().__init__(parent)
        self.preview_mode = preview_mode
        if preview_mode:
            self.setWindowTitle("Preview Prompt Before Sending")
        else:
            self.setWindowTitle("Debug - Current Prompt")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.user_accepted = False  # True if user clicked Send in preview mode
        self.init_ui()

    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # Info group
        info_group = QGroupBox("Prompt Information")
        info_layout = QFormLayout()

        self.prompt_type_label = QLabel("Normal")
        self.prompt_type_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        info_layout.addRow("Prompt Type:", self.prompt_type_label)

        self.message_count_label = QLabel("0")
        info_layout.addRow("Total Messages:", self.message_count_label)

        self.included_messages_label = QLabel("0")
        info_layout.addRow("Included Messages:", self.included_messages_label)

        self.semantic_memory_label = QLabel("Disabled")
        info_layout.addRow("Semantic Memory:", self.semantic_memory_label)

        self.context_mode_label = QLabel("Explicit History")
        info_layout.addRow("Context Mode:", self.context_mode_label)

        self.context_info_label = QLabel("")
        self.context_info_label.setWordWrap(True)
        self.context_info_label.setStyleSheet("color: #888; font-size: 10px;")
        info_layout.addRow("", self.context_info_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Prompt display
        prompt_label = QLabel("Full Prompt (what LLM receives):")
        prompt_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(prompt_label)

        self.prompt_text = QTextEdit()
        self.prompt_text.setReadOnly(True)
        self.prompt_text.setFont(QFont("Consolas", 10))
        self.prompt_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                padding: 8px;
            }
        """
        )
        layout.addWidget(self.prompt_text)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(copy_btn)

        if self.preview_mode:
            # Preview mode: Send and Cancel buttons
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self.reject)
            button_layout.addWidget(cancel_btn)
            
            send_btn = QPushButton("Send")
            send_btn.setDefault(True)
            send_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    padding: 8px 20px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            send_btn.clicked.connect(self._on_send_clicked)
            button_layout.addWidget(send_btn)
        else:
            # Debug mode: Close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(self.accept)
            button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def set_prompt_info(
        self,
        prompt: str,
        prompt_type: str,
        message_count: int,
        included_count: int,
        semantic_memory_enabled: bool,
        context_used: bool = False,
        context_info: str = "",
    ):
        """
        Set prompt information to display.

        Args:
            prompt: Full prompt text
            prompt_type: Type of prompt ("Semantic Memory" or "Normal")
            message_count: Total messages in conversation
            included_count: Number of messages included in prompt
            semantic_memory_enabled: Whether semantic memory is enabled
            context_used: Whether Ollama context is used (vs explicit history)
            context_info: Additional info about context
        """
        self.prompt_text.setPlainText(prompt)
        self.prompt_type_label.setText(prompt_type)
        self.message_count_label.setText(str(message_count))
        self.included_messages_label.setText(str(included_count))

        if semantic_memory_enabled:
            self.semantic_memory_label.setText("Enabled")
            self.semantic_memory_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.semantic_memory_label.setText("Disabled")
            self.semantic_memory_label.setStyleSheet("color: #f44336;")

        # Context mode
        if context_used:
            self.context_mode_label.setText("Ollama Context")
            self.context_mode_label.setStyleSheet("color: #FF9800; font-weight: bold;")
            self.context_info_label.setText(
                f"⚠️ Prompt contains only current message. "
                f"Full conversation history is in Ollama context. {context_info}"
            )
        else:
            self.context_mode_label.setText("Explicit History")
            self.context_mode_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.context_info_label.setText(
                f"✓ Full conversation history is included in prompt text above. {context_info}"
            )

        if prompt_type == "Semantic Memory":
            self.prompt_type_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        else:
            self.prompt_type_label.setStyleSheet("font-weight: bold; color: #4CAF50;")

    def _on_send_clicked(self):
        """Handle Send button in preview mode."""
        self.user_accepted = True
        self.accept()
    
    def copy_to_clipboard(self):
        """Copy prompt to clipboard."""
        clipboard = self.prompt_text.toPlainText()
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(clipboard)
        
        # Show temporary message
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("Copied")
        msg.setText("Prompt copied to clipboard!")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setIcon(QMessageBox.Information)
        # Auto-close after 1 second
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1000, msg.accept)
        msg.exec()

