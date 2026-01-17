"""
ASR Engine for locAI.
NVIDIA Nemotron Speech Streaming for automatic speech recognition.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import numpy as np

# Set higher timeout for Hugging Face downloads (ASR models are large ~600MB-1GB)
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "300")  # 5 minutes

# Optional imports - only load if available
try:
    import torch
    import nemo.collections.asr as nemo_asr

    NEMO_AVAILABLE = True
except ImportError:
    NEMO_AVAILABLE = False
    print("Warning: NeMo ASR not available. Speech recognition disabled.")


class ASREngine:
    """ASR engine using NVIDIA Nemotron Speech Streaming."""

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize ASREngine.

        Args:
            storage_path: Path to model storage (from config)
        """
        self.storage_path = storage_path
        self.model = None
        self.current_model = None
        
        # Force CPU mode for ASR to avoid CUDA crashes
        # CUDA crashes are happening in PyTorch C++ layer which Python can't catch
        # CPU mode is slower but stable
        self.device = "cpu" if NEMO_AVAILABLE else None
        
        # Uncomment below to allow GPU (at your own risk):
        # self.device = (
        #     "cuda"
        #     if torch.cuda.is_available()
        #     else "cpu" if NEMO_AVAILABLE else None
        # )

        # Chunk size configurations mapping
        self.chunk_configs = {
            80: [70, 0],    # Lowest latency
            160: [70, 1],   # Low latency
            560: [70, 6],   # Balanced (default)
            1120: [70, 13]  # Highest accuracy
        }

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
        nemo_path = storage / "nemo"

        os.environ["HF_HOME"] = str(storage)
        os.environ["TRANSFORMERS_CACHE"] = str(storage)
        os.environ["HF_DATASETS_CACHE"] = str(storage)
        os.environ["HF_HUB_CACHE"] = str(storage)
        os.environ["NEMO_CACHE"] = str(nemo_path)

    def is_available(self) -> bool:
        """Check if ASR is available."""
        return NEMO_AVAILABLE and self.device is not None

    def load_model(
        self,
        model_name: str = "nvidia/nemotron-speech-streaming-en-0.6b",
        chunk_size_ms: int = 560,
    ):
        """
        Load Nemotron Speech model.

        Args:
            model_name: Model name (Hugging Face ID)
            chunk_size_ms: Chunk size in milliseconds (80, 160, 560, 1120)
        """
        if not self.is_available():
            raise RuntimeError(
                "ASR not available. Install NeMo toolkit and torch."
            )

        if self.current_model == model_name and self.model is not None:
            # Model already loaded, just update chunk config if needed
            if hasattr(self, '_current_chunk_size') and self._current_chunk_size == chunk_size_ms:
                return  # Already loaded with same config

        print(f"Loading ASR model: {model_name}")

        try:
            # Load model from Hugging Face
            self.model = nemo_asr.models.ASRModel.from_pretrained(model_name)

            # Force CPU mode to avoid CUDA crashes
            # CUDA crashes happen in C++ layer which Python can't catch
            self.device = "cpu"
            self.model = self.model.to(self.device)
            print("ASR model loaded on CPU (forced to avoid CUDA crashes)")

            # Set chunk configuration
            if chunk_size_ms in self.chunk_configs:
                self.att_context_size = self.chunk_configs[chunk_size_ms]
                self._current_chunk_size = chunk_size_ms
                print(f"ASR chunk size set to {chunk_size_ms}ms (att_context_size: {self.att_context_size})")
            else:
                print(f"Warning: Invalid chunk size {chunk_size_ms}ms, using default 560ms")
                self.att_context_size = self.chunk_configs[560]
                self._current_chunk_size = 560

            self.current_model = model_name
            print(f"ASR model {model_name} loaded successfully")

        except Exception as e:
            print(f"Error loading ASR model: {e}")
            import traceback
            traceback.print_exc()
            raise

    def transcribe_audio_file(self, audio_path: str) -> Optional[str]:
        """
        Transcribe audio from file.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text or None on error
        """
        if not self.is_available():
            raise RuntimeError("ASR not available")

        if self.model is None:
            # Try to load default model
            try:
                self.load_model()
            except Exception as e:
                print(f"Cannot load ASR model: {e}")
                return None

        # Check CUDA context validity if using GPU
        if self.device == "cuda" and torch.cuda.is_available():
            try:
                # Verify CUDA context is still valid
                torch.cuda.current_device()
            except RuntimeError as e:
                print(f"CUDA context lost: {e}")
                print("Switching to CPU mode")
                self.device = "cpu"
                if self.model is not None:
                    try:
                        self.model = self.model.to('cpu')
                    except Exception as e2:
                        print(f"Failed to move model to CPU: {e2}")
                        return None

        try:
            # Check if file exists
            if not os.path.exists(audio_path):
                print(f"Audio file not found: {audio_path}")
                return None

            print(f"Transcribing audio file: {audio_path}")

            # Transcribe using NeMo - wrap in try-except for CUDA errors
            try:
                result = self.model.transcribe([audio_path])[0]
            except RuntimeError as e:
                error_str = str(e)
                if "CUDA" in error_str or "cuda" in error_str.lower():
                    print(f"CUDA error during transcription: {e}")
                    print("Attempting to recover by switching to CPU...")
                    # Try to recover by switching to CPU
                    try:
                        self.device = "cpu"
                        self.model = self.model.to('cpu')
                        # Retry transcription on CPU
                        result = self.model.transcribe([audio_path])[0]
                        print("Recovered - transcription completed on CPU")
                    except Exception as e2:
                        print(f"Recovery failed: {e2}")
                        return None
                else:
                    # Re-raise non-CUDA RuntimeErrors
                    raise
            
            # NeMo returns a Hypothesis object, extract text
            if hasattr(result, 'text'):
                transcription = result.text
            else:
                transcription = str(result)
            
            print(f"Transcription completed: {len(transcription)} characters")
            return transcription

        except Exception as e:
            print(f"Error transcribing audio file: {e}")
            import traceback
            traceback.print_exc()
            return None

    def transcribe_audio_array(
        self,
        audio_array: np.ndarray,
        sample_rate: int = 16000,
        chunk_size_ms: Optional[int] = None
    ) -> Optional[str]:
        """
        Transcribe audio from numpy array.

        Args:
            audio_array: Audio data as numpy array (float32, mono)
            sample_rate: Sample rate (should be 16000)
            chunk_size_ms: Optional chunk size override

        Returns:
            Transcribed text or None on error
        """
        if not self.is_available():
            raise RuntimeError("ASR not available")

        if self.model is None:
            try:
                self.load_model()
            except Exception as e:
                print(f"Cannot load ASR model: {e}")
                return None

        # Check CUDA context validity if using GPU
        if self.device == "cuda" and torch.cuda.is_available():
            try:
                # Verify CUDA context is still valid
                torch.cuda.current_device()
            except RuntimeError as e:
                print(f"CUDA context lost: {e}")
                print("Switching to CPU mode")
                self.device = "cpu"
                if self.model is not None:
                    try:
                        self.model = self.model.to('cpu')
                    except Exception as e2:
                        print(f"Failed to move model to CPU: {e2}")
                        return None

        try:
            # Ensure audio is float32 and mono
            if audio_array.dtype != np.float32:
                audio_array = audio_array.astype(np.float32)

            if len(audio_array.shape) > 1:
                # Convert to mono
                audio_array = np.mean(audio_array, axis=1 if audio_array.shape[1] < audio_array.shape[0] else 0)

            # Normalize to [-1, 1] range if needed
            if np.max(np.abs(audio_array)) > 1.0:
                audio_array = audio_array / np.max(np.abs(audio_array))

            print(f"Transcribing audio array: {len(audio_array)} samples at {sample_rate}Hz")

            # Create temporary WAV file for NeMo
            import tempfile
            import soundfile as sf

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_path = tmp_file.name

            try:
                # Save as WAV
                sf.write(tmp_path, audio_array, sample_rate)

                # Transcribe
                transcription = self.transcribe_audio_file(tmp_path)

                return transcription

            finally:
                # Clean up temp file
                try:
                    os.unlink(tmp_path)
                except:
                    pass

        except Exception as e:
            print(f"Error transcribing audio array: {e}")
            import traceback
            traceback.print_exc()
            return None

    def process_streaming_chunk(
        self,
        audio_chunk: np.ndarray,
        is_first_chunk: bool = False,
        is_last_chunk: bool = False
    ) -> Optional[str]:
        """
        Process a streaming audio chunk.

        Args:
            audio_chunk: Audio chunk data
            is_first_chunk: True if this is the first chunk in stream
            is_last_chunk: True if this is the last chunk in stream

        Returns:
            Partial transcription or None
        """
        # For now, implement as batch processing of chunks
        # TODO: Implement true streaming inference when NeMo supports it

        if is_last_chunk and hasattr(self, '_audio_buffer'):
            # Combine with buffered audio
            full_audio = np.concatenate(self._audio_buffer + [audio_chunk])
            self._audio_buffer = []  # Clear buffer
            return self.transcribe_audio_array(full_audio)
        elif not is_last_chunk:
            # Buffer the chunk
            if not hasattr(self, '_audio_buffer'):
                self._audio_buffer = []
            self._audio_buffer.append(audio_chunk)
            return None  # No partial result yet

        # Single chunk processing
        return self.transcribe_audio_array(audio_chunk)

    def unload_model(self):
        """Unload current model to free memory."""
        if self.model is not None:
            try:
                # Move model to CPU first
                if hasattr(self.model, 'to'):
                    self.model = self.model.to('cpu')
            except:
                pass

            # Delete model
            del self.model
            self.model = None
            self.current_model = None

            # Clear any buffered audio
            if hasattr(self, '_audio_buffer'):
                self._audio_buffer = []

            # Force garbage collection
            import gc
            gc.collect()

            # Clear CUDA cache if available
            if torch.cuda.is_available():
                try:
                    torch.cuda.empty_cache()
                except:
                    pass

            print("ASR model unloaded and memory freed")

    def clear_gpu_memory(self):
        """Clear GPU memory without unloading the model."""
        if self.model is None:
            return

        try:
            # Aggressive GPU memory cleanup
            if torch.cuda.is_available():
                torch.cuda.synchronize()
                for _ in range(3):
                    torch.cuda.empty_cache()
                try:
                    torch.cuda.ipc_collect()
                except AttributeError:
                    pass
                try:
                    torch.cuda.reset_peak_memory_stats()
                except:
                    pass
                print("ASR GPU memory cleared")
        except Exception as e:
            print(f"Error clearing ASR GPU memory: {e}")

    def get_supported_chunk_sizes(self) -> List[int]:
        """Get list of supported chunk sizes in milliseconds."""
        return list(self.chunk_configs.keys())

    def get_chunk_config(self, chunk_size_ms: int) -> Optional[List[int]]:
        """Get att_context_size for given chunk size."""
        return self.chunk_configs.get(chunk_size_ms)