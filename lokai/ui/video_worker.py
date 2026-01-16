"""
Video Generation Worker for locAI.
Background thread for generating videos from images.
"""

from PySide6.QtCore import QThread, Signal
from lokai.core.video_generator import VideoGenerator
from lokai.core.config_manager import ConfigManager
from PIL import Image
from pathlib import Path


class VideoGenerationWorker(QThread):
    """Worker thread for video generation."""

    video_generated = Signal(str)  # video_path
    error_occurred = Signal(str)  # error message
    progress_updated = Signal(int)  # progress percentage

    def __init__(
        self,
        video_generator: VideoGenerator,
        image_path: str,  # Path to input image
        config_manager: ConfigManager,
        seed: int = None,
    ):
        super().__init__()
        self.video_generator = video_generator
        self.image_path = image_path
        self.config_manager = config_manager
        self.seed = seed

    def run(self):
        """Run video generation in background thread."""
        try:
            # Load input image
            self.progress_updated.emit(10)
            image = Image.open(self.image_path).convert("RGB")
            self.progress_updated.emit(20)

            # Get settings from config
            model_name = self.config_manager.get(
                "video_gen.model", "stabilityai/stable-video-diffusion-img2vid"
            )
            num_frames = self.config_manager.get("video_gen.num_frames", 14)
            num_inference_steps = self.config_manager.get("video_gen.steps", 25)
            motion_bucket_id = self.config_manager.get(
                "video_gen.motion_bucket_id", 127
            )
            fps = self.config_manager.get("video_gen.fps", 7)
            resolution = self.config_manager.get("video_gen.resolution", "auto")
            print(f"[VideoWorker] Resolution from config: {resolution}")

            # Load model if needed
            model_changed = self.video_generator.current_model != model_name
            if model_changed:
                self.progress_updated.emit(30)
                use_cpu_offload = self.config_manager.get(
                    "video_gen.use_sequential_cpu_offload", True
                )
                self.video_generator.load_model(
                    model_name, use_sequential_cpu_offload=use_cpu_offload
                )
                self.progress_updated.emit(50)

            # Progress callback using callback_on_step_end signature
            # Signature: (pipe, step_index, timestep, callback_kwargs)
            # step_index is 0-based, so step_index=0 is first step, step_index=steps-1 is last step
            def progress_callback(pipe, step_index, timestep, callback_kwargs):
                try:
                    # Calculate progress: 50% (loading) + 40% (generation) = 90%
                    # step_index is 0-based, so we add 1 to get current step (1 to steps)
                    if num_inference_steps > 0 and step_index is not None:
                        # step_index goes from 0 to num_inference_steps-1, so (step_index + 1) / num_inference_steps gives progress
                        current_step = step_index + 1
                        progress = 50 + int((current_step / num_inference_steps) * 40)
                        # Clamp to 90% max (remaining 10% for saving/export)
                        progress = min(progress, 90)
                        self.progress_updated.emit(progress)
                except Exception as e:
                    # Ignore callback errors
                    pass

                # Must return callback_kwargs
                return callback_kwargs if callback_kwargs is not None else {}

            # Generate video (start at 50% since model is loaded)
            self.progress_updated.emit(50)
            video_path = self.video_generator.generate_video_from_image(
                image=image,
                num_frames=num_frames,
                num_inference_steps=num_inference_steps,
                motion_bucket_id=motion_bucket_id,
                fps=fps,
                seed=self.seed,
                resolution=resolution,
                callback=progress_callback,
            )

            if video_path is None:
                self.error_occurred.emit("Failed to generate video")
                return

            # Export is done in generator, so we're at 100%
            self.progress_updated.emit(100)
            self.video_generated.emit(video_path)

        except Exception as e:
            error_msg = f"Error generating video: {str(e)}"
            print(error_msg)
            import traceback

            traceback.print_exc()
            self.error_occurred.emit(error_msg)
