# Changelog

All notable changes to locAI (lokai) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0] - 2025-02-24

### Added
- **Tools toggle** on main window status bar (construction icon): enable/disable Ollama tools; green when on, blue when off.
- **Global shortcuts** in Settings → General: optional TTS and Image shortcuts (e.g. single key or combo); tooltip notes single key is most reliable on Windows.
- **Help / About** dialog updated with feature list (LLM, image/video/audio, TTS, ASR, tools, RAG, README, MIT).
- **Setup wizard**: Hugging Face folder page – user selects where models (TTS, SD, SVD, etc.) are downloaded.
- **Setup wizard**: completion page note that app will close and user should restart for HF folder to take effect.
- **README**: Screenshots section (`screenshots/` folder).
- **README**: expanded documentation for RAG/embeddings, Images & vision, Tools, img2img (image must be in chat).
- **README**: BeautifulSoup4 optional (scrape_webpage); can enable via Settings or `ollama.tools.scrape_webpage: true` in config.

### Changed
- **Chat bubble links**: plain URLs in messages are now fully clickable (trailing punctuation no longer breaks the link).
- **Hover colors** for chat/status buttons: gray → darker blue (`#3B82E0` / `#2F6FC7`); tools button when ON uses green with hover.
- **Settings**: "Prompt templates" moved from separate Prompts tab into General tab as a group.
- **Global shortcuts**: hotkey normalization and per-shortcut registration with remove callback; TTS handler reads clipboard on Qt main thread with delayed copy for reliability.
- **Startup**: HF cache from config (wizard or Settings → Models); app restarts after first-run wizard so HF env is set before any imports.
- **Paths**: removed hardcoded Q:\ path; `default_hf_cache_root()` returns None; HF path comes from config or `LOCAI_HF_CACHE` env.
- **default_config.json**: ASR and RAG off by default; system prompt simplified to "You are a helpful AI assistant."; removed font_size and compact_mode from ui.
- **README**: Python 3.12, GPU (RTX 5060 Ti 16GB / RTX 2080), Support (GitHub Issues), LoRA in `loras/` subfolder.
- **requirements.txt**: torch>=2.9.1 with note on CUDA builds.

### Fixed
- **Cursor in chat input**: cursor sometimes stopped blinking or appeared stuck after sending or after AI finished; now input is refocused and cursor visibility/repaint is forced after send, after `finish_ai_message`, and after voice transcription insert (`_ensure_input_cursor_visible()`).

### Removed
- **TTS pause button** in status panel (hidden; was unreliable).
- **Font size** and **Compact mode** options from Settings (were non-functional).
- **Prompts** as a separate tab (content merged into General).

---

## [1.0.4] - 2026-03-06

### Changed
- **Ollama model unload**: Use API `keep_alive=0` instead of subprocess `ollama stop`; full model name from `/api/ps`; torch cleanup after each unload; 0.5s delay for VRAM release; fallback to subprocess if API fails.
- **GPU memory cleanup**: Replaced multiple gc/empty_cache loops (5x, 10x) with single calls in main_window, audio/video/image generators, TTS, ASR, clear_gpu_memory utility.
- **ASR preload**: Direct `asr_engine.load_model()` in background thread instead of simulating mic click; main window uses shared engine from VoiceInputWidget; fixed settings reinit order.

### Fixed
- **QTimer UnboundLocalError** when tools were disabled: removed redundant local import that shadowed global QTimer.

---

## [Unreleased]

### Added
- **Dystopian theme**: Cyberpunk/terminal aesthetic with monospace fonts (JetBrains Mono, Fira Code, Consolas), neon green text on dark background.
- **CRT scanline overlay**: Optional horizontal scanline effect with vignette for retro CRT look (toggle in Settings → Appearance).
- **Neural Filter panel**: Collapsible side panel showing raw model thinking stream in real-time (Settings → Appearance → Show Neural Filter panel).
- **Settings → Appearance**: Theme (Original Dark, Original Light, Dystopian), CRT scanlines checkbox, Neural Filter visibility checkbox.

### Changed
- **Theme system**: Extended with dystopian palette and monospace font stack; config validates `dystopian` as valid theme.
