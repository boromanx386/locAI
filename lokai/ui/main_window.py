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
from typing import Dict, List
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QFont, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray
from lokai.core.config_manager import ConfigManager
from lokai.ui.theme import Theme
from lokai.ui.status_panel import StatusPanel
from lokai.ui.chat_widget import ChatWidget
from lokai.ui.settings_dialog import SettingsDialog
from lokai.ui.debug_dialog import DebugDialog
from lokai.core.ollama_detector import OllamaDetector
from lokai.core.ollama_client import OllamaClient
from lokai.core.image_generator import ImageGenerator
from lokai.core.video_generator import VideoGenerator
from lokai.core.audio_generator import AudioGenerator
from lokai.core.embedding_client import EmbeddingClient
from lokai.core.chat_vector_store import ChatVectorStore
from lokai.ui.image_worker import ImageGenerationWorker
from lokai.ui.video_worker import VideoGenerationWorker
from lokai.ui.audio_worker import AudioGenerationWorker
from lokai.core.asr_engine import ASREngine
from lokai.core.tools_handler import get_available_tools, execute_tool
from lokai.core.paths import get_embeddings_dir, get_models_storage_path, get_image_storage_path, get_video_storage_path, get_audio_storage_path, get_asr_storage_path
from lokai.ui.attachments import read_text_file_with_limits, format_file_size


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

        # Initialize embedding components for semantic memory (lazy loading)
        self.embedding_enabled = config_manager.get("rag.enabled", False)
        # Manual-only semantic memory: embeddings are created only via UI "Remember…" actions.
        # (We intentionally ignore any legacy auto-embed setting.)
        self.rag_auto_embed = False
        self.embedding_workers = []  # Track all embedding workers to clean up properly
        # Delay embedding initialization to speed up startup
        self.embedding_client = None
        self.chat_vector_store = None
        self.embeddings_dir = None
        self.semantic_memory_threshold = None
        self.top_k_relevant = None
        self.recent_messages_count = None

        if self.embedding_enabled:
            # Initialize embedding components with delay to avoid blocking startup
            QTimer.singleShot(500, self._init_embedding_components)

        # Current conversation context
        self.current_context = None
        self.conversation_history = (
            []
        )  # List of {"role": "user"/"assistant", "content": "..."}

        # Chat ID for semantic memory (unique per chat session)
        self.current_chat_id = None  # Will be generated when starting new chat

        # Image generation seed management
        self.last_image_seed = None  # Last seed used for image generation
        self.seed_locked = False  # Whether seed is locked
        self.current_seed = None  # Current seed displayed in status bar

        # Track last used model for GPU memory management
        self.last_used_model = None
        self.last_was_vision = False  # Track if last request was vision (with images)

        # Cache LLM parameters to avoid repeated config reads
        self._llm_params_cache = None
        self._conversation_settings_cache = None
        # Get default model and cache its settings
        default_model = config_manager.get("ollama.default_model", "llama3.2")
        self._current_model = default_model
        self._cache_config_values(default_model)

        # Setup UI
        self.init_ui()

        # Initial status check (delayed to not block startup)
        # No periodic timer - check only when needed (startup, refresh button, or before sending message)
        QTimer.singleShot(2000, self.check_ollama_status)

        # Flag to track if we've cleared auto-loaded models on first message
        self._startup_models_cleared = False

        # Track last status check to avoid redundant checks
        self._last_status_check = None
        self._status_check_interval = 30000  # Only check if 30+ seconds passed

    def _init_embedding_components(self):
        """Initialize embedding components delayed to speed up startup."""
        try:
            base_url = self.config_manager.get("ollama.base_url", "http://localhost:11434")
            force_cpu = self.config_manager.get("rag.force_cpu", True)
            self.embedding_client = EmbeddingClient(base_url, force_cpu=force_cpu)
            # Manual-only: never auto-embed.
            self.rag_auto_embed = False
            # Set embedding model from config
            embedding_model = self.config_manager.get(
                "rag.embedding_model", "nomic-embed-text:v1.5"
            )
            self.embedding_client.default_model = embedding_model
            # Store embeddings in config directory (will be set per chat)
            self.embeddings_dir = get_embeddings_dir(self.config_manager)
            # Initialize vector store for current chat if we already have a chat id
            if self.current_chat_id:
                embedding_store_path = (
                    self.embeddings_dir / f"chat_{self.current_chat_id}.json"
                )
                self.chat_vector_store = ChatVectorStore(embedding_store_path)
            else:
                self.chat_vector_store = None  # Will be initialized per chat
            self.semantic_memory_threshold = self.config_manager.get(
                "rag.semantic_memory_threshold", 30
            )
            self.top_k_relevant = self.config_manager.get("rag.top_k_relevant", 5)
            self.recent_messages_count = self.config_manager.get(
                "rag.recent_messages_count", 10
            )
            print("[Startup] Embedding components initialized")
        except Exception as e:
            print(f"Error initializing embedding components: {e}")
            import traceback
            traceback.print_exc()
            # Disable embedding on error
            self.embedding_enabled = False
            self.embedding_client = None
            self.chat_vector_store = None

    def _delayed_load_models(self):
        """Load models list delayed to avoid loading models at startup."""
        try:
            models, model_error = self.ollama_detector.get_llm_and_vision_models()
            if models:
                self.status_panel.update_models(models)
        except Exception as e:
            print(f"[Startup] Error loading models list: {e}")

    def _clear_ollama_models_at_startup(self):
        """Clear any models that Ollama may have auto-loaded at startup."""
        try:
            if self.ollama_client.is_running():
                print("[Startup] Clearing any auto-loaded Ollama models to free VRAM...")
                self.ollama_client.unload_all_models_silent()

                # Also clear GPU memory to ensure it's freed
                self._clear_gpu_memory()
        except Exception as e:
            print(f"[Startup] Error clearing Ollama models: {e}")

    def _clear_gpu_memory(self):
        """Clear GPU memory aggressively."""
        try:
            import torch
            import gc

            if torch.cuda.is_available():
                torch.cuda.synchronize()
                # Multiple passes to ensure all memory is freed
                for _ in range(5):
                    torch.cuda.empty_cache()
                try:
                    torch.cuda.ipc_collect()
                except AttributeError:
                    pass
                try:
                    torch.cuda.reset_peak_memory_stats()
                except:
                    pass
                gc.collect()
                print("[Startup] GPU memory cleared")
        except ImportError:
            pass  # PyTorch not available
        except Exception as e:
            print(f"[Startup] Error clearing GPU memory: {e}")

    def _unload_all_ollama_models_at_startup(self):
        """Unload all Ollama models at startup to free VRAM (Ollama may auto-load default model)."""
        try:
            if self.ollama_client.is_running():
                print("[Startup] Unloading all Ollama models to free VRAM...")
                self.ollama_client.unload_all_models_silent()
                print("[Startup] Ollama models unloaded")
        except Exception as e:
            print(f"[Startup] Error unloading Ollama models: {e}")
    
    def _reload_embedding_components(self):
        """Reload embedding components when RAG settings change."""
        # Clean up existing workers
        for worker in self.embedding_workers[:]:
            if worker.isRunning():
                worker.terminate()
                worker.wait()
        self.embedding_workers.clear()

        # Reload config values
        self.embedding_enabled = self.config_manager.get("rag.enabled", False)
        # Manual-only: never auto-embed (ignore legacy config).
        self.rag_auto_embed = False

        if self.embedding_enabled:
            try:
                base_url = self.config_manager.get(
                    "ollama.base_url", "http://localhost:11434"
                )
                force_cpu = self.config_manager.get("rag.force_cpu", True)
                self.embedding_client = EmbeddingClient(base_url, force_cpu=force_cpu)
                # Manual-only: never auto-embed.
                self.rag_auto_embed = False
                # Set embedding model from config
                embedding_model = self.config_manager.get(
                    "rag.embedding_model", "nomic-embed-text:v1.5"
                )
                self.embedding_client.default_model = embedding_model
                # Ensure embeddings directory exists
                self.embeddings_dir = get_embeddings_dir(self.config_manager)
                # Reload threshold and search parameters
                self.semantic_memory_threshold = self.config_manager.get(
                    "rag.semantic_memory_threshold", 30
                )
                self.top_k_relevant = self.config_manager.get("rag.top_k_relevant", 5)
                self.recent_messages_count = self.config_manager.get(
                    "rag.recent_messages_count", 10
                )
                # Reinitialize vector store for current chat if exists
                if self.current_chat_id:
                    embedding_store_path = (
                        self.embeddings_dir / f"chat_{self.current_chat_id}.json"
                    )
                    self.chat_vector_store = ChatVectorStore(embedding_store_path)
                # Update status indicator
                if hasattr(self.status_panel, "update_semantic_memory_status"):
                    message_count = 0
                    if self.chat_vector_store:
                        stats = self.chat_vector_store.get_stats()
                        message_count = stats.get("total_messages", 0)
                    self.status_panel.update_semantic_memory_status(True, message_count)
            except Exception as e:
                print(f"Error reloading embedding components: {e}")
                import traceback

                traceback.print_exc()
                # Disable embedding on error
                self.embedding_enabled = False
                self.embedding_client = None
                self.chat_vector_store = None
                if hasattr(self.status_panel, "update_semantic_memory_status"):
                    self.status_panel.update_semantic_memory_status(False, 0)
        else:
            # Disable embedding
            self.embedding_client = None
            if self.chat_vector_store:
                self.chat_vector_store = None
            if hasattr(self.status_panel, "update_semantic_memory_status"):
                self.status_panel.update_semantic_memory_status(False, 0)

    def _cache_config_values(self, model_name: str = None):
        """
        Cache frequently accessed config values to avoid repeated file reads.
        Uses model-specific settings if available, otherwise uses global defaults.

        Args:
            model_name: Optional model name to load model-specific settings
        """
        # Get model-specific settings if model is provided
        model_settings = None
        if model_name:
            model_settings = self.config_manager.get_llm_model_setting(model_name)

        # Use model-specific settings or fall back to global defaults
        if model_settings and "llm_params" in model_settings:
            llm_params = model_settings["llm_params"]
            self._llm_params_cache = {
                "num_ctx": llm_params.get(
                    "num_ctx",
                    self.config_manager.get("ollama.llm_params.num_ctx", 4096),
                ),
                "temperature": llm_params.get(
                    "temperature",
                    self.config_manager.get("ollama.llm_params.temperature", 0.7),
                ),
                "top_p": llm_params.get(
                    "top_p", self.config_manager.get("ollama.llm_params.top_p", 0.9)
                ),
                "top_k": llm_params.get(
                    "top_k", self.config_manager.get("ollama.llm_params.top_k", 40)
                ),
                "repeat_penalty": llm_params.get(
                    "repeat_penalty",
                    self.config_manager.get("ollama.llm_params.repeat_penalty", 1.1),
                ),
                "num_predict": llm_params.get(
                    "num_predict",
                    self.config_manager.get("ollama.llm_params.num_predict", -1),
                ),
            }
        else:
            # Use global defaults
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
                "num_predict": self.config_manager.get(
                    "ollama.llm_params.num_predict", -1
                ),
            }

        # Conversation settings
        if model_settings and "conversation" in model_settings:
            conv_settings = model_settings["conversation"]
            self._conversation_settings_cache = {
                "use_explicit_history": conv_settings.get(
                    "use_explicit_history",
                    self.config_manager.get(
                        "ollama.conversation.use_explicit_history", False
                    ),
                ),
                "system_prompt": conv_settings.get(
                    "system_prompt",
                    self.config_manager.get(
                        "ollama.conversation.system_prompt",
                        "You are a helpful AI assistant.",
                    ),
                ),
                "max_history": conv_settings.get(
                    "max_history_messages",
                    self.config_manager.get(
                        "ollama.conversation.max_history_messages", 20
                    ),
                ),
            }
        else:
            # Use global defaults
            self._conversation_settings_cache = {
                "use_explicit_history": self.config_manager.get(
                    "ollama.conversation.use_explicit_history", False
                ),
                "system_prompt": self.config_manager.get(
                    "ollama.conversation.system_prompt",
                    "You are a helpful AI assistant.",
                ),
                "max_history": self.config_manager.get(
                    "ollama.conversation.max_history_messages", 20
                ),
            }

    def _init_image_generator(self):
        """Initialize image generator if enabled and path is set."""
        storage_path = get_image_storage_path(self.config_manager)
        if storage_path:
            try:
                # Setup environment before importing diffusers
                from lokai.utils.model_manager import ModelManager

                manager = ModelManager(str(storage_path))
                manager.setup_environment_variables()

                self.image_generator = ImageGenerator(str(storage_path))
                if not self.image_generator.is_available():
                    self.image_generator = None
                    print("Image generation not available (diffusers not installed)")
            except Exception as e:
                print(f"Error initializing image generator: {e}")
                import traceback

                traceback.print_exc()
                self.image_generator = None

    def _init_video_generator(self):
        """Initialize video generator if enabled and path is set."""
        storage_path = get_video_storage_path(self.config_manager)
        if storage_path:
            try:
                # Setup environment before importing diffusers
                from lokai.utils.model_manager import ModelManager

                manager = ModelManager(str(storage_path))
                manager.setup_environment_variables()

                self.video_generator = VideoGenerator(str(storage_path))
                if not self.video_generator.is_available():
                    self.video_generator = None
                    print("Video generation not available (diffusers not installed)")
            except Exception as e:
                print(f"Error initializing video generator: {e}")
                import traceback

                traceback.print_exc()
                self.video_generator = None

    def _init_audio_generator(self):
        """Initialize audio generator if enabled and path is set."""
        storage_path = get_audio_storage_path(self.config_manager)
        if storage_path:
            try:
                # Setup environment before importing diffusers
                from lokai.utils.model_manager import ModelManager

                manager = ModelManager(str(storage_path))
                manager.setup_environment_variables()

                self.audio_generator = AudioGenerator(str(storage_path))
                if not self.audio_generator.is_available():
                    self.audio_generator = None
                    print("Audio generation not available (diffusers not installed)")
            except Exception as e:
                print(f"Error initializing audio generator: {e}")
                import traceback

                traceback.print_exc()
                self.audio_generator = None

    def _init_tts_engine(self):
        """Initialize TTS engine if enabled."""
        try:
            from lokai.core.tts_engine import create_tts_engine, KOKORO_AVAILABLE, POCKET_TTS_AVAILABLE

            # Check if TTS is enabled
            if not self.config_manager.get("tts.enabled", True):
                self.tts_engine = None
                return

            # Get TTS settings
            engine = self.config_manager.get("tts.engine", "kokoro")
            voice = self.config_manager.get("tts.voice", "af_heart")
            speed = self.config_manager.get("tts.speed", 1.0)

            # Check if selected engine is available
            if engine == "kokoro" and not KOKORO_AVAILABLE:
                print("Kokoro TTS not available. Install with: pip install kokoro soundfile")
                self.tts_engine = None
                return
            elif engine == "pocket_tts" and not POCKET_TTS_AVAILABLE:
                print("Pocket TTS not available. Install with: pip install pocket-tts scipy")
                self.tts_engine = None
                return

            # Callback when TTS finishes
            def on_tts_finished():
                self.status_panel.set_tts_playing(False)

            # Create TTS engine based on config
            if engine == "kokoro":
                lang_code = self.config_manager.get("tts.lang_code", "a")
                self.tts_engine = create_tts_engine(
                    "kokoro",
                    lang_code=lang_code,
                    voice=voice,
                    on_finished=on_tts_finished
                )
                # Update voices in status panel
                if hasattr(self.status_panel, "update_voices_for_language"):
                    self.status_panel.update_voices_for_language(lang_code, "kokoro", False)
                
                print(f"TTS engine initialized: engine=Kokoro, lang={lang_code}, voice={voice}")
            else:  # pocket_tts
                voice_cloning_enabled = self.config_manager.get("tts.voice_cloning.enabled", False)
                voice_cloning_file = self.config_manager.get("tts.voice_cloning.file_path", None)
                
                # If voice is "Clone Voice", use cloning file; otherwise use the selected voice
                actual_voice = voice if voice != "Clone Voice" else "alba"
                actual_cloning_file = voice_cloning_file if voice == "Clone Voice" and voice_cloning_enabled else None
                
                self.tts_engine = create_tts_engine(
                    "pocket_tts",
                    voice=actual_voice,
                    voice_cloning_file=actual_cloning_file,
                    on_finished=on_tts_finished
                )
                # Update voices in status panel (include "Clone Voice" if enabled)
                if hasattr(self.status_panel, "update_voices_for_language"):
                    self.status_panel.update_voices_for_language(None, "pocket_tts", voice_cloning_enabled)
                
                print(f"TTS engine initialized: engine=Pocket TTS, voice={voice}, cloning={voice == 'Clone Voice'}")

            # Set speed
            if hasattr(self.tts_engine, "speed"):
                self.tts_engine.speed = speed

            # Set voice from config
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

        except Exception as e:
            print(f"Error initializing TTS engine: {e}")
            import traceback

            traceback.print_exc()
            self.tts_engine = None

    def _init_asr_engine(self):
        """Initialize ASR engine if enabled."""
        try:
            asr_enabled = self.config_manager.get("asr.enabled", False)
            if not asr_enabled:
                print("ASR disabled in config")
                return

            from lokai.core.asr_engine import ASREngine

            storage_path = get_asr_storage_path(self.config_manager)
            # Get device from config (default to CPU)
            device = self.config_manager.get("asr.device", "cpu")
            self.asr_engine = ASREngine(str(storage_path) if storage_path else None, device=device)

            if not self.asr_engine.is_available():
                print("ASR engine not available (NeMo not installed)")
                self.asr_engine = None
                return

            print("ASR engine initialized")
            
            # Preload ASR model by starting and stopping voice input
            # This loads the model in background, avoiding 10-15 second delay on first use
            # Start immediately with minimal delay to ensure chat_widget is ready
            QTimer.singleShot(100, self._preload_asr_by_start_stop)

        except Exception as e:
            print(f"Error initializing ASR engine: {e}")
            import traceback
            traceback.print_exc()
            self.asr_engine = None
    
    def _preload_asr_by_start_stop(self):
        """Preload ASR model by starting and stopping voice input (like user clicked)."""
        try:
            # Check if voice input widget is available
            if not hasattr(self, 'chat_widget') or self.chat_widget is None:
                # Retry after short delay if chat_widget not ready yet
                QTimer.singleShot(200, self._preload_asr_by_start_stop)
                return
            
            if not hasattr(self.chat_widget, 'voice_input_widget') or self.chat_widget.voice_input_widget is None:
                # Retry after short delay if voice_input_widget not ready yet
                QTimer.singleShot(200, self._preload_asr_by_start_stop)
                return
            
            voice_widget = self.chat_widget.voice_input_widget
            
            # Check if asr_worker is available
            if not hasattr(voice_widget, 'asr_worker') or voice_widget.asr_worker is None:
                # Retry after short delay if asr_worker not ready yet
                QTimer.singleShot(200, self._preload_asr_by_start_stop)
                return
            
            # Connect to listening_started signal to know when model is loaded
            def on_listening_started():
                # Model is loaded, now stop voice input
                QTimer.singleShot(100, lambda: self._stop_voice_input_for_preload(voice_widget))
                try:
                    voice_widget.asr_worker.listening_started.disconnect(on_listening_started)
                except:
                    pass  # Already disconnected
            
            voice_widget.asr_worker.listening_started.connect(on_listening_started)
            
            # Start voice input (this will load the model in background)
            print("[ASR Preload] Starting voice input to load model...")
            voice_widget.start_voice_input()
            
        except Exception as e:
            print(f"[ASR Preload] Error preloading ASR: {e}")
            # Retry once more after delay
            QTimer.singleShot(500, self._preload_asr_by_start_stop)
    
    def _stop_voice_input_for_preload(self, voice_widget):
        """Stop voice input after preload."""
        try:
            voice_widget.stop_voice_input()
            print("[ASR Preload] Voice input stopped, model loaded and ready")
        except Exception as e:
            print(f"[ASR Preload] Error stopping voice input: {e}")

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
        # Set reasonable minimum size to prevent window from collapsing too much
        self.setMinimumSize(400, 300)

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
        # Connect stop button
        self.status_panel.stop_clicked.connect(self.on_stop_all_operations)

        # Initialize chat ID and vector store for embedding
        if self.embedding_enabled:
            from datetime import datetime

            if not self.current_chat_id:
                self.current_chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            # embeddings_dir is initialized lazily in _init_embedding_components
            if self.embeddings_dir is not None:
                embedding_store_path = (
                    self.embeddings_dir / f"chat_{self.current_chat_id}.json"
                )
                self.chat_vector_store = ChatVectorStore(embedding_store_path)
            else:
                self.chat_vector_store = None  # will be initialized once components are ready

        # Update semantic memory status indicator
        if self.embedding_enabled and hasattr(
            self.status_panel, "update_semantic_memory_status"
        ):
            message_count = 0
            if self.chat_vector_store:
                stats = self.chat_vector_store.get_stats()
                message_count = stats.get("total_messages", 0)
            self.status_panel.update_semantic_memory_status(True, message_count)

        # Language change is handled through Settings only
        main_layout.addWidget(self.status_panel)

        # Chat widget (center, takes most space)
        self.chat_widget = ChatWidget(self.ollama_client, self.config_manager)
        main_layout.addWidget(self.chat_widget, stretch=1)

        # Connect chat widget signals
        self.chat_widget.message_sent.connect(
            lambda msg, img: self.on_message_sent(msg, img)
        )
        self.chat_widget.image_prompt_sent.connect(self.on_image_prompt_sent)
        self.chat_widget.seed_lock_toggled.connect(self.on_seed_lock_toggled)
        self.chat_widget.seed_increase_requested.connect(self.on_seed_increase)
        self.chat_widget.seed_decrease_requested.connect(self.on_seed_decrease)
        self.chat_widget.text_selected_for_tts.connect(self.on_text_selected_for_tts)
        self.chat_widget.text_selected_for_image.connect(
            self.on_text_selected_for_image
        )
        self.chat_widget.audio_prompt_sent.connect(self.on_audio_prompt_sent)
        self.chat_widget.text_selected_for_audio.connect(
            self.on_text_selected_for_audio
        )
        # Manual semantic memory (RAG)
        if hasattr(self.chat_widget, "remember_selected_text"):
            self.chat_widget.remember_selected_text.connect(
                self.on_remember_selected_text
            )
        if hasattr(self.chat_widget, "remember_message"):
            self.chat_widget.remember_message.connect(self.on_remember_message)
        if hasattr(self.chat_widget, "memory_stats_requested"):
            self.chat_widget.memory_stats_requested.connect(
                self.on_memory_stats_requested
            )

        # Initialize image generator (if enabled) - delayed to speed up startup
        self.image_generator = None
        self.video_generator = None
        self.audio_generator = None
        QTimer.singleShot(1500, self._init_image_generator)
        QTimer.singleShot(1500, self._init_video_generator)
        QTimer.singleShot(1500, self._init_audio_generator)

        # Initialize ASR engine (if enabled)
        self.asr_engine = None
        self._init_asr_engine()

        # Connect video generation signal
        self.chat_widget.image_selected_for_video.connect(
            self.on_image_selected_for_video
        )

        # Initialize TTS engine
        self.tts_engine = None
        self._init_tts_engine()
        # Note: _init_tts_engine already calls update_voices_for_language, so we don't need to call it again here

        # Set voice from config in status panel (voices are already loaded by _init_tts_engine)
        if hasattr(self.status_panel, "tts_voice_combo"):
            voice = self.config_manager.get("tts.voice", "af_heart")
            index = self.status_panel.tts_voice_combo.findText(voice)
            if index >= 0:
                self.status_panel.tts_voice_combo.setCurrentIndex(index)

        # Initialize global shortcuts for system-wide text selection (delayed)
        QTimer.singleShot(2000, self._init_global_shortcuts)

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

        debug_action = QAction("Debug Prompt", self)
        debug_action.setShortcut("Ctrl+D")
        debug_action.triggered.connect(self.show_debug_prompt)
        help_menu.addAction(debug_action)

        help_menu.addSeparator()

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
                    # Get LLM and Vision models (exclude embedding) - but delay to avoid loading models at startup
                    QTimer.singleShot(1000, self._delayed_load_models)
                    self.status_bar.showMessage("Ollama is running")

                    # Clear any auto-loaded models after status check (first time only)
                    if not self._startup_models_cleared:
                        QTimer.singleShot(2000, self._clear_ollama_models_at_startup)
                        self._startup_models_cleared = True
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

        # Update current model and reload settings for this model
        self._current_model = model_name
        self._cache_config_values(model_name)

        self.status_bar.showMessage(f"Selected model: {model_name} - Settings loaded")

    def on_stop_all_operations(self):
        """Stop all running operations (Ollama and Image Generation)."""
        stopped_anything = False

        # Cancel all active Ollama requests first (stops streaming immediately)
        if hasattr(self, "ollama_client") and self.ollama_client:
            print("Cancelling all active Ollama requests...")
            try:
                self.ollama_client.cancel_all_requests()
            except Exception as e:
                print(f"Error cancelling requests: {e}")

        # Stop Ollama worker if running
        if hasattr(self, "current_worker") and self.current_worker is not None:
            if self.current_worker.isRunning():
                print("Stopping Ollama worker...")
                self.current_worker.terminate()
                self.current_worker.wait(1000)  # Wait max 1 second
                self.current_worker = None
                stopped_anything = True

                # Remove incomplete AI bubble if exists
                if (
                    hasattr(self.chat_widget, "current_ai_bubble")
                    and self.chat_widget.current_ai_bubble is not None
                ):
                    try:
                        self.chat_widget.current_ai_bubble.setParent(None)
                        self.chat_widget.current_ai_bubble.deleteLater()
                        self.chat_widget.current_ai_bubble = None
                    except:
                        pass

        # Stop Image Generation worker if running
        if (
            hasattr(self, "current_image_worker")
            and self.current_image_worker is not None
        ):
            if self.current_image_worker.isRunning():
                print("Stopping Image Generation worker...")
                self.current_image_worker.terminate()
                self.current_image_worker.wait(1000)  # Wait max 1 second
                self.current_image_worker = None
                stopped_anything = True

        # Stop model and clear GPU memory, but KEEP chat context
        # (like Ollama app - you can continue the conversation after stopping)
        if stopped_anything:
            # Keep model tracking to know which model to stop
            model_to_stop = self.last_used_model
            # Note: We keep self.current_context and conversation_history intact
            # so user can continue the conversation after stopping

            # Stop the model using Ollama stop command (like Ollama app does)
            if model_to_stop and hasattr(self, "ollama_client") and self.ollama_client:
                print(f"Stopping model {model_to_stop}...")
                try:
                    self.ollama_client.stop_model(model_to_stop)
                except Exception as e:
                    print(f"Error stopping model: {e}")

            # Also unload all models to ensure GPU memory is cleared
            print("Unloading all models...")
            if hasattr(self, "ollama_client") and self.ollama_client:
                try:
                    self.ollama_client.unload_all_models_silent()
                except Exception as e:
                    print(f"Error unloading Ollama models: {e}")

            if hasattr(self, "image_generator") and self.image_generator:
                try:
                    self.image_generator.unload_model()
                except Exception as e:
                    print(f"Error unloading image generator: {e}")

            # Force GPU memory cleanup
            print("Clearing GPU memory...")
            try:
                from lokai.utils.clear_gpu_memory import clear_gpu_memory
                clear_gpu_memory()
            except Exception as e:
                print(f"Error clearing GPU memory: {e}")

            self.status_bar.showMessage(
                "Model stopped and GPU memory cleared. Chat context preserved - you can continue the conversation."
            )
            # Re-enable send button
            self.chat_widget.set_send_enabled(True)
        else:
            # No worker was running - still clear GPU RAM (ollama stop + unload + clear)
            model_to_stop = getattr(self, "last_used_model", None)
            if model_to_stop and hasattr(self, "ollama_client") and self.ollama_client:
                try:
                    self.ollama_client.stop_model(model_to_stop)
                except Exception as e:
                    print(f"Error stopping model: {e}")
            if hasattr(self, "ollama_client") and self.ollama_client:
                try:
                    self.ollama_client.unload_all_models_silent()
                except Exception as e:
                    print(f"Error unloading Ollama models: {e}")
            if hasattr(self, "image_generator") and self.image_generator:
                try:
                    self.image_generator.unload_model()
                except Exception as e:
                    print(f"Error unloading image generator: {e}")
            try:
                from lokai.utils.clear_gpu_memory import clear_gpu_memory
                clear_gpu_memory()
            except Exception as e:
                print(f"Error clearing GPU memory: {e}")
            self.status_bar.showMessage("GPU memory cleared")
            self.chat_widget.set_send_enabled(True)

    def on_message_sent(self, message: str, image_path: str = ""):
        """Handle message sent from chat widget."""
        # Clear any auto-loaded models if not already done (backup in case user sends message quickly)
        if not self._startup_models_cleared:
            self._startup_models_cleared = True
            print("[First Message] Clearing any auto-loaded Ollama models...")
            self._clear_ollama_models_at_startup()

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

        # Consume pending file attachments (next-message-only) and build augmented content for model
        attachments = self.chat_widget.consume_attachments()
        augmented_parts = [message] if message.strip() else []
        max_chars_per_file = self.config_manager.get(
            "chat.attachments.max_chars_per_file", 50_000
        )
        max_total_chars = self.config_manager.get(
            "chat.attachments.max_total_chars", 150_000
        )
        total_chars = len(augmented_parts[0]) if augmented_parts else 0
        truncated_total = False
        for att in attachments:
            if total_chars >= max_total_chars:
                truncated_total = True
                break
            remaining = max_total_chars - total_chars
            limit = min(max_chars_per_file, remaining)
            content, err = read_text_file_with_limits(
                att["path"], max_chars=limit
            )
            if err:
                augmented_parts.append(
                    f"(Could not read {att['name']}: {err})"
                )
                total_chars += len(augmented_parts[-1])
                continue
            block = (
                f"Attached file: {att['name']} ({format_file_size(att['size'])})\n```\n{content}\n```"
            )
            augmented_parts.append(block)
            total_chars += len(block)
        if truncated_total:
            augmented_parts.append(
                f"(Attachment limit reached: max {max_total_chars} chars total.)"
            )
        augmented = "\n\n".join(augmented_parts) if augmented_parts else ""
        display_msg = (
            message
            if message.strip()
            else (f"📎 {len(attachments)} file(s) attached" if attachments else "")
        )

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
                print(
                    f"Image converted to base64: {len(base64_image)} characters ({image_size_kb:.1f} KB)"
                )
                is_vision_request = True
            else:
                QMessageBox.warning(
                    self,
                    "Image Conversion Failed",
                    "Could not convert image to base64. Please try again.",
                )
                return

        # GPU memory management: unload previous model if switching between vision and non-vision
        # or if switching to different model
        if self.last_used_model and self.last_used_model != model:
            print(
                f"Model changed from {self.last_used_model} to {model} - unloading previous model..."
            )
            self.ollama_client.unload_model(self.last_used_model)
            # Clear context when switching models
            self.current_context = None
        elif (
            self.last_used_model == model and self.last_was_vision != is_vision_request
        ):
            # Same model but switching between vision and non-vision - unload to free GPU
            print(
                f"Switching between vision/non-vision mode - unloading model {model}..."
            )
            self.ollama_client.unload_model(model)
            # Clear context when switching modes
            self.current_context = None

        # Update tracking
        self.last_used_model = model
        self.last_was_vision = is_vision_request

        # Add to conversation history (store original message) before creating bubble
        # so the bubble can carry the correct message index for manual memory actions.
        user_message_index = len(self.conversation_history)
        self.conversation_history.append({"role": "user", "content": message})

        # Send message to Ollama (UI bubble uses display_msg; model gets augmented)
        self.chat_widget.add_user_message(
            display_msg,
            image_path=image_path if image_path else None,
            message_index=user_message_index,
        )

        # Manual-only semantic memory: never auto-embed user messages.

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
        context_to_use = (
            None if (images_base64 and len(images_base64) > 0) else self.current_context
        )
        if images_base64 and len(images_base64) > 0:
            print("Image detected - using None context for vision model")
            use_explicit_history = True

        # Manual memory block (RAG) - user curated, small-context friendly
        memory_block = ""
        if (
            self.embedding_enabled
            and self.embedding_client
            and self.chat_vector_store
            and not images_base64
            and not self.rag_auto_embed
        ):
            try:
                memory_block = self._build_manual_memory_block(message)
            except Exception as e:
                print(f"Error building manual memory block: {e}")
                memory_block = ""

        # Auto semantic memory (legacy behavior) - only when auto-embedding is enabled
        if (
            self.rag_auto_embed
            and self.embedding_enabled
            and self.embedding_client
            and self.chat_vector_store
            and len(self.conversation_history) > self.semantic_memory_threshold
            and not images_base64
        ):
            try:
                final_prompt = self._build_prompt_with_semantic_memory(
                    augmented, system_prompt, max_history
                )
            except Exception as e:
                print(f"Error building prompt with semantic memory: {e}")
                import traceback

                traceback.print_exc()
                # Fallback to normal prompt on error
                use_explicit_history = True
                final_prompt = self._build_normal_prompt(
                    augmented, system_prompt, max_history
                )
        elif use_explicit_history:
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
            if memory_block:
                prompt_parts.append(memory_block)

            # Add conversation history
            for msg in history_to_include:
                role_prefix = "User: " if msg["role"] == "user" else "Assistant: "
                prompt_parts.append(role_prefix + msg["content"])

            # Add current message (augmented with attachment content for model)
            prompt_parts.append(f"User: {augmented}")
            prompt_parts.append("Assistant:")

            # Single join operation (much faster than multiple concatenations)
            final_prompt = "\n\n".join(prompt_parts)
        else:
            # Use only current message (context handles history); use augmented for model
            final_prompt = augmented
            if memory_block:
                final_prompt = memory_block + "\n\n" + final_prompt

        # Check if prompt preview is enabled
        show_preview = self.config_manager.get("rag.show_prompt_preview", False)
        if show_preview:
            # Build preview prompt/messages for display
            preview_prompt = ""
            preview_type = "Normal"
            manual_memory_used = bool(memory_block)
            if manual_memory_used:
                preview_type = "Manual Memory"
            
            # Check if tools are enabled (to determine preview format)
            tools_enabled_check = self.config_manager.get("ollama.tools.enabled", False)
            use_tools_check = tools_enabled_check and not images_base64
            
            if use_tools_check:
                # Tools mode: format messages list as readable string
                preview_messages = []
                if system_prompt:
                    preview_messages.append({"role": "system", "content": system_prompt})
                if memory_block:
                    preview_messages.append({"role": "system", "content": memory_block})
                
                history_to_include = self.conversation_history
                if max_history > 0:
                    history_to_include = self.conversation_history[-(max_history + 1) : -1]
                
                for msg in history_to_include:
                    preview_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                
                preview_messages.append({"role": "user", "content": augmented})
                
                # Format messages as readable string
                preview_lines = []
                for msg in preview_messages:
                    role = msg["role"].upper()
                    content = msg["content"]
                    preview_lines.append(f"[{role}]\n{content}")
                preview_prompt = "\n\n---\n\n".join(preview_lines)
            else:
                # Non-tools mode: use final_prompt
                preview_prompt = final_prompt
            
            # Show preview dialog
            dialog = DebugDialog(self, preview_mode=True)
            dialog.set_prompt_info(
                prompt=preview_prompt,
                prompt_type=preview_type,
                message_count=len(self.conversation_history),
                included_count=min(len(self.conversation_history), max_history + 1) if max_history > 0 else len(self.conversation_history),
                semantic_memory_enabled=manual_memory_used,
                context_used=not use_explicit_history,
                context_info=f"Context size: ~{len(self.current_context) if self.current_context else 0} tokens" if self.current_context else "No context yet",
            )
            
            # If user cancels, don't send message
            if not dialog.exec() or not dialog.user_accepted:
                # User cancelled - remove the user message bubble we already added
                # (Actually, we haven't added it yet, so just return)
                return

        # Don't create AI bubble yet - wait for first chunk
        # This prevents empty bubble from appearing immediately
        
        # Start AI message and show model status in footer
        self.chat_widget.start_ai_message(model)

        # Check if tools are enabled
        tools_enabled = self.config_manager.get("ollama.tools.enabled", False)
        use_tools = tools_enabled and not images_base64  # Tools don't work well with images
        
        if use_tools:
            # Use ChatToolsWorker with /api/chat endpoint for tools support
            tools = get_available_tools(self.config_manager)
            
            # Convert conversation history to messages format for chat endpoint
            messages = []
            
            # Add system prompt if exists
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            # Add manual semantic memory (RAG) if available
            if memory_block:
                messages.append({"role": "system", "content": memory_block})
            
            # Add conversation history
            history_to_include = self.conversation_history
            if max_history > 0:
                history_to_include = self.conversation_history[-(max_history + 1) : -1]
            
            for msg in history_to_include:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Add current user message (augmented with attachment content for model)
            messages.append({"role": "user", "content": augmented})
            
            # Create ChatToolsWorker
            worker = ChatToolsWorker(
                self.ollama_client,
                model,
                messages,
                tools,
                llm_params
            )
            # Connect signals - create bubble on first chunk
            worker.chunk_received.connect(self._on_chunk_received)
            worker.finished.connect(lambda content: self._on_tools_response_finished(content))
            worker.error_occurred.connect(self._on_response_error)
            def on_tool_executed(name: str, result: str):
                if name:
                    self.chat_widget.update_tool_status(name)
            worker.tool_call_executed.connect(on_tool_executed)
        else:
            # Use regular OllamaWorker with /api/generate endpoint
            worker = OllamaWorker(
                self.ollama_client,
                model,
                final_prompt,
                context_to_use,
                llm_params,
                images=images_base64 if images_base64 else None,
            )
            # Connect signals - create bubble on first chunk
            worker.chunk_received.connect(self._on_chunk_received)
            worker.finished.connect(self._on_response_finished)
            worker.error_occurred.connect(self._on_response_error)
        
        # Store worker reference to prevent garbage collection
        self.current_worker = worker
        worker.finished.connect(lambda: setattr(self, "current_worker", None))
        worker.error_occurred.connect(lambda: setattr(self, "current_worker", None))
        # Disable send button while generating
        self.chat_widget.set_send_enabled(False)
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

            # Generate new chat ID and initialize new vector store
            if self.embedding_enabled:
                from datetime import datetime

                self.current_chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                embedding_store_path = (
                    self.embeddings_dir / f"chat_{self.current_chat_id}.json"
                )
                self.chat_vector_store = ChatVectorStore(embedding_store_path)
                # Update status indicator
                if hasattr(self.status_panel, "update_semantic_memory_status"):
                    self.status_panel.update_semantic_memory_status(True, 0)

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
                "chat_id": self.current_chat_id,  # Save chat ID to link with embeddings
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

            # Load chat ID from saved chat or generate new one
            self.current_chat_id = chat_data.get("chat_id", None)
            if not self.current_chat_id:
                from datetime import datetime

                self.current_chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Load embeddings for this chat if available
            if self.embedding_enabled:
                embedding_store_path = (
                    self.embeddings_dir / f"chat_{self.current_chat_id}.json"
                )
                self.chat_vector_store = ChatVectorStore(embedding_store_path)
                # Update status indicator
                if hasattr(self.status_panel, "update_semantic_memory_status"):
                    stats = self.chat_vector_store.get_stats()
                    message_count = stats.get("total_messages", 0)
                    self.status_panel.update_semantic_memory_status(True, message_count)

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
                        user_idx = len(self.conversation_history)
                        self.conversation_history.append({"role": "user", "content": content})
                        self.chat_widget.add_user_message(content, message_index=user_idx)
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
                        # already appended above for non-image user messages
                        pass
                elif role == "assistant":
                    # AI message
                    assistant_idx = len(self.conversation_history)
                    self.conversation_history.append({"role": "assistant", "content": content})
                    self.chat_widget.add_assistant_message(content, message_index=assistant_idx)

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

            # Reinit generators if storage paths changed
            if get_image_storage_path(self.config_manager):
                self._init_image_generator()
            if get_video_storage_path(self.config_manager):
                self._init_video_generator()
            if get_audio_storage_path(self.config_manager):
                self._init_audio_generator()

            # Update TTS engine settings
            # Always reinitialize TTS engine when settings dialog closes
            # This ensures engine, language, voice, and voice cloning settings are all updated
            self._init_tts_engine()
            
            # Reinitialize ASR engine if settings changed
            self._init_asr_engine()

            # Status panel voices are already updated in _init_tts_engine()
            # Voice is already set in _init_tts_engine(), no need to update again here

            # Refresh cached config values for current model
            if self._current_model:
                self._cache_config_values(self._current_model)
            else:
                default_model = self.config_manager.get(
                    "ollama.default_model", "llama3.2"
                )
                self._current_model = default_model
                self._cache_config_values(default_model)

            # Reload embedding components if RAG settings changed
            self._reload_embedding_components()

            self.status_bar.showMessage("Settings saved")

    def show_debug_prompt(self):
        """Show debug dialog with current prompt."""
        if not self.conversation_history:
            QMessageBox.information(
                self,
                "Debug Prompt",
                "No conversation history. Send a message first to see the prompt.",
            )
            return

        # Get cached config values
        conv_settings = self._conversation_settings_cache

        system_prompt = conv_settings["system_prompt"]
        max_history = conv_settings["max_history"]
        use_explicit_history = conv_settings["use_explicit_history"]

        # Get last user message (that's what on_message_sent builds prompts for)
        last_user_message = ""
        for msg in reversed(self.conversation_history):
            if msg.get("role") == "user" and msg.get("content"):
                last_user_message = msg.get("content", "")
                break

        if not last_user_message:
            QMessageBox.information(
                self, "Debug Prompt", "No message to debug. Send a message first."
            )
            return

        # Build prompt using same logic as on_message_sent
        final_prompt = ""
        prompt_type = "Normal"
        included_count = 0
        manual_memory_used = False
        context_used = False
        context_info = ""

        # Check if we would use context (same logic as on_message_sent)
        if self.current_context is None and len(self.conversation_history) > 0:
            use_explicit_history = True

        # Manual semantic memory (RAG) - matches on_message_sent behavior
        memory_block = ""
        if (
            self.embedding_enabled
            and self.embedding_client
            and self.chat_vector_store
            and not self.rag_auto_embed
        ):
            try:
                memory_block = self._build_manual_memory_block(last_user_message)
            except Exception as e:
                print(f"Error building manual memory block for debug: {e}")
                memory_block = ""

        manual_memory_used = bool(memory_block)
        if manual_memory_used:
            prompt_type = "Manual Memory"

        if use_explicit_history:
            history_to_include = self.conversation_history
            if max_history > 0:
                history_to_include = self.conversation_history[-(max_history + 1) : -1]

            prompt_parts = []
            if system_prompt:
                prompt_parts.append(system_prompt)
            if memory_block:
                prompt_parts.append(memory_block)

            for msg in history_to_include:
                role_prefix = "User: " if msg.get("role") == "user" else "Assistant: "
                prompt_parts.append(role_prefix + (msg.get("content", "") or ""))

            prompt_parts.append(f"User: {last_user_message}")
            prompt_parts.append("Assistant:")
            final_prompt = "\n\n".join(prompt_parts)

            included_count = min(len(self.conversation_history), max_history + 1)
            context_used = False
            context_info = "N/A (Explicit history in prompt)"
        else:
            # Context-based mode - prompt is just current message, history is in context
            final_prompt = last_user_message
            if memory_block:
                final_prompt = memory_block + "\n\n" + final_prompt
            included_count = 1  # Only current message in prompt
            context_used = True
            if self.current_context:
                # Estimate context size (context is list of token IDs)
                context_size = (
                    len(self.current_context)
                    if isinstance(self.current_context, list)
                    else 0
                )
                context_info = f"Context contains ~{context_size} tokens (full conversation history)"
            else:
                context_info = "No context yet (first message)"

        # Show debug dialog
        dialog = DebugDialog(self)
        dialog.set_prompt_info(
            prompt=final_prompt,
            prompt_type=prompt_type,
            message_count=len(self.conversation_history),
            included_count=included_count,
            semantic_memory_enabled=manual_memory_used,
            context_used=context_used,
            context_info=context_info,
        )
        dialog.exec()

    def on_memory_stats_requested(self):
        """Show stats about user-curated semantic memory for this chat."""
        if not self.embedding_enabled:
            QMessageBox.information(
                self,
                "Semantic Memory Stats",
                "RAG / Semantic Memory is disabled.\n\nEnable it in Settings to store memories.",
            )
            return

        if not self._ensure_semantic_memory_ready():
            QMessageBox.information(
                self,
                "Semantic Memory Stats",
                "Semantic memory is not ready.\n\nEnable RAG in Settings and ensure Ollama is running.",
            )
            return

        try:
            stats = self.chat_vector_store.get_stats() if self.chat_vector_store else {}
            count = int(stats.get("total_messages", 0) or 0)
            path = stats.get("storage_path", "")
            QMessageBox.information(
                self,
                "Semantic Memory Stats",
                f"Remembered items: {count}\n\nStore: {path}",
            )
        except Exception as e:
            QMessageBox.information(
                self,
                "Semantic Memory Stats",
                f"Could not read memory stats: {e}",
            )

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
            # Status indicator and typing indicator already set in start_ai_message()
            # Just create bubble on first chunk if it doesn't exist (should already exist)
            if self.chat_widget.current_ai_bubble is None:
                # Fallback: create message if somehow not created
                model = self.status_panel.get_selected_model()
                self.chat_widget.start_ai_message(model if model else None)
            # Append chunk (only if non-empty - but allow whitespace like newlines)
            if chunk:
                self.chat_widget.append_ai_chunk(chunk)
        except Exception as e:
            print(f"Error in _on_chunk_received: {e}")
            # Don't print full traceback in production - too verbose

    def _embed_message_async(self, message: Dict, index: int):
        """Embed message in background (non-blocking)."""
        if (
            not self.embedding_enabled
            or not self.embedding_client
            or not self.chat_vector_store
        ):
            return

        worker = EmbeddingWorker(self.embedding_client, message, index)
        worker.embedding_ready.connect(self._on_embedding_ready)
        worker.finished.connect(lambda: self._on_embedding_worker_finished(worker))
        # Store reference to prevent garbage collection
        self.embedding_workers.append(worker)
        worker.start()

    def _on_embedding_worker_finished(self, worker):
        """Callback when embedding worker finishes - remove from list."""
        try:
            if worker in self.embedding_workers:
                self.embedding_workers.remove(worker)
        except:
            pass

    def _on_embedding_ready(self, embedding: List[float], message: Dict, index: int):
        """Callback when embedding is ready."""
        if self.chat_vector_store:
            self.chat_vector_store.add_message(message, embedding, index)
            # Manual memory is user-curated; persist immediately so small numbers of
            # remembers aren't lost if the app closes before the periodic save.
            try:
                self.chat_vector_store.force_save()
            except Exception as e:
                print(f"Error force-saving semantic memory: {e}")
            # Update semantic memory status indicator
            if hasattr(self.status_panel, "update_semantic_memory_status"):
                stats = self.chat_vector_store.get_stats()
                message_count = stats.get("total_messages", 0)
                self.status_panel.update_semantic_memory_status(True, message_count)

    def _build_manual_memory_block(self, query_text: str) -> str:
        """
        Build a short, user-curated 'memory' block using semantic search over remembered items.
        This is designed for small context windows (keeps strict character limits).
        """
        if not (self.embedding_enabled and self.embedding_client and self.chat_vector_store):
            return ""

        stats = self.chat_vector_store.get_stats() if self.chat_vector_store else {}
        total_memories = int(stats.get("total_messages", 0) or 0)
        min_needed = int(self.config_manager.get("rag.manual_min_memories", 3) or 3)
        if total_memories < min_needed:
            return ""

        query = (query_text or "").strip()
        if not query:
            return ""

        top_k = int(self.config_manager.get("rag.memory_top_k", 3) or 3)
        max_chars = int(self.config_manager.get("rag.memory_max_chars", 1200) or 1200)
        min_similarity = float(
            self.config_manager.get("rag.memory_min_similarity", 0.0) or 0.0
        )

        try:
            query_embedding = self.embedding_client.generate_embedding(query)
        except Exception as e:
            print(f"Error generating query embedding for manual memory: {e}")
            return ""

        if not query_embedding:
            return ""

        # For manual memory, we don't exclude recent items (user curated)
        results = self.chat_vector_store.search(
            query_embedding, top_k=top_k, exclude_recent=0
        )
        if not results:
            return ""

        lines = [
            "MEMORY (user-curated; use only if relevant; not new chat messages):"
        ]
        used_chars = sum(len(l) for l in lines) + 2

        for r in results:
            sim = float(r.get("similarity", 0.0) or 0.0)
            if sim < min_similarity:
                continue
            role = "User" if r.get("role") == "user" else "Assistant"
            content = (r.get("content") or "").strip()
            if not content:
                continue
            item = f"- ({role}) {content}"
            if used_chars + len(item) + 1 > max_chars:
                break
            lines.append(item)
            used_chars += len(item) + 1

        if len(lines) <= 1:
            return ""

        return "\n".join(lines)

    def _build_prompt_with_semantic_memory(
        self, current_message: str, system_prompt: str, max_history: int
    ) -> str:
        """
        Build prompt with semantic memory for long conversations.
        Uses semantic search to find relevant older messages.
        """
        # Check if embedding client is available
        if not self.embedding_client or not self.chat_vector_store:
            # Fallback to normal prompt if embedding components not available
            return self._build_normal_prompt(
                current_message, system_prompt, max_history
            )

        # 1. Embed current query (with error handling)
        try:
            query_embedding = self.embedding_client.generate_embedding(current_message)
            if not query_embedding:
                # Fallback to normal prompt if embedding fails
                print("Warning: Failed to generate embedding, using normal prompt")
                return self._build_normal_prompt(
                    current_message, system_prompt, max_history
                )
        except Exception as e:
            print(f"Error generating embedding for semantic search: {e}")
            # Fallback to normal prompt on error
            return self._build_normal_prompt(
                current_message, system_prompt, max_history
            )

        # 2. Semantic search for relevant older messages
        relevant_messages = self.chat_vector_store.search(
            query_embedding,
            top_k=self.top_k_relevant,
            exclude_recent=self.recent_messages_count,
        )

        # 3. Get recent messages (always include last N)
        recent_messages = self.conversation_history[-self.recent_messages_count : -1]

        # 4. Combine: relevant + recent, then sort by index
        all_messages = relevant_messages + recent_messages
        # Remove duplicates (keep first occurrence)
        seen_indices = set()
        unique_messages = []
        for msg in all_messages:
            msg_index = msg.get("index", len(self.conversation_history))
            if msg_index not in seen_indices:
                seen_indices.add(msg_index)
                unique_messages.append(msg)

        # Sort by index to maintain chronological order
        unique_messages.sort(key=lambda m: m.get("index", 0))

        # 5. Build prompt
        prompt_parts = []
        if system_prompt:
            prompt_parts.append(system_prompt)

        # Add relevant context from earlier conversation
        older_messages = [
            m
            for m in unique_messages
            if m.get("index", len(self.conversation_history))
            < len(self.conversation_history) - self.recent_messages_count
        ]
        if older_messages:
            prompt_parts.append("Relevant context from earlier in conversation:")
            for msg in older_messages:
                role = "User" if msg["role"] == "user" else "Assistant"
                prompt_parts.append(f"{role}: {msg['content']}")
            prompt_parts.append("")

        # Add recent conversation
        recent_in_prompt = [
            m
            for m in unique_messages
            if m.get("index", len(self.conversation_history))
            >= len(self.conversation_history) - self.recent_messages_count
        ]
        if recent_in_prompt:
            prompt_parts.append("Recent conversation:")
            for msg in recent_in_prompt:
                role = "User" if msg["role"] == "user" else "Assistant"
                prompt_parts.append(f"{role}: {msg['content']}")

        # Add current message
        prompt_parts.append(f"User: {current_message}")
        prompt_parts.append("Assistant:")

        return "\n\n".join(prompt_parts)

    def _build_normal_prompt(
        self, current_message: str, system_prompt: str, max_history: int
    ) -> str:
        """Build normal prompt without semantic memory (fallback)."""
        history_to_include = self.conversation_history
        if max_history > 0:
            history_to_include = self.conversation_history[-(max_history + 1) : -1]

        prompt_parts = []
        if system_prompt:
            prompt_parts.append(system_prompt)

        for msg in history_to_include:
            role_prefix = "User: " if msg["role"] == "user" else "Assistant: "
            prompt_parts.append(role_prefix + msg["content"])

        prompt_parts.append(f"User: {current_message}")
        prompt_parts.append("Assistant:")

        return "\n\n".join(prompt_parts)

    def _on_response_finished(self, new_context):
        """Handle response completion."""
        try:
            self.current_context = new_context

            # Unload model after response to free GPU memory for next request
            # This prevents GPU memory buildup and ensures fast subsequent requests
            if self.last_used_model:
                print(
                    f"Model {self.last_used_model} finished - unloading to free GPU memory..."
                )
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
                    assistant_index = len(self.conversation_history)
                    self.conversation_history.append(
                        {"role": "assistant", "content": response_text}
                    )
                    # Attach index/role to the visible bubble (for manual memory context menu)
                    try:
                        if hasattr(self.chat_widget, "set_current_ai_bubble_metadata"):
                            self.chat_widget.set_current_ai_bubble_metadata(
                                role="assistant", message_index=assistant_index
                            )
                    except Exception as e:
                        print(f"Error setting AI bubble metadata: {e}")
                    # Manual-only semantic memory: never auto-embed assistant messages.

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
                model = self.status_panel.get_selected_model()
                self.chat_widget.start_ai_message(model if model else None)
                self.chat_widget.append_ai_chunk("No response received from model.")
                self.chat_widget.finish_ai_message()
            # Re-enable send button
            self.chat_widget.set_send_enabled(True)
        except Exception as e:
            import traceback
            error_msg = f"Error handling response: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            self.chat_widget.set_send_enabled(True)
            self._on_response_error(error_msg)

    def _on_tools_response_finished(self, content: str):
        """Handle tools response completion (from ChatToolsWorker)."""
        try:
            # ChatToolsWorker doesn't use context, so set to None
            self.current_context = None

            if content:
                response_text = content.strip()
                
                # Add to conversation history
                assistant_index = len(self.conversation_history)
                self.conversation_history.append(
                    {"role": "assistant", "content": response_text}
                )
                # Attach index/role to the visible bubble (for manual memory context menu)
                try:
                    if hasattr(self.chat_widget, "set_current_ai_bubble_metadata"):
                        self.chat_widget.set_current_ai_bubble_metadata(
                            role="assistant", message_index=assistant_index
                        )
                except Exception as e:
                    print(f"Error setting AI bubble metadata (tools): {e}")
                # Manual-only semantic memory: never auto-embed assistant messages.

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
                # If no content, show error
                model = self.status_panel.get_selected_model()
                self.chat_widget.start_ai_message(model if model else None)
                self.chat_widget.append_ai_chunk("No response received from model.")
                self.chat_widget.finish_ai_message()
            
            # Re-enable send button
            self.chat_widget.set_send_enabled(True)
            
        except Exception as e:
            import traceback
            error_msg = f"Error handling tools response: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            self.chat_widget.set_send_enabled(True)
            self._on_response_error(error_msg)

    def _on_response_error(self, error: str):
        """Handle response error."""
        try:
            # Create bubble if it doesn't exist
            if self.chat_widget.current_ai_bubble is None:
                model = self.status_panel.get_selected_model()
                self.chat_widget.start_ai_message(model if model else None)
            # Show error message
            error_msg = f"[Error: {error}]"
            self.chat_widget.append_ai_chunk(error_msg)
            self.chat_widget.finish_ai_message()
            # Hide status indicator on error
            if hasattr(self.chat_widget, "status_indicator"):
                self.chat_widget.status_indicator.setVisible(False)
            # Re-enable send button
            self.chat_widget.set_send_enabled(True)
        except Exception as e:
            print(f"Error in _on_response_error: {e}")
            import traceback

            traceback.print_exc()
            try:
                if self.chat_widget.current_ai_bubble is not None:
                    self.chat_widget.finish_ai_message()
            except:
                pass
            # Re-enable send button even on error
            self.chat_widget.set_send_enabled(True)

    def on_seed_lock_toggled(self, locked: bool):
        """Handle seed lock toggle from chat widget."""
        self.seed_locked = locked
        if locked and self.last_image_seed is not None:
            self.current_seed = self.last_image_seed
            self.update_seed_display()
        else:
            self.current_seed = None
            self.update_seed_display()

    def update_seed_display(self):
        """Update seed display in status bar."""
        if self.current_seed is not None and self.seed_locked:
            mode = (
                "Image"
                if self.chat_widget.image_mode
                else "Audio" if self.chat_widget.audio_mode else ""
            )
            if mode:
                self.status_bar.showMessage(f"Seed ({mode}): {self.current_seed}")
            else:
                current_msg = self.status_bar.currentMessage()
                if current_msg and "Seed" in current_msg:
                    self.status_bar.showMessage("Ready")
        else:
            current_msg = self.status_bar.currentMessage()
            if current_msg and "Seed" in current_msg:
                self.status_bar.showMessage("Ready")

    def on_seed_increase(self):
        """Increase current seed by 1."""
        import random

        if self.current_seed is None:
            if self.last_image_seed is not None:
                self.current_seed = self.last_image_seed
            else:
                self.current_seed = random.randint(0, 2147483647)
        else:
            self.current_seed = (self.current_seed + 1) % 2147483648
        self.last_image_seed = self.current_seed
        if self.seed_locked:
            self.update_seed_display()

    def on_seed_decrease(self):
        """Decrease current seed by 1."""
        import random

        if self.current_seed is None:
            if self.last_image_seed is not None:
                self.current_seed = self.last_image_seed
            else:
                self.current_seed = random.randint(0, 2147483647)
        else:
            self.current_seed = (self.current_seed - 1) % 2147483648
        self.last_image_seed = self.current_seed
        if self.seed_locked:
            self.update_seed_display()

    def on_tts_play(self):
        """Handle TTS play button click."""
        print(f"TTS Play clicked. Engine: {self.tts_engine}")

        if not self.tts_engine:
            self.status_bar.showMessage(
                "TTS engine not initialized. Check Settings > TTS."
            )
            print("TTS engine not initialized")
            return

        # Check if engine is ready (different for Kokoro vs Pocket TTS)
        is_ready = False
        if hasattr(self.tts_engine, "pipeline"):
            # Kokoro TTS - check if pipeline is loaded
            is_ready = self.tts_engine.pipeline is not None
        elif hasattr(self.tts_engine, "model"):
            # Pocket TTS - only check model, voice_state is loaded lazily in speak_async
            is_ready = self.tts_engine.model is not None
        
        if not is_ready:
            self.status_bar.showMessage("TTS not ready. Please wait...")
            print("TTS not ready")
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
            engine = self.config_manager.get("tts.engine", "kokoro")
            
            if engine == "pocket_tts" and voice == "Clone Voice":
                # Use voice cloning
                voice_cloning_file = self.config_manager.get("tts.voice_cloning.file_path", None)
                if voice_cloning_file and hasattr(self.tts_engine, "set_voice_cloning_file"):
                    self.tts_engine.set_voice_cloning_file(voice_cloning_file)
            else:
                # Use regular voice
                if hasattr(self.tts_engine, "set_voice_cloning_file"):
                    # Disable voice cloning first (for Pocket TTS)
                    self.tts_engine.set_voice_cloning_file(None)
                if hasattr(self.tts_engine, "set_voice"):
                    self.tts_engine.set_voice(voice)
            
            # Save to config
            self.config_manager.set("tts.voice", voice)
            self.config_manager.save_config()

    def on_tts_language_changed(self, lang_code: str):
        """Handle TTS language selection change (from Settings)."""
        if self.tts_engine:
            # Only Kokoro supports language change
            if hasattr(self.tts_engine, "set_lang_code"):
                self.tts_engine.set_lang_code(lang_code)
            # Save to config
            self.config_manager.set("tts.lang_code", lang_code)
            self.config_manager.save_config()
            # Update voice dropdown in status panel
            engine = self.config_manager.get("tts.engine", "kokoro")
            if hasattr(self.status_panel, "update_voices_for_language"):
                self.status_panel.update_voices_for_language(lang_code, engine)

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

    def on_image_prompt_sent(self, prompt: str, init_image_path: str = ""):
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
        user_msg = (
            f"Image to image: {prompt}"
            if init_image_path
            else f"Generate image: {prompt}"
        )
        self.chat_widget.add_user_message(user_msg)

        # Determine seed to use
        import random

        if self.seed_locked and self.last_image_seed is not None:
            # Use locked seed (same as last time)
            seed_to_use = self.last_image_seed
        else:
            # Generate random seed
            seed_to_use = random.randint(0, 2147483647)
            self.last_image_seed = seed_to_use
        self.current_seed = seed_to_use
        if self.seed_locked:
            self.update_seed_display()

        # Show generating message
        generating_bubble = self.chat_widget.messages_layout.itemAt(
            self.chat_widget.messages_layout.count() - 2
        )
        if generating_bubble:
            generating_bubble = generating_bubble.widget()

        # Start image generation in background thread
        worker = ImageGenerationWorker(
            self.image_generator,
            prompt,
            self.config_manager,
            seed=seed_to_use,
            init_image_path=init_image_path or None,
        )
        worker.image_generated.connect(self._on_image_generated)
        worker.error_occurred.connect(self._on_image_error)
        worker.progress_updated.connect(self._on_image_progress)
        self.current_image_worker = worker
        worker.finished.connect(lambda: setattr(self, "current_image_worker", None))
        # Disable send button while generating
        self.chat_widget.set_send_enabled(False)
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

            # Clear GPU memory after generation (move model to CPU, keep loaded)
            if self.image_generator:
                print("Clearing GPU memory after image generation...")
                self.image_generator.clear_gpu_memory()

            # Re-enable send button
            self.chat_widget.set_send_enabled(True)
        except Exception as e:
            print(f"Error displaying image: {e}")
            QMessageBox.warning(self, "Error", f"Error displaying image: {e}")

            # Clear GPU memory even on error
            if self.image_generator:
                try:
                    self.image_generator.clear_gpu_memory()
                except:
                    pass

            # Re-enable send button even on error
            self.chat_widget.set_send_enabled(True)

    def on_text_selected_for_tts(self, text: str):
        """Handle text selection for TTS."""
        if not self.tts_engine:
            self.status_bar.showMessage(
                "TTS engine not initialized. Check Settings > TTS."
            )
            return

        # Check if engine is ready (Pocket TTS loads voice_state lazily in speak_async)
        is_ready = False
        if hasattr(self.tts_engine, "pipeline"):
            is_ready = self.tts_engine.pipeline is not None
        elif hasattr(self.tts_engine, "model"):
            is_ready = self.tts_engine.model is not None
        
        if not is_ready:
            self.status_bar.showMessage("TTS not ready. Please wait...")
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

    def _ensure_semantic_memory_ready(self) -> bool:
        """Ensure embedding client + vector store are ready for manual memory actions."""
        if not self.embedding_enabled:
            return False

        # Lazily initialize embedding components if they haven't loaded yet
        if self.embedding_client is None or self.embeddings_dir is None:
            try:
                self._init_embedding_components()
            except Exception as e:
                print(f"Error initializing embedding components on-demand: {e}")
                return False

        # Ensure chat id exists
        if not self.current_chat_id:
            from datetime import datetime

            self.current_chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Ensure per-chat vector store exists
        if self.chat_vector_store is None and self.embeddings_dir is not None:
            try:
                embedding_store_path = (
                    self.embeddings_dir / f"chat_{self.current_chat_id}.json"
                )
                self.chat_vector_store = ChatVectorStore(embedding_store_path)
            except Exception as e:
                print(f"Error creating chat vector store: {e}")
                return False

        return bool(self.embedding_client and self.chat_vector_store)

    def on_remember_selected_text(self, text: str, role: str, message_index: int):
        """User requested: remember selected text for semantic memory."""
        clean_text = (text or "").replace("\u2029", "\n").strip()
        if not clean_text:
            return

        if not self._ensure_semantic_memory_ready():
            self.status_bar.showMessage(
                "Semantic memory not ready. Enable RAG in Settings and ensure Ollama is running."
            )
            return

        # If index is unknown, store with a safe monotonic index
        safe_index = message_index if isinstance(message_index, int) and message_index >= 0 else len(self.conversation_history)
        created_at = datetime.now().isoformat()
        chat_id = self.current_chat_id
        self._embed_message_async(
            {
                "role": role or "user",
                "content": clean_text,
                "source": "selection",
                "created_at": created_at,
                "chat_id": chat_id,
            },
            safe_index,
        )
        self.status_bar.showMessage("Remembered selection for semantic memory")

    def on_remember_message(self, full_text: str, role: str, message_index: int):
        """User requested: remember whole message for semantic memory."""
        clean_text = (full_text or "").replace("\u2029", "\n").strip()
        if not clean_text:
            return

        if not self._ensure_semantic_memory_ready():
            self.status_bar.showMessage(
                "Semantic memory not ready. Enable RAG in Settings and ensure Ollama is running."
            )
            return

        safe_index = message_index if isinstance(message_index, int) and message_index >= 0 else len(self.conversation_history)
        created_at = datetime.now().isoformat()
        chat_id = self.current_chat_id
        self._embed_message_async(
            {
                "role": role or "user",
                "content": clean_text,
                "source": "message",
                "created_at": created_at,
                "chat_id": chat_id,
            },
            safe_index,
        )
        self.status_bar.showMessage("Remembered message for semantic memory")

    def on_audio_prompt_sent(self, prompt: str):
        """Handle audio generation prompt."""
        if not self.audio_generator:
            QMessageBox.warning(
                self,
                "Audio Generation Not Available",
                "Audio generation is not available.\n\n"
                "Please:\n"
                "1. Install requirements: pip install -r requirements.txt\n"
                "2. Set model storage path in Settings > Models",
            )
            return

        # Auto-unload Ollama models before audio generation to free GPU memory
        print("Auto-unloading Ollama models to free GPU memory...")
        self.ollama_client.unload_all_models_silent()

        # Add user message showing the prompt
        self.chat_widget.add_user_message(f"Generate audio: {prompt}")

        # Determine seed to use
        import random

        if self.seed_locked and self.last_image_seed is not None:
            # Use locked seed (same as last time)
            seed_to_use = self.last_image_seed
        else:
            # Generate random seed
            seed_to_use = random.randint(0, 2147483647)
            self.last_image_seed = seed_to_use
        self.current_seed = seed_to_use
        if self.seed_locked:
            self.update_seed_display()

        # Start audio generation in background thread
        worker = AudioGenerationWorker(
            self.audio_generator, prompt, self.config_manager, seed=seed_to_use
        )
        worker.audio_generated.connect(self._on_audio_generated)
        worker.error_occurred.connect(self._on_audio_error)
        worker.progress_updated.connect(self._on_audio_progress)
        self.current_audio_worker = worker
        worker.finished.connect(lambda: setattr(self, "current_audio_worker", None))
        # Disable send button while generating
        self.chat_widget.set_send_enabled(False)
        worker.start()

    def on_text_selected_for_audio(self, text: str):
        """Handle text selection for audio generation."""
        if not self.audio_generator:
            self.status_bar.showMessage(
                "Audio generation not available. Check Settings > Models."
            )
            return

        # Auto-unload Ollama models before audio generation
        print("Auto-unloading Ollama models to free GPU memory...")
        self.ollama_client.unload_all_models_silent()

        # Use selected text as prompt
        prompt = text.strip()
        if not prompt:
            return

        # Generate audio using current settings
        self.on_audio_prompt_sent(prompt)

    def _on_audio_generated(self, audio_path: str):
        """Handle successful audio generation."""
        try:
            # Get prompt from worker
            prompt = getattr(self.current_audio_worker, "prompt", "Generated audio")
            self.chat_widget.add_audio_message(audio_path, prompt)
            self.status_bar.showMessage(
                f"Audio generated: {os.path.basename(audio_path)}"
            )

            # Clear GPU memory after generation
            if self.audio_generator:
                print("Clearing GPU memory after audio generation...")
                self.audio_generator.unload_model()

            self.chat_widget.set_send_enabled(True)
        except Exception as e:
            print(f"Error displaying audio: {e}")
            QMessageBox.warning(self, "Error", f"Error displaying audio: {e}")
            self.chat_widget.set_send_enabled(True)

    def _on_audio_error(self, error_msg: str):
        """Handle audio generation error."""
        QMessageBox.warning(self, "Audio Generation Error", error_msg)

        # Clear GPU memory on error
        if self.audio_generator:
            try:
                self.audio_generator.unload_model()
            except:
                pass

        self.chat_widget.set_send_enabled(True)

    def _on_audio_progress(self, progress: int):
        """Handle audio generation progress."""
        self.status_bar.showMessage(f"Generating audio... {progress}%")

    def on_image_selected_for_video(self, image_path: str):
        """Handle image selection for video generation."""
        if not self.video_generator:
            QMessageBox.warning(
                self,
                "Video Generation Not Available",
                "Video generation is not available.\n\n"
                "Please:\n"
                "1. Install requirements: pip install -r requirements.txt\n"
                "2. Set model storage path in Settings > Models\n"
                "3. Download SVD model (stabilityai/stable-video-diffusion-img2vid)",
            )
            return

        # Auto-unload other models to free GPU memory
        print("Auto-unloading models to free GPU memory...")
        self.ollama_client.unload_all_models_silent()
        if self.image_generator:
            self.image_generator.clear_gpu_memory()

        # Also unload image generator pipeline completely if loaded
        if self.image_generator and self.image_generator.pipeline is not None:
            print("Unloading image generator pipeline completely...")
            self.image_generator.unload_model()

        # Aggressive GPU memory cleanup before video generation
        try:
            import torch

            if torch.cuda.is_available():
                import gc

                print("Performing aggressive GPU memory cleanup...")
                for _ in range(10):
                    gc.collect()
                    torch.cuda.empty_cache()
                print("GPU memory cleanup complete")
        except ImportError:
            pass  # torch not available

        # Add user message
        self.chat_widget.add_user_message("Generate video from image")

        # Determine seed
        import random

        seed = random.randint(0, 2147483647)

        # Start video generation in background thread
        worker = VideoGenerationWorker(
            self.video_generator, image_path, self.config_manager, seed=seed
        )
        worker.video_generated.connect(self._on_video_generated)
        worker.error_occurred.connect(self._on_video_error)
        worker.progress_updated.connect(self._on_video_progress)
        self.current_video_worker = worker
        worker.finished.connect(lambda: setattr(self, "current_video_worker", None))
        self.chat_widget.set_send_enabled(False)
        worker.start()

    def _on_video_generated(self, video_path: str):
        """Handle successful video generation."""
        try:
            self.chat_widget.add_video_message(video_path)
            self.status_bar.showMessage(
                f"Video generated: {os.path.basename(video_path)}"
            )

            # Clear GPU memory after generation
            if self.video_generator:
                print("Clearing GPU memory after video generation...")
                self.video_generator.unload_model()

            self.chat_widget.set_send_enabled(True)
        except Exception as e:
            print(f"Error displaying video: {e}")
            QMessageBox.warning(self, "Error", f"Error displaying video: {e}")
            self.chat_widget.set_send_enabled(True)

    def _on_video_error(self, error_msg: str):
        """Handle video generation error."""
        QMessageBox.warning(self, "Video Generation Error", error_msg)

        # Clear GPU memory on error
        if self.video_generator:
            try:
                self.video_generator.unload_model()
            except:
                pass

        self.chat_widget.set_send_enabled(True)

    def _on_video_progress(self, progress: int):
        """Handle video generation progress."""
        self.status_bar.showMessage(f"Generating video... {progress}%")

    def _on_image_error(self, error: str):
        """Handle image generation error."""
        self.chat_widget.add_user_message(f"[Error generating image: {error}]")
        QMessageBox.warning(self, "Image Generation Error", error)

        # Clear GPU memory on error (move model to CPU, keep loaded)
        if self.image_generator:
            print("Clearing GPU memory after image generation error...")
            try:
                self.image_generator.clear_gpu_memory()
            except Exception as e:
                print(f"Error clearing GPU memory: {e}")

        # Re-enable send button
        self.chat_widget.set_send_enabled(True)

    def _on_image_progress(self, progress: int):
        """Handle image generation progress."""
        self.status_bar.showMessage(f"Generating image... {progress}%")

    def _create_logo_icon(self) -> QIcon:
        """Create application logo icon from SVG."""
        # SVG icon data (home/house icon) - white color to match title bar text
        svg_data = """<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#ffffff"><path d="m480-840 440 330-48 64-72-54v380H160v-380l-72 54-48-64 440-330ZM294-478q0 53 57 113t129 125q72-65 129-125t57-113q0-44-30-73t-72-29q-26 0-47.5 10.5T480-542q-15-17-37.5-27.5T396-580q-42 0-72 29t-30 73Zm426 278v-360L480-740 240-560v360h480Zm0 0H240h480Z"/></svg>"""

        # Create icon
        icon = QIcon()

        # Create different sizes: 16x16, 32x32, 48x48, 64x64, 256x256
        sizes = [16, 32, 48, 64, 256]

        # Create SVG renderer
        svg_bytes = QByteArray(svg_data.encode("utf-8"))
        renderer = QSvgRenderer(svg_bytes)

        for size in sizes:
            pixmap = QPixmap(size, size)
            pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Render SVG to pixmap - scale to fit the pixmap size
            # The SVG viewBox is "0 -960 960 960", so we need to scale it properly
            from PySide6.QtCore import QRectF

            renderer.render(painter, QRectF(0, 0, size, size))

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

        # Wait for all embedding workers to finish
        if hasattr(self, "embedding_workers"):
            for worker in self.embedding_workers[
                :
            ]:  # Copy list to avoid modification during iteration
                if worker.isRunning():
                    worker.terminate()
                    worker.wait(500)  # Wait max 0.5 seconds per worker
            self.embedding_workers.clear()

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

        # Unload ASR engine model
        if hasattr(self, "asr_engine") and self.asr_engine:
            try:
                self.asr_engine.unload_model()
            except Exception as e:
                print(f"Error unloading ASR engine: {e}")

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

        # Save embeddings before closing
        if hasattr(self, "chat_vector_store") and self.chat_vector_store:
            try:
                self.chat_vector_store.force_save()
                print(f"Saved embeddings to {self.chat_vector_store.storage_path}")
            except Exception as e:
                print(f"Error saving embeddings on close: {e}")

        event.accept()


class EmbeddingWorker(QThread):
    """Worker thread for non-blocking embedding generation."""

    embedding_ready = Signal(list, dict, int)  # embedding, message, index

    def __init__(self, embedding_client, message, index):
        super().__init__()
        self.embedding_client = embedding_client
        self.message = message
        self.index = index
        self.setTerminationEnabled(True)  # Allow thread termination

    def run(self):
        """Run in background thread."""
        try:
            embedding = self.embedding_client.generate_embedding(
                self.message["content"]
            )
            if embedding:
                self.embedding_ready.emit(embedding, self.message, self.index)
        except Exception as e:
            print(f"Error generating embedding: {e}")
        finally:
            # Ensure thread finishes cleanly
            pass


class OllamaWorker(QThread):
    """Worker thread for non-blocking Ollama requests."""

    chunk_received = Signal(str)
    finished = Signal(object)  # new_context
    error_occurred = Signal(str)

    def __init__(self, client, model, prompt, context, llm_params=None, images=None, tools=None):
        super().__init__()
        self.client = client
        self.model = model
        self.prompt = prompt
        self.context = context
        self.llm_params = llm_params or {}
        self.images = images  # List of base64-encoded images for vision models
        self.tools = tools  # Optional list of tools for function calling
        import uuid
        self.request_id = str(uuid.uuid4())  # Unique request ID for cancellation

    def run(self):
        """Run in background thread."""
        try:
            chunks_received = False

            def on_chunk(chunk: str):
                nonlocal chunks_received
                try:
                    if chunk:  # Emit all chunks including whitespace (newlines for formatting)
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
                tools=self.tools,
                request_id=self.request_id,
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


class ChatToolsWorker(QThread):
    """Worker thread for Ollama chat with tools/function calling support."""
    
    chunk_received = Signal(str)
    finished = Signal(str)  # final response
    error_occurred = Signal(str)
    tool_call_executed = Signal(str, str)  # tool_name, result
    
    def __init__(self, client, model, messages, tools, llm_params=None):
        super().__init__()
        self.client = client
        self.model = model
        self.messages = messages  # List of messages in chat format
        self.tools = tools
        self.llm_params = llm_params or {}
        self.max_iterations = 50 # Max tool call iterations to avoid loops
        import uuid
        self.request_id = str(uuid.uuid4())  # Unique request ID for cancellation
        
    def run(self):
        """Run in background thread - handle tool calls automatically."""
        try:
            current_messages = self.messages.copy()
            iteration = 0
            
            while iteration < self.max_iterations:
                iteration += 1
                
                # Callback for streaming
                def on_chunk(chunk: str):
                    if chunk:
                        self.chunk_received.emit(chunk)
                
                # Call chat_with_tools with streaming
                result = self.client.chat_with_tools(
                    model=self.model,
                    messages=current_messages,
                    tools=self.tools,
                    num_ctx=self.llm_params.get("num_ctx"),
                    temperature=self.llm_params.get("temperature"),
                    top_p=self.llm_params.get("top_p"),
                    top_k=self.llm_params.get("top_k"),
                    repeat_penalty=self.llm_params.get("repeat_penalty"),
                    num_predict=self.llm_params.get("num_predict"),
                    seed=self.llm_params.get("seed"),
                    stream=True,
                    callback=on_chunk,
                    request_id=self.request_id,
                )
                
                if "error" in result:
                    self.error_occurred.emit(result["error"])
                    return
                
                message = result.get("message", {})
                content = message.get("content", "")
                tool_calls = message.get("tool_calls", [])
                
                # Add assistant message to conversation
                current_messages.append(message)
                
                # If there are tool calls, execute them
                if tool_calls:
                    print(f"[TOOLS] Model je pozvao {len(tool_calls)} tool(s)")
                    
                    tool_results = []
                    for tool_call in tool_calls:
                        func_name = tool_call["function"]["name"]
                        func_args = tool_call["function"]["arguments"]
                        tool_id = tool_call["id"]
                        
                        print(f"[TOOLS] Izvršavam {func_name} sa argumentima: {func_args}")
                        
                        # Emit tool call signal BEFORE execution to show status
                        self.tool_call_executed.emit(func_name, "")
                        
                        # Execute tool
                        try:
                            tool_result = execute_tool(func_name, func_args)
                            self.tool_call_executed.emit(func_name, tool_result)
                            
                            # Add tool result to messages
                            tool_results.append({
                                "role": "tool",
                                "content": tool_result,
                                "tool_call_id": tool_id,
                                "name": func_name
                            })
                        except Exception as e:
                            error_result = f"Greška pri izvršavanju tool-a {func_name}: {str(e)}"
                            print(f"[TOOLS] {error_result}")
                            tool_results.append({
                                "role": "tool",
                                "content": error_result,
                                "tool_call_id": tool_id,
                                "name": func_name
                            })
                    
                    # Add tool results to messages and continue loop
                    current_messages.extend(tool_results)
                    continue  # Loop again to get final response
                
                # No tool calls - finish
                if content:
                    self.finished.emit(content)
                    return
                else:
                    # Empty content but no tool calls - might be thinking
                    self.finished.emit(content or "")
                    return
            
            # Max iterations reached
            self.error_occurred.emit("Dostignut maksimalan broj tool poziva. Možda je infinite loop.")
            
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}"
            print(f"ChatToolsWorker error: {error_msg}")
            traceback.print_exc()
            self.error_occurred.emit(str(e))
