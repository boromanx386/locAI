"""
Setup Wizard for locAI.
First-run setup wizard to guide users through initial configuration.
"""
from pathlib import Path
from PySide6.QtWidgets import (
    QWizard,
    QWizardPage,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QFileDialog,
    QComboBox,
    QMessageBox,
    QTextBrowser,
)
from PySide6.QtCore import Qt
from lokai.core.config_manager import ConfigManager
from lokai.core.ollama_detector import OllamaDetector
from lokai.utils.model_manager import ModelManager


class WelcomePage(QWizardPage):
    """Welcome page of setup wizard."""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to locAI")
        self.setSubTitle("Let's get you started with your local AI assistant")
        
        layout = QVBoxLayout()
        
        welcome_text = QLabel(
            "locAI is a desktop AI assistant that combines:\n\n"
            "• Large Language Models (via Ollama)\n"
            "• Image Generation (Stable Diffusion)\n"
            "• Text-to-Speech (Local TTS)\n\n"
            "This wizard will help you configure locAI for first use."
        )
        welcome_text.setWordWrap(True)
        welcome_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome_text)
        
        layout.addStretch()
        self.setLayout(layout)


class OllamaCheckPage(QWizardPage):
    """Page for checking Ollama installation."""
    
    def __init__(self, detector: OllamaDetector):
        super().__init__()
        self.detector = detector
        self.setTitle("Ollama Check")
        self.setSubTitle("Checking if Ollama is installed and running")
        
        layout = QVBoxLayout()
        
        self.status_label = QLabel("Checking Ollama...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(200)
        layout.addWidget(self.info_text)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.check_ollama)
        button_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        self.setLayout(layout)
        
        # Check on page show
        self.registerField("ollama_installed", self, "ollamaInstalled")
        self.registerField("ollama_running", self, "ollamaRunning")
    
    def initializePage(self):
        """Called when page is shown."""
        self.check_ollama()
    
    def check_ollama(self):
        """Check Ollama status."""
        # Check installation
        is_installed, install_info = self.detector.check_ollama_installed()
        
        if is_installed:
            self.status_label.setText("✓ Ollama is installed")
            self.status_label.setStyleSheet("color: #51CF66; font-weight: bold;")
            
            # Check if running
            is_running, run_info = self.detector.check_ollama_running()
            
            if is_running:
                models, model_error = self.detector.get_installed_models()
                if models:
                    info = f"Ollama is running!\n\nInstalled models:\n"
                    for model in models:
                        info += f"• {model}\n"
                    self.info_text.setText(info)
                    self.setField("ollama_installed", True)
                    self.setField("ollama_running", True)
                else:
                    self.info_text.setText(
                        "Ollama is running but no models are installed.\n\n"
                        "To install a model, run in terminal:\n"
                        "ollama pull llama3.2"
                    )
                    self.setField("ollama_installed", True)
                    self.setField("ollama_running", True)
            else:
                self.info_text.setText(
                    f"Ollama is installed but not running.\n\n"
                    f"Error: {run_info}\n\n"
                    "Please start Ollama and click Refresh."
                )
                self.setField("ollama_installed", True)
                self.setField("ollama_running", False)
        else:
            self.status_label.setText("✗ Ollama is not installed")
            self.status_label.setStyleSheet("color: #EF5350; font-weight: bold;")
            self.info_text.setText(
                f"{install_info}\n\n"
                "Please install Ollama from https://ollama.com\n\n"
                "After installation, restart this wizard."
            )
            self.setField("ollama_installed", False)
            self.setField("ollama_running", False)
    
    ollamaInstalled = False
    ollamaRunning = False


class OllamaGuidePage(QWizardPage):
    """Page showing Ollama installation guide."""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Ollama Installation Guide")
        self.setSubTitle("How to install Ollama")
        
        layout = QVBoxLayout()
        
        guide_text = QTextBrowser()
        guide_text.setOpenExternalLinks(True)
        guide_text.setHtml("""
        <h3>Installing Ollama</h3>
        <ol>
            <li>Visit <a href="https://ollama.com/download">https://ollama.com/download</a></li>
            <li>Download the installer for Windows</li>
            <li>Run the installer and follow the instructions</li>
            <li>After installation, restart locAI</li>
        </ol>
        
        <h3>Installing Your First Model</h3>
        <p>After Ollama is installed, open a terminal and run:</p>
        <pre>ollama pull llama3.2</pre>
        <p>This will download the Llama 3.2 model (about 2GB).</p>
        
        <h3>Other Popular Models</h3>
        <ul>
            <li><code>ollama pull mistral</code> - Mistral 7B</li>
            <li><code>ollama pull codellama</code> - Code Llama</li>
            <li><code>ollama pull llava</code> - Vision model</li>
        </ul>
        """)
        
        layout.addWidget(guide_text)
        self.setLayout(layout)
    
    def initializePage(self):
        """Only show this page if Ollama is not installed."""
        ollama_installed = self.wizard().field("ollama_installed")
        if ollama_installed:
            self.wizard().next()


class ModelLocationPage(QWizardPage):
    """Page for selecting model storage location."""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Model Storage Location")
        self.setSubTitle("Choose where to store image generation models")
        
        layout = QVBoxLayout()
        
        info_label = QLabel(
            "locAI can generate images using Stable Diffusion models.\n"
            "These models are large (several GB) and need storage space.\n\n"
            "Choose a location with sufficient free space:"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        path_layout = QHBoxLayout()
        self.path_label = QLabel()
        self.path_label.setStyleSheet("border: 1px solid #404040; padding: 8px;")
        path_layout.addWidget(self.path_label, stretch=1)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(self.browse_btn)
        
        layout.addLayout(path_layout)
        
        # Set default path
        default_path = Path.home() / "Documents" / "locAI" / "models"
        self.path_label.setText(str(default_path))
        self.registerField("model_path", self.path_label, "text")
        
        layout.addStretch()
        self.setLayout(layout)
    
    def browse_path(self):
        """Browse for storage path."""
        current_path = self.path_label.text()
        if not current_path:
            current_path = str(Path.home() / "Documents" / "locAI" / "models")
        
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Model Storage Location",
            current_path
        )
        
        if path:
            manager = ModelManager()
            is_valid, error = manager.validate_path(path)
            if is_valid:
                self.path_label.setText(path)
            else:
                QMessageBox.warning(self, "Invalid Path", error)


class ThemeSelectionPage(QWizardPage):
    """Page for theme selection."""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Theme Selection")
        self.setSubTitle("Choose your preferred theme")
        
        layout = QVBoxLayout()
        
        info_label = QLabel("Select a theme for locAI:")
        layout.addWidget(info_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        layout.addWidget(self.theme_combo)
        
        self.registerField("theme", self.theme_combo, "currentText")
        
        layout.addStretch()
        self.setLayout(layout)


class CompletionPage(QWizardPage):
    """Final page of setup wizard."""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Setup Complete")
        self.setSubTitle("You're ready to use locAI!")
        
        layout = QVBoxLayout()
        
        completion_text = QLabel(
            "Setup is complete! You can now:\n\n"
            "• Start chatting with your AI assistant\n"
            "• Generate images (if models are installed)\n"
            "• Use text-to-speech features\n\n"
            "You can change these settings later in Preferences."
        )
        completion_text.setWordWrap(True)
        completion_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(completion_text)
        
        layout.addStretch()
        self.setLayout(layout)


class SetupWizard(QWizard):
    """First-run setup wizard."""
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        Initialize SetupWizard.
        
        Args:
            config_manager: ConfigManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("locAI Setup Wizard")
        self.setMinimumSize(600, 500)
        
        # Initialize detector
        base_url = config_manager.get("ollama.base_url", "http://localhost:11434")
        self.detector = OllamaDetector(base_url)
        
        # Add pages
        self.addPage(WelcomePage())
        self.addPage(OllamaCheckPage(self.detector))
        self.addPage(OllamaGuidePage())
        self.addPage(ModelLocationPage())
        self.addPage(ThemeSelectionPage())
        self.addPage(CompletionPage())
        
        # Connect finish signal
        self.finished.connect(self.on_finished)
    
    def on_finished(self, result: int):
        """Handle wizard completion."""
        if result == QWizard.DialogCode.Accepted:
            # Save settings
            model_path = self.field("model_path")
            if model_path:
                self.config_manager.set("models.storage_path", model_path)
                # Setup environment
                manager = ModelManager(model_path)
                manager.setup_environment_variables()
            
            theme = self.field("theme")
            if theme:
                self.config_manager.set("ui.theme", theme)
            
            # Mark first run as complete
            self.config_manager.set_first_run_complete()
            
            # Save config
            self.config_manager.save_config()

