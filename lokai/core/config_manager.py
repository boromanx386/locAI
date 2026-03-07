"""
Configuration Manager for locAI.
Handles loading, saving, and validation of application configuration.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List


class ConfigManager:
    """Manages application configuration with JSON-based storage."""

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize ConfigManager.

        Args:
            config_dir: Optional custom config directory.
                       Defaults to user's AppData/Local on Windows.
        """
        if config_dir is None:
            # Use user-specific config directory
            if os.name == "nt":  # Windows
                self.config_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "locAI"
            else:  # Linux/Mac
                self.config_dir = Path.home() / ".config" / "lokai"
        else:
            self.config_dir = Path(config_dir)

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Config file path
        self.config_file = self.config_dir / "config.json"

        # Default config path (in package)
        from lokai.core.paths import get_package_root

        self.default_config_file = get_package_root() / "config" / "default_config.json"

        # Load configuration
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        # Try to load user config
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    user_config = json.load(f)

                # Merge with default config to ensure all keys exist
                default_config = self._load_default_config()
                config = self._merge_configs(default_config, user_config)
                return config
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}. Using defaults.")

        # Load default config
        return self._load_default_config()

    def reload_config(self) -> None:
        """Reload configuration from disk, merging with defaults."""
        self.config = self._load_config()

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        if self.default_config_file.exists():
            try:
                with open(self.default_config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading default config: {e}")

        # Fallback to hardcoded defaults
        return {
            "ollama": {
                "base_url": "http://localhost:11434",
                "default_model": "llama3.2",
                "auto_start": False,
            },
            "models": {"storage_path": None, "auto_download": False},
            "ui": {"theme": "dark"},
            "tts": {"enabled": True, "voice": "en-US-AriaNeural", "auto_speak": False},
            "image_gen": {"enabled": False, "storage_path": None, "output_path": None},
            "prompts": [],
            "first_run": True,
        }

    def _merge_configs(self, default: Dict, user: Dict) -> Dict:
        """Merge user config with default, preserving nested structure."""
        merged = default.copy()
        for key, value in user.items():
            if (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)
            ):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                # For lists and other types, use user value directly
                # This ensures user prompts and other list values are preserved
                merged[key] = value
        return merged

    def save_config(self) -> bool:
        """Save current configuration to file."""
        try:
            # Create backup if config exists
            if self.config_file.exists():
                backup_file = self.config_file.with_suffix(".json.bak")
                if backup_file.exists():
                    backup_file.unlink()
                self.config_file.rename(backup_file)

            # Write new config
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            return True
        except IOError as e:
            print(f"Error saving config: {e}")
            return False

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated path.

        Args:
            key_path: Dot-separated path (e.g., "ollama.base_url")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split(".")
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value by dot-separated path.

        Args:
            key_path: Dot-separated path (e.g., "ollama.base_url")
            value: Value to set
        """
        keys = key_path.split(".")
        config = self.config

        # Navigate to the parent dict
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # Set the value
        config[keys[-1]] = value

    def validate_config(self) -> tuple[bool, Optional[str]]:
        """
        Validate configuration structure and values.

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_keys = [
            "ollama.base_url",
            "ollama.default_model",
            "ui.theme",
            "tts.enabled",
        ]

        for key_path in required_keys:
            if self.get(key_path) is None:
                return False, f"Missing required config key: {key_path}"

        # Validate URL format
        base_url = self.get("ollama.base_url")
        if not isinstance(base_url, str) or not base_url.startswith(
            ("http://", "https://")
        ):
            return False, "Invalid ollama.base_url format"

        # Validate theme
        theme = self.get("ui.theme")
        if theme not in ["dark", "light", "dystopian"]:
            return False, f"Invalid theme: {theme}"

        return True, None

    def is_first_run(self) -> bool:
        """Check if this is the first run of the application."""
        return self.get("first_run", True)

    def set_first_run_complete(self) -> None:
        """Mark first run as complete."""
        self.set("first_run", False)
        self.save_config()

    def get_config_dir(self) -> Path:
        """Get the configuration directory path."""
        return self.config_dir

    # Model Presets methods
    def get_model_presets(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all model presets.

        Returns:
            Dictionary of model presets, keyed by model_id
        """
        return self.get("model_presets", {})

    def get_model_preset(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get preset for a specific model.

        Args:
            model_id: Model identifier (path or Hugging Face ID)

        Returns:
            Preset dictionary or None if not found
        """
        presets = self.get_model_presets()
        return presets.get(model_id)

    def set_model_preset(self, model_id: str, preset: Dict[str, Any]) -> None:
        """
        Set or update preset for a model.

        Args:
            model_id: Model identifier
            preset: Preset dictionary with keys: name, width, height, steps,
                   guidance_scale, negative_prompt, info_url, description, type
        """
        presets = self.get_model_presets()
        presets[model_id] = preset
        self.set("model_presets", presets)

    def delete_model_preset(self, model_id: str) -> bool:
        """
        Delete preset for a model.

        Args:
            model_id: Model identifier

        Returns:
            True if deleted, False if not found
        """
        presets = self.get_model_presets()
        if model_id in presets:
            del presets[model_id]
            self.set("model_presets", presets)
            return True
        return False

    def get_auto_apply_presets(self) -> bool:
        """Check if auto-apply presets is enabled."""
        return self.get("image_gen.auto_apply_presets", True)

    def set_auto_apply_presets(self, enabled: bool) -> None:
        """Set auto-apply presets setting."""
        self.set("image_gen.auto_apply_presets", enabled)

    # Saved Cloned Voices methods
    def get_saved_cloned_voices(self) -> List[Dict[str, Any]]:
        """
        Get all saved cloned voices.

        Returns:
            List of saved voice dictionaries with keys: name, file_path, created
        """
        return self.get("tts.voice_cloning.saved_voices", [])

    def get_saved_cloned_voice(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific saved cloned voice by name.

        Args:
            name: Voice name

        Returns:
            Voice dictionary or None if not found
        """
        saved_voices = self.get_saved_cloned_voices()
        for voice in saved_voices:
            if voice.get("name") == name:
                return voice
        return None

    def add_saved_cloned_voice(self, name: str, file_path: str, converted_file_path: Optional[str] = None) -> None:
        """
        Add or update a saved cloned voice.

        Args:
            name: Voice name
            file_path: Path to original audio file
            converted_file_path: Optional path to pre-converted PCM int16 file (for faster loading)
        """
        saved_voices = self.get_saved_cloned_voices()
        
        # Remove existing voice with same name if exists
        saved_voices = [v for v in saved_voices if v.get("name") != name]
        
        # Add new voice
        from datetime import datetime
        new_voice = {
            "name": name,
            "file_path": file_path,
            "created": datetime.now().isoformat()
        }
        
        # Add converted file path if provided
        if converted_file_path:
            new_voice["converted_file_path"] = converted_file_path
        
        saved_voices.append(new_voice)
        
        self.set("tts.voice_cloning.saved_voices", saved_voices)

    def remove_saved_cloned_voice(self, name: str) -> bool:
        """
        Remove a saved cloned voice by name.

        Args:
            name: Voice name

        Returns:
            True if removed, False if not found
        """
        saved_voices = self.get_saved_cloned_voices()
        original_count = len(saved_voices)
        saved_voices = [v for v in saved_voices if v.get("name") != name]
        
        if len(saved_voices) < original_count:
            self.set("tts.voice_cloning.saved_voices", saved_voices)
            return True
        return False

    # LoRA Info methods
    def get_lora_infos(self) -> Dict[str, str]:
        """
        Get all LoRA information.

        Returns:
            Dictionary of LoRA info, keyed by LoRA path or display name
        """
        return self.get("lora_infos", {})

    def get_lora_info(self, lora_identifier: str) -> Optional[str]:
        """
        Get information for a specific LoRA.

        Args:
            lora_identifier: LoRA path or display name

        Returns:
            Info string or None if not found
        """
        infos = self.get_lora_infos()
        return infos.get(lora_identifier)

    def set_lora_info(self, lora_identifier: str, info: str) -> None:
        """
        Set or update information for a LoRA.

        Args:
            lora_identifier: LoRA path or display name
            info: Information text
        """
        infos = self.get_lora_infos()
        infos[lora_identifier] = info
        self.set("lora_infos", infos)

    # LLM Model Settings methods (per-model configuration)
    def get_llm_model_settings(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all LLM model-specific settings.

        Returns:
            Dictionary of model settings, keyed by model name
        """
        return self.get("ollama.model_settings", {})

    def get_llm_model_setting(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get settings for a specific LLM model.

        Args:
            model_name: Model name (e.g., "deepseek-r1:128k")

        Returns:
            Settings dictionary with llm_params and conversation settings, or None if not found
        """
        settings = self.get_llm_model_settings()
        return settings.get(model_name)

    def set_llm_model_setting(self, model_name: str, settings: Dict[str, Any]) -> None:
        """
        Set or update settings for an LLM model.

        Args:
            model_name: Model name
            settings: Dictionary with keys like:
                - llm_params: dict with num_ctx, temperature, top_p, top_k, repeat_penalty, num_predict
                - conversation: dict with system_prompt, max_history_messages, use_explicit_history
        """
        model_settings = self.get_llm_model_settings()
        model_settings[model_name] = settings
        self.set("ollama.model_settings", model_settings)

    def delete_llm_model_setting(self, model_name: str) -> bool:
        """
        Delete settings for an LLM model.

        Args:
            model_name: Model name

        Returns:
            True if deleted, False if not found
        """
        model_settings = self.get_llm_model_settings()
        if model_name in model_settings:
            del model_settings[model_name]
            self.set("ollama.model_settings", model_settings)
            return True
        return False

    def get_prompts(self) -> list:
        """Get list of saved prompts."""
        prompts = self.get("prompts", [])
        # Ensure we return a list
        return prompts if isinstance(prompts, list) else []

    def save_prompts(self, prompts: list):
        """Save prompts list."""
        self.config["prompts"] = prompts
        # Note: Don't call save_config() here - let the caller save when ready
        # This prevents race conditions when multiple settings are being saved
