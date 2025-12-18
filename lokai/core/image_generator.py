"""
Image Generator for locAI.
Stable Diffusion image generation with configurable model location.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image

# Optional imports - only load if available
try:
    import torch
    from diffusers import StableDiffusionXLPipeline

    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False
    print("Warning: diffusers not available. Image generation disabled.")


class ImageGenerator:
    """Image generator using Stable Diffusion."""

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize ImageGenerator.

        Args:
            storage_path: Path to model storage (from config)
        """
        self.storage_path = storage_path
        self.pipeline = None
        self.current_model = None
        self.device = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu" if DIFFUSERS_AVAILABLE else None
        )
        self.active_loras = []  # Track loaded LoRAs

        # Setup environment if path provided
        if storage_path:
            self.setup_environment(storage_path)

    def setup_environment(self, storage_path: str):
        """
        Setup environment variables for Hugging Face cache.

        Args:
            storage_path: Path to model storage
        """
        storage = Path(storage_path)
        diffusers_path = storage / "diffusers"

        os.environ["HF_HOME"] = str(storage)
        os.environ["TRANSFORMERS_CACHE"] = str(storage)
        os.environ["HF_DATASETS_CACHE"] = str(storage)
        os.environ["HF_HUB_CACHE"] = str(storage)
        os.environ["DIFFUSERS_CACHE"] = str(diffusers_path)
        os.environ["HF_DIFFUSERS_CACHE"] = str(diffusers_path)

    def is_available(self) -> bool:
        """Check if image generation is available."""
        return DIFFUSERS_AVAILABLE and self.device is not None

    def load_model(self, model_name: str = "stabilityai/stable-diffusion-xl-base-1.0"):
        """
        Load Stable Diffusion model.

        Args:
            model_name: Model name (Hugging Face ID) or path to .safetensors file
        """
        if not self.is_available():
            raise RuntimeError(
                "Image generation not available. Install diffusers and torch."
            )

        if self.current_model == model_name and self.pipeline is not None:
            return  # Already loaded

        print(f"Loading model: {model_name}")

        try:
            # Check if it's a local .safetensors file
            if model_name.endswith(".safetensors") or Path(model_name).is_file():
                # Load from single file
                print(f"Loading from .safetensors file: {model_name}")
                from diffusers import StableDiffusionXLPipeline, StableDiffusionPipeline

                # Try XL first, fallback to base if it fails
                try:
                    self.pipeline = StableDiffusionXLPipeline.from_single_file(
                        model_name,
                        torch_dtype=torch.float32,  # Use float32 for compatibility
                        use_safetensors=True,
                    )
                    print("Loaded as SDXL model")
                except Exception as e:
                    print(f"Failed to load as SDXL, trying base model: {e}")
                    self.pipeline = StableDiffusionPipeline.from_single_file(
                        model_name,
                        torch_dtype=torch.float32,
                        use_safetensors=True,
                    )
                    print("Loaded as base SD model")
            else:
                # Load from Hugging Face or local diffusers format
                # Try XL first, fallback to base if it fails
                try:
                    from diffusers import StableDiffusionXLPipeline

                    self.pipeline = StableDiffusionXLPipeline.from_pretrained(
                        model_name,
                        torch_dtype=torch.float32,  # Use float32 for compatibility
                        use_safetensors=True,
                    )
                    print("Loaded as SDXL model")
                except Exception as e:
                    print(f"Failed to load as SDXL, trying base model: {e}")
                    from diffusers import StableDiffusionPipeline

                    self.pipeline = StableDiffusionPipeline.from_pretrained(
                        model_name,
                        torch_dtype=torch.float32,
                        use_safetensors=True,
                    )
                    print("Loaded as base SD model")

            # Move to device
            # Note: If using sequential CPU offload, don't use .to() as it conflicts
            # Sequential offload manages device automatically
            if self.device == "cuda":
                # Enable sequential CPU offload for memory efficiency
                # This automatically manages device placement
                self.pipeline.enable_sequential_cpu_offload()
                print("Sequential CPU offload enabled")
            else:
                # For CPU, just move to device
                self.pipeline = self.pipeline.to(self.device)

            self.current_model = model_name
            print(f"Model {model_name} loaded successfully")
        except Exception as e:
            print(f"Error loading model: {e}")
            import traceback

            traceback.print_exc()
            raise

    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 50,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
        callback: Optional[callable] = None,
    ) -> Optional[Image.Image]:
        """
        Generate image from prompt.

        Args:
            prompt: Text prompt
            negative_prompt: Negative prompt
            width: Image width
            height: Image height
            steps: Number of inference steps
            guidance_scale: Guidance scale
            seed: Random seed
            callback: Optional progress callback

        Returns:
            Generated PIL Image or None on error
        """
        if not self.is_available():
            raise RuntimeError("Image generation not available")

        if self.pipeline is None:
            # Try to load default model
            try:
                self.load_model()
            except Exception as e:
                print(f"Cannot load model: {e}")
                return None

        try:
            # Generator for reproducibility
            generator = None
            if seed is not None:
                # Generator should be on CUDA if using CUDA
                # Sequential CPU offload will handle device placement automatically
                gen_device = "cuda" if self.device == "cuda" else "cpu"
                generator = torch.Generator(device=gen_device).manual_seed(seed)

            # Generate image
            # Use callback_on_step_end instead of deprecated callback
            pipeline_kwargs = {
                "prompt": prompt,
                "negative_prompt": negative_prompt if negative_prompt else None,
                "width": width,
                "height": height,
                "num_inference_steps": steps,
                "guidance_scale": guidance_scale,
                "generator": generator,
            }

            if callback:
                pipeline_kwargs["callback_on_step_end"] = callback

            image = self.pipeline(**pipeline_kwargs).images[0]

            return image

        except Exception as e:
            print(f"Error generating image: {e}")
            return None

    def unload_model(self):
        """Unload current model to free memory."""
        if self.pipeline is not None:
            # First unload all LoRAs
            self.unload_all_loras()

            # Disable sequential CPU offload if enabled (ensures all components are accessible)
            try:
                if hasattr(self.pipeline, "disable_sequential_cpu_offload"):
                    self.pipeline.disable_sequential_cpu_offload()
            except:
                pass

            # Move pipeline to CPU before deletion to free GPU memory
            try:
                if hasattr(self.pipeline, "to"):
                    self.pipeline = self.pipeline.to("cpu")
            except:
                pass

            # Delete pipeline components explicitly
            try:
                if hasattr(self.pipeline, "unet"):
                    del self.pipeline.unet
                if hasattr(self.pipeline, "vae"):
                    del self.pipeline.vae
                if hasattr(self.pipeline, "text_encoder"):
                    if isinstance(self.pipeline.text_encoder, list):
                        for encoder in self.pipeline.text_encoder:
                            del encoder
                    else:
                        del self.pipeline.text_encoder
                if hasattr(self.pipeline, "text_encoder_2"):
                    del self.pipeline.text_encoder_2
            except:
                pass

            # Delete pipeline
            del self.pipeline
            self.pipeline = None
            self.current_model = None

            # Clear LoRAs when model is unloaded
            self.active_loras = []

            # Force garbage collection (multiple times)
            import gc

            for _ in range(3):
                gc.collect()

            # Clear CUDA cache if available (aggressive cleanup)
            if torch.cuda.is_available():
                try:
                    device = torch.cuda.current_device()
                    torch.cuda.synchronize(device)  # Wait for all operations to complete
                    
                    # Multiple cache clears
                    for _ in range(5):
                        torch.cuda.empty_cache()
                    
                    # Reset peak memory stats
                    try:
                        torch.cuda.reset_peak_memory_stats(device)
                    except:
                        pass
                    
                    # Collect IPC resources
                    try:
                        torch.cuda.ipc_collect()  # Collect IPC resources if available
                    except AttributeError:
                        pass
                    
                    # Final garbage collection
                    gc.collect()
                except Exception as e:
                    print(f"Error in GPU cleanup: {e}")
                    # Fallback
                    try:
                        torch.cuda.empty_cache()
                        gc.collect()
                    except:
                        pass

            print("Model unloaded and GPU memory freed")

    def load_lora(self, lora_path: str, weight: float = 1.0) -> bool:
        """
        Load a LoRA model.

        Args:
            lora_path: Path to LoRA .safetensors file
            weight: LoRA weight (strength)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            print("Image generation not available. Cannot load LoRA.")
            return False

        if self.pipeline is None:
            print("Base model not loaded. Cannot load LoRA.")
            return False

        # Check if LoRA file exists
        lora_file = Path(lora_path)
        if not lora_file.exists():
            print(f"LoRA file not found: {lora_path}")
            return False

        # Check if already loaded
        for active_lora in self.active_loras:
            if active_lora["path"] == str(lora_path):
                print(f"LoRA already loaded: {lora_path}")
                return True

        try:
            # Load LoRA weights using diffusers
            print(f"Loading LoRA: {lora_path} (weight: {weight})")

            # Suppress warnings about CLIPTextModel keys (many LoRAs only affect UNet, not text encoder)
            import warnings

            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore", message=".*No LoRA keys associated to CLIPTextModel.*"
                )
                warnings.filterwarnings(
                    "ignore",
                    message=".*No LoRA keys associated to CLIPTextModelWithProjection.*",
                )
                self.pipeline.load_lora_weights(str(lora_path), weight=weight)

            # Track loaded LoRA
            self.active_loras.append({"path": str(lora_path), "weight": weight})

            print(f"LoRA loaded successfully: {lora_path}")
            return True
        except AttributeError:
            # Fallback: try using fuse_lora if load_lora_weights doesn't exist
            try:
                print(f"Trying alternative LoRA loading method...")
                from diffusers import load_lora_weights

                load_lora_weights(self.pipeline, str(lora_path), weight=weight)
                self.active_loras.append({"path": str(lora_path), "weight": weight})
                print(f"LoRA loaded successfully (alternative method): {lora_path}")
                return True
            except Exception as e2:
                print(f"Error loading LoRA {lora_path} (alternative method): {e2}")
                return False
        except Exception as e:
            print(f"Error loading LoRA {lora_path}: {e}")
            import traceback

            traceback.print_exc()
            return False

    def unload_all_loras(self):
        """Unload all LoRA models."""
        if self.pipeline is None:
            return

        if not self.active_loras:
            return  # Nothing to unload

        try:
            # Try to unload LoRAs
            try:
                self.pipeline.unload_lora_weights()
            except AttributeError:
                # If unload_lora_weights doesn't exist, try fuse_lora with weight 0
                try:
                    from diffusers import load_lora_weights

                    # Unload by loading with weight 0 (this is a workaround)
                    for lora in self.active_loras:
                        try:
                            load_lora_weights(self.pipeline, lora["path"], weight=0.0)
                        except:
                            pass
                except:
                    pass

            self.active_loras = []
            print("All LoRAs unloaded")
        except Exception as e:
            print(f"Error unloading LoRAs: {e}")
            # Clear list anyway
            self.active_loras = []
