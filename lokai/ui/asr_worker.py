"""
ASR Worker for locAI.
Background thread for speech recognition without blocking UI.
"""

import time
import numpy as np
from PySide6.QtCore import QThread, Signal, QTimer
from lokai.core.asr_engine import ASREngine
from lokai.core.config_manager import ConfigManager

# Optional imports - only load if available
try:
    import sounddevice as sd
    SOUNDEVICE_AVAILABLE = True
except ImportError:
    SOUNDEVICE_AVAILABLE = False
    print("Warning: sounddevice not available. Microphone input disabled.")

try:
    import webrtcvad
    WEBRTC_VAD_AVAILABLE = True
except ImportError:
    WEBRTC_VAD_AVAILABLE = False
    print("Warning: webrtcvad not available. Voice activity detection disabled.")


class ASRWorker(QThread):
    """Worker thread for ASR processing."""

    transcription_ready = Signal(str)  # complete transcription
    partial_transcription = Signal(str)  # partial transcription during streaming
    error_occurred = Signal(str)  # error message
    listening_started = Signal()
    listening_stopped = Signal()
    audio_level_updated = Signal(float)  # audio level 0.0-1.0

    def __init__(
        self,
        asr_engine: ASREngine,
        config_manager: ConfigManager,
    ):
        """
        Initialize ASRWorker.

        Args:
            asr_engine: ASREngine instance
            config_manager: ConfigManager for settings
        """
        super().__init__()
        self.asr_engine = asr_engine
        self.config_manager = config_manager

        # Audio settings
        self.sample_rate = 16000
        self.channels = 1  # Mono
        self.chunk_size = 1024  # Audio buffer chunk size

        # Listening state
        self.is_listening = False
        self.should_stop = False

        # Audio buffer for streaming
        self.audio_buffer = []
        self.buffer_duration = 0.0
        self.last_voice_time = 0.0  # Track when we last heard voice

        # VAD (Voice Activity Detection)
        self.vad = None
        self.vad_enabled = WEBRTC_VAD_AVAILABLE

        # Audio level monitoring
        self.audio_level = 0.0

        # Setup VAD if available
        if self.vad_enabled:
            try:
                self.vad = webrtcvad.Vad()
                self.vad.set_mode(3)  # Most aggressive VAD mode
            except Exception as e:
                print(f"Error initializing VAD: {e}")
                self.vad = None
                self.vad_enabled = False

    def run(self):
        """Main ASR worker loop."""
        try:
            # Load ASR model
            self._load_asr_model()

            # Start listening loop
            self._listening_loop()

        except Exception as e:
            error_msg = f"ASR Worker error: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(error_msg)

    def _load_asr_model(self):
        """Load ASR model with configured settings."""
        try:
            model_name = self.config_manager.get(
                "asr.model", "nvidia/nemotron-speech-streaming-en-0.6b"
            )
            chunk_size_ms = self.config_manager.get("asr.chunk_size_ms", 560)

            print(f"Loading ASR model: {model_name}")
            print("Note: First download may take several minutes (model is ~600MB-1GB)")
            print("Please be patient...")
            self.asr_engine.load_model(model_name, chunk_size_ms)
            print("ASR model loaded successfully")

        except Exception as e:
            # Check if it's a timeout error
            if "ReadTimeout" in str(e) or "timeout" in str(e).lower():
                raise RuntimeError(
                    f"Timeout while downloading ASR model. "
                    f"This is normal for first download (model is ~600MB-1GB). "
                    f"Please check your internet connection and try again. "
                    f"Original error: {e}"
                )
            else:
                raise RuntimeError(f"Failed to load ASR model: {e}")

    def _listening_loop(self):
        """Main listening and processing loop."""
        if not SOUNDEVICE_AVAILABLE:
            raise RuntimeError("sounddevice not available for microphone input")

        # Get microphone device
        device = self._get_microphone_device()

        try:
            # Open audio stream
            with sd.InputStream(
                device=device,
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                callback=self._audio_callback,
                dtype=np.float32
            ) as stream:

                self.listening_started.emit()
                self.is_listening = True
                print("ASR listening started (continuous mode - will process on stop)")

                # Main loop - just accumulate audio, don't process until stop
                while not self.should_stop:
                    # Small sleep to prevent busy waiting
                    self.msleep(50)

                # Process ALL accumulated audio when stopping
                if self.audio_buffer:
                    print("Processing all accumulated audio on stop...")
                    self._process_audio_buffer()

                print("ASR listening stopped")

        except Exception as e:
            error_msg = f"Audio stream error: {str(e)}"
            print(error_msg)
            self.error_occurred.emit(error_msg)

        finally:
            self.is_listening = False
            self.listening_stopped.emit()

    def _get_microphone_device(self) -> int:
        """Get configured microphone device index."""
        device_config = self.config_manager.get("asr.microphone_device")
        if device_config is not None:
            return int(device_config)

        # Auto-detect default input device
        try:
            devices = sd.query_devices()
            default_input = sd.default.device[0]  # (input, output)
            return default_input
        except:
            return None

    def _audio_callback(self, indata, frames, time_info, status):
        """Audio stream callback - receives audio chunks."""
        if status:
            print(f"Audio callback status: {status}")

        # Convert to numpy array and ensure proper shape
        audio_chunk = indata.flatten()

        # Update audio level for visualization
        self.audio_level = np.sqrt(np.mean(audio_chunk**2))
        self.audio_level_updated.emit(float(self.audio_level))

        # Add to buffer - just accumulate, don't process yet
        self.audio_buffer.append(audio_chunk)
        self.buffer_duration += len(audio_chunk) / self.sample_rate
        
        # Don't process during listening - wait for explicit stop
        # This allows continuous recording without interruptions

    def _process_audio_buffer(self):
        """Process accumulated audio buffer."""
        if not self.audio_buffer:
            return

        try:
            # Concatenate all buffered chunks
            audio_data = np.concatenate(self.audio_buffer)

            # Clear buffer
            self.audio_buffer = []
            buffer_duration = self.buffer_duration
            self.buffer_duration = 0.0

            # Skip if audio is too short (less than 0.5 second)
            if len(audio_data) / self.sample_rate < 0.5:
                print(f"Skipping - audio too short ({len(audio_data) / self.sample_rate:.1f}s)")
                return

            print(f"Processing {buffer_duration:.1f}s of audio...")

            # Transcribe audio
            transcription = self.asr_engine.transcribe_audio_array(
                audio_data, self.sample_rate
            )

            if transcription and transcription.strip():
                print(f"Transcription: {transcription}")
                self.transcription_ready.emit(transcription.strip())
            else:
                print("No speech detected in audio chunk")

        except Exception as e:
            error_msg = f"Audio processing error: {str(e)}"
            print(error_msg)
            self.error_occurred.emit(error_msg)

    def start_listening(self):
        """Start listening for audio input."""
        if self.isRunning():
            return  # Already running

        self.should_stop = False
        self.audio_buffer = []
        self.buffer_duration = 0.0
        self.start()

    def stop_listening(self):
        """Stop listening and process remaining audio."""
        self.should_stop = True

        # Process any remaining audio in buffer
        if self.audio_buffer:
            self._process_audio_buffer()

    def transcribe_file(self, file_path: str):
        """
        Transcribe audio from file (non-streaming).

        Args:
            file_path: Path to audio file
        """
        try:
            print(f"Transcribing file: {file_path}")
            transcription = self.asr_engine.transcribe_audio_file(file_path)

            if transcription:
                self.transcription_ready.emit(transcription)
            else:
                self.error_occurred.emit("Failed to transcribe audio file")

        except Exception as e:
            error_msg = f"File transcription error: {str(e)}"
            print(error_msg)
            self.error_occurred.emit(error_msg)

    def cleanup(self):
        """Cleanup resources."""
        self.should_stop = True
        if self.isRunning():
            self.wait(2000)  # Wait up to 2 seconds for thread to finish

        # Clear buffers
        self.audio_buffer = []

        # Cleanup ASR engine
        if self.asr_engine:
            try:
                self.asr_engine.clear_gpu_memory()
            except:
                pass