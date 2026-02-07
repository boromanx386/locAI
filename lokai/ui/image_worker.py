"""
Image Generation Worker for locAI.
Background thread for generating images without blocking UI.
"""

from typing import Optional

from PySide6.QtCore import QThread, Signal
from PIL import Image

from lokai.core.image_generator import ImageGenerator
from lokai.core.config_manager import ConfigManager
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
        init_image_path: Optional[str] = None,
    ):
        """
        Initialize ImageGenerationWorker.

        Args:
            image_generator: ImageGenerator instance
            prompt: Image generation prompt
            config_manager: ConfigManager for settings
            seed: Random seed for image generation (None = random)
            init_image_path: Optional path to init image for img2img
        """
        super().__init__()
        self.image_generator = image_generator
        self.prompt = prompt
        self.config_manager = config_manager
        self.seed = seed
        self.init_image_path = init_image_path

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

                # Get sequential CPU offload setting from config
                use_cpu_offload = self.config_manager.get(
                    "image_gen.use_sequential_cpu_offload", True
                )
                self.image_generator.load_model(
                    model_name, use_sequential_cpu_offload=use_cpu_offload
                )
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

            def make_progress_callback(steps_used):
                def progress_callback(pipe, step_index, timestep, callback_kwargs):
                    try:
                        if steps_used > 0 and step_index is not None:
                            current_step = step_index + 1
                            progress = 30 + int((current_step / steps_used) * 60)
                            progress = min(progress, 90)
                            self.progress_updated.emit(progress)
                    except Exception:
                        pass
                    return callback_kwargs if callback_kwargs is not None else {}

                return progress_callback

            # Generate image (start at 30% since model is loaded)
            self.progress_updated.emit(30)
            if self.init_image_path and Path(self.init_image_path).exists():
                init_img = Image.open(self.init_image_path)
                strength = self.config_manager.get(
                    "image_gen.img2img_strength", 0.75
                )
                img2img_steps = self.config_manager.get(
                    "image_gen.img2img_steps", 30
                )
                image = self.image_generator.generate_image_img2img(
                    init_image=init_img,
                    prompt=self.prompt,
                    negative_prompt=negative_prompt,
                    strength=strength,
                    steps=img2img_steps,
                    guidance_scale=guidance_scale,
                    seed=self.seed,
                    callback=make_progress_callback(img2img_steps),
                )
            else:
                image = self.image_generator.generate_image(
                    prompt=self.prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    steps=steps,
                    guidance_scale=guidance_scale,
                    seed=self.seed,
                    callback=make_progress_callback(steps),
                )

            if image is None:
                self.error_occurred.emit("Failed to generate image")
                return

            # Save image to output folder
            self.progress_updated.emit(95)
            # Get output path from config, fallback to default
            output_path = self.config_manager.get("image_gen.output_path")
            if output_path:
                output_dir = Path(output_path)
            else:
                output_dir = Path(self.config_manager.get_config_dir()) / "generated_images"
            output_dir.mkdir(parents=True, exist_ok=True)

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
