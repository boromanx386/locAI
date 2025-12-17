"""
Image Generation Worker for locAI.
Background thread for generating images without blocking UI.
"""

from PySide6.QtCore import QThread, Signal
from lokai.core.image_generator import ImageGenerator
from lokai.core.config_manager import ConfigManager
import tempfile
from pathlib import Path


class ImageGenerationWorker(QThread):
    """Worker thread for image generation."""

    image_generated = Signal(str)  # image_path
    error_occurred = Signal(str)  # error message
    progress_updated = Signal(int)  # progress percentage

    def __init__(
        self,
        image_generator: ImageGenerator,
        prompt: str,
        config_manager: ConfigManager,
        seed: int = None,
    ):
        """
        Initialize ImageGenerationWorker.

        Args:
            image_generator: ImageGenerator instance
            prompt: Image generation prompt
            config_manager: ConfigManager for settings
            seed: Random seed for image generation (None = random)
        """
        super().__init__()
        self.image_generator = image_generator
        self.prompt = prompt
        self.config_manager = config_manager
        self.seed = seed

    def run(self):
        """Run image generation in background thread."""
        try:
            # Get settings from config
            model_name = self.config_manager.get(
                "image_gen.model", "stabilityai/stable-diffusion-xl-base-1.0"
            )
            negative_prompt = self.config_manager.get(
                "image_gen.negative_prompt",
                "blurry, low quality, distorted, ugly, bad anatomy",
            )
            width = self.config_manager.get("image_gen.width", 1024)
            height = self.config_manager.get("image_gen.height", 1024)
            steps = self.config_manager.get("image_gen.steps", 50)
            guidance_scale = self.config_manager.get("image_gen.guidance_scale", 7.5)

            # Load model if needed
            model_changed = self.image_generator.current_model != model_name
            if model_changed:
                self.progress_updated.emit(10)
                # Unload LoRAs when model changes (LoRAs are model-specific)
                if self.image_generator.active_loras:
                    self.image_generator.unload_all_loras()
                self.image_generator.load_model(model_name)
                self.progress_updated.emit(30)

            # Load LoRA if specified (optimized - only load if different from current)
            # Note: If model changed, LoRAs were already unloaded above
            lora_model = self.config_manager.get("image_gen.lora_model", "None")
            lora_weight = self.config_manager.get("image_gen.lora_weight", 1.0)

            if lora_model and lora_model != "None" and lora_model != "None (No LoRA)":
                # Get LoRA path from model manager
                from lokai.utils.model_manager import ModelManager

                storage_path = self.config_manager.get("models.storage_path", "")
                if storage_path:
                    model_manager = ModelManager(storage_path)
                    detected_models = model_manager.detect_existing_models()

                    # Find LoRA by display name
                    lora_path = None
                    for lora in detected_models.get("loras", []):
                        if lora["display"] == lora_model or lora["name"] == lora_model:
                            lora_path = lora["path"]
                            break

                    if lora_path:
                        # Check if this LoRA is already loaded with same weight
                        already_loaded = False
                        for active_lora in self.image_generator.active_loras:
                            if (
                                active_lora["path"] == str(lora_path)
                                and abs(active_lora["weight"] - lora_weight) < 0.001
                            ):
                                already_loaded = True
                                print(
                                    f"LoRA already loaded: {lora_model} (skipping reload)"
                                )
                                break

                        if not already_loaded:
                            # Unload previous LoRAs first (only if different LoRA)
                            self.image_generator.unload_all_loras()
                            # Load new LoRA
                            if self.image_generator.load_lora(lora_path, lora_weight):
                                self.progress_updated.emit(35)
                                print(f"LoRA loaded: {lora_model}")
                            else:
                                print(f"Warning: Failed to load LoRA: {lora_model}")
                    else:
                        print(f"Warning: LoRA not found: {lora_model}")
                else:
                    print(
                        f"Warning: Storage path not set. Cannot load LoRA: {lora_model}"
                    )
            else:
                # Unload LoRAs if None selected (only if any are loaded)
                if self.image_generator.active_loras:
                    self.image_generator.unload_all_loras()

            # Progress callback using callback_on_step_end signature
            # Signature: (pipe, step_index, timestep, callback_kwargs)
            # Must return callback_kwargs (or modified version)
            def progress_callback(pipe, step_index, timestep, callback_kwargs):
                try:
                    # Calculate progress: 30% (loading) + 60% (generation) = 90%
                    # step_index is 0-based, steps is total steps
                    if steps > 0 and step_index is not None:
                        progress = 30 + int((step_index / steps) * 60)
                        # Clamp to 90% max (remaining 10% for saving)
                        progress = min(progress, 90)
                        self.progress_updated.emit(progress)
                except Exception as e:
                    # Ignore callback errors
                    pass

                # Must return callback_kwargs (or modified version)
                return callback_kwargs if callback_kwargs is not None else {}

            # Generate image
            self.progress_updated.emit(40)
            image = self.image_generator.generate_image(
                prompt=self.prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                guidance_scale=guidance_scale,
                seed=self.seed,
                callback=progress_callback,
            )

            if image is None:
                self.error_occurred.emit("Failed to generate image")
                return

            # Save image to temp file
            self.progress_updated.emit(95)
            output_dir = Path(self.config_manager.get_config_dir()) / "generated_images"
            output_dir.mkdir(exist_ok=True)

            import time

            filename = f"image_{int(time.time())}.png"
            image_path = output_dir / filename
            image.save(str(image_path), "PNG")

            self.progress_updated.emit(100)
            self.image_generated.emit(str(image_path))

        except Exception as e:
            error_msg = f"Error generating image: {str(e)}"
            print(error_msg)
            import traceback

            traceback.print_exc()
            self.error_occurred.emit(error_msg)
