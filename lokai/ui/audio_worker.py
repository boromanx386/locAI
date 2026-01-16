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
            output_path = self.config_manager.get("audio_gen.output_folder")

            # Load model if needed
            model_changed = self.audio_generator.current_model != model_name
            if model_changed:
                self.progress_updated.emit(10)
                self.audio_generator.load_model(
                    model_name, use_sequential_cpu_offload=use_cpu_offload
                )
                self.progress_updated.emit(30)

            # Note: StableAudioPipeline doesn't support callback_on_step_end
            # We'll simulate progress updates using a timer-based approach
            import threading
            import time
            
            progress_active = {"value": True}
            
            def simulate_progress():
                """Simulate progress updates during generation."""
                # Start at 30% (model loaded)
                base_progress = 30
                max_progress = 90  # Leave 10% for saving
                progress_range = max_progress - base_progress
                
                # Estimate generation time (rough estimate: ~0.1s per step)
                estimated_time = num_inference_steps * 0.1
                update_interval = max(0.1, estimated_time / 20)  # Update ~20 times
                
                current_progress = base_progress
                start_time = time.time()
                
                while progress_active["value"] and current_progress < max_progress:
                    elapsed = time.time() - start_time
                    # Linear progress based on estimated time
                    if estimated_time > 0:
                        progress_ratio = min(1.0, elapsed / estimated_time)
                        current_progress = base_progress + int(progress_ratio * progress_range)
                        self.progress_updated.emit(current_progress)
                    time.sleep(update_interval)
            
            # Start progress simulation
            progress_thread = threading.Thread(target=simulate_progress, daemon=True)
            progress_thread.start()
            
            # Generate audio (start at 30% since model is loaded)
            self.progress_updated.emit(30)
            audio_path = self.audio_generator.generate_audio_from_text(
                prompt=self.prompt,
                negative_prompt=negative_prompt,
                audio_length_in_s=audio_length,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                seed=self.seed,
                callback=None,  # StableAudioPipeline doesn't support callbacks
                num_waveforms_per_prompt=num_waveforms,
                output_path=output_path,
            )
            
            # Stop progress simulation
            progress_active["value"] = False

            if audio_path is None:
                self.error_occurred.emit("Failed to generate audio")
                return

            # Saving is done in generator, so we're at 100%
            self.progress_updated.emit(100)
            self.audio_generated.emit(audio_path)

        except Exception as e:
            error_msg = f"Error generating audio: {str(e)}"
            print(error_msg)
            import traceback

            traceback.print_exc()
            self.error_occurred.emit(error_msg)

