"""
Audio Generator for locAI.
Stable Audio Open 1.0 for text-to-audio generation.
"""

import os
from pathlib import Path
from typing import Optional
import time
import numpy as np

# Optional imports - only load if available
try:
    import torch
    from diffusers import StableAudioPipeline
    import soundfile as sf

    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False
    print("Warning: diffusers or soundfile not available. Audio generation disabled.")


class AudioGenerator:
    """Audio generator using Stable Audio Open 1.0."""

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize AudioGenerator.

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

        # Setup environment if path provided
        if storage_path:
            self.setup_environment(storage_path)

    def setup_environment(self, storage_path: str):
        """Setup environment variables for Hugging Face cache."""
        storage = Path(storage_path)
        diffusers_path = storage / "diffusers"

        os.environ["HF_HOME"] = str(storage)
        os.environ["TRANSFORMERS_CACHE"] = str(storage)
        os.environ["HF_DATASETS_CACHE"] = str(storage)
        os.environ["HF_HUB_CACHE"] = str(storage)
        os.environ["DIFFUSERS_CACHE"] = str(diffusers_path)
        os.environ["HF_DIFFUSERS_CACHE"] = str(diffusers_path)

    def is_available(self) -> bool:
        """Check if audio generation is available."""
        return DIFFUSERS_AVAILABLE and self.device is not None

    def load_model(
        self,
        model_name: str = "stabilityai/stable-audio-open-1.0",
        use_sequential_cpu_offload: bool = False,
    ):
        """
        Load Stable Audio Open model.

        Args:
            model_name: Model name (Hugging Face ID)
            use_sequential_cpu_offload: If True, enable sequential CPU offload (optional)
        """
        if not self.is_available():
            raise RuntimeError(
                "Audio generation not available. Install diffusers and torch."
            )

        if self.current_model == model_name and self.pipeline is not None:
            return  # Already loaded

        # Unload previous model first to free VRAM when switching
        if self.pipeline is not None:
            self.unload_model()

        print(f"Loading audio model: {model_name}")

        # Ensure environment is set up before loading (in case it was reset)
        if self.storage_path:
            self.setup_environment(self.storage_path)

        # Clear GPU memory before loading model
        if torch.cuda.is_available():
            print("[AudioGenerator] Clearing GPU memory before loading audio model...")
            import gc
            for _ in range(5):
                gc.collect()
                torch.cuda.empty_cache()
            print("[AudioGenerator] GPU memory cleared")

        try:
            self.pipeline = StableAudioPipeline.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
            )

            # Move to device
            if self.device == "cuda":
                # Optional CPU offload (user choice)
                self._last_cpu_offload_setting = use_sequential_cpu_offload
                if use_sequential_cpu_offload:
                    print("[AudioGenerator] Using sequential CPU offload (optional)...")
                    try:
                        self.pipeline.enable_sequential_cpu_offload()
                        print("Sequential CPU offload enabled")
                    except:
                        print("Warning: Sequential CPU offload failed, loading directly to GPU")
                        self.pipeline = self.pipeline.to(self.device)
                        self._last_cpu_offload_setting = False
                else:
                    print("[AudioGenerator] Loading directly to GPU (no CPU offload)")
                    self.pipeline = self.pipeline.to(self.device)
            else:
                self._last_cpu_offload_setting = False
                self.pipeline = self.pipeline.to(self.device)

            self.current_model = model_name
            print(f"Audio model {model_name} loaded successfully")
        except Exception as e:
            print(f"Error loading audio model: {e}")
            import traceback

            traceback.print_exc()
            raise

    def generate_audio_from_text(
        self,
        prompt: str,
        negative_prompt: str = "Low quality.",
        audio_length_in_s: float = 10.0,
        num_inference_steps: int = 200,
        guidance_scale: float = 7.0,
        seed: Optional[int] = None,
        callback: Optional[callable] = None,
        num_waveforms_per_prompt: int = 1,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate audio from text prompt.

        Args:
            prompt: Text prompt describing the audio to generate
            negative_prompt: Negative prompt (what to avoid)
            audio_length_in_s: Length of audio in seconds (max 47.0)
            num_inference_steps: Number of inference steps
            guidance_scale: Guidance scale (CFG)
            seed: Random seed for reproducibility
            callback: Optional progress callback
            num_waveforms_per_prompt: Number of audio variations to generate (1-4)

        Returns:
            Path to generated audio file (first variation) or None on error
        """
        if not self.is_available():
            raise RuntimeError("Audio generation not available")

        if self.pipeline is None:
            try:
                self.load_model()
            except Exception as e:
                print(f"Cannot load audio model: {e}")
                return None

        try:
            # Clamp audio length to max 47 seconds
            audio_length_in_s = min(audio_length_in_s, 47.0)
            audio_length_in_s = max(audio_length_in_s, 1.0)

            # Clear GPU memory before generation
            if torch.cuda.is_available():
                import gc
                for _ in range(2):
                    gc.collect()
                    torch.cuda.empty_cache()

            # Generator for reproducibility
            generator = None
            if seed is not None:
                gen_device = "cuda" if self.device == "cuda" else "cpu"
                generator = torch.Generator(device=gen_device).manual_seed(seed)

            # Generate audio
            print(f"[AudioGenerator] Generating audio: '{prompt[:50]}...'")
            print(f"[AudioGenerator] Length: {audio_length_in_s}s, Steps: {num_inference_steps}, Variations: {num_waveforms_per_prompt}")

            # Note: StableAudioPipeline doesn't support callback_on_step_end
            # Progress will be updated manually in the worker using timer-based simulation
            output = self.pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                audio_end_in_s=audio_length_in_s,
                generator=generator,
                num_waveforms_per_prompt=num_waveforms_per_prompt,
            )

            # Extract audio from output
            sample_rate = self.pipeline.vae.sampling_rate
            
            # Save to output directory
            if output_path:
                output_dir = Path(output_path)
            elif self.storage_path:
                from lokai.core.paths import SUBDIR_GENERATED_AUDIO
                output_dir = Path(self.storage_path) / SUBDIR_GENERATED_AUDIO
            else:
                from lokai.core.paths import get_audio_output_dir
                from lokai.core.config_manager import ConfigManager
                config_manager = ConfigManager()
                output_dir = get_audio_output_dir(config_manager)
            output_dir.mkdir(exist_ok=True, parents=True)

            base_filename = f"audio_{int(time.time())}"
            first_audio_path = None

            # Process and save all variations
            if num_waveforms_per_prompt > 1 and len(output.audios) > 1:
                print(f"[AudioGenerator] Generated {len(output.audios)} variations, saving all...")

            for idx, audio_var in enumerate(output.audios):
                # Convert to numpy if needed
                if isinstance(audio_var, torch.Tensor):
                    audio_var = audio_var.cpu().numpy()

                # Convert to float32 (soundfile doesn't support float16)
                if audio_var.dtype == np.float16:
                    audio_var = audio_var.astype(np.float32)
                elif audio_var.dtype != np.float32:
                    audio_var = audio_var.astype(np.float32)

                # Ensure stereo (2 channels)
                if len(audio_var.shape) == 1:
                    audio_var = audio_var.reshape(1, -1)
                elif audio_var.shape[0] == 1:
                    audio_var = audio_var.repeat(2, axis=0)

                # Transpose if needed
                if audio_var.shape[0] > audio_var.shape[1]:
                    audio_var = audio_var.T

                # Ensure correct shape: [samples, channels] for soundfile
                if audio_var.shape[1] != 2:
                    if audio_var.shape[0] == 2:
                        audio_var = audio_var.T

                # Normalize audio to [-1, 1] range
                audio_max = abs(audio_var).max()
                if audio_max > 1.0:
                    audio_var = audio_var / audio_max

                # Generate filename
                if num_waveforms_per_prompt > 1:
                    filename = f"{base_filename}_var{idx+1}.wav"
                else:
                    filename = f"{base_filename}.wav"
                
                audio_path = output_dir / filename

                # Save audio file
                sf.write(str(audio_path), audio_var, sample_rate)
                
                if idx == 0:
                    first_audio_path = audio_path
                    print(f"[AudioGenerator] Saving audio to {audio_path}")
                else:
                    print(f"[AudioGenerator] Saving variation {idx+1} to {audio_path}")

            print(f"[AudioGenerator] Audio generated successfully: {first_audio_path}")
            return str(first_audio_path)

        except Exception as e:
            print(f"Error generating audio: {e}")
            import traceback

            traceback.print_exc()
            return None

    def unload_model(self):
        """Unload current model to free memory."""
        if self.pipeline is not None:
            try:
                if hasattr(self.pipeline, "disable_sequential_cpu_offload"):
                    self.pipeline.disable_sequential_cpu_offload()
            except:
                pass

            try:
                self.pipeline = self.pipeline.to("cpu")
            except:
                pass

            # Delete components
            try:
                if hasattr(self.pipeline, "transformer"):
                    del self.pipeline.transformer
                if hasattr(self.pipeline, "vae"):
                    del self.pipeline.vae
                if hasattr(self.pipeline, "text_encoder"):
                    del self.pipeline.text_encoder
            except:
                pass

            del self.pipeline
            self.pipeline = None
            self.current_model = None

            # Clear GPU cache
            import gc

            if torch.cuda.is_available():
                for _ in range(5):
                    gc.collect()
                    torch.cuda.empty_cache()

            print("Audio model unloaded and GPU memory freed")

    def clear_gpu_memory(self):
        """Clear GPU memory without unloading the model (moves to CPU)."""
        if self.pipeline is None:
            return

        try:
            # Disable sequential CPU offload if enabled
            if hasattr(self.pipeline, "disable_sequential_cpu_offload"):
                try:
                    self.pipeline.disable_sequential_cpu_offload()
                except:
                    pass

            # Move pipeline to CPU to free GPU memory
            if hasattr(self.pipeline, "to"):
                try:
                    self.pipeline = self.pipeline.to("cpu")
                    print("Audio model moved to CPU to free GPU memory")
                except Exception as e:
                    print(f"Error moving audio model to CPU: {e}")

            # Aggressive GPU memory cleanup
            import gc

            if torch.cuda.is_available():
                try:
                    device = torch.cuda.current_device()
                    torch.cuda.synchronize(device)

                    for _ in range(10):
                        torch.cuda.empty_cache()

                    try:
                        torch.cuda.reset_peak_memory_stats(device)
                    except:
                        pass

                    try:
                        torch.cuda.ipc_collect()
                    except AttributeError:
                        pass

                    for _ in range(3):
                        gc.collect()
                        torch.cuda.empty_cache()

                    gc.collect()
                    print("GPU memory cleared")
                except Exception as e:
                    print(f"Error in GPU cleanup: {e}")
        except Exception as e:
            print(f"Error clearing GPU memory: {e}")

