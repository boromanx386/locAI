"""
Main Window for locAI.
Modern main window with standard title bar and clean layout.
"""

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QMenuBar,
    QMenu,
    QStatusBar,
    QMessageBox,
    QFileDialog,
)
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QEvent, QSize
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QFont, QColor
from lokai.core.config_manager import ConfigManager
from lokai.ui.theme import Theme
from lokai.ui.status_panel import StatusPanel
from lokai.ui.chat_widget import ChatWidget
from lokai.ui.settings_dialog import SettingsDialog
from lokai.core.ollama_detector import OllamaDetector
from lokai.core.ollama_client import OllamaClient
from lokai.core.image_generator import ImageGenerator
from lokai.ui.image_worker import ImageGenerationWorker


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize MainWindow.

        Args:
            config_manager: Configuration manager instance
        """
        super().__init__()
        self.config_manager = config_manager

        # Initialize Ollama components
        base_url = config_manager.get("ollama.base_url", "http://localhost:11434")
        self.ollama_detector = OllamaDetector(base_url)
        self.ollama_client = OllamaClient(base_url)

        # Current conversation context
        self.current_context = None
        self.conversation_history = (
            []
        )  # List of {"role": "user"/"assistant", "content": "..."}

        # Image generation seed management
        self.last_image_seed = None  # Last seed used for image generation
        self.seed_locked = False  # Whether seed is locked

        # Track last used model for GPU memory management
        self.last_used_model = None
        self.last_was_vision = False  # Track if last request was vision (with images)

        # Cache LLM parameters to avoid repeated config reads
        self._llm_params_cache = None
        self._conversation_settings_cache = None
        self._cache_config_values()

        # Setup UI
        self.init_ui()

        # Initial status check (delayed to not block startup)
        # No periodic timer - check only when needed (startup, refresh button, or before sending message)
        QTimer.singleShot(2000, self.check_ollama_status)

        # Track last status check to avoid redundant checks
        self._last_status_check = None
        self._status_check_interval = 30000  # Only check if 30+ seconds passed

    def _cache_config_values(self):
        """Cache frequently accessed config values to avoid repeated file reads."""
        self._llm_params_cache = {
            "num_ctx": self.config_manager.get("ollama.llm_params.num_ctx", 4096),
            "temperature": self.config_manager.get(
                "ollama.llm_params.temperature", 0.7
            ),
            "top_p": self.config_manager.get("ollama.llm_params.top_p", 0.9),
            "top_k": self.config_manager.get("ollama.llm_params.top_k", 40),
            "repeat_penalty": self.config_manager.get(
                "ollama.llm_params.repeat_penalty", 1.1
            ),
            "num_predict": self.config_manager.get("ollama.llm_params.num_predict", -1),
        }
        self._conversation_settings_cache = {
            "use_explicit_history": self.config_manager.get(
                "ollama.conversation.use_explicit_history", False
            ),
            "system_prompt": self.config_manager.get(
                "ollama.conversation.system_prompt", "You are a helpful AI assistant."
            ),
            "max_history": self.config_manager.get(
                "ollama.conversation.max_history_messages", 20
            ),
        }

    def _init_image_generator(self):
        """Initialize image generator if enabled and path is set."""
        storage_path = self.config_manager.get("models.storage_path")
        if storage_path:
            try:
                # Setup environment before importing diffusers
                from lokai.utils.model_manager import ModelManager

                manager = ModelManager(storage_path)
                manager.setup_environment_variables()

                self.image_generator = ImageGenerator(storage_path)
                if not self.image_generator.is_available():
                    self.image_generator = None
                    print("Image generation not available (diffusers not installed)")
            except Exception as e:
                print(f"Error initializing image generator: {e}")
                import traceback

                traceback.print_exc()
                self.image_generator = None

    def _init_tts_engine(self):
        """Initialize TTS engine if enabled."""
        try:
            from lokai.core.tts_engine import TTSEngine, KOKORO_AVAILABLE

            # Check if Kokoro is available
            if not KOKORO_AVAILABLE:
                print(
                    "Kokoro TTS not available. Install with: pip install kokoro soundfile"
                )
                self.tts_engine = None
                return

            # Check if TTS is enabled
            if not self.config_manager.get("tts.enabled", True):
                self.tts_engine = None
                return

            # Get TTS settings
            lang_code = self.config_manager.get("tts.lang_code", "a")
            voice = self.config_manager.get("tts.voice", "af_heart")

            # Callback when TTS finishes
            def on_tts_finished():
                self.status_panel.set_tts_playing(False)

            # Initialize TTS engine
            self.tts_engine = TTSEngine(
                lang_code=lang_code, voice=voice, on_finished=on_tts_finished
            )

            # Set speed if configured
            speed = self.config_manager.get("tts.speed", 1.0)
            if hasattr(self.tts_engine, "speed"):
                self.tts_engine.speed = speed

            # Update voices in status panel based on language
            if hasattr(self.status_panel, "update_voices_for_language"):
                self.status_panel.update_voices_for_language(lang_code)

            # Set voice from config after voices are loaded
            if hasattr(self.status_panel, "tts_voice_combo"):
                index = self.status_panel.tts_voice_combo.findText(voice)
                if index >= 0:
                    self.status_panel.tts_voice_combo.setCurrentIndex(index)
                else:
                    # If voice not found, select first available
                    if self.status_panel.tts_voice_combo.count() > 0:
                        self.status_panel.tts_voice_combo.setCurrentIndex(0)
                        # Update config with first available voice
                        first_voice = self.status_panel.tts_voice_combo.currentText()
                        self.config_manager.set("tts.voice", first_voice)
                        self.config_manager.save_config()

            print(f"TTS engine initialized: lang={lang_code}, voice={voice}")

        except Exception as e:
            print(f"Error initializing TTS engine: {e}")
            import traceback

            traceback.print_exc()
            self.tts_engine = None

    def _init_global_shortcuts(self):
        """Initialize global keyboard shortcuts for system-wide text selection."""
        try:
            from lokai.core.global_shortcuts import GlobalShortcutHandler

            self.global_shortcuts = GlobalShortcutHandler(self)
            self.global_shortcuts.set_callbacks(
                self.on_text_selected_for_tts, self.on_text_selected_for_image
            )
            # Also connect signals as backup
            self.global_shortcuts.text_selected_for_tts.connect(
                self.on_text_selected_for_tts
            )
            self.global_shortcuts.text_selected_for_image.connect(
                self.on_text_selected_for_image
            )

            # Enable global shortcuts
            if self.global_shortcuts.enable():
                self.status_bar.showMessage(
                    "Global shortcuts enabled: F9 (TTS), F10 (Image)",
                    5000,
                )
        except Exception as e:
            print(f"Error initializing global shortcuts: {e}")
            self.global_shortcuts = None

    def init_ui(self):
        """Initialize user interface."""
        self.setWindowTitle("locAI - Local AI Assistant")
        self.setGeometry(100, 100, 1200, 800)
        # Allow window to be collapsed to very small size
        self.setMinimumSize(100, 100)

        # Set window icon
        self.setWindowIcon(self._create_logo_icon())

        # Apply theme
        theme_name = self.config_manager.get("ui.theme", "dark")
        stylesheet = Theme.get_stylesheet(theme_name)
        self.setStyleSheet(stylesheet)

        # Create menu bar
        self.create_menu_bar()

        # Create status bar
        self.create_status_bar()

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Status panel (top)
        self.status_panel = StatusPanel(self.ollama_detector, self.ollama_client)
        self.status_panel.model_selected.connect(self.on_model_selected)
        # Connect TTS signals
        self.status_panel.tts_play_clicked.connect(self.on_tts_play)
        self.status_panel.tts_pause_clicked.connect(self.on_tts_pause)
        self.status_panel.tts_stop_clicked.connect(self.on_tts_stop)
        self.status_panel.tts_voice_changed.connect(self.on_tts_voice_changed)
        # Connect refresh button to force status check
        self.status_panel.refresh_clicked.connect(
            lambda: self.check_ollama_status(force=True)
        )
        # Language change is handled through Settings only
        main_layout.addWidget(self.status_panel)

        # Chat widget (center, takes most space)
        self.chat_widget = ChatWidget(self.ollama_client)
        main_layout.addWidget(self.chat_widget, stretch=1)

        # Connect chat widget signals
        self.chat_widget.message_sent.connect(lambda msg, img: self.on_message_sent(msg, img))
        self.chat_widget.image_prompt_sent.connect(self.on_image_prompt_sent)
        self.chat_widget.seed_lock_toggled.connect(self.on_seed_lock_toggled)
        self.chat_widget.text_selected_for_tts.connect(self.on_text_selected_for_tts)
        self.chat_widget.text_selected_for_image.connect(
            self.on_text_selected_for_image
        )

        # Initialize image generator (if enabled)
        self.image_generator = None
        self._init_image_generator()

        # Initialize TTS engine
        self.tts_engine = None
        self._init_tts_engine()

        # Ensure voices are loaded in status panel (in case TTS is disabled)
        if hasattr(self.status_panel, "update_voices_for_language"):
            lang_code = self.config_manager.get("tts.lang_code", "a")
            self.status_panel.update_voices_for_language(lang_code)
            # Set voice from config
            voice = self.config_manager.get("tts.voice", "af_heart")
            if hasattr(self.status_panel, "tts_voice_combo"):
                index = self.status_panel.tts_voice_combo.findText(voice)
                if index >= 0:
                    self.status_panel.tts_voice_combo.setCurrentIndex(index)

        # Initialize global shortcuts for system-wide text selection
        self._init_global_shortcuts()

    def create_menu_bar(self):
        """Create application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        new_action = QAction("New Chat", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_chat)
        file_menu.addAction(new_action)

        file_menu.addSeparator()

        save_action = QAction("Save Chat", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_chat)
        file_menu.addAction(save_action)

        load_action = QAction("Load Chat", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.load_chat)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Settings menu
        settings_menu = menubar.addMenu("Settings")

        settings_action = QAction("Preferences", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.show_settings)
        settings_menu.addAction(settings_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_status_bar(self):
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def check_ollama_status(self, force: bool = False):
        """
        Check Ollama server status and update UI (non-blocking).

        Args:
            force: If True, check immediately. If False, only check if enough time has passed.
        """
        # Only check if not currently processing a message
        if hasattr(self, "current_worker") and self.current_worker is not None:
            if self.current_worker.isRunning():
                return  # Skip check if worker is running

        # Throttle checks - only check if enough time has passed (unless forced)
        if not force:
            import time

            current_time = time.time() * 1000  # milliseconds
            if (
                self._last_status_check is not None
                and current_time - self._last_status_check < self._status_check_interval
            ):
                return  # Skip if checked recently

        # Use singleShot to avoid blocking UI
        QTimer.singleShot(0, self._check_ollama_status_async)

    def _check_ollama_status_async(self):
        """Actually check status (called asynchronously)."""
        try:
            import time

            self._last_status_check = time.time() * 1000  # Update last check time

            is_running, error = self.ollama_detector.check_ollama_running()

            if is_running:
                # Only update models list if combo is empty or has placeholder
                # Don't reload models every time - only on refresh button or startup
                current_count = self.status_panel.model_combo.count()
                has_models = (
                    current_count > 0
                    and self.status_panel.model_combo.itemText(0)
                    not in ["No models available", "No models installed"]
                )

                if not has_models:
                    # Only load models if list is empty
                    models, model_error = self.ollama_detector.get_installed_models()
                    if models:
                        self.status_panel.update_models(models)
                    self.status_bar.showMessage("Ollama is running")
                else:
                    # Just update status, don't reload models
                    self.status_panel.set_online()
                    self.status_bar.showMessage("Ollama is running")
            else:
                self.status_bar.showMessage("Ollama is not running")
                self.status_panel.set_offline()
        except Exception as e:
            print(f"Error checking Ollama status: {e}")

    def on_model_selected(self, model_name: str):
        """Handle model selection."""
        self.config_manager.set("ollama.default_model", model_name)
        self.config_manager.save_config()
        self.status_bar.showMessage(f"Selected model: {model_name}")

    def on_message_sent(self, message: str, image_path: str = ""):
        """Handle message sent from chat widget."""
        # Quick status check before sending (throttled - only if not checked recently)
        self.check_ollama_status(force=False)

        # Get selected model
        model = self.status_panel.get_selected_model()
        if not model:
            QMessageBox.warning(
                self,
                "No Model Selected",
                "Please select a model from the dropdown above.",
            )
            return

        # Check if Ollama is running
        if not self.ollama_client.is_running():
            QMessageBox.warning(
                self,
                "Ollama Not Running",
                "Ollama server is not running. Please start Ollama first.",
            )
            return

        # Auto-unload image model before LLM generation to free GPU memory
        if self.image_generator and self.image_generator.pipeline is not None:
            print("Auto-unloading image model to free GPU memory...")
            self.image_generator.unload_model()

        # Process image if provided
        images_base64 = []
        is_vision_request = False
        if image_path and os.path.exists(image_path):
            from lokai.core.image_processor import ImageProcessor
            processor = ImageProcessor()
            base64_image = processor.image_to_base64(image_path)
            if base64_image:
                images_base64.append(base64_image)
                image_size_kb = len(base64_image) / 1024
                print(f"Image converted to base64: {len(base64_image)} characters ({image_size_kb:.1f} KB)")
                is_vision_request = True
            else:
                QMessageBox.warning(
                    self,
                    "Image Conversion Failed",
                    "Could not convert image to base64. Please try again."
                )
                return

        # GPU memory management: unload previous model if switching between vision and non-vision
        # or if switching to different model
        if self.last_used_model and self.last_used_model != model:
            print(f"Model changed from {self.last_used_model} to {model} - unloading previous model...")
            self.ollama_client.unload_model(self.last_used_model)
            # Clear context when switching models
            self.current_context = None
        elif self.last_used_model == model and self.last_was_vision != is_vision_request:
            # Same model but switching between vision and non-vision - unload to free GPU
            print(f"Switching between vision/non-vision mode - unloading model {model}...")
            self.ollama_client.unload_model(model)
            # Clear context when switching modes
            self.current_context = None

        # Update tracking
        self.last_used_model = model
        self.last_was_vision = is_vision_request

        # Send message to Ollama
        self.chat_widget.add_user_message(message, image_path=image_path if image_path else None)

        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": message})

        # Use cached config values (much faster than reading from file each time)
        llm_params = self._llm_params_cache.copy()
        conv_settings = self._conversation_settings_cache

        # Build prompt based on conversation settings
        use_explicit_history = conv_settings["use_explicit_history"]
        system_prompt = conv_settings["system_prompt"]
        max_history = conv_settings["max_history"]

        # If context is None but we have conversation history, use explicit history
        # (context cannot be reconstructed from text, so we must use explicit history)
        if self.current_context is None and len(self.conversation_history) > 0:
            use_explicit_history = True

        # If sending image, don't use context (vision models work better without context)
        # Send None for context when images are present (like in old code)
        context_to_use = None if (images_base64 and len(images_base64) > 0) else self.current_context
        if images_base64 and len(images_base64) > 0:
            print("Image detected - using None context for vision model")
            use_explicit_history = True
        
        if use_explicit_history:
            # Build prompt with explicit history (optimized for performance)
            # Pre-allocate list size to avoid reallocations
            history_to_include = self.conversation_history
            if max_history > 0:
                # Take last max_history messages (excluding current)
                history_to_include = self.conversation_history[-(max_history + 1) : -1]

            # Estimate size to avoid multiple string concatenations
            estimated_size = len(system_prompt) if system_prompt else 0
            estimated_size += len(message) + 50  # Current message + overhead
            for msg in history_to_include:
                estimated_size += (
                    len(msg.get("content", "")) + 30
                )  # Per message overhead

            # Use list join for better performance than repeated string concatenation
            prompt_parts = []
            if system_prompt:
                prompt_parts.append(system_prompt)

            # Add conversation history
            for msg in history_to_include:
                role_prefix = "User: " if msg["role"] == "user" else "Assistant: "
                prompt_parts.append(role_prefix + msg["content"])

            # Add current message
            prompt_parts.append(f"User: {message}")
            prompt_parts.append("Assistant:")

            # Single join operation (much faster than multiple concatenations)
            final_prompt = "\n\n".join(prompt_parts)
        else:
            # Use only current message (context handles history)
            final_prompt = message

        # Don't create AI bubble yet - wait for first chunk
        # This prevents empty bubble from appearing immediately

        # Create worker thread for non-blocking generation
        # Use context_to_use (None for images, self.current_context otherwise)
        worker = OllamaWorker(
            self.ollama_client, model, final_prompt, context_to_use, llm_params, images=images_base64 if images_base64 else None
        )
        # Connect signals - create bubble on first chunk
        worker.chunk_received.connect(self._on_chunk_received)
        worker.finished.connect(self._on_response_finished)
        worker.error_occurred.connect(self._on_response_error)
        # Store worker reference to prevent garbage collection
        self.current_worker = worker
        worker.finished.connect(lambda: setattr(self, "current_worker", None))
        worker.error_occurred.connect(lambda: setattr(self, "current_worker", None))
        worker.start()

    def new_chat(self):
        """Start a new chat conversation."""
        # Reset model tracking when starting new chat
        self.last_used_model = None
        self.last_was_vision = False
        
        reply = QMessageBox.question(
            self,
            "New Chat",
            "Start a new conversation? Current conversation will be cleared.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.chat_widget.clear_messages()
            self.current_context = None
            self.conversation_history = []
            self.status_bar.showMessage("New chat started")

    def save_chat(self):
        """Save current chat to JSON file."""
        if not self.conversation_history:
            QMessageBox.information(self, "Save Chat", "No conversation to save.")
            return

        # Get save location
        default_filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Chat", default_filename, "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Prepare data to save
            chat_data = {
                "version": "1.0",
                "saved_at": datetime.now().isoformat(),
                "conversation": self.conversation_history,
                "model": (
                    self.status_panel.model_combo.currentText()
                    if hasattr(self.status_panel, "model_combo")
                    else None
                ),
            }

            # Save to file
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(chat_data, f, indent=2, ensure_ascii=False)

            self.status_bar.showMessage(f"Chat saved to {Path(file_path).name}")
            QMessageBox.information(
                self, "Save Chat", f"Chat saved successfully to:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save chat:\n{str(e)}")

    def load_chat(self):
        """Load chat from JSON file."""
        # Ask user if they want to clear current chat
        if self.conversation_history:
            reply = QMessageBox.question(
                self,
                "Load Chat",
                "Loading a chat will replace the current conversation. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        # Get file to load
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Chat", "", "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Load from file
            with open(file_path, "r", encoding="utf-8") as f:
                chat_data = json.load(f)

            # Validate format
            if "conversation" not in chat_data:
                raise ValueError(
                    "Invalid chat file format: missing 'conversation' field"
                )

            # Clear current chat
            self.chat_widget.clear_messages()
            self.conversation_history = []
            # Reset context when loading chat (cannot reconstruct context from text)
            self.current_context = None

            # Load conversation
            conversation = chat_data["conversation"]
            for msg in conversation:
                role = msg.get("role", "")
                content = msg.get("content", "")
                image_path = msg.get("image_path", None)

                if role == "user":
                    if image_path and os.path.exists(image_path):
                        # User message with image
                        self.chat_widget.add_image_message(image_path, content)
                    else:
                        # Regular user message
                        self.chat_widget.add_user_message(content)
                    # Store in history
                    if image_path:
                        self.conversation_history.append(
                            {
                                "role": "user",
                                "content": content,
                                "image_path": image_path,
                            }
                        )
                    else:
                        self.conversation_history.append(
                            {"role": "user", "content": content}
                        )
                elif role == "assistant":
                    # AI message
                    self.chat_widget.add_assistant_message(content)
                    self.conversation_history.append(
                        {"role": "assistant", "content": content}
                    )

            # Set model if specified
            if "model" in chat_data and chat_data["model"]:
                model_name = chat_data["model"]
                if hasattr(self.status_panel, "model_combo"):
                    index = self.status_panel.model_combo.findText(model_name)
                    if index >= 0:
                        self.status_panel.model_combo.setCurrentIndex(index)

            self.status_bar.showMessage(f"Chat loaded from {Path(file_path).name}")
            QMessageBox.information(
                self,
                "Load Chat",
                f"Chat loaded successfully from:\n{file_path}\n\n{len(conversation)} messages loaded.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load chat:\n{str(e)}")
            import traceback

            traceback.print_exc()

    def show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self.config_manager, self)
        if dialog.exec():
            # Reload theme if changed
            theme_name = self.config_manager.get("ui.theme", "dark")
            stylesheet = Theme.get_stylesheet(theme_name)
            self.setStyleSheet(stylesheet)

            # Reinit image generator if storage path changed
            storage_path = self.config_manager.get("models.storage_path")
            if storage_path:
                self._init_image_generator()

            # Reinit TTS engine if TTS settings changed
            self._init_tts_engine()

            # Update status panel voice dropdown based on current language
            lang_code = self.config_manager.get("tts.lang_code", "a")
            if hasattr(self.status_panel, "update_voices_for_language"):
                self.status_panel.update_voices_for_language(lang_code)

            voice = self.config_manager.get("tts.voice", "af_heart")
            if hasattr(self.status_panel, "tts_voice_combo"):
                # Wait a bit for voices to update
                from PySide6.QtCore import QTimer

                QTimer.singleShot(100, lambda: self._update_status_voice(voice))

            # Refresh cached config values
            self._cache_config_values()

            self.status_bar.showMessage("Settings saved")

    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About locAI",
            "locAI - Local AI Assistant\n\n"
            "Version 1.0.0\n\n"
            "A commercial desktop AI assistant combining:\n"
            "- LLM (via Ollama)\n"
            "- Image Generation (Stable Diffusion)\n"
            "- Text-to-Speech (Edge TTS)\n\n"
            "© 2025",
        )

    def _on_chunk_received(self, chunk: str):
        """Handle chunk received from worker."""
        try:
            # Create bubble on first chunk if it doesn't exist
            if self.chat_widget.current_ai_bubble is None:
                self.chat_widget.start_ai_message()
            # Append chunk (only if non-empty)
            if chunk and chunk.strip():
                self.chat_widget.append_ai_chunk(chunk)
        except Exception as e:
            print(f"Error in _on_chunk_received: {e}")
            # Don't print full traceback in production - too verbose

    def _on_response_finished(self, new_context):
        """Handle response completion."""
        try:
            self.current_context = new_context
            
            # Unload model after response to free GPU memory for next request
            # This prevents GPU memory buildup and ensures fast subsequent requests
            if self.last_used_model:
                print(f"Model {self.last_used_model} finished - unloading to free GPU memory...")
                self.ollama_client.unload_model(self.last_used_model)
                
                # Aggressive GPU memory cleanup after unload
                try:
                    import torch
                    import gc
                    if torch.cuda.is_available():
                        torch.cuda.synchronize()
                        for _ in range(5):
                            torch.cuda.empty_cache()
                        try:
                            torch.cuda.ipc_collect()
                        except AttributeError:
                            pass
                        gc.collect()
                        print("GPU memory cleared after model unload")
                except:
                    pass
                
                # Clear context after vision model (helps with next request)
                if self.last_was_vision:
                    self.current_context = None
            
            # Only finish if bubble exists
            if self.chat_widget.current_ai_bubble is not None:
                # Get the full response text from bubble
                response_text = getattr(
                    self.chat_widget.current_ai_bubble, "current_text", ""
                )
                # Add to conversation history
                if response_text:
                    self.conversation_history.append(
                        {"role": "assistant", "content": response_text}
                    )

                # Limit history if needed (use cached value)
                max_history = self._conversation_settings_cache["max_history"]
                if (
                    max_history > 0 and len(self.conversation_history) > max_history * 2
                ):  # *2 because user+assistant pairs
                    # Keep only last max_history pairs
                    self.conversation_history = self.conversation_history[
                        -(max_history * 2) :
                    ]

                # Auto-speak if enabled
                if self.tts_engine and self.config_manager.get("tts.auto_speak", False):
                    if response_text:
                        # Small delay to ensure UI is updated
                        from PySide6.QtCore import QTimer

                        QTimer.singleShot(500, lambda: self._speak_text(response_text))

                self.chat_widget.finish_ai_message()
            else:
                # If no chunks received, show error
                self.chat_widget.start_ai_message()
                self.chat_widget.append_ai_chunk("No response received from model.")
                self.chat_widget.finish_ai_message()
        except Exception as e:
            print(f"Error in _on_response_finished: {e}")
            import traceback

            traceback.print_exc()
            try:
                if self.chat_widget.current_ai_bubble is not None:
                    self.chat_widget.finish_ai_message()
            except:
                pass

    def _on_response_error(self, error: str):
        """Handle response error."""
        try:
            # Create bubble if it doesn't exist
            if self.chat_widget.current_ai_bubble is None:
                self.chat_widget.start_ai_message()
            # Show error message
            error_msg = f"[Error: {error}]"
            self.chat_widget.append_ai_chunk(error_msg)
            self.chat_widget.finish_ai_message()
            # Hide status indicator on error
            if hasattr(self.chat_widget, "status_indicator"):
                self.chat_widget.status_indicator.setVisible(False)
        except Exception as e:
            print(f"Error in _on_response_error: {e}")
            import traceback

            traceback.print_exc()
            try:
                if self.chat_widget.current_ai_bubble is not None:
                    self.chat_widget.finish_ai_message()
            except:
                pass

    def on_seed_lock_toggled(self, locked: bool):
        """Handle seed lock toggle from chat widget."""
        self.seed_locked = locked

    def on_tts_play(self):
        """Handle TTS play button click."""
        print(
            f"TTS Play clicked. Engine: {self.tts_engine}, Pipeline: {self.tts_engine.pipeline if self.tts_engine else None}"
        )

        if not self.tts_engine:
            self.status_bar.showMessage(
                "TTS engine not initialized. Check Settings > TTS."
            )
            print("TTS engine not initialized")
            return

        if not self.tts_engine.pipeline:
            self.status_bar.showMessage("TTS pipeline not ready. Please wait...")
            print("TTS pipeline not ready")
            return

        # Get last AI response from conversation history
        if self.conversation_history:
            # Find last assistant message
            for msg in reversed(self.conversation_history):
                if msg.get("role") == "assistant" and msg.get("content"):
                    text_to_speak = msg["content"]
                    print(f"Speaking text: {text_to_speak[:50]}...")
                    # Speak the text
                    self.tts_engine.speak(text_to_speak)
                    self.status_panel.set_tts_playing(True)
                    self.status_bar.showMessage("Reading last AI response...")
                    return

            # If no assistant message found, try current bubble
            if self.chat_widget.current_ai_bubble:
                text = getattr(self.chat_widget.current_ai_bubble, "current_text", "")
                if text:
                    print(f"Speaking from current bubble: {text[:50]}...")
                    self.tts_engine.speak(text)
                    self.status_panel.set_tts_playing(True)
                    self.status_bar.showMessage("Reading current AI response...")
                    return

        # If no text found
        print("No AI response found in history or current bubble")
        self.status_bar.showMessage("No AI response to read. Send a message first.")

    def on_tts_pause(self):
        """Handle TTS pause button click."""
        if not self.tts_engine:
            return

        if self.tts_engine.is_speaking:
            self.tts_engine.pause()
            self.status_panel.set_tts_playing(False)
            self.status_bar.showMessage("TTS paused")
        else:
            # Resume if paused
            self.tts_engine.resume()
            self.status_panel.set_tts_playing(True)
            self.status_bar.showMessage("TTS resumed")

    def on_tts_stop(self):
        """Handle TTS stop button click."""
        if not self.tts_engine:
            return

        self.tts_engine.stop()
        self.status_panel.set_tts_playing(False)
        self.status_bar.showMessage("TTS stopped")

    def on_tts_voice_changed(self, voice: str):
        """Handle TTS voice selection change."""
        if self.tts_engine:
            self.tts_engine.set_voice(voice)
            # Save to config
            self.config_manager.set("tts.voice", voice)
            self.config_manager.save_config()

    def on_tts_language_changed(self, lang_code: str):
        """Handle TTS language selection change (from Settings)."""
        if self.tts_engine:
            self.tts_engine.set_lang_code(lang_code)
            # Save to config
            self.config_manager.set("tts.lang_code", lang_code)
            self.config_manager.save_config()
            # Update voice dropdown in status panel
            if hasattr(self.status_panel, "update_voices_for_language"):
                self.status_panel.update_voices_for_language(lang_code)

    def _speak_text(self, text: str):
        """Helper method to speak text and update UI."""
        if self.tts_engine and text:
            self.tts_engine.speak(text)
            self.status_panel.set_tts_playing(True)

    def _update_status_voice(self, voice: str):
        """Update status panel voice dropdown."""
        if hasattr(self.status_panel, "tts_voice_combo"):
            index = self.status_panel.tts_voice_combo.findText(voice)
            if index >= 0:
                self.status_panel.tts_voice_combo.setCurrentIndex(index)

    def on_image_prompt_sent(self, prompt: str):
        """Handle image generation prompt."""
        if not self.image_generator:
            QMessageBox.warning(
                self,
                "Image Generation Not Available",
                "Image generation is not available.\n\n"
                "Please:\n"
                "1. Install requirements: pip install -r requirements.txt\n"
                "2. Set model storage path in Settings > Models",
            )
            return

        # Auto-unload Ollama models before image generation to free GPU memory
        print("Auto-unloading Ollama models to free GPU memory...")
        self.ollama_client.unload_all_models_silent()

        # Add user message showing the prompt
        self.chat_widget.add_user_message(f"Generate image: {prompt}")

        # Determine seed to use
        import random

        if self.seed_locked and self.last_image_seed is not None:
            # Use locked seed (same as last time)
            seed_to_use = self.last_image_seed
        else:
            # Generate random seed
            seed_to_use = random.randint(0, 2147483647)
            self.last_image_seed = seed_to_use

        # Show generating message
        generating_bubble = self.chat_widget.messages_layout.itemAt(
            self.chat_widget.messages_layout.count() - 2
        )
        if generating_bubble:
            generating_bubble = generating_bubble.widget()

        # Start image generation in background thread
        worker = ImageGenerationWorker(
            self.image_generator, prompt, self.config_manager, seed=seed_to_use
        )
        worker.image_generated.connect(self._on_image_generated)
        worker.error_occurred.connect(self._on_image_error)
        worker.progress_updated.connect(self._on_image_progress)
        self.current_image_worker = worker
        worker.finished.connect(lambda: setattr(self, "current_image_worker", None))
        worker.start()

    def _on_image_generated(self, image_path: str):
        """Handle successful image generation."""
        try:
            # Get prompt from worker
            prompt = getattr(self.current_image_worker, "prompt", "Generated image")
            self.chat_widget.add_image_message(image_path, prompt)
            # Save to conversation history with image path
            self.conversation_history.append(
                {"role": "user", "content": prompt, "image_path": image_path}
            )
            self.status_bar.showMessage(
                f"Image generated: {os.path.basename(image_path)}"
            )
        except Exception as e:
            print(f"Error displaying image: {e}")
            QMessageBox.warning(self, "Error", f"Error displaying image: {e}")

    def on_text_selected_for_tts(self, text: str):
        """Handle text selection for TTS."""
        if not self.tts_engine:
            self.status_bar.showMessage(
                "TTS engine not initialized. Check Settings > TTS."
            )
            return

        if not self.tts_engine.pipeline:
            self.status_bar.showMessage("TTS pipeline not ready. Please wait...")
            return

        # Clean and speak the selected text
        clean_text = text.strip()
        if clean_text:
            self.tts_engine.speak(clean_text)
            self.status_panel.set_tts_playing(True)
            self.status_bar.showMessage(f"Reading selected text...")

    def on_text_selected_for_image(self, text: str):
        """Handle text selection for image generation."""
        if not self.image_generator:
            self.status_bar.showMessage(
                "Image generation not available. Check Settings > Models."
            )
            return

        # Auto-unload Ollama models before image generation
        print("Auto-unloading Ollama models to free GPU memory...")
        self.ollama_client.unload_all_models_silent()

        # Use selected text as prompt
        prompt = text.strip()
        if not prompt:
            return

        # Generate image using current settings
        self.on_image_prompt_sent(prompt)

    def _on_image_error(self, error: str):
        """Handle image generation error."""
        self.chat_widget.add_user_message(f"[Error generating image: {error}]")
        QMessageBox.warning(self, "Image Generation Error", error)

    def _on_image_progress(self, progress: int):
        """Handle image generation progress."""
        self.status_bar.showMessage(f"Generating image... {progress}%")

    def _create_logo_icon(self) -> QIcon:
        """Create application logo icon."""
        # Create pixmap for icon (multiple sizes for better quality)
        icon = QIcon()

        # Create different sizes: 16x16, 32x32, 48x48, 64x64, 256x256
        sizes = [16, 32, 48, 64, 256]

        for size in sizes:
            pixmap = QPixmap(size, size)
            pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Draw background circle with gradient-like effect
            # Use primary color from theme
            primary_color = QColor(74, 158, 255)  # #4A9EFF
            painter.setBrush(primary_color)
            painter.setPen(Qt.PenStyle.NoPen)

            # Draw circle with padding
            padding = size // 8
            painter.drawEllipse(
                padding, padding, size - 2 * padding, size - 2 * padding
            )

            # Draw "AI" text in white
            painter.setPen(QColor(255, 255, 255))
            font = QFont()
            font.setBold(True)
            # Scale font size based on icon size
            font_size = max(8, size // 3)
            font.setPixelSize(font_size)
            painter.setFont(font)

            # Center text
            text = "AI"
            painter.drawText(0, 0, size, size, Qt.AlignmentFlag.AlignCenter, text)

            painter.end()

            # Add pixmap to icon
            icon.addPixmap(pixmap)

        return icon

    def _set_dark_title_bar(self):
        """Set dark title bar for Windows 10/11."""
        if sys.platform == "win32":
            try:
                from ctypes import windll, byref, sizeof, c_int

                # Windows 10/11 dark mode API
                # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20

                # Get window handle (use windowHandle() for PySide6)
                window_handle = self.windowHandle()
                if window_handle:
                    hwnd = int(window_handle.winId())

                    # Set dark mode
                    value = c_int(1)  # Enable dark mode
                    windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, byref(value), sizeof(value)
                    )
            except Exception:
                # If API call fails, silently continue
                # (older Windows versions or API not available)
                pass

    def showEvent(self, event):
        """Handle window show event."""
        super().showEvent(event)
        # Set dark title bar after window is shown
        self._set_dark_title_bar()

    def closeEvent(self, event):
        """Handle window close event."""
        # Disable global shortcuts
        if hasattr(self, "global_shortcuts") and self.global_shortcuts:
            self.global_shortcuts.disable()

        # No timer to stop anymore (removed periodic checks)

        # Wait for current worker to finish (with timeout)
        if hasattr(self, "current_worker") and self.current_worker is not None:
            if self.current_worker.isRunning():
                self.current_worker.terminate()
                self.current_worker.wait(1000)  # Wait max 1 second

        # Unload all models to free GPU memory before closing
        print("Unloading all models to free GPU memory...")
        
        # Unload Ollama models
        if hasattr(self, "ollama_client") and self.ollama_client:
            try:
                self.ollama_client.unload_all_models_silent()
            except Exception as e:
                print(f"Error unloading Ollama models: {e}")
        
        # Unload image generator model
        if hasattr(self, "image_generator") and self.image_generator:
            try:
                if self.image_generator.pipeline is not None:
                    self.image_generator.unload_model()
            except Exception as e:
                print(f"Error unloading image generator: {e}")
        
        # Force final GPU memory cleanup (aggressive)
        try:
            import torch
            import gc
            import os
            
            # Force garbage collection multiple times
            for _ in range(3):
                gc.collect()
            
            # Clear CUDA cache if available (very aggressive cleanup)
            if torch.cuda.is_available():
                # Reset CUDA context to force release of all memory
                try:
                    # Get current device
                    device = torch.cuda.current_device()
                    # Synchronize all operations
                    torch.cuda.synchronize(device)
                    
                    # Multiple cache clears
                    for _ in range(5):
                        torch.cuda.empty_cache()
                    
                    # Try to reset CUDA context (if possible)
                    try:
                        torch.cuda.reset_peak_memory_stats(device)
                    except:
                        pass
                    
                    # Collect IPC resources
                    try:
                        torch.cuda.ipc_collect()
                    except AttributeError:
                        pass
                    
                    # Final garbage collection
                    gc.collect()
                    
                    print("GPU memory cache aggressively cleared")
                except Exception as e:
                    print(f"Error in aggressive GPU cleanup: {e}")
                    # Fallback: try basic cleanup
                    try:
                        torch.cuda.empty_cache()
                        gc.collect()
                    except:
                        pass
        except Exception as e:
            print(f"Error clearing GPU cache: {e}")

        # Save any pending configuration
        try:
            self.config_manager.save_config()
        except:
            pass
        event.accept()


class OllamaWorker(QThread):
    """Worker thread for non-blocking Ollama requests."""

    chunk_received = Signal(str)
    finished = Signal(object)  # new_context
    error_occurred = Signal(str)

    def __init__(self, client, model, prompt, context, llm_params=None, images=None):
        super().__init__()
        self.client = client
        self.model = model
        self.prompt = prompt
        self.context = context
        self.llm_params = llm_params or {}
        self.images = images  # List of base64-encoded images for vision models

    def run(self):
        """Run in background thread."""
        try:
            chunks_received = False

            def on_chunk(chunk: str):
                nonlocal chunks_received
                try:
                    if chunk and chunk.strip():  # Only emit non-empty chunks
                        chunks_received = True
                        self.chunk_received.emit(chunk)
                except Exception as e:
                    print(f"Error emitting chunk: {e}")
                    import traceback

                    traceback.print_exc()

            response, new_context = self.client.generate_response_stream(
                model=self.model,
                prompt=self.prompt,
                context=self.context,
                callback=on_chunk,
                images=self.images,
                num_ctx=self.llm_params.get("num_ctx"),
                temperature=self.llm_params.get("temperature"),
                top_p=self.llm_params.get("top_p"),
                top_k=self.llm_params.get("top_k"),
                repeat_penalty=self.llm_params.get("repeat_penalty"),
                num_predict=self.llm_params.get("num_predict"),
            )

            # Check if response is an error message
            if response and (
                response.startswith("Error") or response.startswith("Error generating")
            ):
                self.error_occurred.emit(response)
            elif not chunks_received:
                # No chunks received - might be empty response
                self.error_occurred.emit(
                    "Model returned empty response. Please try again."
                )
            else:
                # Success - emit context
                self.finished.emit(new_context)
        except Exception as e:
            import traceback

            error_msg = f"{str(e)}"
            print(f"OllamaWorker error: {error_msg}")
            traceback.print_exc()
            self.error_occurred.emit(str(e))
