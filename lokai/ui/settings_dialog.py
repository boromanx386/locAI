"""
Settings Dialog for locAI.
Configuration dialog with tabs for all settings.
"""

from pathlib import Path
import os
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QFormLayout,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from lokai.core.config_manager import ConfigManager
from lokai.core.paths import (
    default_hf_cache_suggestion,
    get_image_output_dir,
    get_video_output_dir,
    get_audio_output_dir,
    get_models_storage_path,
    get_video_storage_path,
    get_audio_storage_path,
)
from lokai.utils.model_manager import ModelManager
from lokai.ui.material_icons import MaterialIcons
from lokai.core.ollama_detector import OllamaDetector


class SettingsDialog(QDialog):
    """Settings dialog with tabbed interface."""
    
    # Class-level cache for embedding models (loaded once per app session)
    _embedding_models_cache = None
    _embedding_models_loaded = False

    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        Initialize SettingsDialog.

        Args:
            config_manager: ConfigManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Settings")
        self.setMinimumWidth(820)
        self.setMinimumHeight(500)

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()

        # Tab widget
        self.tabs = QTabWidget()

        # General tab
        self.general_tab = self.create_general_tab()
        self.tabs.addTab(self.general_tab, "General")

        # Ollama tab
        self.ollama_tab = self.create_ollama_tab()
        self.tabs.addTab(self.ollama_tab, "Ollama")

        # Image Generation tab
        self.image_gen_tab = self.create_image_gen_tab()
        self.tabs.addTab(self.image_gen_tab, "Image Generation")

        # Video Generation tab
        self.video_gen_tab = self.create_video_gen_tab()
        self.tabs.addTab(self.video_gen_tab, "Video Generation")

        # Audio Generation tab
        self.audio_gen_tab = self.create_audio_gen_tab()
        self.tabs.addTab(self.audio_gen_tab, "Audio Generation")

        # LoRA tab
        self.lora_tab = self.create_lora_tab()
        self.tabs.addTab(self.lora_tab, "LoRA")

        # TTS tab
        self.tts_tab = self.create_tts_tab()
        self.tabs.addTab(self.tts_tab, "TTS")

        # ASR tab
        self.asr_tab = self.create_asr_tab()
        self.tabs.addTab(self.asr_tab, "ASR")

        # Semantic Memory tab
        self.rag_tab = self.create_rag_tab()
        self.tabs.addTab(self.rag_tab, "Semantic Memory")

        layout.addWidget(self.tabs)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def create_general_tab(self) -> QWidget:
        """Create General settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # Theme group
        theme_group = QGroupBox("Appearance")
        theme_layout = QFormLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        theme_layout.addRow("Theme:", self.theme_combo)

        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # Global shortcuts group
        shortcuts_group = QGroupBox("Global Shortcuts")
        shortcuts_layout = QFormLayout()

        # Enable/disable global shortcuts
        self.global_shortcuts_check = QCheckBox("Enable global shortcuts (system-wide)")
        self.global_shortcuts_check.setToolTip(
            "If enabled, locAI can react to a global hotkey even when it is not focused.\n"
            "The selected text will be sent to TTS or Image generation."
        )
        shortcuts_layout.addRow("", self.global_shortcuts_check)

        # TTS shortcut key (free-form, supports combos like 'ctrl+shift+t')
        self.tts_shortcut_edit = QLineEdit()
        self.tts_shortcut_edit.setPlaceholderText("e.g. f9, ctrl+shift+t")
        self.tts_shortcut_edit.setToolTip(
            "Single key (e.g. f9) is most reliable. Combos: ctrl+shift+t, alt+f9.\n"
            "Use only + between keys, no spaces. On Windows, combos may need app run as Administrator."
        )
        shortcuts_layout.addRow("TTS shortcut:", self.tts_shortcut_edit)

        # Image shortcut key (free-form, supports combos like 'ctrl+shift+i')
        self.image_shortcut_edit = QLineEdit()
        self.image_shortcut_edit.setPlaceholderText("e.g. f10, ctrl+shift+i")
        self.image_shortcut_edit.setToolTip(
            "Single key (e.g. f10) is most reliable. Combos: ctrl+shift+i, alt+f10.\n"
            "Use only + between keys, no spaces. On Windows, combos may need app run as Administrator."
        )
        shortcuts_layout.addRow("Image shortcut:", self.image_shortcut_edit)

        shortcuts_group.setLayout(shortcuts_layout)
        layout.addWidget(shortcuts_group)

        # Prompt templates (merged from former Prompts tab)
        prompts_group = QGroupBox("Prompt templates")
        prompts_group_layout = QVBoxLayout()
        info_label = QLabel(
            "Manage prompt templates for the chat prompt button. Add, edit, or delete."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; padding: 4px 0;")
        prompts_group_layout.addWidget(info_label)
        self.prompts_list = QListWidget()
        self.prompts_list.setToolTip("List of saved prompts. Double-click to edit.")
        self.prompts_list.setMaximumHeight(120)
        self.prompts_list.itemDoubleClicked.connect(self.edit_prompt)
        prompts_group_layout.addWidget(self.prompts_list)
        btn_layout = QHBoxLayout()
        self.add_prompt_btn = QPushButton("Add")
        MaterialIcons.apply_to_button(
            self.add_prompt_btn, MaterialIcons.SAVE_SVG, size=18
        )
        self.add_prompt_btn.clicked.connect(self.add_prompt)
        self.edit_prompt_btn = QPushButton("Edit")
        MaterialIcons.apply_to_button(
            self.edit_prompt_btn, MaterialIcons.SETTINGS_SVG, size=18
        )
        self.edit_prompt_btn.clicked.connect(self.edit_prompt)
        self.delete_prompt_btn = QPushButton("Delete")
        MaterialIcons.apply_to_button(
            self.delete_prompt_btn, MaterialIcons.DELETE_SVG, size=18
        )
        self.delete_prompt_btn.clicked.connect(self.delete_prompt)
        btn_layout.addWidget(self.add_prompt_btn)
        btn_layout.addWidget(self.edit_prompt_btn)
        btn_layout.addWidget(self.delete_prompt_btn)
        btn_layout.addStretch()
        prompts_group_layout.addLayout(btn_layout)
        prompts_group.setLayout(prompts_group_layout)
        layout.addWidget(prompts_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_ollama_tab(self) -> QWidget:
        """Create Ollama settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        ollama_group = QGroupBox("Ollama Configuration")
        ollama_layout = QFormLayout()

        self.ollama_url_edit = QLineEdit()
        self.ollama_url_edit.setPlaceholderText("http://localhost:11434")
        ollama_layout.addRow("Base URL:", self.ollama_url_edit)

        self.default_model_edit = QLineEdit()
        self.default_model_edit.setPlaceholderText("llama3.2")
        ollama_layout.addRow("Default Model:", self.default_model_edit)

        self.auto_start_check = QCheckBox("Auto-start Ollama")
        ollama_layout.addRow("", self.auto_start_check)

        ollama_group.setLayout(ollama_layout)
        layout.addWidget(ollama_group)

        # Tools/Function Calling Group
        tools_group = QGroupBox("Tools / Function Calling")
        tools_layout = QFormLayout()

        self.tools_enabled_check = QCheckBox("Enable tools (web search, weather, etc.)")
        self.tools_enabled_check.setToolTip(
            "Omogući modelu da koristi tools za pretragu interneta i druge funkcije. "
            "Radi samo sa modelima koji podržavaju tools (qwen3, deepseek-r1, itd.)."
        )
        tools_layout.addRow("", self.tools_enabled_check)

        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)

        # LLM Generation Parameters Group
        llm_params_group = QGroupBox("LLM Generation Parameters")
        llm_params_layout = QFormLayout()

        # Context Window
        self.context_window_spin = QSpinBox()
        self.context_window_spin.setRange(512, 200000)  # Support up to 200k context
        self.context_window_spin.setValue(4096)
        self.context_window_spin.setSingleStep(1024)  # Larger step for big models
        self.context_window_spin.setToolTip(
            "Maximum context size in tokens (512-200000). Higher values require more memory."
        )
        llm_params_layout.addRow("Context Window:", self.context_window_spin)

        # Temperature
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setValue(0.7)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setDecimals(1)
        self.temperature_spin.setToolTip(
            "Creativity: Higher = more creative, Lower = more focused (0.0-2.0)"
        )
        llm_params_layout.addRow("Temperature:", self.temperature_spin)

        # Top P
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setValue(0.9)
        self.top_p_spin.setSingleStep(0.05)
        self.top_p_spin.setDecimals(2)
        self.top_p_spin.setToolTip("Nucleus sampling threshold (0.0-1.0)")
        llm_params_layout.addRow("Top P:", self.top_p_spin)

        # Top K
        self.top_k_spin = QSpinBox()
        self.top_k_spin.setRange(1, 100)
        self.top_k_spin.setValue(40)
        self.top_k_spin.setToolTip("Consider top K tokens (1-100)")
        llm_params_layout.addRow("Top K:", self.top_k_spin)

        # Repeat Penalty
        self.repeat_penalty_spin = QDoubleSpinBox()
        self.repeat_penalty_spin.setRange(0.0, 2.0)
        self.repeat_penalty_spin.setValue(1.1)
        self.repeat_penalty_spin.setSingleStep(0.1)
        self.repeat_penalty_spin.setDecimals(1)
        self.repeat_penalty_spin.setToolTip(
            "Penalty for repetition (1.0 = no penalty, 0.0-2.0)"
        )
        llm_params_layout.addRow("Repeat Penalty:", self.repeat_penalty_spin)

        # Max Tokens
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(-1, 32768)
        self.max_tokens_spin.setValue(-1)
        self.max_tokens_spin.setSpecialValueText("Unlimited")
        self.max_tokens_spin.setToolTip("Maximum tokens to generate (-1 = unlimited)")
        llm_params_layout.addRow("Max Tokens:", self.max_tokens_spin)

        llm_params_group.setLayout(llm_params_layout)
        layout.addWidget(llm_params_group)

        # Conversation Settings Group
        conversation_group = QGroupBox("Conversation Settings")
        conversation_layout = QFormLayout()

        # System Prompt
        self.system_prompt_edit = QTextEdit()
        self.system_prompt_edit.setMaximumHeight(80)
        self.system_prompt_edit.setPlaceholderText("You are a helpful AI assistant.")
        conversation_layout.addRow("System Prompt:", self.system_prompt_edit)

        # Max History Messages
        self.max_history_spin = QSpinBox()
        self.max_history_spin.setRange(0, 100)
        self.max_history_spin.setValue(20)
        self.max_history_spin.setSpecialValueText("Unlimited")
        self.max_history_spin.setToolTip(
            "Maximum number of previous messages to remember (0 = unlimited)"
        )
        conversation_layout.addRow("Max History Messages:", self.max_history_spin)

        # Use Explicit History
        self.explicit_history_check = QCheckBox("Use Explicit History")
        self.explicit_history_check.setToolTip(
            "Send conversation history explicitly in prompt (instead of only using context)"
        )
        conversation_layout.addRow("", self.explicit_history_check)

        conversation_group.setLayout(conversation_layout)
        layout.addWidget(conversation_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_image_gen_tab(self) -> QWidget:
        """Create Image Generation settings tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(14)
        content.setMinimumHeight(560)

        # Model Storage section (moved from Models tab)
        models_group = QGroupBox("Model Storage")
        models_layout = QVBoxLayout()

        path_layout = QHBoxLayout()
        self.model_path_edit = QLineEdit()
        self.model_path_edit.setReadOnly(True)
        self.model_path_edit.setPlaceholderText("Select folder with image models...")
        path_layout.addWidget(self.model_path_edit, stretch=1)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_model_path)
        path_layout.addWidget(self.browse_btn)

        models_layout.addLayout(path_layout)

        self.auto_download_check = QCheckBox("Auto-download models")
        models_layout.addWidget(self.auto_download_check)

        models_group.setLayout(models_layout)
        layout.addWidget(models_group)

        image_group = QGroupBox("Image Generation Settings")
        image_layout = QFormLayout()
        image_layout.setVerticalSpacing(8)

        self.image_enabled_check = QCheckBox("Enable Image Generation")
        image_layout.addRow("", self.image_enabled_check)

        # Model selection with detection
        model_layout = QHBoxLayout()
        self.image_model_combo = QComboBox()
        self.image_model_combo.setEditable(False)  # Not editable - proper dropdown
        self.image_model_combo.setMinimumWidth(300)
        # Make dropdown more visible
        self.image_model_combo.setStyleSheet(
            """
            QComboBox {
                padding: 4px;
                border: 1px solid #555;
                border-radius: 10px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #aaa;
                width: 0;
                height: 0;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #555;
                selection-background-color: #3a3a3a;
            }
        """
        )
        model_layout.addWidget(self.image_model_combo, stretch=1)

        self.refresh_models_btn = QPushButton("Refresh")
        MaterialIcons.apply_to_button(
            self.refresh_models_btn, MaterialIcons.REFRESH_SVG, size=18
        )
        self.refresh_models_btn.setToolTip("Refresh detected models")
        self.refresh_models_btn.clicked.connect(self.refresh_image_models)
        model_layout.addWidget(self.refresh_models_btn)

        # Add manual entry option
        self.manual_model_btn = QPushButton("Custom")
        # Using edit icon (similar to pencil)
        edit_svg = """<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
<path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z" fill="currentColor"/>
</svg>"""
        MaterialIcons.apply_to_button(self.manual_model_btn, edit_svg, size=18)
        self.manual_model_btn.setToolTip("Enter custom model name")
        self.manual_model_btn.clicked.connect(self.add_custom_model)
        model_layout.addWidget(self.manual_model_btn)

        # Model Info button
        self.model_info_btn = QPushButton("Info")
        MaterialIcons.apply_to_button(
            self.model_info_btn, MaterialIcons.INFO_SVG, size=18
        )
        self.model_info_btn.setToolTip("View/edit model information and preset")
        self.model_info_btn.clicked.connect(self.show_model_info)
        model_layout.addWidget(self.model_info_btn)

        image_layout.addRow("Model:", model_layout)

        # Auto-apply presets checkbox
        self.auto_apply_check = QCheckBox("Auto-apply preset when model changes")
        self.auto_apply_check.setToolTip(
            "Automatically apply saved preset settings when selecting a model"
        )
        image_layout.addRow("", self.auto_apply_check)

        # Sequential CPU offload checkbox
        self.cpu_offload_check = QCheckBox(
            "Use Sequential CPU Offload (Save GPU Memory)"
        )
        self.cpu_offload_check.setToolTip(
            "Enable sequential CPU offload to minimize GPU VRAM usage. "
            "Model components are moved between CPU and GPU as needed. "
            "Recommended for GPUs with limited VRAM (8GB or less). "
            "Disable for faster generation if you have enough GPU memory."
        )
        image_layout.addRow("", self.cpu_offload_check)

        # Output folder for generated images
        image_output_layout = QHBoxLayout()
        self.image_output_path_edit = QLineEdit()
        self.image_output_path_edit.setReadOnly(True)
        self.image_output_path_edit.setPlaceholderText(
            "Select folder for generated images..."
        )
        image_output_layout.addWidget(self.image_output_path_edit, stretch=1)

        self.browse_image_output_btn = QPushButton("Browse...")
        self.browse_image_output_btn.clicked.connect(self.browse_image_output_path)
        image_output_layout.addWidget(self.browse_image_output_btn)

        image_layout.addRow("Output Folder:", image_output_layout)

        self.image_width_spin = QSpinBox()
        self.image_width_spin.setRange(256, 2048)
        self.image_width_spin.setValue(1024)
        self.image_width_spin.setSingleStep(64)
        image_layout.addRow("Width:", self.image_width_spin)

        self.image_height_spin = QSpinBox()
        self.image_height_spin.setRange(256, 2048)
        self.image_height_spin.setValue(1024)
        self.image_height_spin.setSingleStep(64)
        image_layout.addRow("Height:", self.image_height_spin)

        self.image_steps_spin = QSpinBox()
        self.image_steps_spin.setRange(1, 150)
        self.image_steps_spin.setValue(50)
        image_layout.addRow("Steps:", self.image_steps_spin)

        self.image_guidance_spin = QDoubleSpinBox()
        self.image_guidance_spin.setRange(1.0, 20.0)
        self.image_guidance_spin.setValue(7.5)
        self.image_guidance_spin.setSingleStep(0.5)
        self.image_guidance_spin.setDecimals(1)
        image_layout.addRow("Guidance Scale:", self.image_guidance_spin)

        self.img2img_strength_spin = QDoubleSpinBox()
        self.img2img_strength_spin.setRange(0.2, 1.0)
        self.img2img_strength_spin.setValue(0.75)
        self.img2img_strength_spin.setSingleStep(0.05)
        self.img2img_strength_spin.setDecimals(2)
        self.img2img_strength_spin.setToolTip(
            "Img2img: How much to change the image (0.3-0.5 subtle, 0.7-0.9 strong)"
        )
        image_layout.addRow("Img2img Strength:", self.img2img_strength_spin)

        self.img2img_steps_spin = QSpinBox()
        self.img2img_steps_spin.setRange(5, 100)
        self.img2img_steps_spin.setValue(30)
        self.img2img_steps_spin.setToolTip(
            "Img2img: Number of inference steps (fewer than txt2img typical)"
        )
        image_layout.addRow("Img2img Steps:", self.img2img_steps_spin)

        self.negative_prompt_edit = QTextEdit()
        self.negative_prompt_edit.setMinimumHeight(52)
        self.negative_prompt_edit.setMaximumHeight(80)
        self.negative_prompt_edit.setPlaceholderText(
            "blurry, low quality, distorted, ugly..."
        )
        image_layout.addRow("Negative Prompt:", self.negative_prompt_edit)

        image_group.setLayout(image_layout)
        layout.addWidget(image_group)

        # Model Preset Management
        preset_group = QGroupBox("Model Preset Management")
        preset_layout = QVBoxLayout()

        # Current preset info
        self.preset_info_label = QLabel("No preset saved for current model")
        self.preset_info_label.setWordWrap(True)
        self.preset_info_label.setStyleSheet("color: #888; padding: 8px;")
        preset_layout.addWidget(self.preset_info_label)

        # Preset buttons
        preset_buttons_layout = QHBoxLayout()

        self.save_preset_btn = QPushButton("Save Current Settings as Preset")
        MaterialIcons.apply_to_button(
            self.save_preset_btn, MaterialIcons.SAVE_SVG, size=18
        )
        self.save_preset_btn.setToolTip(
            "Save current settings as preset for selected model"
        )
        self.save_preset_btn.clicked.connect(self.save_current_preset)
        preset_buttons_layout.addWidget(self.save_preset_btn)

        self.reset_preset_btn = QPushButton("Reset to Preset")
        MaterialIcons.apply_to_button(
            self.reset_preset_btn, MaterialIcons.RESET_SVG, size=18
        )
        self.reset_preset_btn.setToolTip(
            "Reset settings to saved preset for selected model"
        )
        self.reset_preset_btn.clicked.connect(self.reset_to_preset)
        preset_buttons_layout.addWidget(self.reset_preset_btn)

        self.delete_preset_btn = QPushButton("Delete Preset")
        MaterialIcons.apply_to_button(
            self.delete_preset_btn, MaterialIcons.DELETE_SVG, size=18
        )
        self.delete_preset_btn.setToolTip("Delete saved preset for selected model")
        self.delete_preset_btn.clicked.connect(self.delete_preset)
        preset_buttons_layout.addWidget(self.delete_preset_btn)

        preset_layout.addLayout(preset_buttons_layout)
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

        # Connect model change to update preset info and auto-apply
        self.image_model_combo.currentTextChanged.connect(self.on_model_changed)

        layout.addStretch()
        scroll.setWidget(content)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(scroll)
        return wrapper

    def create_video_gen_tab(self) -> QWidget:
        """Create Video Generation settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        video_group = QGroupBox("Video Generation Settings")
        video_layout = QFormLayout()

        # Video model storage path
        video_path_layout = QHBoxLayout()
        self.video_model_path_edit = QLineEdit()
        self.video_model_path_edit.setReadOnly(True)
        self.video_model_path_edit.setPlaceholderText(
            "Select folder with video models..."
        )
        video_path_layout.addWidget(self.video_model_path_edit, stretch=1)

        self.browse_video_path_btn = QPushButton("Browse...")
        self.browse_video_path_btn.clicked.connect(self.browse_video_model_path)
        video_path_layout.addWidget(self.browse_video_path_btn)

        video_layout.addRow("Video Models Folder:", video_path_layout)

        # Output folder for generated videos
        video_output_layout = QHBoxLayout()
        self.video_output_path_edit = QLineEdit()
        self.video_output_path_edit.setReadOnly(True)
        self.video_output_path_edit.setPlaceholderText(
            "Select folder for generated videos..."
        )
        video_output_layout.addWidget(self.video_output_path_edit, stretch=1)

        self.browse_video_output_btn = QPushButton("Browse...")
        self.browse_video_output_btn.clicked.connect(self.browse_video_output_path)
        video_output_layout.addWidget(self.browse_video_output_btn)

        video_layout.addRow("Output Folder:", video_output_layout)

        # Video resolution selection
        self.video_resolution_combo = QComboBox()
        self.video_resolution_combo.addItems(
            [
                "Auto (detect from image)",
                "576x1024 (Portrait/Vertical)",
                "1024x576 (Landscape/Horizontal/Wide)",
            ]
        )
        self.video_resolution_combo.setToolTip(
            "Resolution for video generation:\n"
            "Auto: Automatically detects from input image aspect ratio\n"
            "576x1024: Portrait/vertical format (9:16)\n"
            "1024x576: Landscape/horizontal/wide format (16:9)"
        )
        video_layout.addRow("Video Resolution:", self.video_resolution_combo)

        # Model selection with detection
        model_layout = QHBoxLayout()
        self.video_model_combo = QComboBox()
        self.video_model_combo.setEditable(True)
        self.video_model_combo.setMinimumWidth(300)
        self.video_model_combo.setStyleSheet(
            """
            QComboBox {
                padding: 4px;
                border: 1px solid #555;
                border-radius: 10px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #aaa;
                width: 0;
                height: 0;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #555;
                selection-background-color: #3a3a3a;
            }
        """
        )
        model_layout.addWidget(self.video_model_combo, stretch=1)

        self.refresh_video_models_btn = QPushButton("Refresh")
        MaterialIcons.apply_to_button(
            self.refresh_video_models_btn, MaterialIcons.REFRESH_SVG, size=18
        )
        self.refresh_video_models_btn.setToolTip("Refresh detected video models")
        self.refresh_video_models_btn.clicked.connect(self.refresh_video_models)
        model_layout.addWidget(self.refresh_video_models_btn)

        self.video_model_combo.setToolTip(
            "SVD: 14 frames\n" "SVD-XT: 25 frames (longer video)"
        )
        video_layout.addRow("Model:", model_layout)

        # Sequential CPU offload checkbox
        self.video_cpu_offload_check = QCheckBox(
            "Use Sequential CPU Offload (Save GPU Memory)"
        )
        self.video_cpu_offload_check.setToolTip(
            "Enable sequential CPU offload to minimize GPU VRAM usage. "
            "Model components are moved between CPU and GPU as needed. "
            "Recommended for GPUs with limited VRAM (8GB or less). "
            "Disable for faster generation if you have enough GPU memory."
        )
        video_layout.addRow("", self.video_cpu_offload_check)

        # Number of frames
        self.video_frames_spin = QSpinBox()
        self.video_frames_spin.setRange(1, 25)
        self.video_frames_spin.setValue(14)
        self.video_frames_spin.setToolTip(
            "Number of frames to generate.\n"
            "SVD: up to 14 frames (recommended: 14)\n"
            "SVD-XT: up to 25 frames (recommended: 25)\n"
            "Note: More frames = longer video but more VRAM usage"
        )
        video_layout.addRow("Number of Frames:", self.video_frames_spin)

        # Inference steps
        self.video_steps_spin = QSpinBox()
        self.video_steps_spin.setRange(1, 150)
        self.video_steps_spin.setValue(25)
        self.video_steps_spin.setToolTip(
            "Number of inference steps. More steps = better quality but slower. "
            "Recommended: 25-50"
        )
        video_layout.addRow("Inference Steps:", self.video_steps_spin)

        # Motion bucket ID (jačina pokreta)
        self.video_motion_spin = QSpinBox()
        self.video_motion_spin.setRange(1, 255)
        self.video_motion_spin.setValue(127)
        self.video_motion_spin.setToolTip(
            "Motion Bucket ID - kontroliše jačinu pokreta u videu.\n"
            "Niže vrednosti (1-100): Manje pokreta, statičniji video\n"
            "Srednje vrednosti (100-150): Umeren pokret (preporučeno: 127)\n"
            "Više vrednosti (150-255): Više pokreta, dinamičniji video\n"
            "Default: 127 (uravnoteženo)"
        )
        video_layout.addRow(
            "Motion Bucket ID (Jačina Pokreta):", self.video_motion_spin
        )

        # FPS
        self.video_fps_spin = QSpinBox()
        self.video_fps_spin.setRange(1, 30)
        self.video_fps_spin.setValue(7)
        self.video_fps_spin.setToolTip(
            "Frames per second for output video. "
            "Recommended: 7 fps for natural motion"
        )
        video_layout.addRow("FPS:", self.video_fps_spin)

        video_group.setLayout(video_layout)
        layout.addWidget(video_group)

        # Info label
        info_label = QLabel(
            "Note: Video generation requires an input image.\n"
            "Right-click on any generated image and select 'Generate Video'."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; padding: 8px;")
        layout.addWidget(info_label)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_audio_gen_tab(self) -> QWidget:
        """Create Audio Generation settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        audio_group = QGroupBox("Audio Generation Settings")
        audio_layout = QFormLayout()

        # Audio model storage path
        audio_path_layout = QHBoxLayout()
        self.audio_model_path_edit = QLineEdit()
        self.audio_model_path_edit.setReadOnly(True)
        self.audio_model_path_edit.setPlaceholderText(
            "Select folder with audio models..."
        )
        audio_path_layout.addWidget(self.audio_model_path_edit, stretch=1)

        self.browse_audio_path_btn = QPushButton("Browse...")
        self.browse_audio_path_btn.clicked.connect(self.browse_audio_model_path)
        audio_path_layout.addWidget(self.browse_audio_path_btn)

        audio_layout.addRow("Audio Models Folder:", audio_path_layout)

        # Output folder for generated audio files
        audio_output_layout = QHBoxLayout()
        self.audio_output_path_edit = QLineEdit()
        self.audio_output_path_edit.setReadOnly(True)
        self.audio_output_path_edit.setPlaceholderText(
            "Select folder for generated audio..."
        )
        audio_output_layout.addWidget(self.audio_output_path_edit, stretch=1)

        self.browse_audio_output_btn = QPushButton("Browse...")
        self.browse_audio_output_btn.clicked.connect(self.browse_audio_output_path)
        audio_output_layout.addWidget(self.browse_audio_output_btn)

        audio_layout.addRow("Output Folder:", audio_output_layout)

        # Model selection
        model_layout = QHBoxLayout()
        self.audio_model_combo = QComboBox()
        self.audio_model_combo.addItem("stabilityai/stable-audio-open-1.0")
        self.audio_model_combo.setEditable(True)
        self.audio_model_combo.setMinimumWidth(300)
        self.audio_model_combo.setStyleSheet(
            """
            QComboBox {
                padding: 4px;
                border: 1px solid #555;
                border-radius: 10px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #aaa;
                width: 0;
                height: 0;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #555;
                selection-background-color: #3a3a3a;
            }
        """
        )
        model_layout.addWidget(self.audio_model_combo, stretch=1)
        audio_layout.addRow("Model:", model_layout)

        # Audio length (seconds)
        self.audio_length_spin = QDoubleSpinBox()
        self.audio_length_spin.setRange(1.0, 47.0)
        self.audio_length_spin.setValue(10.0)
        self.audio_length_spin.setSingleStep(1.0)
        self.audio_length_spin.setDecimals(1)
        self.audio_length_spin.setToolTip(
            "Length of generated audio in seconds (1-47). Longer audio requires more VRAM."
        )
        audio_layout.addRow("Audio Length (seconds):", self.audio_length_spin)

        # Inference steps
        self.audio_steps_spin = QSpinBox()
        self.audio_steps_spin.setRange(50, 500)
        self.audio_steps_spin.setValue(200)
        self.audio_steps_spin.setToolTip(
            "Number of inference steps. More steps = better quality but slower. "
            "Recommended: 200"
        )
        audio_layout.addRow("Inference Steps:", self.audio_steps_spin)

        # Guidance scale
        self.audio_guidance_spin = QDoubleSpinBox()
        self.audio_guidance_spin.setRange(1.0, 20.0)
        self.audio_guidance_spin.setValue(7.0)
        self.audio_guidance_spin.setSingleStep(0.5)
        self.audio_guidance_spin.setDecimals(1)
        self.audio_guidance_spin.setToolTip(
            "Guidance scale (CFG). Higher = follows prompt more closely. "
            "Recommended: 7.0"
        )
        audio_layout.addRow("Guidance Scale:", self.audio_guidance_spin)

        # Negative prompt
        self.audio_negative_prompt_edit = QLineEdit()
        self.audio_negative_prompt_edit.setPlaceholderText("Low quality.")
        self.audio_negative_prompt_edit.setToolTip(
            "Negative prompt - what to avoid in generated audio"
        )
        audio_layout.addRow("Negative Prompt:", self.audio_negative_prompt_edit)

        # Number of waveforms per prompt (variations)
        self.audio_num_waveforms_spin = QSpinBox()
        self.audio_num_waveforms_spin.setRange(1, 4)
        self.audio_num_waveforms_spin.setValue(1)
        self.audio_num_waveforms_spin.setToolTip(
            "Number of audio variations to generate per prompt (1-4). "
            "More variations = more VRAM usage and longer generation time."
        )
        audio_layout.addRow("Number of Variations:", self.audio_num_waveforms_spin)

        # Sequential CPU offload checkbox (optional)
        self.audio_cpu_offload_check = QCheckBox(
            "Use Sequential CPU Offload (Save GPU Memory)"
        )
        self.audio_cpu_offload_check.setToolTip(
            "Enable sequential CPU offload to minimize GPU VRAM usage. "
            "Model components are moved between CPU and GPU as needed. "
            "Optional - disable for faster generation if you have enough GPU memory."
        )
        audio_layout.addRow("", self.audio_cpu_offload_check)

        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)

        # Info label
        info_label = QLabel(
            "Note: Audio generation requires text prompts.\n"
            "Use the audio mode button in chat or right-click selected text and choose 'Generate Audio'."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; padding: 8px;")
        layout.addWidget(info_label)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_lora_tab(self) -> QWidget:
        """Create LoRA settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        lora_group = QGroupBox("LoRA Configuration")
        lora_layout = QFormLayout()

        # LoRA selection
        lora_select_layout = QHBoxLayout()
        self.lora_combo = QComboBox()
        self.lora_combo.addItem("None (No LoRA)")
        self.lora_combo.setMinimumWidth(200)
        self.lora_combo.currentTextChanged.connect(self.on_lora_changed)
        lora_select_layout.addWidget(self.lora_combo, stretch=1)

        self.refresh_lora_btn = QPushButton("Refresh")
        MaterialIcons.apply_to_button(
            self.refresh_lora_btn, MaterialIcons.REFRESH_SVG, size=18
        )
        self.refresh_lora_btn.setToolTip("Refresh detected LoRA models")
        self.refresh_lora_btn.clicked.connect(self.refresh_lora_models)
        lora_select_layout.addWidget(self.refresh_lora_btn)

        lora_layout.addRow("LoRA Model:", lora_select_layout)

        # LoRA weight
        self.lora_weight_spin = QDoubleSpinBox()
        self.lora_weight_spin.setRange(0.0, 2.0)
        self.lora_weight_spin.setValue(1.0)
        self.lora_weight_spin.setSingleStep(0.1)
        self.lora_weight_spin.setDecimals(1)
        self.lora_weight_spin.setToolTip(
            "LoRA strength/weight (0.0 = no effect, 1.0 = full effect, 2.0 = double effect)"
        )
        lora_layout.addRow("LoRA Weight:", self.lora_weight_spin)

        lora_group.setLayout(lora_layout)
        layout.addWidget(lora_group)

        # LoRA Info section
        info_group = QGroupBox("LoRA Information")
        info_layout = QVBoxLayout()

        # Display current info (read-only)
        self.lora_info_label = QLabel("Select a LoRA model to view its information.")
        self.lora_info_label.setWordWrap(True)
        self.lora_info_label.setStyleSheet(
            "color: #888; padding: 8px; min-height: 60px;"
        )
        self.lora_info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        info_layout.addWidget(self.lora_info_label)

        info_layout.addWidget(QLabel("Edit Information:"))

        # Editable info text area
        self.lora_info_edit = QTextEdit()
        self.lora_info_edit.setPlaceholderText(
            "Enter information about this LoRA model..."
        )
        self.lora_info_edit.setMaximumHeight(150)
        self.lora_info_edit.setEnabled(False)  # Disabled until LoRA is selected
        info_layout.addWidget(self.lora_info_edit)

        # Save button
        save_info_layout = QHBoxLayout()
        save_info_layout.addStretch()
        self.save_lora_info_btn = QPushButton("Save Information")
        MaterialIcons.apply_to_button(
            self.save_lora_info_btn, MaterialIcons.SAVE_SVG, size=18
        )
        self.save_lora_info_btn.setToolTip("Save information for selected LoRA model")
        self.save_lora_info_btn.setEnabled(False)  # Disabled until LoRA is selected
        self.save_lora_info_btn.clicked.connect(self.save_lora_info)
        save_info_layout.addWidget(self.save_lora_info_btn)

        info_layout.addLayout(save_info_layout)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_tts_tab(self) -> QWidget:
        """Create TTS settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        tts_group = QGroupBox("Text-to-Speech")
        tts_layout = QFormLayout()

        self.tts_enabled_check = QCheckBox("Enable TTS")
        tts_layout.addRow("", self.tts_enabled_check)

        # TTS Engine selection
        self.tts_engine_combo = QComboBox()
        self.tts_engine_combo.addItems(["Kokoro-82M", "Pocket TTS"])
        self.tts_engine_combo.currentTextChanged.connect(self.on_tts_engine_changed)
        tts_layout.addRow("TTS Engine:", self.tts_engine_combo)

        # Language selection
        self.lang_code_combo = QComboBox()
        self.lang_code_combo.addItems(
            [
                "American English (a)",
                "British English (b)",
                "Spanish (e)",
                "French (f)",
                "Hindi (h)",
                "Italian (i)",
                "Japanese (j)",
                "Brazilian Portuguese (p)",
                "Mandarin Chinese (z)",
            ]
        )
        self.lang_code_combo.currentTextChanged.connect(self.on_language_changed)
        tts_layout.addRow("Language:", self.lang_code_combo)

        # Voice selection (will be populated dynamically based on language)
        self.voice_combo = QComboBox()
        # Don't initialize voices here - will be loaded when settings are loaded or language changes
        tts_layout.addRow("Voice:", self.voice_combo)

        # Speed control
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setMinimum(0.5)
        self.speed_spin.setMaximum(2.0)
        self.speed_spin.setSingleStep(0.1)
        self.speed_spin.setValue(1.0)
        self.speed_spin.setDecimals(1)
        tts_layout.addRow("Speed:", self.speed_spin)

        self.auto_speak_check = QCheckBox("Auto-speak responses")
        tts_layout.addRow("", self.auto_speak_check)

        tts_group.setLayout(tts_layout)
        layout.addWidget(tts_group)

        # Voice Cloning (samo za Pocket TTS)
        voice_cloning_group = QGroupBox("Voice Cloning (Pocket TTS only)")
        cloning_layout = QVBoxLayout()

        self.voice_cloning_enabled_check = QCheckBox("Enable Voice Cloning")
        cloning_layout.addWidget(self.voice_cloning_enabled_check)

        file_layout = QHBoxLayout()
        self.voice_cloning_file_edit = QLineEdit()
        self.voice_cloning_file_edit.setPlaceholderText("Select audio file for voice cloning...")
        self.voice_cloning_browse_btn = QPushButton("Browse...")
        self.voice_cloning_browse_btn.clicked.connect(self.browse_voice_cloning_file)
        file_layout.addWidget(self.voice_cloning_file_edit)
        file_layout.addWidget(self.voice_cloning_browse_btn)
        cloning_layout.addLayout(file_layout)

        info_label = QLabel("Note: Audio file will be converted to PCM int16 format automatically.")
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        cloning_layout.addWidget(info_label)

        voice_cloning_group.setLayout(cloning_layout)
        layout.addWidget(voice_cloning_group)

        # Initially hide if Kokoro is selected
        self.voice_cloning_group = voice_cloning_group

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_asr_tab(self) -> QWidget:
        """Create ASR settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        asr_group = QGroupBox("Automatic Speech Recognition")
        asr_layout = QFormLayout()

        self.asr_enabled_check = QCheckBox("Enable ASR")
        asr_layout.addRow("", self.asr_enabled_check)

        # ASR Model selection
        self.asr_model_combo = QComboBox()
        self.asr_model_combo.addItems([
            "nvidia/nemotron-speech-streaming-en-0.6b",
        ])
        asr_layout.addRow("ASR Model:", self.asr_model_combo)

        # Chunk size selection
        self.chunk_size_combo = QComboBox()
        self.chunk_size_combo.addItems([
            "80ms (Lowest latency)",
            "160ms (Low latency)",
            "560ms (Balanced)",
            "1120ms (Highest accuracy)"
        ])
        self.chunk_size_combo.setCurrentIndex(2)  # Default to balanced
        asr_layout.addRow("Chunk Size:", self.chunk_size_combo)

        # Language selection (for future multi-language support)
        self.asr_language_combo = QComboBox()
        self.asr_language_combo.addItems([
            "English (en)",
        ])
        asr_layout.addRow("Language:", self.asr_language_combo)

        # Punctuation & Capitalization
        self.punctuation_check = QCheckBox("Punctuation & Capitalization")
        self.punctuation_check.setChecked(True)
        asr_layout.addRow("", self.punctuation_check)

        # Device selection (CPU/GPU)
        self.asr_device_combo = QComboBox()
        self.asr_device_combo.addItems([
            "CPU (Stable)",
            "GPU (CUDA - Experimental)"
        ])
        self.asr_device_combo.setCurrentIndex(0)  # Default to CPU
        asr_layout.addRow("Device:", self.asr_device_combo)

        asr_group.setLayout(asr_layout)
        layout.addWidget(asr_group)

        # Audio Input Settings
        audio_group = QGroupBox("Audio Input")
        audio_layout = QFormLayout()

        # Microphone device selection
        self.mic_device_combo = QComboBox()
        self._populate_microphone_devices()
        audio_layout.addRow("Microphone:", self.mic_device_combo)

        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_rag_tab(self) -> QWidget:
        """Create Semantic Memory (RAG) settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # Main RAG group
        rag_group = QGroupBox("Semantic Memory (RAG)")
        rag_layout = QFormLayout()

        # Enable/Disable checkbox
        self.rag_enabled_check = QCheckBox("Enable Semantic Memory")
        self.rag_enabled_check.setToolTip(
            "Enable semantic memory to improve context handling in long conversations. "
            "Uses embeddings to find relevant past messages."
        )
        rag_layout.addRow("", self.rag_enabled_check)

        # Embedding model selection
        self.embedding_model_combo = QComboBox()
        self.embedding_model_combo.setEditable(True)  # Allow custom model names
        self.embedding_model_combo.setToolTip(
            "Embedding model for semantic search. Smaller models use less memory.\n"
            "Shows only installed embedding models. You can also type a custom model name."
        )
        
        # Load installed embedding models from Ollama
        self._load_embedding_models()
        
        rag_layout.addRow("Embedding Model:", self.embedding_model_combo)

        # Force CPU checkbox
        self.rag_force_cpu_check = QCheckBox("Force CPU (Save GPU Memory)")
        self.rag_force_cpu_check.setToolTip(
            "Run embedding model on CPU instead of GPU to save GPU memory for LLM."
        )
        rag_layout.addRow("", self.rag_force_cpu_check)

        # Auto-embed checkbox (deprecated): this app is manual-only embedding.
        self.rag_auto_embed_check = QCheckBox("Auto-embed all chat messages (deprecated)")
        self.rag_auto_embed_check.setToolTip(
            "Deprecated. Manual-only embedding is enforced: nothing is embedded automatically.\n"
            "Use right-click 'Remember…' actions in chat bubbles to create memories."
        )
        self.rag_auto_embed_check.setChecked(False)
        self.rag_auto_embed_check.setEnabled(False)
        rag_layout.addRow("", self.rag_auto_embed_check)

        # Show prompt preview before sending
        self.show_prompt_preview_check = QCheckBox("Show prompt preview before sending")
        self.show_prompt_preview_check.setToolTip(
            "When enabled, shows a preview dialog with the full prompt before sending to the model.\n"
            "Useful for debugging and understanding what context the model receives."
        )
        rag_layout.addRow("", self.show_prompt_preview_check)

        rag_group.setLayout(rag_layout)
        layout.addWidget(rag_group)

        # Manual memory parameters (right-click Remember)
        manual_group = QGroupBox("Manual Memory (Right-click Remember)")
        manual_layout = QFormLayout()

        self.manual_min_memories_spin = QSpinBox()
        self.manual_min_memories_spin.setRange(1, 50)
        self.manual_min_memories_spin.setValue(3)
        self.manual_min_memories_spin.setToolTip(
            "RAG retrieval activates only after at least this many remembered items exist in the chat."
        )
        manual_layout.addRow("Min remembered items:", self.manual_min_memories_spin)

        self.memory_top_k_spin = QSpinBox()
        self.memory_top_k_spin.setRange(1, 20)
        self.memory_top_k_spin.setValue(3)
        self.memory_top_k_spin.setToolTip(
            "How many remembered items to retrieve and inject into context."
        )
        manual_layout.addRow("Memory Top K:", self.memory_top_k_spin)

        self.memory_max_chars_spin = QSpinBox()
        self.memory_max_chars_spin.setRange(200, 10000)
        self.memory_max_chars_spin.setValue(1200)
        self.memory_max_chars_spin.setToolTip(
            "Hard limit for injected memory text to keep small models responsive."
        )
        manual_layout.addRow("Memory max chars:", self.memory_max_chars_spin)

        self.memory_min_similarity_spin = QDoubleSpinBox()
        self.memory_min_similarity_spin.setRange(0.0, 1.0)
        self.memory_min_similarity_spin.setSingleStep(0.05)
        self.memory_min_similarity_spin.setValue(0.0)
        self.memory_min_similarity_spin.setToolTip(
            "Optional similarity filter (0 = include all retrieved items)."
        )
        manual_layout.addRow("Min similarity:", self.memory_min_similarity_spin)

        manual_group.setLayout(manual_layout)
        layout.addWidget(manual_group)

        # Info label
        info_label = QLabel(
            "Semantic memory helps maintain context in long conversations by finding "
            "relevant past messages using semantic similarity. Embeddings are stored per chat."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; padding: 8px;")
        layout.addWidget(info_label)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _load_embedding_models(self):
        """Load installed embedding models from Ollama and populate combo box.
        Uses class-level cache to load only once per app session."""
        # Use cached list if already loaded
        if SettingsDialog._embedding_models_loaded and SettingsDialog._embedding_models_cache is not None:
            self.embedding_model_combo.clear()
            self.embedding_model_combo.addItems(SettingsDialog._embedding_models_cache)
            return
        
        # Load from Ollama (only once)
        try:
            detector = OllamaDetector()
            embedding_models, error = detector.get_embedding_models()
            
            if error:
                print(f"Warning: Could not load embedding models: {error}")
                # Fallback to default list if detection fails
                embedding_models = [
                    "nomic-embed-text:v1.5",
                    "nomic-embed-text",
                    "all-minilm",
                    "mxbai-embed-large",
                ]
            elif not embedding_models:
                # If no embedding models found, add default suggestions
                embedding_models = [
                    "nomic-embed-text:v1.5",
                    "nomic-embed-text",
                ]
            
            # Cache the result
            SettingsDialog._embedding_models_cache = embedding_models
            SettingsDialog._embedding_models_loaded = True
            
            # Clear and populate combo box
            self.embedding_model_combo.clear()
            self.embedding_model_combo.addItems(embedding_models)
            
            print(f"Loaded {len(embedding_models)} embedding models: {embedding_models}")
        except Exception as e:
            print(f"Error loading embedding models: {e}")
            # Fallback to default list on error
            fallback_models = [
                "nomic-embed-text:v1.5",
                "nomic-embed-text",
                "all-minilm",
                "mxbai-embed-large",
            ]
            SettingsDialog._embedding_models_cache = fallback_models
            SettingsDialog._embedding_models_loaded = True
            self.embedding_model_combo.clear()
            self.embedding_model_combo.addItems(fallback_models)

    def add_prompt(self):
        """Add a new prompt."""
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "Add Prompt", "Enter prompt name:")
        if not ok or not name.strip():
            return

        text, ok = QInputDialog.getMultiLineText(
            self, "Add Prompt", "Enter prompt text:", ""
        )
        if not ok:
            return

        # Add to list
        item = QListWidgetItem(name)
        item.setData(
            Qt.ItemDataRole.UserRole, {"name": name.strip(), "text": text.strip()}
        )
        self.prompts_list.addItem(item)

    def edit_prompt(self):
        """Edit selected prompt."""
        current_item = self.prompts_list.currentItem()
        if not current_item:
            QMessageBox.information(
                self, "No Selection", "Please select a prompt to edit."
            )
            return

        from PySide6.QtWidgets import QInputDialog

        prompt_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not prompt_data:
            prompt_data = {"name": current_item.text(), "text": ""}

        # Edit name
        name, ok = QInputDialog.getText(
            self, "Edit Prompt", "Enter prompt name:", text=prompt_data.get("name", "")
        )
        if not ok or not name.strip():
            return

        # Edit text
        text, ok = QInputDialog.getMultiLineText(
            self, "Edit Prompt", "Enter prompt text:", prompt_data.get("text", "")
        )
        if not ok:
            return

        # Update item
        current_item.setText(name.strip())
        current_item.setData(
            Qt.ItemDataRole.UserRole, {"name": name.strip(), "text": text.strip()}
        )

    def delete_prompt(self):
        """Delete selected prompt."""
        current_item = self.prompts_list.currentItem()
        if not current_item:
            QMessageBox.information(
                self, "No Selection", "Please select a prompt to delete."
            )
            return

        reply = QMessageBox.question(
            self,
            "Delete Prompt",
            f"Are you sure you want to delete '{current_item.text()}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            row = self.prompts_list.row(current_item)
            self.prompts_list.takeItem(row)

    def on_language_changed(self, lang_text: str):
        """Handle language selection change - update voice list."""
        # Extract lang_code from text (e.g., "American English (a)" -> "a")
        lang_code = lang_text.split("(")[1].split(")")[0] if "(" in lang_text else "a"
        self.update_voices_for_language(lang_code)

    def update_voices_for_language(self, lang_code: str):
        """Update voice combo box with voices for selected language."""
        # Use hardcoded voice lists to avoid initializing TTSEngine (which loads Kokoro model)
        voices_by_language = {
            "a": [  # American English
                "af_alloy",
                "af_aoede",
                "af_bella",
                "af_heart",
                "af_jessica",
                "af_kore",
                "af_nicole",
                "af_nova",
                "af_river",
                "af_sarah",
                "af_sky",
                "am_adam",
                "am_echo",
                "am_eric",
                "am_fenrir",
                "am_liam",
                "am_michael",
                "am_onyx",
                "am_puck",
                "am_santa",
            ],
            "b": [  # British English
                "bf_alice",
                "bf_emma",
                "bf_isabella",
                "bf_lily",
                "bm_daniel",
                "bm_fable",
                "bm_george",
                "bm_lewis",
            ],
            "e": [  # Spanish
                "ef_dora",
                "em_alex",
                "em_santa",
            ],
            "f": [  # French
                "ff_siwis",
            ],
            "h": [  # Hindi
                "hf_alpha",
                "hf_beta",
                "hm_omega",
                "hm_psi",
            ],
            "i": [  # Italian
                "if_sara",
                "im_nicola",
            ],
            "j": [  # Japanese
                "jf_alpha",
                "jf_gongitsune",
                "jf_nezumi",
                "jf_tebukuro",
                "jm_kumo",
            ],
            "p": [  # Brazilian Portuguese
                "pf_dora",
                "pm_alex",
                "pm_santa",
            ],
            "z": [  # Mandarin Chinese
                "zf_xiaobei",
                "zf_xiaoni",
                "zf_xiaoxiao",
                "zf_xiaoyi",
            ],
        }

        voices = voices_by_language.get(lang_code, voices_by_language["a"])

        # Save current selection if it exists in new list
        current_voice = self.voice_combo.currentText()

        # Update combo box
        self.voice_combo.clear()
        self.voice_combo.addItems(voices)

        # Restore selection if still available
        if current_voice in voices:
            index = self.voice_combo.findText(current_voice)
            if index >= 0:
                self.voice_combo.setCurrentIndex(index)
        else:
            # Select first voice if previous not available
            if voices:
                self.voice_combo.setCurrentIndex(0)

    def on_tts_engine_changed(self, engine_text: str):
        """Handle TTS engine selection change."""
        is_pocket_tts = (engine_text == "Pocket TTS")
        
        # Show/hide language selector (Pocket TTS only English)
        self.lang_code_combo.setEnabled(not is_pocket_tts)
        
        # Show/hide voice cloning options
        self.voice_cloning_group.setVisible(is_pocket_tts)
        
        # Update voices for current engine
        if is_pocket_tts:
            # Pocket TTS voices (English only)
            voices = ['alba', 'marius', 'javert', 'jean', 'fantine', 'cosette', 'eponine', 'azelma']
            self.voice_combo.clear()
            self.voice_combo.addItems(voices)
        else:
            # Kokoro voices (update based on selected language)
            lang_code = self._get_lang_code_from_text(self.lang_code_combo.currentText())
            self.update_voices_for_language(lang_code)

    def _get_lang_code_from_text(self, lang_text: str) -> str:
        """Extract lang_code from language dropdown text."""
        # Extract lang_code from text (e.g., "American English (a)" -> "a")
        if "(" in lang_text and ")" in lang_text:
            return lang_text.split("(")[1].split(")")[0]
        return "a"  # Default to American English

    def browse_voice_cloning_file(self):
        """Browse for voice cloning audio file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File for Voice Cloning",
            "",
            "Audio Files (*.wav *.mp3 *.ogg *.flac);;All Files (*.*)"
        )
        
        if file_path:
            self.voice_cloning_file_edit.setText(file_path)

    def browse_model_path(self):
        """Browse for model storage path."""
        current_path = self.model_path_edit.text()
        if not current_path:
            current_path = str(Path.home() / "Documents" / "locAI" / "models")

        path = QFileDialog.getExistingDirectory(
            self, "Select Model Storage Location", current_path
        )

        if path:
            # Validate path
            manager = ModelManager()
            is_valid, error = manager.validate_path(path)
            if is_valid:
                self.model_path_edit.setText(path)
                # Refresh image models after path change
                self.refresh_image_models()
                # Refresh video models after path change
                if hasattr(self, "refresh_video_models"):
                    self.refresh_video_models()
            else:
                QMessageBox.warning(self, "Invalid Path", error)

    def browse_video_model_path(self):
        """Browse for video model storage path."""
        current_path = self.video_model_path_edit.text()
        if not current_path:
            current_path = (
                self.model_path_edit.text()
                or default_hf_cache_suggestion()
            )

        path = QFileDialog.getExistingDirectory(
            self, "Select Video Models Folder", current_path
        )

        if path:
            # Validate path
            manager = ModelManager()
            is_valid, error = manager.validate_path(path)
            if is_valid:
                self.video_model_path_edit.setText(path)
                # Refresh video models after path change
                if hasattr(self, "refresh_video_models"):
                    self.refresh_video_models()
            else:
                QMessageBox.warning(self, "Invalid Path", error)

    def browse_image_output_path(self):
        """Browse for image output folder."""
        current_path = self.image_output_path_edit.text()
        if not current_path:
            current_path = str(get_image_output_dir(self.config_manager))

        path = QFileDialog.getExistingDirectory(
            self, "Select Image Output Folder", current_path
        )

        if path:
            self.image_output_path_edit.setText(path)

    def browse_video_output_path(self):
        """Browse for video output folder."""
        current_path = self.video_output_path_edit.text()
        if not current_path:
            current_path = str(get_video_output_dir(self.config_manager))

        path = QFileDialog.getExistingDirectory(
            self, "Select Video Output Folder", current_path
        )

        if path:
            self.video_output_path_edit.setText(path)

    def browse_audio_model_path(self):
        """Browse for audio model storage path."""
        current_path = self.audio_model_path_edit.text()
        if not current_path:
            current_path = (
                self.model_path_edit.text()
                or default_hf_cache_suggestion()
            )

        path = QFileDialog.getExistingDirectory(
            self, "Select Audio Models Folder", current_path
        )

        if path:
            # Validate path
            manager = ModelManager()
            is_valid, error = manager.validate_path(path)
            if is_valid:
                self.audio_model_path_edit.setText(path)
            else:
                QMessageBox.warning(self, "Invalid Path", error)

    def browse_audio_output_path(self):
        """Browse for audio output folder."""
        current_path = self.audio_output_path_edit.text()
        if not current_path:
            current_path = str(get_audio_output_dir(self.config_manager))

        path = QFileDialog.getExistingDirectory(
            self, "Select Audio Output Folder", current_path
        )

        if path:
            self.audio_output_path_edit.setText(path)

    def refresh_video_models(self):
        """Refresh list of detected video models."""
        self.video_model_combo.clear()

        # Get video model storage path
        video_storage_path = self.video_model_path_edit.text()
        if not video_storage_path:
            p = get_video_storage_path(self.config_manager)
            video_storage_path = str(p) if p else (self.model_path_edit.text() or default_hf_cache_suggestion() or "")

        if video_storage_path:
            try:
                manager = ModelManager(video_storage_path)
                models = manager.get_available_diffusers_models()

                # Filter for video models
                video_models = [
                    m for m in models if "stable-video-diffusion" in m.lower()
                ]

                if video_models:
                    # Add detected video models
                    for model in video_models:
                        self.video_model_combo.addItem(model)

                    # Add separator if we have detected models
                    if video_models:
                        self.video_model_combo.insertSeparator(len(video_models))

                # Add common video models that might not be detected yet
                common_video_models = [
                    "stabilityai/stable-video-diffusion-img2vid",
                    "stabilityai/stable-video-diffusion-img2vid-xt",
                ]

                for model in common_video_models:
                    if model not in video_models:
                        self.video_model_combo.addItem(model)
            except Exception as e:
                print(f"Error detecting video models: {e}")
                # Add default models on error
                self.video_model_combo.addItems(
                    [
                        "stabilityai/stable-video-diffusion-img2vid",
                        "stabilityai/stable-video-diffusion-img2vid-xt",
                    ]
                )
        else:
            # No storage path, add default models
            self.video_model_combo.addItems(
                [
                    "stabilityai/stable-video-diffusion-img2vid",
                    "stabilityai/stable-video-diffusion-img2vid-xt",
                ]
            )

    def refresh_image_models(self):
        """Refresh list of detected image models."""
        self.image_model_combo.clear()

        # Get storage path
        storage_path = self.model_path_edit.text()
        if not storage_path:
            storage_path = self.config_manager.get("models.storage_path")

        if storage_path:
            try:
                manager = ModelManager(storage_path)
                models = manager.get_available_diffusers_models()

                if models:
                    # Add detected models
                    for model in models:
                        self.image_model_combo.addItem(model)

                    # Add separator
                    self.image_model_combo.insertSeparator(len(models))

                    # Add common models that might not be detected yet
                    common_models = [
                        "stabilityai/stable-diffusion-xl-base-1.0",
                        "stabilityai/stable-diffusion-2-1-base",
                        "runwayml/stable-diffusion-v1-5",
                        "stabilityai/stable-diffusion-x4-upscaler",
                    ]

                    for model in common_models:
                        if model not in models:
                            self.image_model_combo.addItem(model)
                else:
                    # No models detected, add common ones
                    self.image_model_combo.addItems(
                        [
                            "stabilityai/stable-diffusion-xl-base-1.0",
                            "stabilityai/stable-diffusion-2-1-base",
                            "runwayml/stable-diffusion-v1-5",
                            "stabilityai/stable-diffusion-x4-upscaler",
                        ]
                    )
            except Exception as e:
                print(f"Error detecting models: {e}")
                # Add default models on error
                self.image_model_combo.addItems(
                    [
                        "stabilityai/stable-diffusion-xl-base-1.0",
                        "stabilityai/stable-diffusion-2-1-base",
                        "runwayml/stable-diffusion-v1-5",
                    ]
                )

    def refresh_lora_models(self):
        """Refresh list of detected LoRA models."""
        self.lora_combo.clear()
        self.lora_combo.addItem("None (No LoRA)")

        storage_path = self.model_path_edit.text()
        if not storage_path:
            p = get_models_storage_path(self.config_manager)
            storage_path = str(p) if p else None

        if storage_path:
            try:
                manager = ModelManager(storage_path)
                models = manager.detect_existing_models()

                if models["loras"]:
                    for lora in models["loras"]:
                        self.lora_combo.addItem(lora["display"])

                # Restore selection if still available
                current_selection = getattr(self, "_last_lora_selection", None)
                if current_selection and current_selection != "None (No LoRA)":
                    index = self.lora_combo.findText(current_selection)
                    if index >= 0:
                        self.lora_combo.setCurrentIndex(index)
            except Exception as e:
                print(f"Error detecting LoRA models: {e}")

    def on_lora_changed(self, lora_name: str):
        """Handle LoRA selection change - update info display."""
        if not hasattr(self, "lora_info_label"):
            return

        if not lora_name or lora_name == "None (No LoRA)":
            self.lora_info_label.setText("Select a LoRA model to view its information.")
            self.lora_info_edit.setPlainText("")
            self.lora_info_edit.setEnabled(False)
            self.save_lora_info_btn.setEnabled(False)
            self._current_lora_identifier = None
            return

        # Save current selection
        self._last_lora_selection = lora_name

        # Get storage path
        storage_path = self.model_path_edit.text()
        if not storage_path:
            storage_path = self.config_manager.get("models.storage_path")

        if storage_path:
            try:
                manager = ModelManager(storage_path)
                models = manager.detect_existing_models()

                # Find selected LoRA
                for lora in models.get("loras", []):
                    if lora["display"] == lora_name or lora["name"] == lora_name:
                        # Store current LoRA identifier for saving
                        self._current_lora_identifier = lora[
                            "path"
                        ]  # Use path as unique identifier

                        # Display LoRA info
                        info_text = f"<b>Name:</b> {lora['display']}<br>"
                        info_text += f"<b>File:</b> {Path(lora['path']).name}<br>"
                        info_text += f"<b>Path:</b> {lora['path']}<br>"

                        # Load saved info from config
                        saved_info = self.config_manager.get_lora_info(lora["path"])
                        if saved_info:
                            info_text += (
                                f"<br><b>Saved Information:</b><br>{saved_info}"
                            )
                        elif "info" in lora and lora["info"]:
                            info_text += f"<br><b>Information:</b><br>{lora['info']}"
                        else:
                            info_text += (
                                "<br><i>No additional information available.</i>"
                            )

                        self.lora_info_label.setText(info_text)

                        # Load saved info into edit field
                        if saved_info:
                            self.lora_info_edit.setPlainText(saved_info)
                        else:
                            self.lora_info_edit.setPlainText("")

                        # Enable editing
                        self.lora_info_edit.setEnabled(True)
                        self.save_lora_info_btn.setEnabled(True)
                        return

                # LoRA not found - disable editing
                self.lora_info_label.setText(f"LoRA '{lora_name}' not found.")
                self.lora_info_edit.setPlainText("")
                self.lora_info_edit.setEnabled(False)
                self.save_lora_info_btn.setEnabled(False)
                self._current_lora_identifier = None

                # LoRA not found
                self.lora_info_label.setText(f"LoRA '{lora_name}' not found.")
            except Exception as e:
                print(f"Error loading LoRA info: {e}")
                self.lora_info_label.setText(
                    f"Error loading LoRA information: {str(e)}"
                )
                self.lora_info_edit.setPlainText("")
                self.lora_info_edit.setEnabled(False)
                self.save_lora_info_btn.setEnabled(False)
                self._current_lora_identifier = None
        else:
            # No storage path - disable editing
            self.lora_info_edit.setPlainText("")
            self.lora_info_edit.setEnabled(False)
            self.save_lora_info_btn.setEnabled(False)
            self._current_lora_identifier = None

    def save_lora_info(self):
        """Save LoRA information to config."""
        if (
            not hasattr(self, "_current_lora_identifier")
            or not self._current_lora_identifier
        ):
            QMessageBox.warning(
                self, "No LoRA Selected", "Please select a LoRA model first."
            )
            return

        info_text = self.lora_info_edit.toPlainText().strip()

        # Save to config
        self.config_manager.set_lora_info(self._current_lora_identifier, info_text)
        self.config_manager.save_config()

        # Update display
        self.on_lora_changed(self.lora_combo.currentText())

        QMessageBox.information(
            self, "Information Saved", f"Information for LoRA model has been saved."
        )

    def add_custom_model(self):
        """Add a custom model name to the combo box."""
        from PySide6.QtWidgets import QInputDialog

        text, ok = QInputDialog.getText(
            self,
            "Custom Model",
            "Enter model name or path (e.g., stabilityai/stable-diffusion-xl-base-1.0 or C:\\models\\model.safetensors):",
            text="",
        )

        if ok and text:
            # Check if already exists
            index = self.image_model_combo.findText(text)
            if index >= 0:
                self.image_model_combo.setCurrentIndex(index)
            else:
                # Add to combo and select it
                self.image_model_combo.addItem(text)
                self.image_model_combo.setCurrentText(text)
            self.update_preset_info()

    def show_model_info(self):
        """Show/edit model information and preset dialog."""
        model_id = self.image_model_combo.currentText()
        if not model_id:
            QMessageBox.warning(self, "No Model", "Please select a model first.")
            return

        preset = self.config_manager.get_model_preset(model_id)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Model Info: {model_id}")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(400)

        layout = QVBoxLayout()

        # Model ID (read-only)
        model_id_layout = QFormLayout()
        model_id_label = QLabel(model_id)
        model_id_label.setWordWrap(True)
        model_id_label.setStyleSheet("color: #aaa; padding: 4px;")
        model_id_layout.addRow("Model ID:", model_id_label)
        layout.addLayout(model_id_layout)

        # Name
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Enter display name for this model")
        if preset:
            name_edit.setText(preset.get("name", ""))
        name_layout = QFormLayout()
        name_layout.addRow("Display Name:", name_edit)
        layout.addLayout(name_layout)

        # Description
        desc_edit = QTextEdit()
        desc_edit.setPlaceholderText("Enter description of this model...")
        desc_edit.setMaximumHeight(80)
        if preset:
            desc_edit.setPlainText(preset.get("description", ""))
        desc_layout = QFormLayout()
        desc_layout.addRow("Description:", desc_edit)
        layout.addLayout(desc_layout)

        # Info URL
        url_edit = QLineEdit()
        url_edit.setPlaceholderText(
            "https://huggingface.co/... or https://civitai.com/..."
        )
        if preset:
            url_edit.setText(preset.get("info_url", ""))
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Info URL:"))
        url_layout.addWidget(url_edit, stretch=1)
        open_url_btn = QPushButton("🌐 Open")
        open_url_btn.setEnabled(bool(url_edit.text()))

        def open_url():
            url = url_edit.text()
            if url:
                QDesktopServices.openUrl(url)

        open_url_btn.clicked.connect(open_url)
        url_edit.textChanged.connect(
            lambda: open_url_btn.setEnabled(bool(url_edit.text()))
        )
        url_layout.addWidget(open_url_btn)
        layout.addLayout(url_layout)

        # Preset settings preview
        preset_group = QGroupBox("Preset Settings")
        preset_layout = QFormLayout()

        preset_width_label = QLabel(
            str(preset.get("width", "N/A")) if preset else "N/A"
        )
        preset_layout.addRow("Width:", preset_width_label)

        preset_height_label = QLabel(
            str(preset.get("height", "N/A")) if preset else "N/A"
        )
        preset_layout.addRow("Height:", preset_height_label)

        preset_steps_label = QLabel(
            str(preset.get("steps", "N/A")) if preset else "N/A"
        )
        preset_layout.addRow("Steps:", preset_steps_label)

        preset_guidance_label = QLabel(
            str(preset.get("guidance_scale", "N/A")) if preset else "N/A"
        )
        preset_layout.addRow("Guidance Scale:", preset_guidance_label)

        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_btn = QPushButton("Save Info")
        MaterialIcons.apply_to_button(save_btn, MaterialIcons.SAVE_SVG, size=18)
        save_btn.clicked.connect(
            lambda: self.save_model_info(
                dialog,
                model_id,
                name_edit.text(),
                desc_edit.toPlainText(),
                url_edit.text(),
            )
        )
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec()

    def save_model_info(self, dialog, model_id, name, description, info_url):
        """Save model information."""
        preset = self.config_manager.get_model_preset(model_id) or {}

        # Update preset with info
        preset["name"] = (
            name if name else model_id.split("/")[-1] if "/" in model_id else model_id
        )
        preset["description"] = description
        preset["info_url"] = info_url

        # Preserve existing settings if preset exists
        if not preset.get("width"):
            preset["width"] = self.image_width_spin.value()
        if not preset.get("height"):
            preset["height"] = self.image_height_spin.value()
        if not preset.get("steps"):
            preset["steps"] = self.image_steps_spin.value()
        if not preset.get("guidance_scale"):
            preset["guidance_scale"] = self.image_guidance_spin.value()
        if not preset.get("negative_prompt"):
            preset["negative_prompt"] = self.negative_prompt_edit.toPlainText()

        self.config_manager.set_model_preset(model_id, preset)
        self.update_preset_info()
        dialog.accept()
        QMessageBox.information(self, "Saved", "Model information saved successfully.")

    def update_preset_info(self):
        """Update preset info label based on current model selection."""
        model_id = self.image_model_combo.currentText()
        if not model_id:
            self.preset_info_label.setText("No model selected")
            self.reset_preset_btn.setEnabled(False)
            self.delete_preset_btn.setEnabled(False)
            return

        preset = self.config_manager.get_model_preset(model_id)
        if preset:
            name = preset.get("name", model_id)
            desc = preset.get("description", "")
            info = f"<b>{name}</b>"
            if desc:
                info += f"<br>{desc}"
            info += f"<br><small>Width: {preset.get('width', 'N/A')} × Height: {preset.get('height', 'N/A')} | Steps: {preset.get('steps', 'N/A')} | Guidance: {preset.get('guidance_scale', 'N/A')}</small>"
            self.preset_info_label.setText(info)
            self.reset_preset_btn.setEnabled(True)
            self.delete_preset_btn.setEnabled(True)
        else:
            self.preset_info_label.setText(
                f"No preset saved for <b>{model_id}</b><br><small>Configure settings and click 'Save Current Settings as Preset' to create one.</small>"
            )
            self.reset_preset_btn.setEnabled(False)
            self.delete_preset_btn.setEnabled(False)

    def save_current_preset(self):
        """Save current settings as preset for selected model."""
        model_id = self.image_model_combo.currentText()
        if not model_id:
            QMessageBox.warning(self, "No Model", "Please select a model first.")
            return

        preset = {
            "name": model_id.split("/")[-1] if "/" in model_id else model_id,
            "width": self.image_width_spin.value(),
            "height": self.image_height_spin.value(),
            "steps": self.image_steps_spin.value(),
            "guidance_scale": self.image_guidance_spin.value(),
            "negative_prompt": self.negative_prompt_edit.toPlainText(),
            "info_url": "",
            "description": "",
            "type": (
                "xl"
                if "xl" in model_id.lower() or self.image_width_spin.value() >= 1024
                else "base"
            ),
        }

        # Preserve existing info if preset exists
        existing = self.config_manager.get_model_preset(model_id)
        if existing:
            preset["name"] = existing.get("name", preset["name"])
            preset["info_url"] = existing.get("info_url", "")
            preset["description"] = existing.get("description", "")

        self.config_manager.set_model_preset(model_id, preset)
        self.update_preset_info()
        QMessageBox.information(self, "Preset Saved", f"Preset saved for {model_id}")

    def reset_to_preset(self):
        """Reset current settings to saved preset."""
        model_id = self.image_model_combo.currentText()
        if not model_id:
            return

        preset = self.config_manager.get_model_preset(model_id)
        if not preset:
            QMessageBox.warning(self, "No Preset", "No preset found for this model.")
            return

        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset current settings to saved preset?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.image_width_spin.setValue(preset.get("width", 1024))
            self.image_height_spin.setValue(preset.get("height", 1024))
            self.image_steps_spin.setValue(preset.get("steps", 50))
            self.image_guidance_spin.setValue(preset.get("guidance_scale", 7.5))
            self.negative_prompt_edit.setPlainText(preset.get("negative_prompt", ""))
            QMessageBox.information(self, "Reset", "Settings reset to preset values.")

    def delete_preset(self):
        """Delete preset for selected model."""
        model_id = self.image_model_combo.currentText()
        if not model_id:
            return

        preset = self.config_manager.get_model_preset(model_id)
        if not preset:
            QMessageBox.warning(self, "No Preset", "No preset found for this model.")
            return

        reply = QMessageBox.question(
            self,
            "Delete Preset",
            f"Delete preset for {model_id}?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.config_manager.delete_model_preset(model_id)
            self.update_preset_info()
            QMessageBox.information(self, "Deleted", "Preset deleted successfully.")

    def on_model_changed(self, model_id: str):
        """Handle model selection change - update preset info and auto-apply if enabled."""
        self.update_preset_info()

        # Auto-apply preset if enabled
        if self.auto_apply_check.isChecked():
            preset = self.config_manager.get_model_preset(model_id)
            if preset:
                self.image_width_spin.setValue(preset.get("width", 1024))
                self.image_height_spin.setValue(preset.get("height", 1024))
                self.image_steps_spin.setValue(preset.get("steps", 50))
                self.image_guidance_spin.setValue(preset.get("guidance_scale", 7.5))
                self.negative_prompt_edit.setPlainText(
                    preset.get("negative_prompt", "")
                )

    def load_settings(self):
        """Load settings from config."""
        # General
        theme = self.config_manager.get("ui.theme", "dark")
        self.theme_combo.setCurrentText(theme)

        # Global shortcuts
        shortcuts_enabled = self.config_manager.get("shortcuts.global.enabled", True)
        self.global_shortcuts_check.setChecked(shortcuts_enabled)

        tts_key = self.config_manager.get("shortcuts.global.tts", "f9")
        image_key = self.config_manager.get("shortcuts.global.image", "f10")
        # Show the exact strings (uppercased just for display)
        self.tts_shortcut_edit.setText((tts_key or "f9").upper())
        self.image_shortcut_edit.setText((image_key or "f10").upper())

        # Ollama
        ollama_url = self.config_manager.get(
            "ollama.base_url", "http://localhost:11434"
        )
        self.ollama_url_edit.setText(ollama_url)

        default_model = self.config_manager.get("ollama.default_model", "llama3.2")
        self.default_model_edit.setText(default_model)

        auto_start = self.config_manager.get("ollama.auto_start", False)
        self.auto_start_check.setChecked(auto_start)

        tools_enabled = self.config_manager.get("ollama.tools.enabled", False)
        self.tools_enabled_check.setChecked(tools_enabled)

        # Get current model from parent (MainWindow) if available
        current_model = None
        if self.parent() and hasattr(self.parent(), "_current_model"):
            current_model = self.parent()._current_model

        # If no current model, use default model
        if not current_model:
            current_model = self.config_manager.get("ollama.default_model", "llama3.2")

        # Try to load model-specific settings first
        model_settings = self.config_manager.get_llm_model_setting(current_model)

        # LLM Parameters - use model-specific or fall back to global defaults
        if model_settings and "llm_params" in model_settings:
            llm_params = model_settings["llm_params"]
            num_ctx = llm_params.get(
                "num_ctx", self.config_manager.get("ollama.llm_params.num_ctx", 4096)
            )
            temperature = llm_params.get(
                "temperature",
                self.config_manager.get("ollama.llm_params.temperature", 0.7),
            )
            top_p = llm_params.get(
                "top_p", self.config_manager.get("ollama.llm_params.top_p", 0.9)
            )
            top_k = llm_params.get(
                "top_k", self.config_manager.get("ollama.llm_params.top_k", 40)
            )
            repeat_penalty = llm_params.get(
                "repeat_penalty",
                self.config_manager.get("ollama.llm_params.repeat_penalty", 1.1),
            )
            num_predict = llm_params.get(
                "num_predict",
                self.config_manager.get("ollama.llm_params.num_predict", -1),
            )
        else:
            # Use global defaults
            num_ctx = self.config_manager.get("ollama.llm_params.num_ctx", 4096)
            temperature = self.config_manager.get("ollama.llm_params.temperature", 0.7)
            top_p = self.config_manager.get("ollama.llm_params.top_p", 0.9)
            top_k = self.config_manager.get("ollama.llm_params.top_k", 40)
            repeat_penalty = self.config_manager.get(
                "ollama.llm_params.repeat_penalty", 1.1
            )
            num_predict = self.config_manager.get("ollama.llm_params.num_predict", -1)

        self.context_window_spin.setValue(num_ctx)
        self.temperature_spin.setValue(temperature)
        self.top_p_spin.setValue(top_p)
        self.top_k_spin.setValue(top_k)
        self.repeat_penalty_spin.setValue(repeat_penalty)
        self.max_tokens_spin.setValue(num_predict)

        # Conversation Settings - use model-specific or fall back to global defaults
        if model_settings and "conversation" in model_settings:
            conv_settings = model_settings["conversation"]
            system_prompt = conv_settings.get(
                "system_prompt",
                self.config_manager.get(
                    "ollama.conversation.system_prompt",
                    "You are a helpful AI assistant.",
                ),
            )
            max_history = conv_settings.get(
                "max_history_messages",
                self.config_manager.get("ollama.conversation.max_history_messages", 20),
            )
            use_explicit = conv_settings.get(
                "use_explicit_history",
                self.config_manager.get(
                    "ollama.conversation.use_explicit_history", False
                ),
            )
        else:
            # Use global defaults
            system_prompt = self.config_manager.get(
                "ollama.conversation.system_prompt", "You are a helpful AI assistant."
            )
            max_history = self.config_manager.get(
                "ollama.conversation.max_history_messages", 20
            )
            use_explicit = self.config_manager.get(
                "ollama.conversation.use_explicit_history", False
            )

        self.system_prompt_edit.setPlainText(system_prompt)
        self.max_history_spin.setValue(max_history)
        self.explicit_history_check.setChecked(use_explicit)

        # Models
        model_path = self.config_manager.get("models.storage_path")
        if model_path:
            self.model_path_edit.setText(model_path)

        auto_download = self.config_manager.get("models.auto_download", False)
        self.auto_download_check.setChecked(auto_download)

        # TTS
        tts_enabled = self.config_manager.get("tts.enabled", True)
        self.tts_enabled_check.setChecked(tts_enabled)

        # TTS Engine
        engine = self.config_manager.get("tts.engine", "kokoro")
        engine_text = "Kokoro-82M" if engine == "kokoro" else "Pocket TTS"
        index = self.tts_engine_combo.findText(engine_text)
        if index >= 0:
            self.tts_engine_combo.setCurrentIndex(index)
        
        # Trigger engine change to update UI
        self.on_tts_engine_changed(engine_text)

        # Language code
        lang_code = self.config_manager.get("tts.lang_code", "a")
        lang_map = {
            "a": "American English (a)",
            "b": "British English (b)",
            "e": "Spanish (e)",
            "f": "French (f)",
            "h": "Hindi (h)",
            "i": "Italian (i)",
            "j": "Japanese (j)",
            "p": "Brazilian Portuguese (p)",
            "z": "Mandarin Chinese (z)",
        }
        lang_text = lang_map.get(lang_code, "American English (a)")
        index = self.lang_code_combo.findText(lang_text)
        if index >= 0:
            self.lang_code_combo.setCurrentIndex(index)
            # Update voices for selected language
            self.update_voices_for_language(lang_code)

        # Voice (after voices are loaded for language)
        voice = self.config_manager.get("tts.voice", "af_heart")
        index = self.voice_combo.findText(voice)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)

        # Speed
        speed = self.config_manager.get("tts.speed", 1.0)
        self.speed_spin.setValue(speed)

        # Auto-speak
        auto_speak = self.config_manager.get("tts.auto_speak", False)
        self.auto_speak_check.setChecked(auto_speak)

        # Voice Cloning (Pocket TTS)
        voice_cloning_enabled = self.config_manager.get("tts.voice_cloning.enabled", False)
        self.voice_cloning_enabled_check.setChecked(voice_cloning_enabled)
        
        voice_cloning_file = self.config_manager.get("tts.voice_cloning.file_path", None)
        if voice_cloning_file:
            self.voice_cloning_file_edit.setText(voice_cloning_file)

        # RAG/Semantic Memory settings
        rag_enabled = self.config_manager.get("rag.enabled", False)
        self.rag_enabled_check.setChecked(rag_enabled)

        embedding_model = self.config_manager.get(
            "rag.embedding_model", "nomic-embed-text:v1.5"
        )
        # For editable combo, we can just set the text directly
        # It will add to list if not present, or select existing item
        if hasattr(self, "embedding_model_combo"):
            index = self.embedding_model_combo.findText(embedding_model)
            if index >= 0:
                self.embedding_model_combo.setCurrentIndex(index)
            else:
                # If model not in list, set it as current text (editable combo will handle it)
                self.embedding_model_combo.setCurrentText(embedding_model)

        rag_force_cpu = self.config_manager.get("rag.force_cpu", True)
        self.rag_force_cpu_check.setChecked(rag_force_cpu)

        # Manual-only embedding enforced (ignore any legacy config).
        if hasattr(self, "rag_auto_embed_check"):
            self.rag_auto_embed_check.setChecked(False)

        # Show prompt preview option
        show_preview = self.config_manager.get("rag.show_prompt_preview", False)
        if hasattr(self, "show_prompt_preview_check"):
            self.show_prompt_preview_check.setChecked(show_preview)

        # Manual memory settings
        manual_min = self.config_manager.get("rag.manual_min_memories", 3)
        if hasattr(self, "manual_min_memories_spin"):
            self.manual_min_memories_spin.setValue(int(manual_min))

        memory_top_k = self.config_manager.get("rag.memory_top_k", 3)
        if hasattr(self, "memory_top_k_spin"):
            self.memory_top_k_spin.setValue(int(memory_top_k))

        memory_max_chars = self.config_manager.get("rag.memory_max_chars", 1200)
        if hasattr(self, "memory_max_chars_spin"):
            self.memory_max_chars_spin.setValue(int(memory_max_chars))

        memory_min_sim = self.config_manager.get("rag.memory_min_similarity", 0.0)
        if hasattr(self, "memory_min_similarity_spin"):
            self.memory_min_similarity_spin.setValue(float(memory_min_sim))

        # Speed
        speed = self.config_manager.get("tts.speed", 1.0)
        self.speed_spin.setValue(speed)

        auto_speak = self.config_manager.get("tts.auto_speak", False)
        self.auto_speak_check.setChecked(auto_speak)

        # Image Generation
        image_enabled = self.config_manager.get("image_gen.enabled", False)
        self.image_enabled_check.setChecked(image_enabled)

        # Load image models - just add defaults, skip filesystem scan for speed
        # User can click Refresh button if needed
        if self.image_model_combo.count() == 0:
            common_models = [
                "stabilityai/stable-diffusion-xl-base-1.0",
                "stabilityai/stable-diffusion-2-1-base",
                "runwayml/stable-diffusion-v1-5",
                "stabilityai/stable-diffusion-x4-upscaler",
            ]
            self.image_model_combo.addItems(common_models)

        image_model = self.config_manager.get(
            "image_gen.model", "stabilityai/stable-diffusion-xl-base-1.0"
        )
        # Try to find in combo, otherwise add as custom item first
        index = self.image_model_combo.findText(image_model)
        if index >= 0:
            self.image_model_combo.setCurrentIndex(index)
        else:
            # Add the model as an item first, then select it
            self.image_model_combo.addItem(image_model)
            index = self.image_model_combo.findText(image_model)
            if index >= 0:
                self.image_model_combo.setCurrentIndex(index)

        image_width = self.config_manager.get("image_gen.width", 1024)
        self.image_width_spin.setValue(image_width)

        image_height = self.config_manager.get("image_gen.height", 1024)
        self.image_height_spin.setValue(image_height)

        image_steps = self.config_manager.get("image_gen.steps", 50)
        self.image_steps_spin.setValue(image_steps)

        image_guidance = self.config_manager.get("image_gen.guidance_scale", 7.5)
        self.image_guidance_spin.setValue(float(image_guidance))

        img2img_strength = self.config_manager.get("image_gen.img2img_strength", 0.75)
        self.img2img_strength_spin.setValue(float(img2img_strength))
        img2img_steps = self.config_manager.get("image_gen.img2img_steps", 30)
        self.img2img_steps_spin.setValue(img2img_steps)

        negative_prompt = self.config_manager.get("image_gen.negative_prompt", "")
        self.negative_prompt_edit.setPlainText(negative_prompt)

        # Load and populate LoRA models
        self.refresh_lora_models()

        lora_model = self.config_manager.get("image_gen.lora_model", "None")
        index = self.lora_combo.findText(lora_model)
        if index >= 0:
            self.lora_combo.setCurrentIndex(index)
        else:
            self.lora_combo.setCurrentText(lora_model)

        # Load LoRA weight
        lora_weight = self.config_manager.get("image_gen.lora_weight", 1.0)
        self.lora_weight_spin.setValue(lora_weight)

        # Update LoRA info (after combo is populated)
        if hasattr(self, "lora_combo"):
            self.on_lora_changed(self.lora_combo.currentText())

        # Auto-apply presets
        auto_apply = self.config_manager.get_auto_apply_presets()
        self.auto_apply_check.setChecked(auto_apply)

        # Sequential CPU offload
        use_cpu_offload = self.config_manager.get(
            "image_gen.use_sequential_cpu_offload", True
        )
        self.cpu_offload_check.setChecked(use_cpu_offload)

        # Image output folder
        image_output_path = self.config_manager.get("image_gen.output_path")
        if image_output_path:
            self.image_output_path_edit.setText(image_output_path)

        # Video Generation
        # Load video model storage path
        video_storage_p = get_video_storage_path(self.config_manager)
        video_model_path = str(video_storage_p) if video_storage_p else default_hf_cache_suggestion()
        if video_model_path:
            self.video_model_path_edit.setText(video_model_path)

        # Load video models - just add defaults, skip filesystem scan for speed
        # User can click Refresh button if needed
        if self.video_model_combo.count() == 0:
            common_video_models = [
                "stabilityai/stable-video-diffusion-img2vid",
                "stabilityai/stable-video-diffusion-img2vid-xt",
            ]
            self.video_model_combo.addItems(common_video_models)

        video_model = self.config_manager.get(
            "video_gen.model", "stabilityai/stable-video-diffusion-img2vid"
        )
        # Try to find in combo, otherwise add as custom item first
        index = self.video_model_combo.findText(video_model)
        if index >= 0:
            self.video_model_combo.setCurrentIndex(index)
        else:
            # Add the model as an item first, then select it
            self.video_model_combo.addItem(video_model)
            index = self.video_model_combo.findText(video_model)
            if index >= 0:
                self.video_model_combo.setCurrentIndex(index)

        video_frames = self.config_manager.get("video_gen.num_frames", 14)
        self.video_frames_spin.setValue(video_frames)

        video_steps = self.config_manager.get("video_gen.steps", 25)
        self.video_steps_spin.setValue(video_steps)

        video_motion = self.config_manager.get("video_gen.motion_bucket_id", 127)
        self.video_motion_spin.setValue(video_motion)

        video_fps = self.config_manager.get("video_gen.fps", 7)
        self.video_fps_spin.setValue(video_fps)

        video_resolution = self.config_manager.get("video_gen.resolution", "auto")
        if video_resolution == "auto":
            self.video_resolution_combo.setCurrentIndex(0)
        elif video_resolution == "576x1024":
            self.video_resolution_combo.setCurrentIndex(1)
        elif video_resolution == "1024x576":
            self.video_resolution_combo.setCurrentIndex(2)
        else:
            self.video_resolution_combo.setCurrentIndex(0)  # Default to auto

        # Video output folder
        video_output_path = self.config_manager.get("video_gen.output_path")
        if video_output_path:
            self.video_output_path_edit.setText(video_output_path)

        self.video_cpu_offload_check.setChecked(
            self.config_manager.get("video_gen.use_sequential_cpu_offload", True)
        )

        # Audio Generation
        # Load audio model storage path
        audio_storage_p = get_audio_storage_path(self.config_manager)
        audio_model_path = str(audio_storage_p) if audio_storage_p else default_hf_cache_suggestion()
        if audio_model_path:
            self.audio_model_path_edit.setText(audio_model_path)

        audio_model = self.config_manager.get(
            "audio_gen.model", "stabilityai/stable-audio-open-1.0"
        )
        # Try to find in combo, otherwise add as custom
        index = self.audio_model_combo.findText(audio_model)
        if index >= 0:
            self.audio_model_combo.setCurrentIndex(index)
        else:
            # Add as custom entry
            self.audio_model_combo.setCurrentText(audio_model)

        audio_length = self.config_manager.get("audio_gen.audio_length", 10.0)
        self.audio_length_spin.setValue(audio_length)

        audio_steps = self.config_manager.get("audio_gen.steps", 200)
        self.audio_steps_spin.setValue(audio_steps)

        audio_guidance = self.config_manager.get("audio_gen.guidance_scale", 7.0)
        self.audio_guidance_spin.setValue(audio_guidance)

        audio_negative_prompt = self.config_manager.get(
            "audio_gen.negative_prompt", "Low quality."
        )
        self.audio_negative_prompt_edit.setText(audio_negative_prompt)

        num_waveforms = self.config_manager.get("audio_gen.num_waveforms_per_prompt", 1)
        self.audio_num_waveforms_spin.setValue(num_waveforms)

        # Audio output folder
        audio_output_path = self.config_manager.get("audio_gen.output_folder")
        if audio_output_path:
            self.audio_output_path_edit.setText(audio_output_path)

        self.audio_cpu_offload_check.setChecked(
            self.config_manager.get("audio_gen.use_sequential_cpu_offload", False)
        )

        # Update preset info
        self.update_preset_info()

        # Load prompts
        if hasattr(self, "prompts_list"):
            self.prompts_list.clear()
            prompts = self.config_manager.get_prompts()
            for prompt_data in prompts:
                if isinstance(prompt_data, dict) and "name" in prompt_data:
                    item = QListWidgetItem(prompt_data["name"])
                    item.setData(Qt.ItemDataRole.UserRole, prompt_data)
                    self.prompts_list.addItem(item)

        # ASR
        if hasattr(self, "asr_enabled_check"):
            asr_enabled = self.config_manager.get("asr.enabled", False)
            self.asr_enabled_check.setChecked(asr_enabled)

            asr_model = self.config_manager.get("asr.model", "nvidia/nemotron-speech-streaming-en-0.6b")
            index = self.asr_model_combo.findText(asr_model)
            if index >= 0:
                self.asr_model_combo.setCurrentIndex(index)

            chunk_size_ms = self.config_manager.get("asr.chunk_size_ms", 560)
            chunk_size_map_reverse = {
                80: "80ms (Lowest latency)",
                160: "160ms (Low latency)",
                560: "560ms (Balanced)",
                1120: "1120ms (Highest accuracy)"
            }
            chunk_size_text = chunk_size_map_reverse.get(chunk_size_ms, "560ms (Balanced)")
            index = self.chunk_size_combo.findText(chunk_size_text)
            if index >= 0:
                self.chunk_size_combo.setCurrentIndex(index)

            # Device selection
            asr_device = self.config_manager.get("asr.device", "cpu")
            if asr_device.lower() == "cuda" or asr_device.lower() == "gpu":
                self.asr_device_combo.setCurrentIndex(1)  # GPU
            else:
                self.asr_device_combo.setCurrentIndex(0)  # CPU (default)

            asr_lang = self.config_manager.get("asr.language", "en")
            # Handle both "en" and "English" formats
            if asr_lang.lower() in ["english", "en"]:
                lang_text = "English (en)"
            else:
                lang_text = f"{asr_lang.capitalize()} ({asr_lang})"
            index = self.asr_language_combo.findText(lang_text)
            if index >= 0:
                self.asr_language_combo.setCurrentIndex(index)

            self.punctuation_check.setChecked(self.config_manager.get("asr.punctuation_capitalization", True))

            # Microphone device
            mic_device = self.config_manager.get("asr.microphone_device")
            if mic_device is not None:
                # Find device by data
                for i in range(self.mic_device_combo.count()):
                    if self.mic_device_combo.itemData(i) == mic_device:
                        self.mic_device_combo.setCurrentIndex(i)
                        break

    def save_settings(self):
        """Save settings to config."""
        # General
        self.config_manager.set("ui.theme", self.theme_combo.currentText())

        # Global shortcuts
        self.config_manager.set(
            "shortcuts.global.enabled", self.global_shortcuts_check.isChecked()
        )
        # Store keys in lowercase form (keyboard library expects this format)
        tts_key = (self.tts_shortcut_edit.text() or "F9").strip().lower()
        image_key = (self.image_shortcut_edit.text() or "F10").strip().lower()
        self.config_manager.set("shortcuts.global.tts", tts_key)
        self.config_manager.set("shortcuts.global.image", image_key)

        # Ollama
        self.config_manager.set("ollama.base_url", self.ollama_url_edit.text())
        self.config_manager.set("ollama.default_model", self.default_model_edit.text())
        self.config_manager.set("ollama.auto_start", self.auto_start_check.isChecked())
        self.config_manager.set("ollama.tools.enabled", self.tools_enabled_check.isChecked())

        # Get current model from parent (MainWindow) if available
        current_model = None
        if self.parent() and hasattr(self.parent(), "_current_model"):
            current_model = self.parent()._current_model

        # If no current model, use default model
        if not current_model:
            current_model = self.config_manager.get("ollama.default_model", "llama3.2")

        # Save LLM Parameters - save to model-specific settings if model is set
        llm_params = {
            "num_ctx": self.context_window_spin.value(),
            "temperature": self.temperature_spin.value(),
            "top_p": self.top_p_spin.value(),
            "top_k": self.top_k_spin.value(),
            "repeat_penalty": self.repeat_penalty_spin.value(),
            "num_predict": self.max_tokens_spin.value(),
        }

        # Conversation Settings
        conversation_settings = {
            "system_prompt": self.system_prompt_edit.toPlainText(),
            "max_history_messages": self.max_history_spin.value(),
            "use_explicit_history": self.explicit_history_check.isChecked(),
        }

        # Save to model-specific settings
        model_settings = {
            "llm_params": llm_params,
            "conversation": conversation_settings,
        }
        self.config_manager.set_llm_model_setting(current_model, model_settings)

        # Also save as global defaults (for backward compatibility and new models)
        self.config_manager.set(
            "ollama.llm_params.num_ctx", self.context_window_spin.value()
        )
        self.config_manager.set(
            "ollama.llm_params.temperature", self.temperature_spin.value()
        )
        self.config_manager.set("ollama.llm_params.top_p", self.top_p_spin.value())
        self.config_manager.set("ollama.llm_params.top_k", self.top_k_spin.value())
        self.config_manager.set(
            "ollama.llm_params.repeat_penalty", self.repeat_penalty_spin.value()
        )
        self.config_manager.set(
            "ollama.llm_params.num_predict", self.max_tokens_spin.value()
        )
        self.config_manager.set(
            "ollama.conversation.system_prompt", self.system_prompt_edit.toPlainText()
        )
        self.config_manager.set(
            "ollama.conversation.max_history_messages", self.max_history_spin.value()
        )
        self.config_manager.set(
            "ollama.conversation.use_explicit_history",
            self.explicit_history_check.isChecked(),
        )

        # Models
        model_path = self.model_path_edit.text()
        if model_path:
            manager = ModelManager(model_path)
            is_valid, error = manager.validate_path(model_path)
            if is_valid:
                manager.setup_environment_variables()
                self.config_manager.set("models.storage_path", model_path)
            else:
                QMessageBox.warning(self, "Invalid Path", error)
                return

        self.config_manager.set(
            "models.auto_download", self.auto_download_check.isChecked()
        )

        # TTS
        self.config_manager.set("tts.enabled", self.tts_enabled_check.isChecked())

        # TTS Engine
        engine_text = self.tts_engine_combo.currentText()
        engine = "kokoro" if engine_text == "Kokoro-82M" else "pocket_tts"
        self.config_manager.set("tts.engine", engine)

        # Extract lang_code from combo text (e.g., "American English (a)" -> "a")
        lang_text = self.lang_code_combo.currentText()
        lang_code = lang_text.split("(")[1].split(")")[0] if "(" in lang_text else "a"
        self.config_manager.set("tts.lang_code", lang_code)

        self.config_manager.set("tts.voice", self.voice_combo.currentText())
        self.config_manager.set("tts.speed", self.speed_spin.value())
        self.config_manager.set("tts.auto_speak", self.auto_speak_check.isChecked())

        # Voice Cloning (Pocket TTS)
        self.config_manager.set("tts.voice_cloning.enabled", self.voice_cloning_enabled_check.isChecked())
        self.config_manager.set("tts.voice_cloning.file_path", self.voice_cloning_file_edit.text() or None)

        # RAG/Semantic Memory settings
        self.config_manager.set("rag.enabled", self.rag_enabled_check.isChecked())
        self.config_manager.set(
            "rag.embedding_model", self.embedding_model_combo.currentText()
        )
        self.config_manager.set("rag.force_cpu", self.rag_force_cpu_check.isChecked())
        # Manual-only embedding enforced (never auto-embed).
        self.config_manager.set("rag.auto_embed", False)
        # Show prompt preview option
        if hasattr(self, "show_prompt_preview_check"):
            self.config_manager.set("rag.show_prompt_preview", self.show_prompt_preview_check.isChecked())
        # Manual memory settings
        if hasattr(self, "manual_min_memories_spin"):
            self.config_manager.set(
                "rag.manual_min_memories", self.manual_min_memories_spin.value()
            )
        if hasattr(self, "memory_top_k_spin"):
            self.config_manager.set("rag.memory_top_k", self.memory_top_k_spin.value())
        if hasattr(self, "memory_max_chars_spin"):
            self.config_manager.set(
                "rag.memory_max_chars", self.memory_max_chars_spin.value()
            )
        if hasattr(self, "memory_min_similarity_spin"):
            self.config_manager.set(
                "rag.memory_min_similarity", self.memory_min_similarity_spin.value()
            )

        # Save prompts
        if hasattr(self, "prompts_list"):
            prompts = []
            for i in range(self.prompts_list.count()):
                item = self.prompts_list.item(i)
                prompt_data = item.data(Qt.ItemDataRole.UserRole)
                if prompt_data:
                    prompts.append(prompt_data)
            self.config_manager.save_prompts(prompts)

        # Image Generation
        self.config_manager.set(
            "image_gen.enabled", self.image_enabled_check.isChecked()
        )
        self.config_manager.set("image_gen.model", self.image_model_combo.currentText())
        self.config_manager.set("image_gen.width", self.image_width_spin.value())
        self.config_manager.set("image_gen.height", self.image_height_spin.value())
        self.config_manager.set("image_gen.steps", self.image_steps_spin.value())
        guidance = self.image_guidance_spin.value()
        self.config_manager.set("image_gen.guidance_scale", guidance)
        self.config_manager.set(
            "image_gen.img2img_strength", self.img2img_strength_spin.value()
        )
        self.config_manager.set(
            "image_gen.img2img_steps", self.img2img_steps_spin.value()
        )
        self.config_manager.set(
            "image_gen.negative_prompt", self.negative_prompt_edit.toPlainText()
        )
        self.config_manager.set("image_gen.lora_model", self.lora_combo.currentText())
        self.config_manager.set("image_gen.lora_weight", self.lora_weight_spin.value())
        self.config_manager.set_auto_apply_presets(self.auto_apply_check.isChecked())
        self.config_manager.set(
            "image_gen.use_sequential_cpu_offload", self.cpu_offload_check.isChecked()
        )

        # Save image output path
        image_output_path = self.image_output_path_edit.text()
        if image_output_path:
            self.config_manager.set("image_gen.output_path", image_output_path)

        # Video Generation
        video_model_path = self.video_model_path_edit.text()
        if video_model_path:
            self.config_manager.set("video_gen.storage_path", video_model_path)

        self.config_manager.set("video_gen.model", self.video_model_combo.currentText())
        self.config_manager.set("video_gen.num_frames", self.video_frames_spin.value())
        self.config_manager.set("video_gen.steps", self.video_steps_spin.value())
        self.config_manager.set(
            "video_gen.motion_bucket_id", self.video_motion_spin.value()
        )
        self.config_manager.set("video_gen.fps", self.video_fps_spin.value())

        # Save resolution setting
        resolution_index = self.video_resolution_combo.currentIndex()
        if resolution_index == 0:
            resolution = "auto"
        elif resolution_index == 1:
            resolution = "576x1024"
        else:
            resolution = "1024x576"
        self.config_manager.set("video_gen.resolution", resolution)

        # Save video output path
        video_output_path = self.video_output_path_edit.text()
        if video_output_path:
            self.config_manager.set("video_gen.output_path", video_output_path)

        self.config_manager.set(
            "video_gen.use_sequential_cpu_offload",
            self.video_cpu_offload_check.isChecked(),
        )

        # Audio Generation
        audio_model_path = self.audio_model_path_edit.text()
        if audio_model_path:
            self.config_manager.set("audio_gen.storage_path", audio_model_path)

        self.config_manager.set("audio_gen.model", self.audio_model_combo.currentText())
        self.config_manager.set(
            "audio_gen.audio_length", self.audio_length_spin.value()
        )
        self.config_manager.set("audio_gen.steps", self.audio_steps_spin.value())
        self.config_manager.set(
            "audio_gen.guidance_scale", self.audio_guidance_spin.value()
        )
        self.config_manager.set(
            "audio_gen.negative_prompt", self.audio_negative_prompt_edit.text()
        )
        self.config_manager.set(
            "audio_gen.num_waveforms_per_prompt", self.audio_num_waveforms_spin.value()
        )

        # Save audio output path
        audio_output_path = self.audio_output_path_edit.text()
        if audio_output_path:
            self.config_manager.set("audio_gen.output_folder", audio_output_path)

        self.config_manager.set(
            "audio_gen.use_sequential_cpu_offload",
            self.audio_cpu_offload_check.isChecked(),
        )

        # ASR
        if hasattr(self, "asr_enabled_check"):
            self.config_manager.set("asr.enabled", self.asr_enabled_check.isChecked())
            self.config_manager.set("asr.model", self.asr_model_combo.currentText())

            # Map chunk size text to milliseconds
            chunk_size_text = self.chunk_size_combo.currentText()
            chunk_size_map = {
                "80ms (Lowest latency)": 80,
                "160ms (Low latency)": 160,
                "560ms (Balanced)": 560,
                "1120ms (Highest accuracy)": 1120
            }
            chunk_size_ms = chunk_size_map.get(chunk_size_text, 560)
            self.config_manager.set("asr.chunk_size_ms", chunk_size_ms)

            self.config_manager.set("asr.language", self.asr_language_combo.currentText().split(" ")[0])
            self.config_manager.set("asr.punctuation_capitalization", self.punctuation_check.isChecked())

            # Device selection (CPU/GPU)
            device_text = self.asr_device_combo.currentText()
            if "GPU" in device_text or "CUDA" in device_text:
                self.config_manager.set("asr.device", "cuda")
            else:
                self.config_manager.set("asr.device", "cpu")

            # Microphone device (store index or None)
            mic_device = self.mic_device_combo.currentData()
            self.config_manager.set("asr.microphone_device", mic_device)

        # Save config (only once at the end)
        if self.config_manager.save_config():
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Failed to save settings.")

    def _populate_microphone_devices(self):
        """Populate microphone device dropdown."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            self.mic_device_combo.clear()
            self.mic_device_combo.addItem("Default", None)

            for i, device in enumerate(devices):
                if device.get('max_input_channels', 0) > 0:  # Input device
                    name = device.get('name', f'Device {i}')
                    self.mic_device_combo.addItem(f"{i}: {name}", i)
        except ImportError:
            self.mic_device_combo.addItem("sounddevice not installed", None)
        except Exception as e:
            self.mic_device_combo.addItem(f"Error: {e}", None)

