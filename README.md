# locAI - Local AI Assistant

locAI is a desktop AI assistant that combines Large Language Models (LLM), Image Generation, Video Generation, Audio Generation, Automatic Speech Recognition (ASR), and Text-to-Speech (TTS) in one accessible package.

**Repository:** [https://github.com/boromanx386/locAI](https://github.com/boromanx386/locAI) · **Version:** 1.0.0

## Screenshots

| Chat | GUI / model bar | Image generated |
|------|-----------------|-----------------|
| ![Chat](screenshots/locAI%20chat.png) | ![GUI](screenshots/locAI%20GUI.png) | ![Image](screenshots/locAI%20image.png) |

| Vision | Audio |
|--------|-------|
| ![Vision](screenshots/locAI%20vision.png) | ![Sound](screenshots/lockAI%20sound.png) |

## Features

- **LLM Chat**: Chat with AI models via Ollama ([Qwen3.5](https://ollama.com/library/qwen3.5), [Qwen3-VL](https://ollama.com/library/qwen3-vl), ministral-3:14b, and more)
- **Image Generation**: Generate images using Stable Diffusion (optional)
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
- **Python 3.12** (developed and tested on 3.12;)
- **Ollama** – install from [ollama.com](https://ollama.com/download) and ensure it’s in your PATH
- Dependencies from one of `lokai/requirements*.txt` (see below)

### Requirements files (pick one)

| File | Contents | For whom |
|------|----------|----------|
| `requirements.txt` | Core, Tools, TTS, shortcuts | Chat + TTS only (no GPU needed) |
| `requirements-image.txt` | Above + torch, diffusers, peft (image/video/audio) | Image, video, audio generation (NVIDIA GPU) |
| `requirements-full.txt` | Above + ASR (NeMo) | Full features including voice input |

**Base (`requirements.txt`):**
- **Core**: PySide6, requests, Pillow (GUI, Ollama API, images)
- **Tools**: ddgs, yt-dlp, youtube-transcript-api, deep-translator, beautifulsoup4 (web search, YouTube, translate, scrape; beautifulsoup4 optional—without it, `scrape_webpage` is unavailable)
- **TTS**: kokoro, soundfile, pygame, pocket-tts, scipy (Kokoro and/or PocketTTS; works without CUDA)
- **Other**: keyboard (global shortcuts)

**Image (`requirements-image.txt`):**  
Adds torch, diffusers, transformers, peft, numpy for Stable Diffusion, SVD, Stable Audio. **Install PyTorch with CUDA *before* running `pip install -r requirements-image.txt`** (see Optional – GPU below).

**Full (`requirements-full.txt`):**  
Adds ASR (NVIDIA NeMo) for voice input. Heavy install (~several GB).

### Optional – BeautifulSoup (scrape_webpage)
The `scrape_webpage` tool uses BeautifulSoup4 to parse HTML. If `beautifulsoup4` is not installed, the app works normally but `scrape_webpage` will not be available. To use it: `pip install beautifulsoup4`. It is disabled by default; enable it in **Settings → Ollama → Tools** or manually in config: `ollama.tools.scrape_webpage: true`.

### Optional – GPU (image / video / audio)
- **NVIDIA GPU with CUDA** for acceleration (recommended for image, video, and audio generation).
- Use `requirements-image.txt` or `requirements-full.txt`. **Install PyTorch with CUDA *before* the rest:**
  ```bash
  pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cu128
  ```
  Replace `cu128` with your CUDA version (e.g. `cu118`, `cu124`) from [pytorch.org](https://pytorch.org/get-started/locally/).
- Tested on **RTX 5060 Ti 16GB** and **RTX 2080 8GB**.

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
ollama pull qwen3.5:9b
```

This downloads the [Qwen3.5:9b](https://ollama.com/library/qwen3.5) model (multimodal, 256K context, ~6.6GB).

**Other recommended models:**
- `ollama pull qwen3-vl` – Vision model ([Qwen3-VL](https://ollama.com/library/qwen3-vl))
- `ollama pull ministral-3:14b` – Ministral 3 14B

### 3. Install locAI

Choose one of the following (from project root or from inside `lokai`):

**Base (chat + TTS only):**
```bash
pip install -r lokai/requirements.txt
```

**With image/video/audio (NVIDIA GPU):** Install PyTorch with CUDA first, then:
```bash
pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cu128
pip install -r lokai/requirements-image.txt
```

**Full (includes ASR voice input):**
```bash
pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cu128
pip install -r lokai/requirements-full.txt
```

Replace `cu128` with your CUDA version if different (see Optional – GPU above).

### 4. Run locAI

From the project root:

```bash
python -m lokai
```

Or from inside `lokai`:

```bash
cd lokai
python main.py
```

On first run, the setup wizard will guide you through:
- Ollama detection and verification
- **Hugging Face folder** (where models are downloaded – TTS, image/video/audio)
- Theme selection

After you finish the wizard, the app will close. Start it again so the chosen folder is used.

## Usage

### Starting a Chat

1. Ensure Ollama is running (check the status indicator at the top)
2. Select a model from the dropdown
3. Type your message and press Send
4. The AI response will stream in real-time

### Attaching files to chat

**Images:** Paste (Ctrl+V) or drag & drop onto the chat input. Supported: JPG, PNG, BMP, GIF, TIFF. Use a vision-capable model (e.g. qwen3.5, qwen3-vl) to discuss images. See Images and vision below.

**Text/code files:** Drag & drop files onto the chat input area. Supported extensions include `.txt`, `.md`, `.json`, `.yaml`, `.py`, `.js`, `.ts`, `.html`, `.css`, `.c`, `.cpp`, `.rs`, `.go`, `.java`, `.sql`, `.sh`, and many other text/code formats. Up to 5 files, 10 MB each; content is truncated at 50k characters. The file contents are sent as part of the prompt so the model can analyze or edit them. Attachments can be enabled/disabled and max file count adjusted in config (`chat.attachments.enabled`, `chat.attachments.max_files`).

### Settings

Access settings via **File > Preferences** or press `Ctrl+,`

**Settings tabs:**
- **General**: Theme, prompt templates, global shortcuts
- **Ollama**: Base URL, default model, auto-start, LLM parameters (including context window)
- **Models**: Hugging Face / model storage path (image, video, audio, ASR)
- **TTS**: Engine (Kokoro or PocketTTS), voice, voice cloning, auto-speak
- **ASR**: ASR settings (if NeMo is installed)
- **RAG**: Semantic memory (embeddings), embedding model, CPU/GPU, memory options

### System monitoring (CPU, RAM, VRAM)

The **top-right corner** of the window shows live CPU, RAM and GPU (VRAM) usage. This helps you track memory use when running LLM, image generation, or TTS. To adapt when VRAM is high: change the **model** (dropdown in the status bar) to a smaller one, or reduce **Context Window** in **Settings → Ollama → LLM Generation Parameters**. The monitor uses `psutil` and `nvidia-ml-py` (pynvml); if no GPU is detected, only CPU and RAM are shown.

### RAG / Semantic memory (embeddings)

RAG gives the model a “memory” of important bits from the conversation by storing **embeddings** of messages you choose and then injecting relevant ones into the prompt.

**How it works:**
1. **Embedding model** – Runs in Ollama (same server as chat). Default: **nomic-embed-text:v1.5**. Install with `ollama pull nomic-embed-text`. You can pick another model in **Settings → RAG** (list comes from your installed Ollama models, or you can type a custom name). Embeddings run on CPU by default so the GPU stays free for the chat model.
2. **Manual “Remember”** – Nothing is embedded automatically. You choose what to remember: right‑click in the chat and use **“Remember selection”** or **“Remember message”**. That text is sent to Ollama’s embedding API, the vector is stored in a per‑chat file under `chat_embeddings/` (next to your config), and the message is kept with its embedding.
3. **When you send a message** – The current message is embedded and compared (cosine similarity) to all stored “remembered” items. The top‑k most relevant are selected and formatted into a short **memory block** that is prepended to the prompt (e.g. “Relevant context from earlier…”). So the model sees: system prompt + optional memory block + recent conversation + your new message.
4. **Settings** – In **Settings → RAG** you can set: embedding model, “top k” relevant memories, character limits, minimum similarity, and enable/disable RAG. Stored data is in the config directory under `chat_embeddings/` (one JSON file per chat).

### Images and vision

**Chat with images (vision models):**
- You can **attach images** to a message (or paste) in the chat. Supported formats: JPG, PNG, BMP, GIF, TIFF.
- Images are **resized** if larger than 1024 px (aspect ratio kept), converted to JPEG (quality 85), then to **base64** and sent to Ollama in the same request as your text (`images` array in the API).
- You must use a **vision-capable model** (e.g. **qwen3.5**, **qwen3-vl**, **llava**, **bakllava**, **moondream**). The model dropdown in locAI shows both plain LLM and vision models; vision models are detected by name or by Ollama’s “vision” capability.
- When the request includes images, the app sends them **without** previous conversation context (vision models often work better that way). After the reply, context is cleared for the next turn to avoid confusion.

**Image generation (Stable Diffusion):**
- Separate from vision: this **creates** images from text (or image→image) using **Stable Diffusion** (diffusers), not Ollama. Models and outputs use the **Hugging Face folder** you set in the wizard or in **Settings → Models**. It works with **all SD-compatible models and checkpoints**: base models like SDXL, SD 2.1, SD 1.5, plus community checkpoints from [Civitai](https://civitai.com) and similar. Place downloaded models (e.g. `.safetensors` or diffusers-style) in your Hugging Face folder—subfolders are fine; the app will find them. **LoRA** files must go in the **`loras`** subfolder of that HF folder (e.g. `YourHFFolder/loras/`); the app only lists LoRAs from there (Settings → Image generation → LoRA tab). Generated images can then be attached in chat for a vision model to discuss, or used for **Generate Video** (SVD).
- **Edit image (img2img):** Same principle as vision—you must **add the image to the chat** first (attach or paste). Then use the edit/image option on that message; the attached image is used as the source for img2img (strength and steps are in Settings → Image generation).

### Tools (function calling)

The model can call **tools** (web search, weather, YouTube, translate, etc.) when you have **tools enabled** and use a model that supports function calling.

**Available tools:**  
`search_web` (DuckDuckGo + WorldTimeAPI for time), `get_weather`, `search_code` (GitHub), `translate`, `search_youtube`, `fact_check`, `open_url`, `scrape_webpage`. Each can be turned on/off in **Settings → Ollama → Tools** (e.g. web_search, weather, scrape_webpage). The **status bar** has a tools toggle (construction icon): green = tools on, blue = off.

**How it works:**
1. When you send a message, if tools are enabled the app sends the **tool definitions** (name, description, parameters) to Ollama together with the prompt.
2. If the model decides to use a tool, it returns a **tool call** (function name + arguments). The app runs the tool locally (e.g. HTTP request to DuckDuckGo, yt-dlp, etc.), then sends the **tool result** back to the model in the next message.
3. The model can call several tools in sequence before giving you the final answer. Tool execution is done by locAI; only public HTTP/HTTPS URLs are allowed (localhost and private IPs are blocked for safety).

**Requirements:**  
Install dependencies from `requirements.txt` or another `requirements*.txt` (e.g. `ddgs`, `yt-dlp`, `deep-translator`, `beautifulsoup4`). No API keys are required for the default tools. **BeautifulSoup4** is optional—the app runs without it; only `scrape_webpage` is unavailable. If installed, you can enable it in Settings or by setting `ollama.tools.scrape_webpage` to `true` in your config file.

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
- Use the TTS controls (play/stop) in the status panel
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

### Config and data locations

- **Config file**:  
  - Windows: `%LOCALAPPDATA%\locAI\config.json`  
  - Linux/Mac: `~/.config/lokai/config.json`
- **Generated files** (unless you set custom paths in Settings): images, video, and audio go into subfolders of the config directory (`generated_images`, `generated_videos`, `generated_audio`).
- **Chat embeddings** (RAG): in the config directory under `chat_embeddings`.

### Model storage location

You choose the Hugging Face folder in the **setup wizard** (first run) or later in **Settings → Models**. Default suggestion if you don’t set it:
- Windows: `Documents\locAI\models`
- Linux/Mac: `~/Documents/locAI/models`

That folder is used for all Hugging Face downloads (Stable Diffusion, SVD, Stable Audio, TTS voices, NeMo ASR).

### Environment variables

- **`LOCAI_HF_CACHE`** (optional): Override the Hugging Face cache root **before** starting the app (e.g. to use another drive). If unset, the app uses the path you chose in the setup wizard or in Settings → Models.
- The app also sets: `HF_HOME`, `HF_HUB_CACHE`, `TRANSFORMERS_CACHE`, `HF_DATASETS_CACHE`, `DIFFUSERS_CACHE` when using image/video/audio features.

## GPU Memory Optimization

locAI is specifically optimized to run efficiently on GPUs with limited VRAM, including systems with only 8GB of GPU memory. Key optimizations include:

- **Automatic Model Unloading**: Models are automatically unloaded from GPU memory after use (LLM, Vision, Image Generation, and TTS)
- **Aggressive Memory Cleanup**: Multiple cache clearing passes and IPC resource collection ensure maximum memory is freed
- **Smart Memory Management**: Models are unloaded when switching between different model types or when switching models
- **Sequential CPU Offload**: Image generation models use sequential CPU offload to minimize VRAM usage
- **Memory Cleanup on Exit**: All GPU memory is properly released when the application closes

Tested with **PyTorch 2.9.1+cu128** on **RTX 5060 Ti 16GB**; also runs on **RTX 2080 8GB** and similar.

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

1. Install a model: `ollama pull qwen3.5:9b`
2. Click "Refresh" in the status panel
3. Verify models: `ollama list`

### Image Generation Not Working

1. Use `requirements-image.txt` or `requirements-full.txt`. Install PyTorch with CUDA first (see Optional – GPU), then `pip install -r lokai/requirements-image.txt`
2. Check that your Hugging Face folder (Settings → Models) has enough free space (models are several GB)
3. For GPU: install a CUDA build of PyTorch from [pytorch.org](https://pytorch.org/get-started/locally/)
4. If you see "CUDA out of memory", the app will try to unload models automatically; close other GPU apps or use a smaller model


The application is optimized for 8GB+ GPUs, but if you have less VRAM, you may need to:
- Use smaller models
- Unload models manually between tasks
- Use CPU mode for some operations

### TTS Not Working

**For Kokoro-82M:**
1. Ensure `kokoro` and `soundfile` are installed: `pip install kokoro soundfile`
2. Voice files are downloaded to your **Hugging Face folder** (the one from the setup wizard or Settings → Models) on first use
3. If voices are missing, manually download them from [Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M/tree/main/voices) and place them in that folder (under the usual hub structure)
4. Check Settings → TTS for language and voice selection

**For PocketTTS:**
1. Ensure `pocket-tts` and `scipy` are installed: `pip install pocket-tts scipy`
2. PocketTTS models are automatically downloaded on first use
3. For voice cloning, upload a clear audio sample (WAV format recommended)
4. Check Settings > TTS to select PocketTTS engine and configure voice cloning

### ASR Not Working

1. Install `requirements-full.txt`: `pip install -r lokai/requirements-full.txt` (install PyTorch with CUDA first if you use GPU)
2. ASR models are downloaded to your Hugging Face folder on first use
3. Check microphone permissions (e.g. Windows Settings)
4. In Settings → ASR, verify the correct input device is selected

## Project Structure

```
lokai/
├── main.py             # Entry point
├── requirements.txt        # Base: core, tools, TTS
├── requirements-image.txt  # + image/video/audio (torch, diffusers)
├── requirements-full.txt   # + ASR (NeMo)
├── config/
│   └── default_config.json
├── core/               # Core logic (no UI)
│   ├── config_manager.py   # Config load/save
│   ├── paths.py            # Centralized paths (cache, output dirs)
│   ├── ollama_client.py    # Ollama API
│   ├── ollama_detector.py
│   ├── asr_engine.py       # ASR (NeMo)
│   ├── tts_engine.py       # Kokoro TTS
│   ├── pocket_tts_engine.py
│   ├── image_generator.py  # Stable Diffusion
│   ├── video_generator.py  # SVD
│   ├── audio_generator.py  # Stable Audio
│   ├── tools_handler.py    # Web search, YouTube, translate, scrape
│   └── ...
├── ui/                 # PySide6 UI
│   ├── main_window.py
│   ├── chat_widget.py
│   ├── settings_dialog.py
│   ├── setup_wizard.py
│   ├── voice_input_widget.py
│   ├── audio_player_widget.py
│   └── ...
└── utils/
    └── model_manager.py
```

## Development

### Running from source

Same as **Installation** above: pick the appropriate `requirements*.txt` (base, image, or full), install, then run `python -m lokai` from project root.

### Building

locAI uses PySide6 for the GUI. For distribution:
- Consider using PyInstaller or cx_Freeze for standalone executables
- Include Ollama installation instructions with distribution

## License

This project is licensed under the **MIT License**.  
See the `LICENSE` file for the full text.

## Support

For bugs, questions, or contributions please use [GitHub Issues](https://github.com/boromanx386/locAI/issues). When opening an issue, include your OS, Python version, and whether you use GPU (and which one) so we can help faster.

## Credits

- **Ollama**: [ollama.com](https://ollama.com) - Local LLM runtime
- **Stable Diffusion**: [stability.ai](https://stability.ai) - Image generation
- **Stable Video Diffusion**: [stability.ai](https://stability.ai) - Video generation
- **Stable Audio Open**: [stability.ai](https://stability.ai) - Audio generation
- **Kokoro-82M**: [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) - Multi-language TTS engine
- **PocketTTS**: [tannonk/pocket-tts](https://github.com/tannonk/pocket-tts) - Voice cloning TTS engine
- **NeMo ASR**: [NVIDIA NeMo](https://github.com/NVIDIA/NeMo) - Automatic Speech Recognition
- **PySide6**: Qt for Python - GUI framework

