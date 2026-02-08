# locAI - Local AI Assistant

locAI is a desktop AI assistant that combines Large Language Models (LLM), Image Generation, Video Generation, Audio Generation, Automatic Speech Recognition (ASR), and Text-to-Speech (TTS) in one accessible package.

## Features

- **LLM Chat**: Chat with AI models via Ollama (llama3.2, mistral, codellama, and more)
- **Image Generation**: Generate images using Stable Diffusion (optional, requires additional dependencies)
- **Video Generation**: Create videos from images using Stable Video Diffusion (SVD) - optional
- **Audio Generation**: Generate audio using Stable Audio Open - optional
- **Automatic Speech Recognition (ASR)**: Voice input using NVIDIA Nemotron Speech Streaming - optional
- **Text-to-Speech**: Natural voice synthesis using Kokoro-82M TTS or PocketTTS (with voice cloning support)
- **Modern GUI**: Eye-friendly interface with customizable themes
- **Easy Setup**: First-run wizard guides you through configuration
- **Flexible Configuration**: Customize model storage locations and settings
- **Optimized GPU Memory Management**: Advanced memory management allows running on GPUs with as little as 8GB VRAM, with automatic model unloading and aggressive memory cleanup

## Requirements

### Essential
- **Python 3.8+**
- **Ollama**: Must be installed separately from [ollama.com](https://ollama.com/download)
- **PySide6**: GUI framework (installed automatically)

### Optional (for Image Generation)
- **PyTorch**: For Stable Diffusion models
- **CUDA**: For GPU acceleration (recommended)
- **diffusers**: Stable Diffusion library
- **GPU**: NVIDIA GPU with 8GB+ VRAM recommended (optimized to work efficiently with 8GB)

### TTS Requirements
- **kokoro**: Kokoro-82M TTS engine (optional, for multi-language support)
- **pocket-tts**: PocketTTS engine with voice cloning support (optional)
- **soundfile**: Audio file handling for TTS
- **scipy**: For PocketTTS audio processing

### ASR Requirements (Optional)
- **nemo_toolkit**: NVIDIA NeMo Toolkit for Automatic Speech Recognition
- **sounddevice**: Audio input device interface
- **webrtcvad**: Voice Activity Detection
- **Cython**: Required for NeMo ASR installation

### Video Generation Requirements (Optional)
- **diffusers**: For Stable Video Diffusion models
- **GPU**: NVIDIA GPU with 8GB+ VRAM recommended

### Audio Generation Requirements (Optional)
- **diffusers**: For Stable Audio Open models

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

**Full installation (includes Image Generation):**
```bash
pip install -r requirements.txt
```

**Note:** 
- TTS supports both `kokoro` (multi-language) and `pocket-tts` (voice cloning) engines
- ASR requires `nemo_toolkit` which is installed from source (see requirements.txt)
- All optional dependencies are included in requirements.txt, but can be skipped if you don't need those features

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
- **Models**: Storage path for image/video/audio generation models
- **TTS**: TTS engine selection (Kokoro or PocketTTS), voice selection, voice cloning, auto-speak options
- **ASR**: ASR settings (if available)

### Text-to-Speech

locAI supports two TTS engines:

**Kokoro-82M** (Multi-language support):
- Select language and voice in Settings > TTS
- Supports multiple languages with various voice options
- Voice files are automatically downloaded from Hugging Face

**PocketTTS** (Voice cloning support):
- Select PocketTTS engine in Settings > TTS
- Supports voice cloning from audio samples
- Upload an audio file to clone a voice
- English-only, but excellent quality and cloning capabilities

**TTS Usage:**
- Responses are automatically spoken (if auto-speak is enabled)
- Use the TTS controls (play/pause/stop) in the status panel
- Right-click selected text in chat for "Read with TTS" option
- Use global shortcut F9 to read any selected text in Windows

### Automatic Speech Recognition (ASR)

ASR allows voice input using NVIDIA Nemotron Speech Streaming:
- Enable ASR in settings (requires NeMo toolkit installation)
- Use voice input widget to speak your messages
- Supports real-time speech recognition with low latency
- Configurable chunk sizes for different latency/accuracy trade-offs

### Video Generation

Generate videos from images using Stable Video Diffusion:
- Select an image in the chat or use a generated image
- Choose "Generate Video" option
- Videos are generated with smooth motion from static images
- Optional feature requiring Stable Video Diffusion models

### Audio Generation

Generate audio using Stable Audio Open:
- Enter text prompts to generate audio
- Supports various audio types and styles
- Optional feature requiring Stable Audio models

## Configuration

### Model Storage Location

By default, all models (image, video, audio, ASR, TTS) are stored in:
- Windows: `Documents/locAI/models`
- Linux/Mac: `~/Documents/locAI/models`

You can change this location in Settings > Models. The application automatically organizes models by type:
- Image generation models (Stable Diffusion)
- Video generation models (Stable Video Diffusion)
- Audio generation models (Stable Audio)
- ASR models (NVIDIA Nemotron)
- TTS voice files (Hugging Face cache)

### Environment Variables

locAI automatically sets Hugging Face cache environment variables based on your configured model storage path:
- `HF_HOME`
- `TRANSFORMERS_CACHE`
- `HF_DATASETS_CACHE`
- `HF_HUB_CACHE`
- `DIFFUSERS_CACHE`

## GPU Memory Optimization

locAI is specifically optimized to run efficiently on GPUs with limited VRAM, including systems with only 8GB of GPU memory. Key optimizations include:

- **Automatic Model Unloading**: Models are automatically unloaded from GPU memory after use (LLM, Vision, Image Generation, and TTS)
- **Aggressive Memory Cleanup**: Multiple cache clearing passes and IPC resource collection ensure maximum memory is freed
- **Smart Memory Management**: Models are unloaded when switching between different model types or when switching models
- **Sequential CPU Offload**: Image generation models use sequential CPU offload to minimize VRAM usage
- **Memory Cleanup on Exit**: All GPU memory is properly released when the application closes

This allows you to run powerful local AI models (including vision models and image generation) even on mid-range GPUs like the RTX 2080 with 8GB VRAM.

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
4. If you encounter "CUDA out of memory" errors, the application will automatically unload models to free memory

### GPU Memory Issues

If GPU memory remains high after closing the application:

1. Run the GPU memory cleaner utility: `python lokai/utils/clear_gpu_memory.py`
2. Restart your GPU driver (Device Manager > Display adapters > Disable/Enable)
3. Restart your computer if memory persists

The application is optimized for 8GB+ GPUs, but if you have less VRAM, you may need to:
- Use smaller models
- Unload models manually between tasks
- Use CPU mode for some operations

### TTS Not Working

**For Kokoro-82M:**
1. Ensure `kokoro` and `soundfile` are installed: `pip install kokoro soundfile`
2. Voice files are automatically downloaded to Hugging Face cache on first use
3. Default cache location: `~/.cache/huggingface/hub/models--hexgrad--Kokoro-82M/`
4. If voices are missing, manually download them from [Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M/tree/main/voices) and place them in the cache directory
5. Check Settings > TTS to verify language and voice selection

**For PocketTTS:**
1. Ensure `pocket-tts` and `scipy` are installed: `pip install pocket-tts scipy`
2. PocketTTS models are automatically downloaded on first use
3. For voice cloning, upload a clear audio sample (WAV format recommended)
4. Check Settings > TTS to select PocketTTS engine and configure voice cloning

### ASR Not Working

1. Ensure `nemo_toolkit[asr]` is installed from source (see requirements.txt)
2. NeMo installation requires Cython: `pip install Cython>=0.29.0`
3. Install from GitHub: `pip install git+https://github.com/NVIDIA/NeMo.git@main`
4. Ensure `sounddevice` and `webrtcvad` are installed: `pip install sounddevice webrtcvad`
5. ASR models are automatically downloaded on first use
6. Check microphone permissions in Windows settings
7. Verify audio input device is working in Settings > ASR

## Project Structure

```
lokai/
├── core/           # Core functionality (Ollama, TTS, ASR, Image/Video/Audio Gen)
│   ├── asr_engine.py          # Automatic Speech Recognition
│   ├── audio_generator.py     # Audio generation (Stable Audio)
│   ├── image_generator.py     # Image generation (Stable Diffusion)
│   ├── pocket_tts_engine.py   # PocketTTS engine with voice cloning
│   ├── tts_engine.py          # Kokoro TTS engine
│   ├── video_generator.py     # Video generation (SVD)
│   └── ...                    # Other core modules
├── ui/             # User interface components
│   ├── asr_worker.py          # ASR background worker
│   ├── audio_player_widget.py # Audio playback widget
│   ├── voice_input_widget.py  # Voice input interface
│   └── ...                    # Other UI components
├── utils/          # Utility modules
├── config/         # Configuration files
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
- **Stable Video Diffusion**: [stability.ai](https://stability.ai) - Video generation
- **Stable Audio Open**: [stability.ai](https://stability.ai) - Audio generation
- **Kokoro-82M**: [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) - Multi-language TTS engine
- **PocketTTS**: [tannonk/pocket-tts](https://github.com/tannonk/pocket-tts) - Voice cloning TTS engine
- **NeMo ASR**: [NVIDIA NeMo](https://github.com/NVIDIA/NeMo) - Automatic Speech Recognition
- **PySide6**: Qt for Python - GUI framework

