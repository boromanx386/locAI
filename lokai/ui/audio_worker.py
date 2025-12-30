"""
Audio Generation Worker for locAI.
Background thread for generating audio without blocking UI.
"""

from PySide6.QtCore import QThread, Signal
from lokai.core.audio_generator import AudioGenerator
from lokai.core.config_manager import ConfigManager


class AudioGenerationWorker(QThread):
    """Worker thread for audio generation."""

    audio_generated = Signal(str)  # audio_path
    error_occurred = Signal(str)  # error message
    progress_updated = Signal(int)  # progress percentage

    def __init__(
        self,
        audio_generator: AudioGenerator,
        prompt: str,
        config_manager: ConfigManager,
        seed: int = None,
    ):
        """
        Initialize AudioGenerationWorker.

        Args:
            audio_generator: AudioGenerator instance
            prompt: Audio generation prompt
            config_manager: ConfigManager for settings
            seed: Random seed for audio generation (None = random)
        """
        super().__init__()
        self.audio_generator = audio_generator
        self.prompt = prompt
        self.config_manager = config_manager
        self.seed = seed

    def run(self):
        """Run audio generation in background thread."""
        try:
            # Get settings from config
            model_name = self.config_manager.get(
                "audio_gen.model", "stabilityai/stable-audio-open-1.0"
            )
            audio_length = self.config_manager.get("audio_gen.audio_length", 10.0)
            num_inference_steps = self.config_manager.get("audio_gen.steps", 200)
            guidance_scale = self.config_manager.get("audio_gen.guidance_scale", 7.0)
            negative_prompt = self.config_manager.get(
                "audio_gen.negative_prompt", "Low quality."
            )
            use_cpu_offload = self.config_manager.get(
                "audio_gen.use_sequential_cpu_offload", False
            )
            num_waveforms = self.config_manager.get(
                "audio_gen.num_waveforms_per_prompt", 1
            )

            # Load model if needed
            model_changed = self.audio_generator.current_model != model_name
            if model_changed:
                self.progress_updated.emit(10)
                self.audio_generator.load_model(
                    model_name, use_sequential_cpu_offload=use_cpu_offload
                )
                self.progress_updated.emit(30)

            # Progress callback
            def progress_callback(pipe, step_index, timestep, callback_kwargs):
                try:
                    # Calculate progress: 30% (loading) + 60% (generation) = 90%
                    if num_inference_steps > 0 and step_index is not None:
                        progress = 30 + int((step_index / num_inference_steps) * 60)
                        # Clamp to 90% max (remaining 10% for saving)
                        progress = min(progress, 90)
                        self.progress_updated.emit(progress)
                except Exception as e:
                    # Ignore callback errors
                    pass

                # Must return callback_kwargs
                return callback_kwargs if callback_kwargs is not None else {}

            # Generate audio
            self.progress_updated.emit(40)
            audio_path = self.audio_generator.generate_audio_from_text(
                prompt=self.prompt,
                negative_prompt=negative_prompt,
                audio_length_in_s=audio_length,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                seed=self.seed,
                callback=progress_callback,
                num_waveforms_per_prompt=num_waveforms,
            )

            if audio_path is None:
                self.error_occurred.emit("Failed to generate audio")
                return

            self.progress_updated.emit(100)
            self.audio_generated.emit(audio_path)

        except Exception as e:
            error_msg = f"Error generating audio: {str(e)}"
            print(error_msg)
            import traceback

            traceback.print_exc()
            self.error_occurred.emit(error_msg)

