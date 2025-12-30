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

            # Generate video
            self.progress_updated.emit(60)
            video_path = self.video_generator.generate_video_from_image(
                image=image,
                num_frames=num_frames,
                num_inference_steps=num_inference_steps,
                motion_bucket_id=motion_bucket_id,
                fps=fps,
                seed=self.seed,
                resolution=resolution,
            )

            if video_path is None:
                self.error_occurred.emit("Failed to generate video")
                return

            self.progress_updated.emit(100)
            self.video_generated.emit(video_path)

        except Exception as e:
            error_msg = f"Error generating video: {str(e)}"
            print(error_msg)
            import traceback

            traceback.print_exc()
            self.error_occurred.emit(error_msg)
