"""
Centralized path configuration for locAI.
All path constants and resolvers for config dir, model storage, and output dirs.
"""

import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from lokai.core.config_manager import ConfigManager

# --- Subdirectory names (single source of truth) ---
SUBDIR_CHAT_EMBEDDINGS = "chat_embeddings"
SUBDIR_GENERATED_IMAGES = "generated_images"
SUBDIR_GENERATED_VIDEOS = "generated_videos"
SUBDIR_GENERATED_AUDIO = "generated_audio"
SUBDIR_VOICE_CACHE = "voice_cache"

# Suggested HF cache root when Q: drive exists (used by main.py and Settings UI)
DEFAULT_HF_CACHE_SUGGESTION = "Q:\\huggingface_cache"


def default_hf_cache_root() -> Optional[str]:
    """
    Suggested Hugging Face cache root before config is loaded (e.g. at startup).
    Returns DEFAULT_HF_CACHE_SUGGESTION if Q:\\ exists, else None.
    Environment variable LOCAI_HF_CACHE overrides this when set in main.py.
    """
    if os.path.exists("Q:\\"):
        return DEFAULT_HF_CACHE_SUGGESTION
    return None


def get_embeddings_dir(config_manager: "ConfigManager") -> Path:
    """Directory for RAG/chat embeddings (config_dir / chat_embeddings)."""
    base = Path(config_manager.get_config_dir())
    path = base / SUBDIR_CHAT_EMBEDDINGS
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_image_output_dir(config_manager: "ConfigManager") -> Path:
    """Directory for generated images. Uses image_gen.output_path if set."""
    base = Path(config_manager.get_config_dir())
    output_path = config_manager.get("image_gen.output_path")
    if output_path:
        path = Path(output_path)
    else:
        path = base / SUBDIR_GENERATED_IMAGES
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_video_output_dir(config_manager: "ConfigManager") -> Path:
    """Directory for generated videos. Uses video_gen.output_path if set."""
    base = Path(config_manager.get_config_dir())
    output_path = config_manager.get("video_gen.output_path")
    if output_path:
        path = Path(output_path)
    else:
        path = base / SUBDIR_GENERATED_VIDEOS
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_audio_output_dir(config_manager: "ConfigManager") -> Path:
    """Directory for generated audio. Uses audio_gen.output_folder if set."""
    base = Path(config_manager.get_config_dir())
    output_path = config_manager.get("audio_gen.output_folder")
    if output_path:
        path = Path(output_path)
    else:
        path = base / SUBDIR_GENERATED_AUDIO
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_voice_cache_dir(config_manager: "ConfigManager") -> Path:
    """Directory for TTS voice cache (e.g. Pocket TTS converted files)."""
    base = Path(config_manager.get_config_dir())
    path = base / SUBDIR_VOICE_CACHE
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_models_storage_path(config_manager: "ConfigManager") -> Optional[Path]:
    """Models storage path (HF cache root). None if not configured."""
    raw = config_manager.get("models.storage_path")
    if not raw:
        return None
    return Path(raw)


def get_image_storage_path(config_manager: "ConfigManager") -> Optional[Path]:
    """Image models storage. Falls back to models.storage_path."""
    raw = config_manager.get("image_gen.storage_path")
    if not raw:
        raw = config_manager.get("models.storage_path")
    if not raw:
        return None
    return Path(raw)


def get_video_storage_path(config_manager: "ConfigManager") -> Optional[Path]:
    """Video models storage. Falls back to models.storage_path."""
    raw = config_manager.get("video_gen.storage_path")
    if not raw:
        raw = config_manager.get("models.storage_path")
    if not raw:
        return None
    return Path(raw)


def get_audio_storage_path(config_manager: "ConfigManager") -> Optional[Path]:
    """Audio models storage. Falls back to models.storage_path."""
    raw = config_manager.get("audio_gen.storage_path")
    if not raw:
        raw = config_manager.get("models.storage_path")
    if not raw:
        return None
    return Path(raw)


def get_asr_storage_path(config_manager: "ConfigManager") -> Optional[Path]:
    """ASR models storage. Falls back to models.storage_path."""
    raw = config_manager.get("asr.storage_path")
    if not raw:
        raw = config_manager.get("models.storage_path")
    if not raw:
        return None
    return Path(raw)
