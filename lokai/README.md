# locAI - Local AI Assistant

locAI is a commercial desktop AI assistant that combines Large Language Models (LLM), Image Generation, and Text-to-Speech (TTS) in one accessible package.

## Features

- **LLM Chat**: Chat with AI models via Ollama (llama3.2, mistral, codellama, and more)
- **Image Generation**: Generate images using Stable Diffusion (optional, requires additional dependencies)
- **Text-to-Speech**: Natural voice synthesis using Edge TTS
- **Modern GUI**: Eye-friendly interface with customizable themes
- **Easy Setup**: First-run wizard guides you through configuration
- **Flexible Configuration**: Customize model storage locations and settings

## Requirements

### Essential
- **Python 3.8+**
- **Ollama**: Must be installed separately from [ollama.com](https://ollama.com/download)
- **PySide6**: GUI framework (installed automatically)

### Optional (for Image Generation)
- **PyTorch**: For Stable Diffusion models
- **CUDA**: For GPU acceleration (recommended)
- **diffusers**: Stable Diffusion library

## Installation

### 1. Install Ollama

**Windows:**
1. Visit [https://ollama.com/download](https://ollama.com/download)
2. Download the Windows installer
3. Run the installer and follow the instructions
4. Verify installation by opening a terminal and running: `ollama --version`

### 2. Install Your First Model

After Ollama is installed, open a terminal and run:

```bash
ollama pull llama3.2
```

This downloads the Llama 3.2 model (approximately 2GB).

**Other popular models:**
- `ollama pull mistral` - Mistral 7B
- `ollama pull codellama` - Code Llama
- `ollama pull llava` - Vision model (for image understanding)

### 3. Install locAI

**Minimal installation (LLM + TTS only):**
```bash
pip install -r requirements-minimal.txt
```

**Full installation (includes Image Generation):**
```bash
pip install -r requirements.txt
```

### 4. Run locAI

```bash
python main.py
```

On first run, the setup wizard will guide you through:
- Ollama detection and verification
- Model storage location configuration
- Theme selection

## Usage

### Starting a Chat

1. Ensure Ollama is running (check the status indicator at the top)
2. Select a model from the dropdown
3. Type your message and press Send
4. The AI response will stream in real-time

### Settings

Access settings via **File > Preferences** or press `Ctrl+,`

**Settings tabs:**
- **General**: Theme, font size, compact mode
- **Ollama**: Base URL, default model, auto-start
- **Models**: Storage path for image generation models
- **TTS**: Voice selection, auto-speak options

### Text-to-Speech

TTS is enabled by default. To use:
- Responses are automatically spoken (if auto-speak is enabled)
- Or use the TTS controls in the chat interface

## Configuration

### Model Storage Location

By default, image generation models are stored in:
- Windows: `Documents/locAI/models`
- Linux/Mac: `~/Documents/locAI/models`

You can change this location in Settings > Models.

### Environment Variables

locAI automatically sets Hugging Face cache environment variables based on your configured model storage path:
- `HF_HOME`
- `TRANSFORMERS_CACHE`
- `HF_DATASETS_CACHE`
- `HF_HUB_CACHE`
- `DIFFUSERS_CACHE`

## Troubleshooting

### Ollama Not Detected

1. Verify Ollama is installed: `ollama --version`
2. Ensure Ollama is in your system PATH
3. Restart locAI after installing Ollama

### Ollama Not Running

1. Start Ollama manually: `ollama serve`
2. Or ensure Ollama service is running (Windows: check Services)
3. Check the status indicator in locAI

### No Models Available

1. Install a model: `ollama pull llama3.2`
2. Click "Refresh" in the status panel
3. Verify models: `ollama list`

### Image Generation Not Working

1. Ensure full requirements are installed: `pip install -r requirements.txt`
2. Check that model storage path has sufficient space (models are several GB)
3. Verify CUDA is available for GPU acceleration (optional but recommended)

## Project Structure

```
lokai/
├── core/           # Core functionality (Ollama, TTS, Image Gen)
├── ui/             # User interface components
├── utils/          # Utility modules
├── config/         # Configuration files
├── resources/       # Resources (icons, guides)
└── main.py         # Entry point
```

## Development

### Running from Source

```bash
# Clone or navigate to project directory
cd lokai

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

### Building

locAI uses PySide6 for the GUI. For distribution:
- Consider using PyInstaller or cx_Freeze for standalone executables
- Include Ollama installation instructions with distribution

## License

[Add your license here]

## Support

For issues, questions, or contributions, please [add your contact/support information].

## Credits

- **Ollama**: [ollama.com](https://ollama.com) - Local LLM runtime
- **Stable Diffusion**: [stability.ai](https://stability.ai) - Image generation
- **Edge TTS**: Microsoft Edge TTS - Text-to-speech
- **PySide6**: Qt for Python - GUI framework

