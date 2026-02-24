# Changelog

All notable changes to locAI (lokai) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0] - 2026-02-24

### Added
- **Tools toggle** on main window status bar (construction icon): enable/disable Ollama tools; green when on, blue when off.
- **Global shortcuts** in Settings → General: optional TTS and Image shortcuts (e.g. single key or combo); tooltip notes single key is most reliable on Windows.
- **Help / About** dialog updated with feature list (LLM, image/video/audio, TTS, ASR, tools, RAG, README, MIT).

### Changed
- **Chat bubble links**: plain URLs in messages are now fully clickable (trailing punctuation no longer breaks the link).
- **Hover colors** for chat/status buttons: gray → darker blue (`#3B82E0` / `#2F6FC7`); tools button when ON uses green with hover.
- **Settings**: "Prompt templates" moved from separate Prompts tab into General tab as a group.
- **Global shortcuts**: hotkey normalization and per-shortcut registration with remove callback; TTS handler reads clipboard on Qt main thread with delayed copy for reliability.

### Fixed
- **Cursor in chat input**: cursor sometimes stopped blinking or appeared stuck after sending or after AI finished; now input is refocused and cursor visibility/repaint is forced after send, after `finish_ai_message`, and after voice transcription insert (`_ensure_input_cursor_visible()`).

### Removed
- **TTS pause button** in status panel (hidden; was unreliable).
- **Font size** and **Compact mode** options from Settings (were non-functional).
- **Prompts** as a separate tab (content merged into General).

---

## [Unreleased]

*Add new entries here for the next release.*

---
