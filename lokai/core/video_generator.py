"""
Video Generator for locAI.
Stable Video Diffusion (SVD) for image-to-video generation.
"""

import os
from pathlib import Path
from typing import Optional
from PIL import Image
import numpy as np

# Optional imports - only load if available
try:
    import torch
    from diffusers import StableVideoDiffusionPipeline
    from diffusers.utils import export_to_video

    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False
    print("Warning: diffusers not available. Video generation disabled.")


class VideoGenerator:
    """Video generator using Stable Video Diffusion."""

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize VideoGenerator.

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
        """Check if video generation is available."""
        return DIFFUSERS_AVAILABLE and self.device is not None

    def load_model(
        self,
        model_name: str = "stabilityai/stable-video-diffusion-img2vid",
        use_sequential_cpu_offload: bool = True,
    ):
        """
        Load Stable Video Diffusion model.

        Args:
            model_name: Model name (Hugging Face ID)
            use_sequential_cpu_offload: If True, enable sequential CPU offload
        """
        if not self.is_available():
            raise RuntimeError(
                "Video generation not available. Install diffusers and torch."
            )

        if self.current_model == model_name and self.pipeline is not None:
            return  # Already loaded

        print(f"Loading video model: {model_name}")

        # Clear GPU memory before loading model (in case image generation left memory)
        if torch.cuda.is_available():
            print("[VideoGenerator] Clearing GPU memory before loading video model...")
            import gc
            for _ in range(5):
                gc.collect()
                torch.cuda.empty_cache()
            print("[VideoGenerator] GPU memory cleared")

        try:
            self.pipeline = StableVideoDiffusionPipeline.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
                variant="fp16",
            )

            # Move to device
            # ALWAYS use CPU offload for SVD to prevent VRAM overflow
            if self.device == "cuda":
                # Force CPU offload even if user didn't select it (SVD needs it)
                self._last_cpu_offload_setting = True
                print("[VideoGenerator] Forcing CPU offload for SVD (required for 16GB VRAM)...")
                try:
                    self.pipeline.enable_model_cpu_offload()
                    print("Model CPU offload enabled (lowest VRAM usage)")
                except:
                    # Fallback to sequential CPU offload
                    try:
                        self.pipeline.enable_sequential_cpu_offload()
                        print("Sequential CPU offload enabled")
                    except:
                        # Last resort: try to load with low_mem settings
                        print("Warning: CPU offload failed, loading directly to GPU (may cause OOM)")
                        self.pipeline = self.pipeline.to(self.device)
                        self._last_cpu_offload_setting = False
            else:
                self._last_cpu_offload_setting = False
                self.pipeline = self.pipeline.to(self.device)

            self.current_model = model_name
            print(f"Video model {model_name} loaded successfully")
        except Exception as e:
            print(f"Error loading video model: {e}")
            import traceback

            traceback.print_exc()
            raise

    def generate_video_from_image(
        self,
        image: Image.Image,
        num_frames: int = 14,
        num_inference_steps: int = 25,
        motion_bucket_id: int = 127,
        fps: int = 7,
        seed: Optional[int] = None,
        callback: Optional[callable] = None,
        resolution: str = "auto",
    ) -> Optional[str]:
        """
        Generate video from image.

        Args:
            image: Input PIL Image (will be resized based on resolution setting)
            num_frames: Number of frames to generate (14 for SVD, 25 for SVD-XT)
            num_inference_steps: Number of inference steps
            motion_bucket_id: Motion bucket ID (controls motion amount)
            fps: Frames per second for output video
            seed: Random seed
            callback: Optional progress callback

        Returns:
            Path to generated video file or None on error
        """
        if not self.is_available():
            raise RuntimeError("Video generation not available")

        if self.pipeline is None:
            try:
                self.load_model()
            except Exception as e:
                print(f"Cannot load video model: {e}")
                return None

        try:
            # Resize image to SVD required resolution
            # SVD supports two resolutions with 9:16 or 16:9 aspect ratio:
            # - 576x1024 (portrait/vertical)
            # - 1024x576 (landscape/horizontal/wide)
            original_width, original_height = image.size
            print(
                f"[VideoGenerator] Original image size: {original_width}x{original_height}"
            )
            print(f"[VideoGenerator] Resolution setting: {resolution}")

            # Determine target resolution based on setting
            # Note: PIL Image.resize expects (width, height)
            # SVD supports: 576x1024 (portrait) or 1024x576 (landscape)
            if resolution == "auto":
                # Auto-detect based on aspect ratio
                aspect_ratio = original_width / original_height
                print(f"[VideoGenerator] Aspect ratio: {aspect_ratio}")
                if (
                    aspect_ratio < 1.0
                ):  # Portrait (height > width) - use portrait format
                    target_size = (576, 1024)  # width=576, height=1024
                    print(f"[VideoGenerator] Auto-detected: Portrait -> 576x1024")
                else:  # Landscape (width >= height) - use landscape format
                    target_size = (1024, 576)  # width=1024, height=576
                    print(f"[VideoGenerator] Auto-detected: Landscape -> 1024x576")
            elif resolution == "576x1024":
                # User selected 576x1024 = width=576, height=1024
                # Use it directly - PIL resize expects (width, height)
                target_size = (576, 1024)
                print(
                    f"[VideoGenerator] Using forced resolution: 576x1024 (width x height)"
                )
            elif resolution == "1024x576":
                # User selected 1024x576 = width=1024, height=576
                # Use it directly - PIL resize expects (width, height)
                target_size = (1024, 576)
                print(
                    f"[VideoGenerator] Using forced resolution: 1024x576 (width x height)"
                )
            else:
                # Fallback to auto if invalid setting
                print(
                    f"[VideoGenerator] Invalid resolution '{resolution}', falling back to auto"
                )
                aspect_ratio = original_width / original_height
                if aspect_ratio < 1.0:
                    target_size = (576, 1024)
                else:
                    target_size = (1024, 576)

            print(f"[VideoGenerator] Resizing to: {target_size} (width x height)")
            resized_image = image.resize(target_size, Image.Resampling.LANCZOS)
            print(
                f"[VideoGenerator] Resized image size: {resized_image.size[0]}x{resized_image.size[1]}"
            )

            # If user wants 576x1024, rotate input image 90 degrees before sending to SVD
            if resolution == "576x1024":
                print(
                    f"[VideoGenerator] Rotating input image 90 degrees before sending to SVD"
                )
                resized_image = resized_image.rotate(90, expand=True)
                print(
                    f"[VideoGenerator] Rotated input image to: {resized_image.size[0]}x{resized_image.size[1]}"
                )

            image = resized_image

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

            # Generate video frames
            # Use smaller decode_chunk_size to reduce VRAM usage
            decode_chunk_size = 4  # Reduced from 8 to save VRAM (can go to 2 if needed)
            frames = self.pipeline(
                image,
                decode_chunk_size=decode_chunk_size,
                generator=generator,
                num_frames=num_frames,
                num_inference_steps=num_inference_steps,
                motion_bucket_id=motion_bucket_id,
            ).frames[0]

            # SVD pipeline ALWAYS outputs 1024x576 (landscape), so rotate frames if user wants portrait
            if resolution == "576x1024":
                print(
                    f"[VideoGenerator] SVD always outputs 1024x576, rotating {len(frames)} frames 90 degrees to get 576x1024"
                )

                rotated_frames = []
                for i, frame in enumerate(frames):
                    # Convert to PIL Image if it's numpy array
                    if isinstance(frame, np.ndarray):
                        frame_img = Image.fromarray(frame)
                    elif hasattr(frame, "mode"):  # Already PIL Image
                        frame_img = frame
                    else:
                        # Try to convert
                        frame_img = Image.fromarray(np.array(frame))

                    # Rotate -90 degrees (clockwise) to fix orientation after SVD processing
                    # We rotated input 90 degrees, so rotate output -90 to get back to correct orientation
                    rotated_frame = frame_img.rotate(-90, expand=True)

                    # Convert back to numpy if original was numpy
                    if isinstance(frame, np.ndarray):
                        rotated_frames.append(np.array(rotated_frame))
                    else:
                        rotated_frames.append(rotated_frame)

                frames = rotated_frames
                print(
                    f"[VideoGenerator] Successfully rotated frames from 1024x576 to 576x1024"
                )

            # UNLOAD MODEL BEFORE EXPORT to free VRAM
            print("[VideoGenerator] Unloading model before export to free VRAM...")
            model_was_unloaded = False
            if self.pipeline is not None and torch.cuda.is_available():
                try:
                    # Disable CPU offload if enabled
                    if hasattr(self.pipeline, "disable_sequential_cpu_offload"):
                        try:
                            self.pipeline.disable_sequential_cpu_offload()
                        except:
                            pass
                    if hasattr(self.pipeline, "disable_model_cpu_offload"):
                        try:
                            self.pipeline.disable_model_cpu_offload()
                        except:
                            pass
                    
                    # Move pipeline to CPU
                    try:
                        self.pipeline = self.pipeline.to("cpu")
                        model_was_unloaded = True
                    except:
                        pass
                    
                    # Clear GPU cache aggressively
                    import gc
                    for _ in range(5):
                        gc.collect()
                        torch.cuda.empty_cache()
                    
                    print("[VideoGenerator] Model unloaded, GPU memory freed")
                except Exception as e:
                    print(f"[VideoGenerator] Error unloading model: {e}")

            # Clear GPU memory BEFORE export to prevent OOM during encoding
            print("[VideoGenerator] Clearing GPU memory before video export...")
            if torch.cuda.is_available():
                import gc
                # Move frames to CPU if they're on GPU
                if isinstance(frames, list) and len(frames) > 0:
                    if isinstance(frames[0], torch.Tensor):
                        frames = [frame.cpu().numpy() if frame.is_cuda else frame.numpy() for frame in frames]
                    elif isinstance(frames[0], np.ndarray):
                        # Already numpy, but make sure it's on CPU
                        pass
                
                # Clear GPU cache
                for _ in range(3):
                    gc.collect()
                    torch.cuda.empty_cache()
                print("[VideoGenerator] GPU memory cleared")

            # Save to output directory
            import time

            from lokai.core.config_manager import ConfigManager
            config_manager = ConfigManager()
            
            # Get output path from config, fallback to default
            output_path = config_manager.get("video_gen.output_path")
            if output_path:
                output_dir = Path(output_path)
            elif self.storage_path:
                output_dir = Path(self.storage_path) / "generated_videos"
            else:
                output_dir = Path(config_manager.get_config_dir()) / "generated_videos"

            output_dir.mkdir(exist_ok=True, parents=True)

            filename = f"video_{int(time.time())}.mp4"
            video_path = output_dir / filename

            # Export frames to video - use imageio directly (more memory efficient)
            print(f"[VideoGenerator] Exporting {len(frames)} frames to video (this may take a moment)...")
            
            # Convert frames to numpy arrays (one at a time to save memory)
            frame_arrays = []
            for i, frame in enumerate(frames):
                if isinstance(frame, Image.Image):
                    frame_arrays.append(np.array(frame))
                elif isinstance(frame, np.ndarray):
                    # Make sure it's uint8 and on CPU
                    if frame.dtype != np.uint8:
                        frame = (frame * 255).astype(np.uint8) if frame.max() <= 1.0 else frame.astype(np.uint8)
                    frame_arrays.append(frame)
                else:
                    frame_arrays.append(np.array(frame))
                
                # Clear reference to original frame to free memory
                frames[i] = None
                if i % 5 == 0:
                    import gc
                    gc.collect()
            
            # Clear frames list
            frames = None
            import gc
            gc.collect()
            
            # Try imageio first (most memory efficient)
            try:
                import imageio
                print("[VideoGenerator] Using imageio for export (memory efficient)...")
                # Use imageio with low memory settings
                imageio.mimsave(
                    str(video_path), 
                    frame_arrays, 
                    fps=fps, 
                    codec='libx264',
                    quality=8,
                    macro_block_size=None  # Let imageio decide
                )
                print(f"[VideoGenerator] Video exported successfully using imageio to {video_path}")
            except ImportError:
                print("[VideoGenerator] imageio not available, trying opencv...")
                try:
                    import cv2
                    # Get frame dimensions
                    h, w = frame_arrays[0].shape[:2]
                    
                    # Create video writer with H.264 codec (better compression)
                    fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264 codec
                    out = cv2.VideoWriter(str(video_path), fourcc, fps, (w, h))
                    
                    if not out.isOpened():
                        # Fallback to mp4v
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        out = cv2.VideoWriter(str(video_path), fourcc, fps, (w, h))
                    
                    # Write frames one by one
                    for i, frame in enumerate(frame_arrays):
                        if len(frame.shape) == 3 and frame.shape[2] == 3:
                            # RGB to BGR for OpenCV
                            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                            out.write(frame_bgr)
                        else:
                            out.write(frame)
                        
                        # Clear frame from list to free memory
                        frame_arrays[i] = None
                        if i % 5 == 0:
                            gc.collect()
                    
                    out.release()
                    print(f"[VideoGenerator] Video exported successfully using OpenCV to {video_path}")
                except Exception as e2:
                    print(f"[VideoGenerator] OpenCV failed: {e2}, trying export_to_video as last resort...")
                    # Last resort: use export_to_video
                    # Reconstruct frames list
                    frames = [Image.fromarray(f) if isinstance(f, np.ndarray) else f for f in frame_arrays]
                    export_to_video(frames, str(video_path), fps=fps)
                    print(f"[VideoGenerator] Video exported successfully using export_to_video to {video_path}")
            except Exception as e:
                print(f"[VideoGenerator] imageio failed: {e}, trying opencv...")
                try:
                    import cv2
                    # Get frame dimensions
                    h, w = frame_arrays[0].shape[:2]
                    
                    # Create video writer
                    fourcc = cv2.VideoWriter_fourcc(*'avc1')
                    out = cv2.VideoWriter(str(video_path), fourcc, fps, (w, h))
                    
                    if not out.isOpened():
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        out = cv2.VideoWriter(str(video_path), fourcc, fps, (w, h))
                    
                    # Write frames
                    for i, frame in enumerate(frame_arrays):
                        if len(frame.shape) == 3 and frame.shape[2] == 3:
                            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                            out.write(frame_bgr)
                        else:
                            out.write(frame)
                        frame_arrays[i] = None
                        if i % 5 == 0:
                            gc.collect()
                    
                    out.release()
                    print(f"[VideoGenerator] Video exported successfully using OpenCV to {video_path}")
                except Exception as e2:
                    print(f"[VideoGenerator] All export methods failed: {e2}")
                    raise

            # Reload model after export if it was unloaded
            if model_was_unloaded and self.pipeline is not None and self.current_model:
                print("[VideoGenerator] Reloading model after export...")
                try:
                    use_cpu_offload = getattr(self, '_last_cpu_offload_setting', True)
                    if torch.cuda.is_available() and use_cpu_offload:
                        try:
                            self.pipeline.enable_model_cpu_offload()
                            print("[VideoGenerator] Model CPU offload re-enabled")
                        except:
                            self.pipeline.enable_sequential_cpu_offload()
                            print("[VideoGenerator] Sequential CPU offload re-enabled")
                    elif torch.cuda.is_available():
                        self.pipeline = self.pipeline.to("cuda")
                        print("[VideoGenerator] Model moved back to GPU")
                except Exception as e:
                    print(f"[VideoGenerator] Error reloading model: {e}")

            return str(video_path)

        except Exception as e:
            print(f"Error generating video: {e}")
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

            print("Video model unloaded and GPU memory freed")

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
                        self.pipeline = self.pipeline.to("cpu")
                        print("Video model moved to CPU to free GPU memory")
                    else:
                        print(
                            "Video model kept on GPU (float16 doesn't work on CPU), clearing GPU cache only"
                        )
                except Exception as e:
                    print(f"Error moving video model to CPU: {e}")

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
