"""
TTS Engine for locAI.
Text-to-Speech using Kokoro-82M.
"""
import asyncio
import pygame
import soundfile as sf
import tempfile
import os
from typing import Optional, Dict
from pathlib import Path

# Try to import Kokoro, fallback to None if not available
try:
    from kokoro import KPipeline
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False
    print("Warning: kokoro not available. Install with: pip install kokoro soundfile")

# Try to import Pocket TTS, fallback to None if not available
try:
    from pocket_tts import TTSModel
    POCKET_TTS_AVAILABLE = True
except ImportError:
    POCKET_TTS_AVAILABLE = False
    print("Warning: pocket-tts not available. Install with: pip install pocket-tts scipy")


class TTSEngine:
    """Text-to-Speech engine using Kokoro-82M."""
    
    def __init__(self, lang_code: str = "a", voice: str = "af_heart", on_finished=None):
        """
        Initialize TTSEngine.
        
        Args:
            lang_code: Language code ('a'=American English, 'b'=British English, etc.)
            voice: Voice name to use (e.g., 'af_heart', 'af_bella', etc.)
            on_finished: Optional callback when TTS finishes (called with no args)
        """
        self.lang_code = lang_code
        self.voice = voice
        self.speed = 1.0
        self.is_speaking = False
        self.is_paused = False
        self.should_stop = False
        self.pipeline = None
        self.on_finished = on_finished
        
        # Available language codes
        self.language_codes = {
            "American English": "a",
            "British English": "b",
            "Spanish": "e",
            "French": "f",
            "Hindi": "h",
            "Italian": "i",
            "Japanese": "j",
            "Brazilian Portuguese": "p",
            "Mandarin Chinese": "z",
        }
        
        # Voices organized by language code
        # Format: {lang_code: [list of voices]}
        # Updated to match actual voices available in cache
        self.voices_by_language = {
            "a": [  # American English
                "af_alloy", "af_aoede", "af_bella", "af_heart", "af_jessica",
                "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
                "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam",
                "am_michael", "am_onyx", "am_puck", "am_santa",
            ],
            "b": [  # British English
                "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
                "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
            ],
            "e": [  # Spanish
                "ef_dora", "em_alex", "em_santa",
            ],
            "f": [  # French
                "ff_siwis",
            ],
            "h": [  # Hindi
                "hf_alpha", "hf_beta", "hm_omega", "hm_psi",
            ],
            "i": [  # Italian
                "if_sara", "im_nicola",
            ],
            "j": [  # Japanese
                "jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo",
            ],
            "p": [  # Brazilian Portuguese
                "pf_dora", "pm_alex", "pm_santa",
            ],
            "z": [  # Mandarin Chinese
                "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi",
            ],
        }
        
        # Get voices for current language
        self.voices = self.voices_by_language.get(lang_code, self.voices_by_language["a"])
        
        # Initialize pygame mixer
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        
        # Initialize Kokoro pipeline if available
        if KOKORO_AVAILABLE:
            try:
                self.pipeline = KPipeline(lang_code=lang_code)
            except Exception as e:
                print(f"Error initializing Kokoro pipeline: {e}")
                self.pipeline = None
        else:
            print("Kokoro not available. TTS will not work.")
    
    def set_voice(self, voice: str):
        """
        Set TTS voice.
        
        Args:
            voice: Voice name (e.g., 'af_heart')
        """
        self.voice = voice
    
    def set_lang_code(self, lang_code: str):
        """
        Set language code.
        
        Args:
            lang_code: Language code ('a', 'b', 'e', etc.)
        """
        self.lang_code = lang_code
        # Update available voices for this language
        self.voices = self.voices_by_language.get(lang_code, self.voices_by_language["a"])
        # Reinitialize pipeline with new language
        if KOKORO_AVAILABLE:
            try:
                self.pipeline = KPipeline(lang_code=lang_code)
            except Exception as e:
                print(f"Error reinitializing Kokoro pipeline: {e}")
    
    def get_voices_for_language(self, lang_code: str) -> list:
        """
        Get list of voices for a specific language.
        
        Args:
            lang_code: Language code ('a', 'b', 'e', etc.)
            
        Returns:
            List of voice names
        """
        return self.voices_by_language.get(lang_code, self.voices_by_language["a"])
    
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
        # Split by newlines first to preserve them
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Clean up extra whitespace within each line
            cleaned_line = ' '.join(line.split())
            if cleaned_line:  # Only add non-empty lines
                cleaned_lines.append(cleaned_line)
        
        # Join with newlines preserved (this will create pauses)
        return '\n'.join(cleaned_lines)
    
    def split_text_into_chunks(self, text: str, max_size: int = 500) -> list:
        """
        Split text into chunks for TTS.
        
        Args:
            text: Input text
            max_size: Maximum chunk size (smaller for Kokoro)
            
        Returns:
            List of text chunks
        """
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        # Split by sentences first
        sentences = text.split('. ')
        
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 <= max_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def speak_async(self, text: str):
        """
        Speak text asynchronously.
        
        Args:
            text: Text to speak
        """
        if not text or self.is_speaking or not self.pipeline:
            return
        
        self.is_speaking = True
        self.should_stop = False
        
        try:
            # Clean text (now preserves newlines)
            clean_text = self.clean_text(text)
            if not clean_text:
                return
            
            # Split by newlines to add pauses between paragraphs
            paragraphs = clean_text.split('\n')
            
            for para_idx, paragraph in enumerate(paragraphs):
                if not paragraph.strip() or self.should_stop:
                    continue
                
                # Add pause before new paragraph (except first)
                if para_idx > 0:
                    # Small pause between paragraphs (0.3 seconds)
                    await asyncio.sleep(0.3)
                
                # Split into chunks if paragraph is too long
                chunks = self.split_text_into_chunks(paragraph, max_size=500)
                
                for i, chunk in enumerate(chunks):
                    if not chunk.strip() or self.should_stop:
                        continue
                    
                    # Generate TTS with Kokoro
                    try:
                        generator = self.pipeline(
                            chunk,
                            voice=self.voice,
                            speed=self.speed,
                            split_pattern=r'\n+'
                        )
                    except Exception as voice_error:
                        # If voice is not available, try default voice
                        if "404" in str(voice_error) or "not found" in str(voice_error).lower():
                            print(f"Voice {self.voice} not available, trying default voice 'af_heart'")
                            try:
                                generator = self.pipeline(
                                    chunk,
                                    voice="af_heart",  # Fallback to default
                                    speed=self.speed,
                                    split_pattern=r'\n+'
                                )
                            except Exception as fallback_error:
                                print(f"TTS voice error: {fallback_error}")
                                continue
                        else:
                            print(f"TTS error: {voice_error}")
                            continue
                    
                    # Collect all audio chunks
                    audio_chunks = []
                    for gs, ps, audio in generator:
                        if self.should_stop:
                            break
                        audio_chunks.append(audio)
                    
                    if not audio_chunks or self.should_stop:
                        continue
                    
                    # Concatenate audio chunks
                    import numpy as np
                    full_audio = np.concatenate(audio_chunks)
                    
                    # Save to temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                        tmp_path = tmp_file.name
                    
                    # Save as WAV (24kHz sample rate for Kokoro)
                    sf.write(tmp_path, full_audio, 24000)
                    
                    # Play audio
                    if not self.should_stop:
                        pygame.mixer.music.load(tmp_path)
                        pygame.mixer.music.play()
                        
                        # Wait for playback to finish
                        while pygame.mixer.music.get_busy() and not self.should_stop:
                            await asyncio.sleep(0.1)
                    
                    # Clean up
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                
        except Exception as e:
            print(f"TTS error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_speaking = False
            
            # Clear GPU memory after TTS finishes
            self._clear_gpu_memory()
            
            # Call finished callback if provided
            if self.on_finished:
                try:
                    self.on_finished()
                except:
                    pass
    
    def speak(self, text: str):
        """
        Speak text (synchronous wrapper).
        Runs in background thread to avoid blocking UI.
        
        Args:
            text: Text to speak
        """
        if self.is_speaking:
            print("TTS is already speaking")
            return
        
        if not self.pipeline:
            print("TTS pipeline not initialized")
            return
        
        # Run in background thread to avoid blocking UI
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
        
        # Clear GPU memory when stopped
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
        except Exception as e:
            # Silently ignore errors
            pass


def create_tts_engine(engine_type: str, **kwargs):
    """
    Factory funkcija za kreiranje TTS engine-a.
    
    Args:
        engine_type: "kokoro" ili "pocket_tts"
        **kwargs: parametri za odabrani engine
        
    Returns:
        TTSEngine ili PocketTTSEngine instance
    """
    if engine_type == "kokoro":
        if not KOKORO_AVAILABLE:
            raise RuntimeError("Kokoro TTS nije dostupan")
        return TTSEngine(**kwargs)
    elif engine_type == "pocket_tts":
        if not POCKET_TTS_AVAILABLE:
            raise RuntimeError("Pocket TTS nije dostupan")
        from lokai.core.pocket_tts_engine import PocketTTSEngine
        return PocketTTSEngine(**kwargs)
    else:
        raise ValueError(f"Unknown TTS engine: {engine_type}")
