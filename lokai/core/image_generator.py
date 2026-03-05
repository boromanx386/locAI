"""
Image Generator for locAI.
Stable Diffusion image generation with configurable model location.
"""

from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image

# Optional imports - only load if available
try:
    import torch
    from diffusers import (
        StableDiffusionXLPipeline,
        StableDiffusionXLImg2ImgPipeline,
        StableDiffusionImg2ImgPipeline,
    )

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
        self._img2img_pipeline = None  # Cached img2img pipeline (reuses components)

    def is_available(self) -> bool:
        """Check if image generation is available."""
        return DIFFUSERS_AVAILABLE and self.device is not None

    def load_model(
        self,
        model_name: str = "stabilityai/stable-diffusion-xl-base-1.0",
        use_sequential_cpu_offload: bool = True,
    ):
        """
        Load Stable Diffusion model.

        Args:
            model_name: Model name (Hugging Face ID) or path to .safetensors file
            use_sequential_cpu_offload: If True, enable sequential CPU offload for memory efficiency
        """
        if not self.is_available():
            raise RuntimeError(
                "Image generation not available. Install diffusers and torch."
            )

        if self.current_model == model_name and self.pipeline is not None:
            # Model already loaded, but might be on CPU - move to GPU if needed
            if self.device == "cuda" and use_sequential_cpu_offload:
                # If sequential CPU offload is enabled, just enable it (model stays in memory)
                try:
                    if hasattr(self.pipeline, "enable_sequential_cpu_offload"):
                        self.pipeline.enable_sequential_cpu_offload()
                except:
                    pass
            elif self.device == "cuda":
                # Check if model is on CPU and move to GPU
                try:
                    # Try to detect if model is on CPU by checking first component
                    if (
                        hasattr(self.pipeline, "unet")
                        and next(self.pipeline.unet.parameters()).device.type == "cpu"
                    ):
                        self.pipeline = self.pipeline.to(self.device)
                        print("Model moved from CPU to GPU")
                except:
                    pass
            return  # Already loaded

        # Unload previous model first to free VRAM when switching
        if self.pipeline is not None:
            self.unload_model()

        print(f"Loading model: {model_name}")

        try:
            cache_kwargs = {"cache_dir": self.storage_path} if self.storage_path else {}

            # Check if it's a local .safetensors file
            if model_name.endswith(".safetensors") or Path(model_name).is_file():
                # Load from single file
                print(f"Loading from .safetensors file: {model_name}")
                from diffusers import StableDiffusionXLPipeline, StableDiffusionPipeline

                # Try XL first, fallback to base if it fails
                # Use float16 for faster inference and VAE decoding
                try:
                    self.pipeline = StableDiffusionXLPipeline.from_single_file(
                        model_name,
                        torch_dtype=torch.float16,  # Use float16 for faster inference and VAE decoding
                        use_safetensors=True,
                    )
                    print("Loaded as SDXL model (float16)")
                except Exception as e:
                    print(f"Failed to load as SDXL, trying base model: {e}")
                    self.pipeline = StableDiffusionPipeline.from_single_file(
                        model_name,
                        torch_dtype=torch.float16,
                        use_safetensors=True,
                    )
                    print("Loaded as base SD model (float16)")
            else:
                # Load from Hugging Face or local diffusers format
                # Try XL first, fallback to base if it fails
                try:
                    from diffusers import StableDiffusionXLPipeline

                    # Try with fp16 variant first (optimized VAE)
                    try:
                        self.pipeline = StableDiffusionXLPipeline.from_pretrained(
                            model_name,
                            torch_dtype=torch.float16,
                            use_safetensors=True,
                            variant="fp16",  # Use FP16 variant if available (optimized VAE)
                            **cache_kwargs,
                        )
                        print("Loaded as SDXL model (float16, fp16 variant)")
                    except Exception as e:
                        # Fallback: load without variant
                        self.pipeline = StableDiffusionXLPipeline.from_pretrained(
                            model_name,
                            torch_dtype=torch.float16,
                            use_safetensors=True,
                            **cache_kwargs,
                        )
                        print("Loaded as SDXL model (float16)")
                except Exception as e:
                    print(f"Failed to load as SDXL, trying base model: {e}")
                    from diffusers import StableDiffusionPipeline

                    self.pipeline = StableDiffusionPipeline.from_pretrained(
                        model_name,
                        torch_dtype=torch.float16,
                        use_safetensors=True,
                        **cache_kwargs,
                    )
                    print("Loaded as base SD model (float16)")

            # Move to device
            # Note: If using sequential CPU offload, don't use .to() as it conflicts
            # Sequential offload manages device automatically
            if self.device == "cuda":
                if use_sequential_cpu_offload:
                    # Enable sequential CPU offload for memory efficiency
                    # This automatically manages device placement
                    self.pipeline.enable_sequential_cpu_offload()
                    print("Sequential CPU offload enabled")
                else:
                    # Move entire pipeline to GPU (uses more VRAM but faster)
                    self.pipeline = self.pipeline.to(self.device)
                    print("Pipeline loaded directly to GPU (no CPU offload)")

                # Optimize VAE for faster decoding
                if hasattr(self.pipeline, "vae"):
                    try:
                        # Ensure VAE is on GPU
                        self.pipeline.vae = self.pipeline.vae.to(self.device)

                        # Ensure VAE is in float16 (should already be if model loaded in float16)
                        vae_dtype = next(self.pipeline.vae.parameters()).dtype
                        if vae_dtype != torch.float16:
                            self.pipeline.vae = self.pipeline.vae.to(
                                dtype=torch.float16
                            )
                            print("VAE converted to float16")

                        # Disable slicing/tiling for faster decoding
                        if hasattr(self.pipeline.vae, "disable_slicing"):
                            self.pipeline.vae.disable_slicing()
                        if hasattr(self.pipeline.vae, "disable_tiling"):
                            self.pipeline.vae.disable_tiling()
                    except Exception as e:
                        print(f"Warning: Could not optimize VAE: {e}")
            else:
                # For CPU, just move to device
                self.pipeline = self.pipeline.to(self.device)

            self.current_model = model_name
            self._img2img_pipeline = None  # Invalidate cached img2img pipeline
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

        # If model is on CPU, move to GPU before generation (if using GPU and not sequential offload)
        if self.device == "cuda":
            try:
                # Check if model is on CPU by checking first component
                if hasattr(self.pipeline, "unet"):
                    first_param = next(self.pipeline.unet.parameters())
                    if first_param.device.type == "cpu":
                        # Check if sequential CPU offload is enabled - if so, don't move manually
                        # Sequential offload will handle device placement automatically during generation
                        sequential_offload_enabled = getattr(
                            self.pipeline, "_sequential_cpu_offload_enabled", False
                        )
                        if not sequential_offload_enabled:
                            self.pipeline = self.pipeline.to(self.device)
                            print("Model moved from CPU to GPU for generation")
            except Exception as e:
                print(f"Warning: Could not check/move model device: {e}")

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

    def generate_image_img2img(
        self,
        init_image: Image.Image,
        prompt: str,
        negative_prompt: str = "",
        strength: float = 0.75,
        steps: int = 50,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
        callback: Optional[callable] = None,
    ) -> Optional[Image.Image]:
        """
        Generate image from init image + prompt (image-to-image).

        Args:
            init_image: PIL Image to use as base
            prompt: Text prompt for modifications
            negative_prompt: Negative prompt
            strength: How much to change the image (0.3-0.5 = subtle, 0.7-0.9 = strong)
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
            try:
                self.load_model()
            except Exception as e:
                print(f"Cannot load model: {e}")
                return None

        # Ensure init_image is RGB
        if init_image.mode != "RGB":
            init_image = init_image.convert("RGB")

        # Build or reuse img2img pipeline from existing components
        if self._img2img_pipeline is None:
            if hasattr(self.pipeline, "text_encoder_2"):
                self._img2img_pipeline = StableDiffusionXLImg2ImgPipeline(
                    vae=self.pipeline.vae,
                    text_encoder=self.pipeline.text_encoder,
                    text_encoder_2=self.pipeline.text_encoder_2,
                    tokenizer=self.pipeline.tokenizer,
                    tokenizer_2=self.pipeline.tokenizer_2,
                    unet=self.pipeline.unet,
                    scheduler=self.pipeline.scheduler,
                )
            else:
                self._img2img_pipeline = StableDiffusionImg2ImgPipeline(
                    vae=self.pipeline.vae,
                    text_encoder=self.pipeline.text_encoder,
                    tokenizer=self.pipeline.tokenizer,
                    unet=self.pipeline.unet,
                    scheduler=self.pipeline.scheduler,
                )
            if self.device == "cuda":
                try:
                    if hasattr(self.pipeline, "_sequential_cpu_offload_enabled"):
                        if getattr(
                            self.pipeline, "_sequential_cpu_offload_enabled", False
                        ):
                            self._img2img_pipeline.enable_sequential_cpu_offload()
                    else:
                        self._img2img_pipeline = self._img2img_pipeline.to(
                            self.device
                        )
                except Exception as e:
                    print(f"Warning: img2img device setup: {e}")

        pipe = self._img2img_pipeline

        try:
            generator = None
            if seed is not None:
                gen_device = "cuda" if self.device == "cuda" else "cpu"
                generator = torch.Generator(device=gen_device).manual_seed(seed)

            pipeline_kwargs = {
                "prompt": prompt,
                "image": init_image,
                "negative_prompt": negative_prompt if negative_prompt else None,
                "strength": strength,
                "num_inference_steps": steps,
                "guidance_scale": guidance_scale,
                "generator": generator,
            }
            if callback:
                pipeline_kwargs["callback_on_step_end"] = callback

            image = pipe(**pipeline_kwargs).images[0]
            return image
        except Exception as e:
            print(f"Error in img2img: {e}")
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
            self._img2img_pipeline = None

            # Clear LoRAs when model is unloaded
            self.active_loras = []

            import gc

            gc.collect()

            # Clear CUDA cache if available
            if torch.cuda.is_available():
                try:
                    device = torch.cuda.current_device()
                    torch.cuda.synchronize(device)
                    torch.cuda.empty_cache()

                    try:
                        torch.cuda.reset_peak_memory_stats(device)
                    except:
                        pass

                    try:
                        torch.cuda.ipc_collect()
                    except AttributeError:
                        pass

                    gc.collect()
                except Exception as e:
                    print(f"Error in GPU cleanup: {e}")

            print("Model unloaded and GPU memory freed")

    def clear_gpu_memory(self):
        """Clear GPU memory without unloading the model (moves to CPU)."""
        if self.pipeline is None:
            return

        try:
            # Disable sequential CPU offload if enabled (to manually control device)
            if hasattr(self.pipeline, "disable_sequential_cpu_offload"):
                try:
                    self.pipeline.disable_sequential_cpu_offload()
                except:
                    pass

            # Move pipeline to CPU to free GPU memory (but keep model loaded)
            # Note: If pipeline is in float16, it cannot run on CPU
            if hasattr(self.pipeline, "to"):
                try:
                    # Check if pipeline is in float16
                    pipeline_is_float16 = False
                    if hasattr(self.pipeline, "vae"):
                        try:
                            first_param = next(self.pipeline.vae.parameters())
                            if first_param.dtype == torch.float16:
                                pipeline_is_float16 = True
                        except:
                            pass

                    if not pipeline_is_float16:
                        # Pipeline is not in float16, can move to CPU
                        self.pipeline = self.pipeline.to("cpu")
                        print("Image model moved to CPU to free GPU memory")
                    else:
                        # Pipeline is in float16, keep on GPU (float16 doesn't work on CPU)
                        print(
                            "Image model kept on GPU (float16 doesn't work on CPU), clearing GPU cache only"
                        )
                except Exception as e:
                    print(f"Error moving model to CPU: {e}")

            # Aggressive GPU memory cleanup
            import gc

            if torch.cuda.is_available():
                try:
                    device = torch.cuda.current_device()
                    torch.cuda.synchronize(device)
                    torch.cuda.empty_cache()

                    try:
                        torch.cuda.reset_peak_memory_stats(device)
                    except:
                        pass

                    try:
                        torch.cuda.ipc_collect()
                    except AttributeError:
                        pass

                    gc.collect()
                    print("GPU memory cleared")
                except Exception as e:
                    print(f"Error in GPU cleanup: {e}")
        except Exception as e:
            print(f"Error clearing GPU memory: {e}")

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
