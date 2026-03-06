"""
Pocket TTS Engine for locAI.
Text-to-Speech using Pocket TTS with voice cloning support.
"""
import asyncio
import pygame
import tempfile
import os
import numpy as np
import hashlib
from typing import Optional
from pathlib import Path

# Try to import Pocket TTS, fallback to None if not available
try:
    from pocket_tts import TTSModel
    import scipy.io.wavfile as wav
    POCKET_TTS_AVAILABLE = True
except ImportError:
    POCKET_TTS_AVAILABLE = False
    print("Warning: pocket-tts not available. Install with: pip install pocket-tts scipy")


class PocketTTSEngine:
    """Text-to-Speech engine using Pocket TTS."""
    
    def __init__(self, voice: str = "alba", voice_cloning_file: Optional[str] = None, on_finished=None):
        """
        Initialize PocketTTSEngine.
        
        Args:
            voice: Voice name to use (e.g., 'alba', 'marius', etc.)
            voice_cloning_file: Path to audio file for voice cloning (optional)
            on_finished: Optional callback when TTS finishes (called with no args)
        """
        self.voice = voice
        self.voice_cloning_file = voice_cloning_file
        self.speed = 1.0  # Note: Pocket TTS doesn't support speed adjustment
        self.is_speaking = False
        self.is_paused = False
        self.should_stop = False
        self.model = None
        self.voice_state = None
        self.on_finished = on_finished
        
        # Available voices for Pocket TTS (English only)
        self.voices = ['alba', 'marius', 'javert', 'jean', 'fantine', 'cosette', 'eponine', 'azelma']
        
        # Initialize pygame mixer
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        
        # Initialize Pocket TTS model if available (but don't load voice state yet - lazy loading)
        if POCKET_TTS_AVAILABLE:
            try:
                self.model = TTSModel.load_model()
                # Voice state will be loaded lazily when first needed (in speak_async)
            except Exception as e:
                print(f"Error initializing Pocket TTS model: {e}")
                self.model = None
        else:
            print("Pocket TTS not available. TTS will not work.")
    
    def _load_voice_state(self):
        """Load voice state for current voice or voice cloning file."""
        if self.model is None:
            return
        
        try:
            if self.voice_cloning_file and os.path.exists(self.voice_cloning_file):
                # Use voice cloning with local file
                print(f"Loading voice from file: {self.voice_cloning_file}")
                
                # Check if file is already in cache directory (pre-converted)
                cache_dir = self._get_cache_dir()
                voice_file_path = Path(self.voice_cloning_file)
                
                try:
                    # Check if file is in cache directory
                    if cache_dir in voice_file_path.parents or voice_file_path.parent == cache_dir:
                        # Already converted and in cache, use directly
                        pcm_file = self.voice_cloning_file
                    else:
                        # Not in cache, convert if needed
                        pcm_file = self._convert_to_pcm_int16(self.voice_cloning_file)
                except Exception:
                    # Fallback: use conversion method
                    pcm_file = self._convert_to_pcm_int16(self.voice_cloning_file)
                
                # Load voice state
                self.voice_state = self.model.get_state_for_audio_prompt(pcm_file)
                
                # Note: Don't delete cached files - they're kept for reuse
                # Only delete if it was a temporary file (not in cache)
                pcm_path = Path(pcm_file)
                if pcm_file != self.voice_cloning_file:
                    try:
                        if cache_dir not in pcm_path.parents and pcm_path.parent != cache_dir:
                            # Not a cached file, safe to delete if temporary
                            if "temp" in pcm_file.lower():
                                os.unlink(pcm_file)
                    except:
                        pass
                
                print(f"Voice cloning loaded successfully")
            else:
                # Use built-in voice
                if self.voice not in self.voices:
                    print(f"Voice {self.voice} not available, using 'alba'")
                    self.voice = "alba"
                
                self.voice_state = self.model.get_state_for_audio_prompt(self.voice)
                print(f"Voice '{self.voice}' loaded successfully")
        except Exception as e:
            print(f"Error loading voice state: {e}")
            import traceback
            traceback.print_exc()
            self.voice_state = None
    
    def _get_cache_dir(self) -> Path:
        """Get cache directory for converted audio files."""
        try:
            from lokai.core.config_manager import ConfigManager
            from lokai.core.paths import get_voice_cache_dir
            config_manager = ConfigManager()
            return get_voice_cache_dir(config_manager)
        except Exception:
            # Fallback to temp directory if config manager not available
            return Path(tempfile.gettempdir()) / "lokai_voice_cache"
    
    def _get_cached_file_path(self, audio_file: str) -> Path:
        """Get cached file path for converted audio."""
        cache_dir = self._get_cache_dir()
        
        # Create hash from file path and modification time
        file_path = Path(audio_file)
        if file_path.exists():
            mtime = file_path.stat().st_mtime
            # Use absolute path for hash to ensure uniqueness
            hash_input = f"{file_path.resolve()}_{mtime}"
        else:
            hash_input = str(file_path.resolve())
        
        # Create hash
        file_hash = hashlib.md5(hash_input.encode()).hexdigest()
        cached_file = cache_dir / f"{file_hash}.wav"
        
        return cached_file
    
    def _convert_to_pcm_int16(self, audio_file: str) -> str:
        """
        Convert audio file to PCM int16 format if needed.
        Uses cache to avoid re-conversion.
        
        Args:
            audio_file: Path to audio file (may be original or already converted)
            
        Returns:
            Path to PCM int16 WAV file (may be original, cached, or temp file)
        """
        try:
            # Check if file exists
            if not os.path.exists(audio_file):
                print(f"Warning: Audio file not found: {audio_file}")
                return audio_file
            
            # If file is already in cache directory, assume it's already converted and ready to use
            cache_dir = self._get_cache_dir()
            audio_path = Path(audio_file)
            try:
                if cache_dir in audio_path.parents or audio_path.parent == cache_dir:
                    return audio_file
            except Exception:
                # Fallback to string check if Path comparison fails
                if "voice_cache" in audio_file:
                    return audio_file
            
            # Read audio file to check format (only if not in cache)
            sample_rate, data = wav.read(audio_file)
            
            # Check if already PCM int16 and mono (no conversion needed)
            if data.dtype == np.int16:
                # Check if mono (single channel)
                if len(data.shape) == 1 or (len(data.shape) == 2 and data.shape[1] == 1):
                    return audio_file
            
            # Check cache first
            cached_file = self._get_cached_file_path(audio_file)
            if cached_file.exists():
                # Verify cache is still valid (check if original file hasn't changed)
                try:
                    original_mtime = Path(audio_file).stat().st_mtime
                    cached_mtime = cached_file.stat().st_mtime
                    
                    # If cached file is newer than original, use cache
                    if cached_mtime >= original_mtime:
                        return str(cached_file)
                except Exception:
                    # If we can't check mtime, use cache anyway
                    return str(cached_file)
            
            # Need to convert
            print(f"Converting audio to PCM int16: {audio_file}")
            
            # Convert stereo to mono if needed
            if len(data.shape) > 1 and data.shape[1] > 1:
                data = np.mean(data, axis=1).astype(data.dtype)
                print(f"Converted stereo to mono")
            
            # Convert to int16
            if data.dtype == np.float32 or data.dtype == np.float64:
                # Float audio in range [-1, 1]
                data = np.clip(data, -1.0, 1.0)
                data_int16 = (data * 32767).astype(np.int16)
            else:
                # Other integer formats
                data_int16 = data.astype(np.int16)
            
            # Save to cache directory
            cached_file.parent.mkdir(parents=True, exist_ok=True)
            wav.write(str(cached_file), sample_rate, data_int16)
            print(f"Cached converted file: {cached_file}")
            
            return str(cached_file)
        except Exception as e:
            print(f"Error converting audio to PCM int16: {e}")
            import traceback
            traceback.print_exc()
            return audio_file
    
    def set_voice(self, voice: str):
        """
        Set TTS voice.
        
        Args:
            voice: Voice name (e.g., 'alba', 'marius')
        """
        if voice != self.voice:
            self.voice = voice
            # Only reload voice state if it was already loaded (don't load if not needed yet)
            if self.voice_state is not None:
                self._load_voice_state()
            # Otherwise, voice state will be loaded lazily when speak is called
    
    def set_voice_cloning_file(self, file_path: Optional[str]):
        """
        Set voice cloning file.
        
        Args:
            file_path: Path to audio file for voice cloning (None to disable)
        """
        self.voice_cloning_file = file_path
        # Only reload voice state if it was already loaded (don't load if not needed yet)
        if self.voice_state is not None:
            self._load_voice_state()
        # Otherwise, voice state will be loaded lazily when speak is called
    
    def clean_text(self, text: str) -> str:
        """
        Clean text for TTS (remove special characters, but preserve newlines for pauses).
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        # Remove markdown code blocks
        import re
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`[^`]+`', '', text)
        
        # Remove asterisks (*) only
        text = text.replace('*', '')
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Preserve newlines but clean up multiple spaces
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            cleaned_line = ' '.join(line.split())
            if cleaned_line:
                cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines)
    
    def split_text_into_chunks(self, text: str, max_size: int = 250) -> list:
        """
        Split text into chunks for TTS.
        Optimized for faster initial playback - smaller chunks mean less waiting time.
        
        Args:
            text: Input text
            max_size: Maximum chunk size (default 250 for faster processing)
            
        Returns:
            List of text chunks
        """
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        # First split by sentences (periods)
        parts = text.split('. ')
        
        # If sentences are too long, split by commas
        sentences = []
        for part in parts:
            if len(part) <= max_size:
                sentences.append(part)
            else:
                # Split long sentences by commas
                comma_parts = part.split(', ')
                current_sentence = ""
                for comma_part in comma_parts:
                    if len(current_sentence) + len(comma_part) + 2 <= max_size:
                        current_sentence += comma_part + ", "
                    else:
                        if current_sentence:
                            sentences.append(current_sentence.strip().rstrip(','))
                        current_sentence = comma_part + ", "
                if current_sentence:
                    sentences.append(current_sentence.strip().rstrip(','))
        
        # Now group sentences into chunks
        current_chunk = ""
        for sentence in sentences:
            sentence_with_period = sentence if sentence.endswith('.') else sentence + "."
            if len(current_chunk) + len(sentence_with_period) + 1 <= max_size:
                current_chunk += sentence_with_period + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence_with_period + " "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def speak_async(self, text: str):
        """
        Speak text asynchronously with streaming (generate and play chunks as they're ready).
        
        Args:
            text: Text to speak
        """
        if not text or self.is_speaking or not self.model:
            return
        
        # Lazy load voice state if not already loaded
        if self.voice_state is None:
            self._load_voice_state()
            if self.voice_state is None:
                return
        
        self.is_speaking = True
        self.should_stop = False
        
        try:
            # Clean text
            clean_text = self.clean_text(text)
            if not clean_text:
                return
            
            # Split by newlines (but don't add pauses - just process all text)
            paragraphs = clean_text.split('\n')
            
            # Prepare text chunks for generation
            text_chunks = []
            for paragraph in paragraphs:
                if not paragraph.strip():
                    continue
                
                # Split into chunks for processing (smaller chunks = faster initial playback)
                chunks = self.split_text_into_chunks(paragraph, max_size=250)
                text_chunks.extend(chunks)
            
            if not text_chunks:
                return
            
            # Optimized streaming: generate small chunks and play them as they're ready
            # This reduces initial wait time from 20-30s to just a few seconds (250 chars vs 1000)
            
            async def generate_chunk_audio(chunk_text):
                """Generate audio for a single chunk."""
                if not chunk_text or not chunk_text.strip():
                    return None
                
                try:
                    audio = self.model.generate_audio(self.voice_state, chunk_text)
                    audio_np = audio.numpy()
                    if audio_np.dtype == np.float32 or audio_np.dtype == np.float64:
                        audio_int16 = (audio_np * 32767).astype(np.int16)
                    else:
                        audio_int16 = audio_np.astype(np.int16)
                    return audio_int16
                except Exception as e:
                    print(f"TTS generation error for chunk: {e}")
                    return None
            
            # Generate and play chunks one by one for smoother streaming
            temp_files = []
            
            try:
                for chunk_idx, chunk_text in enumerate(text_chunks):
                    if self.should_stop:
                        break
                    
                    # Generate audio for this chunk
                    chunk_audio = await generate_chunk_audio(chunk_text)
                    if chunk_audio is None:
                        continue
                    
                    # If this is the first chunk, start playing immediately
                    # Otherwise, wait for previous chunk to finish
                    if chunk_idx > 0:
                        # Wait for previous playback to finish
                        while pygame.mixer.music.get_busy() and not self.should_stop:
                            await asyncio.sleep(0.05)
                    
                    if self.should_stop:
                        break
                    
                    # Save chunk to temp file and play
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                        tmp_path = tmp_file.name
                    
                    wav.write(tmp_path, self.model.sample_rate, chunk_audio)
                    pygame.mixer.music.load(tmp_path)
                    pygame.mixer.music.play()
                    temp_files.append(tmp_path)
                
                # Wait for final chunk to finish
                while pygame.mixer.music.get_busy() and not self.should_stop:
                    await asyncio.sleep(0.05)
                
            except Exception as e:
                print(f"TTS generation/playback error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # Clean up all temp files
                for tmp_file in temp_files:
                    try:
                        if os.path.exists(tmp_file):
                            os.unlink(tmp_file)
                    except:
                        pass
        
        except Exception as e:
            print(f"TTS error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_speaking = False
            
            # Clear GPU memory
            self._clear_gpu_memory()
            
            # Call finished callback
            if self.on_finished:
                try:
                    self.on_finished()
                except:
                    pass
    
    def speak(self, text: str):
        """
        Speak text (synchronous wrapper).
        
        Args:
            text: Text to speak
        """
        if self.is_speaking:
            print("TTS is already speaking")
            return
        
        if not self.model:
            print("TTS model not initialized")
            return
        
        # Voice state will be loaded lazily in speak_async if needed
        # Don't check it here to allow lazy loading
        
        # Run in background thread
        import threading
        def run_tts():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.speak_async(text))
                loop.close()
            except Exception as e:
                print(f"TTS error: {e}")
                import traceback
                traceback.print_exc()
                self.is_speaking = False
        
        thread = threading.Thread(target=run_tts, daemon=True)
        thread.start()
    
    def stop(self):
        """Stop current speech."""
        self.should_stop = True
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        self.is_speaking = False
        
        # Clear GPU memory
        self._clear_gpu_memory()
    
    def pause(self):
        """Pause current speech."""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.is_paused = True
    
    def resume(self):
        """Resume paused speech."""
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
    
    def _clear_gpu_memory(self):
        """Clear GPU memory after TTS operations."""
        try:
            import torch
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.synchronize()
                torch.cuda.empty_cache()
                try:
                    torch.cuda.ipc_collect()
                except AttributeError:
                    pass
        except Exception:
            pass
