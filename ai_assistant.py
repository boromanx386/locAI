import sys
import json
import requests
import subprocess
import threading
import time
import feedparser
from datetime import datetime, timedelta
import pyttsx3
import pygame
import edge_tts
import asyncio
import tempfile
import os
import random
import string
import base64
import io

# Opcioni import-ovi za upscaling funkcionalnost
try:
    import cv2
    import numpy as np

    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("Warning: cv2 not available. Real-ESRGAN upscaling will be disabled.")
    print("To enable Real-ESRGAN upscaling, install: pip install opencv-python")

# ControlNet import-ovi za img2img funkcionalnost
try:
    from controlnet_aux import CannyDetector, OpenposeDetector, MidasDetector
    from diffusers import ControlNetModel, StableDiffusionXLControlNetPipeline
    from PIL import Image
    import torch

    CONTROLNET_AVAILABLE = True
    print("ControlNet libraries loaded successfully!")
except ImportError as e:
    CONTROLNET_AVAILABLE = False
    print(
        f"Warning: ControlNet not available. Image-to-image will be disabled. Error: {e}"
    )
    print("To enable ControlNet, install: pip install controlnet-aux")

# Postavi Hugging Face cache na Q: disk PRVO pre bilo čega
os.environ["HF_HOME"] = "Q:\\huggingface_cache"
os.environ["TRANSFORMERS_CACHE"] = "Q:\\huggingface_cache"
os.environ["HF_DATASETS_CACHE"] = "Q:\\huggingface_cache"
os.environ["HF_HUB_CACHE"] = "Q:\\huggingface_cache"

# Postavi dodatne cache direktorijume na Q: disk
os.environ["DIFFUSERS_CACHE"] = "Q:\\huggingface_cache\\diffusers"
os.environ["HF_DIFFUSERS_CACHE"] = "Q:\\huggingface_cache\\diffusers"

# Kreiraj direktorijume ako ne postoje
cache_dirs = [
    "Q:\\huggingface_cache",
    "Q:\\huggingface_cache\\diffusers",
    "Q:\\huggingface_cache\\models--stabilityai--stable-diffusion-xl-base-1.0",
    "Q:\\huggingface_cache\\models--stabilityai--stable-diffusion-2-1-base",
    "Q:\\huggingface_cache\\models--runwayml--stable-diffusion-v1-5",
    "Q:\\huggingface_cache\\models--stabilityai--stable-diffusion-x4-upscaler",
    "Q:\\huggingface_cache\\models--xinntao--realesrgan-x4plus",
    "Q:\\huggingface_cache\\models--xinntao--realesrgan-x4plus-anime",
    "Q:\\huggingface_cache\\loras",
    "Q:\\huggingface_cache\\embeddings",
]

for cache_dir in cache_dirs:
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
        print(f"Created cache directory: {cache_dir}")

print("Hugging Face cache set to Q: drive:")
print(f"HF_HOME = {os.environ.get('HF_HOME')}")
print(f"TRANSFORMERS_CACHE = {os.environ.get('TRANSFORMERS_CACHE')}")
print(f"HF_DATASETS_CACHE = {os.environ.get('HF_DATASETS_CACHE')}")
print(f"HF_HUB_CACHE = {os.environ.get('HF_HUB_CACHE')}")

from PIL import Image
import torch
from diffusers import StableDiffusionXLPipeline
import time
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QSpacerItem,
    QSizePolicy,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QLabel,
    QScrollArea,
    QFrame,
    QMessageBox,
    QComboBox,
    QStatusBar,
    QProgressBar,
    QFileDialog,
    QListWidget,
    QSlider,
    QGroupBox,
    QCheckBox,
    QListWidgetItem,
    QDialog,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QPalette, QColor


class EdgeTTS:
    """Edge TTS sa Microsoft glasovima"""

    def __init__(self):
        self.voices = {
            "srpski": "sr-RS-SophieNeural",  # Srpski ženski glas
            "engleski": "en-US-AriaNeural",  # Engleski ženski glas
            "jenny": "en-US-JennyNeural",  # Engleski ženski glas
            "davis": "en-US-DavisNeural",  # Engleski muški glas
            "emma": "en-US-EmmaNeural",  # Engleski ženski glas
            "brian": "en-US-BrianNeural",  # Engleski muški glas
            "britanski": "en-GB-SoniaNeural",  # Britanski ženski glas
            "australijski": "en-AU-NatashaNeural",  # Australijski ženski glas
        }
        self.current_language = "engleski"
        self.voice = self.voices[self.current_language]
        self.rate = "+0%"  # Brzina govora
        self.pitch = "+0Hz"  # Visina tona
        self.volume = "+0%"  # Glasnoća
        self.is_speaking = False
        self.is_paused = False
        self.should_stop = False
        self.test_voice()

    def test_voice(self):
        """Testira da li glas radi"""
        try:
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.test_voice_async())
            loop.close()
        except Exception as e:
            print(f"Greška pri testiranju glasa: {e}")
            # Fallback na drugi engleski glas
            self.voice = "en-US-GuyNeural"

    async def test_voice_async(self):
        """Testira glas asinhrono"""
        try:
            communicate = edge_tts.Communicate("test", self.voice)
            # Ako ne baca grešku, glas radi
            print(f"Edge TTS glas {self.voice} je spreman!")
        except Exception as e:
            print(f"Glas {self.voice} ne radi: {e}")
            # Pokušaj sa drugim engleskim glasom
            self.voice = "en-US-GuyNeural"
            print(f"Koristim fallback glas: {self.voice}")

    async def speak_async(self, text):
        """Asinhrono čita tekst"""
        if not text or self.is_speaking:
            return

        self.is_speaking = True
        self.should_stop = False

        # Inicijalizuj pygame mixer jednom
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        try:
            # Očisti tekst - ukloni specijalne karaktere
            clean_text = self.clean_text(text)
            if not clean_text:
                print("Tekst je prazan nakon čišćenja")
                return

            # Podeli tekst na delove ako je previše dug
            max_chunk_size = 2000  # Edge TTS radi bolje sa kraćim delovima
            chunks = self.split_text_into_chunks(clean_text, max_chunk_size)

            for i, chunk in enumerate(chunks):
                if not chunk.strip() or self.should_stop:
                    continue

                print(f"Čitam deo {i+1}/{len(chunks)}: {len(chunk)} karaktera")

                # Kreiraj TTS komunikaciju
                communicate = edge_tts.Communicate(
                    chunk,
                    self.voice,
                    rate=self.rate,
                    pitch=self.pitch,
                    volume=self.volume,
                )

                # Kreiraj privremeni fajl sa eksplicitnom putanjom
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(
                    temp_dir, f"edge_tts_{int(time.time())}_{i}.mp3"
                )

                # Sačuvaj u temp fajl
                await communicate.save(temp_path)

                # Proveri da li je fajl kreiran i nije prazan
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    # Reprodukuj audio
                    if not pygame.mixer.get_init():
                        pygame.mixer.init()
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.play()

                    # Čekaj da se završi
                    while pygame.mixer.music.get_busy() and not self.should_stop:
                        if self.is_paused:
                            await asyncio.sleep(0.1)
                            continue
                        await asyncio.sleep(0.1)

                    # Očisti privremeni fajl
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                else:
                    print(f"Audio fajl za deo {i+1} nije kreiran ili je prazan")

                # Kratka pauza između delova
                if i < len(chunks) - 1 and not self.should_stop:
                    await asyncio.sleep(0.5)

        except Exception as e:
            print(f"Greška pri Edge TTS: {e}")
        finally:
            self.is_speaking = False
            self.is_paused = False
            # Ne gasi pygame mixer ovde, ostavi ga aktivan

    def clean_text(self, text):
        """Čisti tekst za TTS"""
        if not text:
            return ""

        # Ukloni HTML tagove
        import re

        text = re.sub(r"<[^>]+>", "", text)

        # Ukloni previše razmaka
        text = re.sub(r"\s+", " ", text)

        # Ukloni specijalne karaktere koji mogu da prave probleme
        text = re.sub(r"[^\w\s.,!?;:-]", "", text)

        # Ograniči dužinu (Edge TTS ima limit)
        if len(text) > 5000:
            text = text[:5000] + "..."

        return text.strip()

    def split_text_into_chunks(self, text, max_chunk_size):
        """Podeli tekst na delove za TTS"""
        if len(text) <= max_chunk_size:
            return [text]

        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 <= max_chunk_size:
                current_chunk.append(word)
                current_length += len(word) + 1
            else:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = len(word)

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def speak(self, text):
        """Pokreće TTS u background thread-u"""
        if not text or self.is_speaking:
            return

        # Pokreni TTS u background thread-u da ne blokira UI
        def run_tts():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.speak_async(text))
                loop.close()
            except Exception as e:
                print(f"Greška pri pokretanju Edge TTS: {e}")
            finally:
                # Resetuj UI dugmad kada se završi (thread-safe)
                if hasattr(self, "app") and hasattr(self.app, "tts_pause_btn"):
                    # Koristi QTimer.singleShot za thread-safe UI ažuriranje
                    from PySide6.QtCore import QTimer

                    QTimer.singleShot(0, lambda: self.reset_tts_ui())

        # Pokreni u background thread-u
        tts_thread = threading.Thread(target=run_tts, daemon=True)
        tts_thread.start()

    def reset_tts_ui(self):
        """Resetuje TTS UI dugmad (thread-safe)"""
        if hasattr(self, "app") and hasattr(self.app, "tts_pause_btn"):
            self.app.tts_pause_btn.setEnabled(False)
            self.app.tts_stop_btn.setEnabled(False)
            self.app.tts_pause_btn.setText("⏸️ Pauza")

    def pause(self):
        """Pauziraj TTS"""
        if self.is_speaking and not self.is_paused:
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.music.pause()
                self.is_paused = True
                print("TTS pauziran")
            except Exception as e:
                print(f"Greška pri pauziranju: {e}")

    def resume(self):
        """Nastavi TTS"""
        if self.is_speaking and self.is_paused:
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.music.unpause()
                self.is_paused = False
                print("TTS nastavljen")
            except Exception as e:
                print(f"Greška pri nastavljanju: {e}")

    def stop(self):
        """Zaustavlja čitanje"""
        self.should_stop = True
        self.is_speaking = False
        self.is_paused = False
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception as e:
            print(f"Greška pri zaustavljanju: {e}")
        print("TTS zaustavljen")

    def switch_language(self, language):
        """Prebacuje između jezika"""
        if language in self.voices:
            self.current_language = language
            self.voice = self.voices[language]
            print(f"Edge TTS glas prebačen na: {language} ({self.voice})")
            return True
        return False

    def get_available_languages(self):
        """Vraća dostupne jezike"""
        return list(self.voices.keys())


class NewsReader:
    """Čita vesti iz RSS feed-ova"""

    def __init__(self):
        # Srpski RSS feed-ovi
        self.feeds = {
            "B92": "https://www.b92.net/info/rss/vesti.xml",
            "RTS": "https://www.rts.rs/page/rss/ci/story/2/region.html",
            "Politika": "https://www.politika.rs/rss",
            "Novosti": "https://www.novosti.rs/rss",
            "Kurir": "https://www.kurir.rs/rss",
        }

    def get_latest_news(self, hours=24, max_news=10):
        """Dobija najnovije vesti iz poslednjih X sati"""
        all_news = []
        cutoff_time = datetime.now() - timedelta(hours=hours)

        for source, feed_url in self.feeds.items():
            try:
                feed = feedparser.parse(feed_url)

                for entry in feed.entries:
                    # Parsiraj datum
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])

                        if pub_date > cutoff_time:
                            all_news.append(
                                {
                                    "title": entry.title,
                                    "link": entry.link,
                                    "summary": getattr(entry, "summary", "Nema opisa"),
                                    "published": entry.published,
                                    "source": source,
                                }
                            )
            except Exception as e:
                print(f"Greška sa {source}: {e}")

        # Sortiraj po datumu (najnovije prvo)
        all_news.sort(key=lambda x: x["published"], reverse=True)
        return all_news[:max_news]

    def search_news(self, keyword):
        """Pretražuje vesti po ključnoj reči"""
        all_news = []

        for source, feed_url in self.feeds.items():
            try:
                feed = feedparser.parse(feed_url)

                for entry in feed.entries:
                    if (
                        keyword.lower() in entry.title.lower()
                        or keyword.lower() in getattr(entry, "summary", "").lower()
                    ):
                        all_news.append(
                            {
                                "title": entry.title,
                                "link": entry.link,
                                "summary": getattr(entry, "summary", "Nema opisa"),
                                "published": entry.published,
                                "source": source,
                            }
                        )
            except Exception as e:
                print(f"Greška sa {source}: {e}")

        return all_news[:10]


class ImageProcessor:
    """Klasa za obradu slika za LLaVA model"""

    def __init__(self):
        self.max_image_size = 1024  # Maksimalna veličina slike u pikselima
        self.supported_formats = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff"]

    def is_supported_image(self, file_path):
        """Proverava da li je fajl podržana slika"""
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.supported_formats

    def resize_image_if_needed(self, image):
        """Resize sliku ako je prevelika"""
        width, height = image.size

        # Ako je slika veća od max_image_size, resize-uj je
        if width > self.max_image_size or height > self.max_image_size:
            # Zadrži aspect ratio
            if width > height:
                new_width = self.max_image_size
                new_height = int((height * self.max_image_size) / width)
            else:
                new_height = self.max_image_size
                new_width = int((width * self.max_image_size) / height)

            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            print(f"Resized image from {width}x{height} to {new_width}x{new_height}")

        return image

    def image_to_base64(self, image_path):
        """Konvertuje sliku u base64 string"""
        try:
            # Otvori sliku
            with Image.open(image_path) as img:
                # Konvertuj u RGB ako je potrebno (za PNG sa transparency)
                if img.mode in ("RGBA", "LA", "P"):
                    # Kreiraj belu pozadinu
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(
                        img, mask=img.split()[-1] if img.mode == "RGBA" else None
                    )
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Resize ako je potrebno
                img = self.resize_image_if_needed(img)

                # Konvertuj u base64
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)
                img_bytes = buffer.getvalue()

                try:
                    base64_string = base64.b64encode(img_bytes).decode("utf-8")
                    # Ollama očekuje samo base64 string, ne data URL
                    return base64_string
                except UnicodeDecodeError as e:
                    print(f"UTF-8 decode error: {e}")
                    # Fallback: encode as latin-1 then decode as utf-8
                    base64_string = base64.b64encode(img_bytes).decode("latin-1")
                    return base64_string

        except Exception as e:
            print(f"Greška pri konvertovanju slike {image_path}: {e}")
            return None

    def get_image_info(self, image_path):
        """Dobija informacije o slici"""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                format_name = img.format
                mode = img.mode
                file_size = os.path.getsize(image_path)

                return {
                    "width": width,
                    "height": height,
                    "format": format_name,
                    "mode": mode,
                    "file_size": file_size,
                    "file_size_mb": round(file_size / (1024 * 1024), 2),
                }
        except Exception as e:
            print(f"Greška pri dobijanju informacija o slici {image_path}: {e}")
            return None


class ImageGenerator:
    """Klasa za generaciju slika sa različitim Stable Diffusion modelima"""

    def __init__(self):
        self.pipeline = None
        self.model_loaded = False
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"CUDA available: {torch.cuda.is_available()}")
        print(f"Device selected: {self.device}")
        if torch.cuda.is_available():
            print(f"CUDA device: {torch.cuda.get_device_name(0)}")
            print(
                f"CUDA memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
            )
        self.generation_in_progress = False
        self.is_loading = False

        # Dostupni modeli
        self.available_models = {
            "SDXL Base (1024x1024)": {
                "model_id": "stabilityai/stable-diffusion-xl-base-1.0",
                "type": "xl",
                "default_size": (1024, 1024),
                "default_steps": 50,
                "default_guidance": 7.5,
                "default_negative": "blurry, low quality, distorted, ugly, bad anatomy, duplicate, multiple, two, double, repeated, extra",
                "description": "Najbolji kvalitet, veća memorija (~6GB) - optimizovano",
            },
            "Juggernaut XL (832x1216)": {
                "model_id": "Q:\\huggingface_cache\\models\\juggernautXL_ragnarokBy.safetensors",
                "type": "xl",
                "default_size": (832, 1216),
                "default_steps": 35,
                "default_guidance": 4.5,
                "default_negative": "",  # Juggernaut preporučuje bez negative prompt-a
                "description": "Fotorealistični model - poboljšane poze, ruke, noge, digitalno slikanje",
            },
            "DynaVision XL (1024x1024)": {
                "model_id": "Q:\\huggingface_cache\\models\\dynavisionXLAllInOneStylized_releaseV0610Bakedvae.safetensors",
                "type": "xl",
                "default_size": (1024, 1024),
                "default_steps": 30,
                "default_guidance": 6.0,
                "default_negative": "blurry, low quality, distorted, ugly, bad anatomy, duplicate, multiple, two, double, repeated, extra, realistic, photorealistic",
                "description": "3D stilizovani model - Pixar/Dreamworks/Disney stil, SFW i NSFW, NE KORISTI REFINER",
            },
            "OmnigenXL (1024x1024)": {
                "model_id": "Q:\\huggingface_cache\\models\\omnigenxlNSFWSFW_v10.safetensors",
                "type": "xl",
                "default_size": (1024, 1024),
                "default_steps": 25,  # Preporučeno 20-30 za SFW, 20-30 za NSFW
                "default_guidance": 7.0,  # Preporučeno 5-9 za SFW, 6-8 za NSFW
                "default_negative": "blurry, low quality, distorted, ugly, bad anatomy, duplicate, multiple, two, double, repeated, extra",
                "description": "OmnigenXL - Versatile SFW/NSFW, perfekcija bez refiner-a",
            },
            "SD 2.1 Base (512x512)": {
                "model_id": "stabilityai/stable-diffusion-2-1-base",
                "type": "base",
                "default_size": (512, 512),
                "default_steps": 40,
                "default_guidance": 7.0,
                "default_negative": "blurry, low quality, distorted, ugly, bad anatomy, duplicate, multiple, two, double, repeated, extra",
                "description": "Brži, manje memorije (~5GB)",
            },
            "SD 1.5 (512x512)": {
                "model_id": "runwayml/stable-diffusion-v1-5",
                "type": "base",
                "default_size": (512, 512),
                "default_steps": 35,
                "default_guidance": 7.0,
                "default_negative": "blurry, low quality, distorted, ugly, bad anatomy, duplicate, multiple, two, double, repeated, extra",
                "description": "Najbrži, najmanje memorije (~4GB)",
            },
            "PornVision (512x512)": {
                "model_id": "Q:\\huggingface_cache\\models\\pornvision_final.safetensors",
                "type": "base",
                "default_size": (512, 512),
                "default_steps": 30,
                "default_guidance": 7.5,
                "default_negative": "blurry, low quality, distorted, ugly, bad anatomy, duplicate, multiple, two, double, repeated, extra, censored, censored content",
                "description": "PornVision - Specialized adult content model",
            },
            "epiCRealism XL (1024x1024)": {
                "model_id": "Q:\\huggingface_cache\\models\\epicrealismXL_vxviiCrystalclear.safetensors",
                "type": "xl",
                "default_size": (1024, 1024),
                "default_steps": 30,
                "default_guidance": 6.0,
                "default_negative": "anime, cartoon, blurry, low quality, distorted, ugly, bad anatomy",
                "description": "Fotorealistični model - poboljšane lica i ruke, crisp output, Clip Skip: 1",
            },
            "ZavyChromaXL (1024x1024)": {
                "model_id": "Q:\\huggingface_cache\\models\\zavychromaxl_v100.safetensors",
                "type": "xl",
                "default_size": (1024, 1024),
                "default_steps": 25,
                "default_guidance": 6.5,
                "default_negative": "anime, high contrast, oily skin, plastic skin, blurry, low quality, distorted, ugly, bad anatomy",
                "description": "Fotorealistični model - poboljšana saturacija, bolje zube, oči, ruke i noge",
            },
        }

        # Trenutno selektovani model
        self.current_model = "Juggernaut XL (832x1216)"

        # LoRA modeli - koristi Q: particiju (samo oni koji postoje)
        self.available_loras = {
            "Logo.Redmond": {
                "path": "Q:\\huggingface_cache\\loras\\LogoRedmondV2-Logo-LogoRedmAF.safetensors",
                "trigger": "logologoredmaf",
                "strength": 0.8,
                "description": "Logo generacija - Logo.Redmond LoRA za SDXL",
                "base_model": "SDXL Base",
            },
            "Add Detail XL": {
                "path": "Q:\\huggingface_cache\\loras\\add-detail-xl.safetensors",
                "trigger": "adddetail",
                "strength": 0.6,
                "description": "Dodaje detalje i oštrinu u slike - SDXL",
                "base_model": "SDXL Base",
            },
            "Logo Maker 9000": {
                "path": "Q:\\huggingface_cache\\loras\\logo.safetensors",
                "trigger": "logomkrdsxlvectorlogo",
                "strength": 0.9,
                "description": "Logo Maker 9000 SDXL - vector quality logotipi u beskonačnom broju stilova",
                "base_model": "SDXL Base",
            },
            "Bad Quality v02": {
                "path": "Q:\\huggingface_cache\\loras\\badquality_v02.safetensors",
                "trigger": "badquality",
                "strength": 0.7,
                "description": "Poboljšava kvalitet slika - uklanja artifacts i noise",
                "base_model": "Juggernaut XL",
            },
            "Colossus Project XL": {
                "path": "Q:\\huggingface_cache\\loras\\FF.102.colossusProjectXLSFW_49bExperimental.LORA.safetensors",
                "trigger": "",
                "strength": 1.2,
                "description": "Colossus Project XL 4.9b - FFusionAI ekstraktovana LoRA iz 400GB repository",
                "base_model": "SDXL Base",
            },
            "JuggerCine XL": {
                "path": "Q:\\huggingface_cache\\loras\\JuggerCineXL2.safetensors",
                "trigger": "juggercine",
                "strength": 0.7,
                "description": "JuggerCine XL - cinematički stil za film-like slike",
                "base_model": "Juggernaut XL",
            },
            "Cinematic Style v1": {
                "path": "Q:\\huggingface_cache\\loras\\CinematicStyle_v1.safetensors",
                "trigger": "cinematicstyle",
                "strength": 0.8,
                "description": "Cinematički stil - profesionalni film look sa dramskim osvetljenjem",
                "base_model": "Juggernaut XL",
            },
            "Super Eye Detailer": {
                "path": "Q:\\huggingface_cache\\loras\\Super_Eye_Detailer_By_Stable_Yogi_SDPD0.safetensors",
                "trigger": "supereye",
                "strength": 0.7,
                "description": "Poboljšava detalje očiju - realistične i izražajne oči",
                "base_model": "Juggernaut XL",
            },
            "Disney Princess XL": {
                "path": "Q:\\huggingface_cache\\loras\\princess_xl_v2.safetensors",
                "trigger": "Anna, Ariel, Aurora, Belle, Cinderella, Elsa, Jasmine, Merida, Moana, Mulan, Pocahontas, Rapunzel, Snow White, Tiana",
                "strength": 0.6,
                "description": "All Disney Princess XL - sve Disney princeze iz Ralph Breaks the Internet",
                "base_model": "SDXL Base",
            },
            "Pixel Art XL": {
                "path": "Q:\\huggingface_cache\\loras\\pixel-art-xl-v1.1.safetensors",
                "trigger": "",
                "strength": 0.9,
                "description": "Pixel Art XL - generiše pixel art stil, ne koristi 'pixel art' u promptu",
                "base_model": "SDXL Base",
            },
            "Extremely Detailed": {
                "path": "Q:\\huggingface_cache\\loras\\detailed_notrigger.safetensors",
                "trigger": "",
                "strength": 1.0,
                "description": "Extremely detailed slider - opseg -1 do 1, bez trigger reči",
                "base_model": "SDXL Base",
            },
            "Real Humans": {
                "path": "Q:\\huggingface_cache\\loras\\real-humans-PublicPrompts.safetensors",
                "trigger": "photo, portrait photo",
                "strength": 1.0,
                "description": "Real Humans - fotorealistični ljudi, odličan za selfie portrete",
                "base_model": "SDXL Base",
            },
            "Hand Fine Tuning XL": {
                "path": "Q:\\huggingface_cache\\loras\\HandFineTuning_XL.safetensors",
                "trigger": "",
                "strength": 0.8,
                "description": "Hand Fine Tuning - poboljšava renderovanje ruku, kompatibilan sa realističnim i anime modelima",
                "base_model": "SDXL Base",
            },
            "ParchartXL CODA": {
                "path": "Q:\\huggingface_cache\\loras\\ParchartXL_CODA.safetensors",
                "trigger": "on parchment",
                "strength": 1.0,
                "description": "ParchartXL - ilustracije na pergamentu sa teksturom i anotacijama",
                "base_model": "SDXL Base",
            },
            "Dolls Kill Collection": {
                "path": "Q:\\huggingface_cache\\loras\\Dollskill_Downbeat_Spiked.safetensors",
                "trigger": "dollskill",
                "strength": 0.8,
                "description": "Dolls Kill Collection - kolekcija outfita (streetwear, clubwear, cute dresses, lingerie)",
                "base_model": "SDXL Base",
            },
            "Sketchit": {
                "path": "Q:\\huggingface_cache\\loras\\sketch_it.safetensors",
                "trigger": "",
                "strength": 1.0,
                "description": "Sketchit - crno-beli crtež u ink wash stilu sa ekspresivnim linijama",
                "base_model": "SDXL Base",
            },
            "XL More Art Enhancer": {
                "path": "Q:\\huggingface_cache\\loras\\xl_more_art-full_v1.safetensors",
                "trigger": "Aerial",
                "strength": 0.9,
                "description": "XL More Art Enhancer - poboljšava estetiku, artistički i kreativni izgled, detaljnije slike",
                "base_model": "SDXL Base",
            },
            "MS Paint Portraits": {
                "path": "Q:\\huggingface_cache\\loras\\SDXL_MSPaint_Portrait.safetensors",
                "trigger": "MSPaint portrait, MSPaint drawing",
                "strength": 1.0,
                "description": "SDXL MS Paint Portraits - loš kvalitet MS Paint stil (namerno!)",
                "base_model": "SDXL Base",
            },
            "Greg Rutkowski Style": {
                "path": "Q:\\huggingface_cache\\loras\\greg_rutkowski_xl_2.safetensors",
                "trigger": "greg rutkowski",
                "strength": 1.0,
                "description": "Greg Rutkowski inspired style - fantasy art u ArtStation stilu",
                "base_model": "SDXL Base",
            },
            "Eldritch Comics": {
                "path": "Q:\\huggingface_cache\\loras\\EldritchComicsXL1.2.safetensors",
                "trigger": "comic book",
                "strength": 1.0,
                "description": "Eldritch Comics - comic book stil sa oštrim konturama",
                "base_model": "SDXL Base",
            },
            "Sarah Miller TLOU": {
                "path": "Q:\\huggingface_cache\\loras\\sarah_tlou_sdxl_v3-000088.safetensors",
                "trigger": "sarah miller",
                "strength": 0.8,
                "description": "Sarah Miller iz The Last of Us - karakter LoRA",
                "base_model": "SDXL Base",
            },
        }

        # TI Embeddings - koristi Q: particiju
        self.available_embeddings = {
            "My Art Style": {
                "path": "Q:\\huggingface_cache\\embeddings\\my_art_style.bin",
                "trigger": "my_art_style",
                "description": "Moj umetnički stil",
            },
            "Logo Style": {
                "path": "Q:\\huggingface_cache\\embeddings\\logo_style.bin",
                "trigger": "logo_style",
                "description": "Stil za logotipe",
            },
            "Portrait Style": {
                "path": "Q:\\huggingface_cache\\embeddings\\portrait_style.bin",
                "trigger": "portrait_style",
                "description": "Stil za portrete",
            },
        }

        # Aktivni LoRA i embedding modeli
        self.active_loras = []
        self.active_embeddings = []

        # ControlNet varijable za img2img
        self.controlnet_pipeline = None
        self.controlnet_loaded = False
        self.available_controlnets = {
            "Canny": {
                "model_id": "Q:/huggingface_cache/controlnet/canny",
                "detector": "canny",
                "description": "Edge detection - dobro za konture i oblike",
            },
            "Depth": {
                "model_id": "Q:/huggingface_cache/controlnet/depth",
                "detector": "depth",
                "description": "Depth map - dobro za 3D strukture",
            },
        }
        self.current_controlnet = None
        self.controlnet_detector = None

    def switch_model(self, model_name):
        """Prebacuje na drugi model"""
        if model_name not in self.available_models:
            print(f"Model {model_name} not available")
            return False

        if self.current_model == model_name and self.model_loaded:
            print(f"Model {model_name} already loaded")
            return True

        if self.is_loading:
            print(f"Model is already being loaded, skipping switch to {model_name}")
            return False

        # Unload current model
        if self.model_loaded:
            try:
                self.unload_model()
            except AttributeError:
                # Fallback - manual cleanup if unload_model method is missing
                if hasattr(self, "pipeline") and self.pipeline is not None:
                    del self.pipeline
                    self.pipeline = None
                    self.model_loaded = False
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    print("Model unloaded manually (fallback)")

        self.current_model = model_name
        print(f"Switched to model: {model_name}")
        return True

    def load_model(self):
        """Učitava selektovani model"""
        try:
            if self.model_loaded:
                return True

            if self.is_loading:
                print(f"Model is already being loaded, skipping load")
                return False

            self.is_loading = True
            model_info = self.available_models[self.current_model]
            model_id = model_info["model_id"]
            model_type = model_info["type"]

            print(f"Loading {self.current_model} model on {self.device}...")
            print(f"Model ID: {model_id}")
            print(f"Model type: {model_type}")

            # Kreiraj pipeline sa optimizacijama za RTX 2080
            print(f"Loading model with device: {self.device}")
            print("Using torch_dtype: torch.float32 (to avoid mixed precision issues)")
            print("Using variant: None (to avoid fp16 precision issues)")

            # MIXED PRECISION FIX: Use float32 to avoid Half/float mismatch
            if model_type == "xl":
                from diffusers import StableDiffusionXLPipeline

                # Check if it's a local .safetensors file
                if model_id.endswith(".safetensors"):
                    print("Loading Juggernaut XL from local .safetensors file...")
                    self.pipeline = StableDiffusionXLPipeline.from_single_file(
                        model_id,
                        torch_dtype=torch.float32,
                        use_safetensors=True,
                    )
                else:
                    self.pipeline = StableDiffusionXLPipeline.from_pretrained(
                        model_id,
                        torch_dtype=torch.float32,  # Use float32 instead of float16 to avoid mixed precision issues
                        use_safetensors=True,
                        variant=None,  # Don't use fp16 variant to avoid precision issues
                    )
            else:
                from diffusers import StableDiffusionPipeline

                # Check if it's a local .safetensors file
                if model_id.endswith(".safetensors"):
                    print(
                        f"Loading {self.current_model} from local .safetensors file..."
                    )
                    self.pipeline = StableDiffusionPipeline.from_single_file(
                        model_id,
                        torch_dtype=torch.float32,
                        use_safetensors=True,
                    )
                else:
                    self.pipeline = StableDiffusionPipeline.from_pretrained(
                        model_id,
                        torch_dtype=torch.float32,
                        use_safetensors=True,
                        variant=None,
                    )

            # Optimizacije za RTX 2080
            if self.device == "cuda":
                print(f"Moving pipeline to CUDA device...")
                self.pipeline = self.pipeline.to(self.device)
                print(
                    f"Pipeline moved to CUDA. CUDA memory: {torch.cuda.memory_allocated()/1024**3:.2f} GB"
                )
                # Enable sequential CPU offload for memory efficiency
                self.pipeline.enable_sequential_cpu_offload()
                print("Sequential CPU offload enabled for memory efficiency")

                # Proveri VAE status
                print(f"VAE device: {self.pipeline.vae.device}")
                print(f"VAE dtype: {self.pipeline.vae.dtype}")

                # VAE FIX: Force VAE to use float32 instead of float16
                # Ovo rešava NaN problem koji uzrokuje crne slike
                if hasattr(self.pipeline.vae, "config"):
                    self.pipeline.vae.config.force_upcast = (
                        True  # Force upcast to float32
                    )
                    print("VAE force_upcast set to True (float32)")

                # DODATNI FIX: Force VAE to float32 (already done by pipeline dtype)
                print("VAE using float32 (from pipeline torch_dtype=float32)")

                # DEVICE FIX: Keep VAE on CUDA but with float32 to avoid device mismatch
                # VAE mora biti na istom device-u kao ostale komponente
                print("VAE kept on CUDA with float32 - avoiding device mismatch")

            self.model_loaded = True
            print(f"Stable Diffusion XL model loaded successfully on {self.device}")
            return True

        except Exception as e:
            print(f"Error loading Stable Diffusion XL model: {str(e)}")
            return False
        finally:
            self.is_loading = False

    def load_lora(self, lora_name, strength=0.8):
        """Učitava LoRA model"""
        if lora_name in self.available_loras:
            lora_info = self.available_loras[lora_name]
            try:
                if not self.model_loaded:
                    if not self.load_model():
                        return False

                # Proveri da li fajl postoji
                if not os.path.exists(lora_info["path"]):
                    print(f"LoRA file not found: {lora_info['path']}")
                    print(
                        f"Please download and place the LoRA file in the correct location."
                    )
                    return False

                # Proveri da li je LoRA već učitan
                for active_lora in self.active_loras:
                    if active_lora["name"] == lora_name:
                        print(f"LoRA {lora_name} already loaded")
                        return True

                # Učitaj LoRA sa PEFT
                try:
                    from peft import PeftModel

                    self.pipeline.load_lora_weights(lora_info["path"])
                except ImportError:
                    print("PEFT not installed. Installing...")
                    import subprocess

                    subprocess.check_call(["pip", "install", "peft>=0.7.0"])
                    from peft import PeftModel

                    self.pipeline.load_lora_weights(lora_info["path"])

                self.active_loras.append(
                    {
                        "name": lora_name,
                        "trigger": lora_info["trigger"],
                        "strength": strength,
                    }
                )
                print(f"Loaded LoRA: {lora_name} with strength {strength}")
                return True
            except Exception as e:
                print(f"Error loading LoRA {lora_name}: {e}")
                return False
        return False

    def unload_lora(self, lora_name):
        """Uklanja LoRA model"""
        try:
            if not self.model_loaded:
                return False

            # Ukloni iz liste aktivnih
            self.active_loras = [
                lora for lora in self.active_loras if lora["name"] != lora_name
            ]

            # Unload LoRA weights
            self.pipeline.unload_lora_weights()
            print(f"Unloaded LoRA: {lora_name}")
            return True
        except Exception as e:
            print(f"Error unloading LoRA {lora_name}: {e}")
            return False

    def load_embedding(self, embedding_name):
        """Učitava TI embedding"""
        if embedding_name in self.available_embeddings:
            embedding_info = self.available_embeddings[embedding_name]
            try:
                if not self.model_loaded:
                    if not self.load_model():
                        return False

                # Proveri da li fajl postoji
                if not os.path.exists(embedding_info["path"]):
                    print(f"Embedding file not found: {embedding_info['path']}")
                    print(
                        f"Please download and place the embedding file in the correct location."
                    )
                    return False

                # Proveri da li je embedding već učitan
                if embedding_info["trigger"] in self.active_embeddings:
                    print(f"Embedding {embedding_name} already loaded")
                    return True

                # Učitaj embedding
                self.pipeline.load_textual_inversion(embedding_info["path"])
                self.active_embeddings.append(embedding_info["trigger"])
                print(f"Loaded embedding: {embedding_name}")
                return True
            except Exception as e:
                print(f"Error loading embedding {embedding_name}: {e}")
                return False
        return False

    def unload_embedding(self, embedding_name):
        """Uklanja TI embedding"""
        try:
            if not self.model_loaded:
                return False

            if embedding_name in self.available_embeddings:
                trigger = self.available_embeddings[embedding_name]["trigger"]
                if trigger in self.active_embeddings:
                    self.active_embeddings.remove(trigger)
                    print(f"Unloaded embedding: {embedding_name}")
                    return True
            return False
        except Exception as e:
            print(f"Error unloading embedding {embedding_name}: {e}")
            return False

    def apply_loras_to_prompt(self, prompt):
        """Dodaje LoRA triggere u prompt"""
        for lora in self.active_loras:
            trigger = lora["trigger"]
            strength = lora["strength"]
            prompt = f"<lora:{trigger}:{strength}> {prompt}"
        return prompt

    def apply_embeddings_to_prompt(self, prompt):
        """Dodaje TI embedding triggere u prompt"""
        for trigger in self.active_embeddings:
            prompt = f"{trigger} {prompt}"
        return prompt

    def get_image_context_from_llm(self, user_prompt, conversation_history=None):
        """Izvlači kontekst iz LLM conversation history za image generation"""
        if conversation_history is None or not conversation_history:
            return user_prompt

        # Uzmi poslednje 4 poruke iz LLM-a (2 user + 2 AI)
        recent_messages = conversation_history[-8:]  # 4 user + 4 AI

        context_parts = []
        for msg in recent_messages:
            if msg["role"] == "user":
                # Skrati user poruku na maksimalno 50 karaktera
                user_content = (
                    msg["content"][:50] + "..."
                    if len(msg["content"]) > 50
                    else msg["content"]
                )
                context_parts.append(f"User: {user_content}")
            elif msg["role"] == "assistant":
                # Skrati AI odgovor na maksimalno 50 karaktera
                ai_content = (
                    msg["content"][:50] + "..."
                    if len(msg["content"]) > 50
                    else msg["content"]
                )
                context_parts.append(f"AI: {ai_content}")

        # Kombinuj sa trenutnim promptom (kratko da ne pređe CLIP limit)
        if context_parts:
            context = " | ".join(context_parts[-4:])  # Samo poslednje 4
            enhanced_prompt = f"{context} | Now: {user_prompt}"
        else:
            enhanced_prompt = user_prompt

        print(f"LLM Context enhanced prompt: {enhanced_prompt}")
        return enhanced_prompt

    def add_image_to_llm_context(
        self, image_path, prompt, settings, conversation_history=None, max_history=50
    ):
        """Dodaje generisanu sliku u LLM kontekst"""
        try:
            if conversation_history is None:
                print("Warning: conversation_history not provided")
                return

            # Kreiraj image info za LLM kontekst
            image_info = {
                "role": "assistant",
                "content": f"Generated image: {prompt} ({settings['width']}x{settings['height']})",
                "image_path": image_path,
                "timestamp": time.time(),
                "type": "image_generation",
            }

            # Dodaj u conversation history
            conversation_history.append(image_info)

            # Zadrži samo poslednje N poruka
            if len(conversation_history) > max_history:
                conversation_history[:] = conversation_history[-max_history:]

            print(f"Image added to LLM context: {prompt}")

        except Exception as e:
            print(f"Error adding image to LLM context: {e}")

    def generate_image(
        self,
        prompt,
        negative_prompt="",
        width=1024,
        height=1024,
        steps=20,
        guidance_scale=7.5,
        seed=None,
        progress_callback=None,
        conversation_history=None,
    ):
        """Generiše sliku na osnovu prompt-a"""
        try:
            if not self.model_loaded:
                if not self.load_model():
                    return None, "Failed to load model"

            if self.generation_in_progress:
                return None, "Generation already in progress"

            self.generation_in_progress = True
            start_time = time.time()

            # Koristi samo originalni prompt (bez LLM konteksta)
            original_prompt = prompt

            # Primijeni LoRA i TI embedding modele na prompt
            prompt = self.apply_embeddings_to_prompt(prompt)
            prompt = self.apply_loras_to_prompt(prompt)

            print(f"Generating image with prompt: '{prompt}'")
            print(f"Original prompt: '{original_prompt}'")
            print(f"Negative prompt: '{negative_prompt}'")
            print(f"Active LoRAs: {[lora['name'] for lora in self.active_loras]}")
            print(f"Active embeddings: {self.active_embeddings}")
            print(
                f"Settings: {width}x{height}, {steps} steps, guidance={guidance_scale}"
            )

            # Postavi seed ako je dat
            if seed is not None:
                torch.manual_seed(seed)

            # Callback funkcija za progress
            def internal_progress_callback(step, timestep, latents):
                progress = int((step / steps) * 100)
                print(f"Generation progress: {progress}% (step {step}/{steps})")

                # Pozovi eksterni callback ako postoji
                if progress_callback:
                    progress_callback(step, timestep, latents)

            # Clear GPU cache before generation
            if self.device == "cuda":
                torch.cuda.empty_cache()
                print("GPU cache cleared before generation")

            # VAE STATUS CHECK: Proveri VAE pre generacije
            print(f"VAE device before generation: {self.pipeline.vae.device}")
            print(f"VAE dtype before generation: {self.pipeline.vae.dtype}")
            if hasattr(self.pipeline.vae.config, "force_upcast"):
                print(f"VAE force_upcast: {self.pipeline.vae.config.force_upcast}")

            # DEVICE CONSISTENCY: Proveri da su sve komponente na istom device-u
            print(f"UNet device: {self.pipeline.unet.device}")
            print(f"Text Encoder device: {self.pipeline.text_encoder.device}")

            # Generiši sliku sa originalnim postavkama
            if self.device == "cuda":
                # VAE FIX: Temporarily enable VAE upcasting to prevent NaN
                original_force_upcast = None
                if hasattr(self.pipeline.vae.config, "force_upcast"):
                    original_force_upcast = self.pipeline.vae.config.force_upcast
                    self.pipeline.vae.config.force_upcast = True
                    print("VAE upcasting enabled to prevent NaN values")

                try:
                    # AUTOCAST FIX: Remove autocast completely - it causes black images!
                    # Prema Hugging Face forumu, autocast uzrokuje crne slike

                    # Kreiraj generator sa seed-om ako je dat
                    generator = None
                    if seed is not None:
                        generator = torch.Generator(device=self.device).manual_seed(
                            seed
                        )

                    result = self.pipeline(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        width=width,
                        height=height,
                        num_inference_steps=steps,
                        guidance_scale=guidance_scale,
                        num_images_per_prompt=1,
                        generator=generator,
                        callback=internal_progress_callback,
                        callback_steps=1,
                    )
                finally:
                    # Restore original VAE setting
                    if original_force_upcast is not None:
                        self.pipeline.vae.config.force_upcast = original_force_upcast
                        print("VAE upcasting restored to original setting")
            else:
                # Za CPU koristi originalne postavke
                with torch.no_grad():
                    # Kreiraj generator sa seed-om ako je dat
                    generator = None
                    if seed is not None:
                        generator = torch.Generator(device=self.device).manual_seed(
                            seed
                        )

                    result = self.pipeline(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        width=width,
                        height=height,
                        num_inference_steps=steps,
                        guidance_scale=guidance_scale,
                        num_images_per_prompt=1,
                        generator=generator,
                        callback=internal_progress_callback,
                        callback_steps=1,
                    )

            # Clear GPU cache after generation
            if self.device == "cuda":
                torch.cuda.empty_cache()
                print("GPU cache cleared after generation")

            generation_time = time.time() - start_time
            print(f"Image generated in {generation_time:.2f} seconds")

            # Debug informacije o generisanoj slici
            if result.images and len(result.images) > 0:
                image = result.images[0]
                print(f"Generated image type: {type(image)}")
                print(f"Generated image mode: {getattr(image, 'mode', 'N/A')}")
                print(f"Generated image size: {getattr(image, 'size', 'N/A')}")

                # NAN DETECTION: Proveri da li slika sadrži NaN vrednosti
                if hasattr(image, "getdata"):
                    image_data = list(image.getdata())
                    if any(
                        any(
                            isinstance(pixel, (int, float)) and (pixel != pixel)
                            for pixel in (
                                pixel if isinstance(pixel, tuple) else [pixel]
                            )
                        )
                        for pixel in image_data[:10]
                    ):
                        print("ERROR: Image contains NaN values!")
                        # Clean up NaN values
                        import numpy as np

                        img_array = np.array(image)
                        img_array = np.nan_to_num(
                            img_array, nan=0.0, posinf=1.0, neginf=0.0
                        )
                        image = Image.fromarray(img_array.astype(np.uint8))
                        print("NaN values cleaned up")

                # Proveri da li je slika crna
                if hasattr(image, "getbbox"):
                    bbox = image.getbbox()
                    print(f"Image bbox: {bbox}")
                    if bbox is None:
                        print(
                            "WARNING: Generated image appears to be completely black!"
                        )

                # Slika će biti dodana u LLM kontekst u ImageGenerationWorker

                self.generation_in_progress = False
                return image, None
            else:
                self.generation_in_progress = False
                return None, "No image generated"

        except Exception as e:
            self.generation_in_progress = False
            print(f"Error during image generation: {e}")
            import traceback

            traceback.print_exc()
            return None, str(e)

    def load_controlnet(self, controlnet_name):
        """Učitava ControlNet model"""
        if not CONTROLNET_AVAILABLE:
            print("ControlNet not available. Please install controlnet-aux.")
            return False

        if controlnet_name not in self.available_controlnets:
            print(f"ControlNet {controlnet_name} not available")
            return False

        try:
            controlnet_info = self.available_controlnets[controlnet_name]
            model_id = controlnet_info["model_id"]
            detector_type = controlnet_info["detector"]

            print(f"Loading ControlNet: {controlnet_name}...")

            # Učitaj ControlNet model
            controlnet = ControlNetModel.from_pretrained(
                model_id, torch_dtype=torch.float16, cache_dir="Q:\\huggingface_cache"
            )

            # Kreiraj ControlNet pipeline - koristi SDXL base model
            self.controlnet_pipeline = (
                StableDiffusionXLControlNetPipeline.from_pretrained(
                    "stabilityai/stable-diffusion-xl-base-1.0",
                    controlnet=controlnet,
                    torch_dtype=torch.float16,
                    cache_dir="Q:\\huggingface_cache",
                ).to(self.device)
            )

            # Učitaj detektor
            if detector_type == "canny":
                self.controlnet_detector = CannyDetector()
            elif detector_type == "depth":
                self.controlnet_detector = MidasDetector()
            elif detector_type == "openpose":
                self.controlnet_detector = OpenposeDetector()

            self.current_controlnet = controlnet_name
            self.controlnet_loaded = True
            print(f"ControlNet {controlnet_name} loaded successfully!")
            return True

        except Exception as e:
            print(f"Error loading ControlNet {controlnet_name}: {e}")
            return False

    def unload_controlnet(self):
        """Oslobađa ControlNet memoriju"""
        if self.controlnet_pipeline is not None:
            del self.controlnet_pipeline
            self.controlnet_pipeline = None
            self.controlnet_loaded = False
            self.current_controlnet = None
            self.controlnet_detector = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("ControlNet unloaded")

    def generate_control_image(self, input_image, controlnet_type):
        """Generiše control image na osnovu input slike"""
        if not self.controlnet_loaded or not self.controlnet_detector:
            print("ControlNet not loaded")
            return None

        try:
            # Konvertuj PIL Image u numpy array ako potrebno
            if isinstance(input_image, Image.Image):
                image = input_image
            else:
                image = Image.open(input_image)

            # Generiši control image
            if controlnet_type == "canny":
                control_image = self.controlnet_detector(image)
            elif controlnet_type == "depth":
                control_image = self.controlnet_detector(image)
            elif controlnet_type == "openpose":
                control_image = self.controlnet_detector(image)
            else:
                print(f"Unknown controlnet type: {controlnet_type}")
                return None

            return control_image

        except Exception as e:
            print(f"Error generating control image: {e}")
            return None

    def generate_image_to_image(
        self,
        prompt,
        input_image,
        controlnet_type="canny",
        negative_prompt="",
        width=1024,
        height=1024,
        steps=20,
        guidance_scale=7.5,
        controlnet_conditioning_scale=1.0,
        seed=None,
        progress_callback=None,
        conversation_history=None,
    ):
        """Generiše sliku na osnovu input slike i prompt-a (img2img)"""
        try:
            if not CONTROLNET_AVAILABLE:
                return None, "ControlNet not available. Please install controlnet-aux."

            if not self.controlnet_loaded:
                return (
                    None,
                    "ControlNet not loaded. Please load a ControlNet model first.",
                )

            if self.generation_in_progress:
                return None, "Generation already in progress"

            self.generation_in_progress = True

            # Generiši control image
            control_image = self.generate_control_image(input_image, controlnet_type)
            if control_image is None:
                self.generation_in_progress = False
                return None, "Failed to generate control image"

            # Primijeni LoRA i TI embedding modele na prompt
            if self.active_loras:
                prompt = self.apply_loras_to_prompt(prompt)

            # Generiši seed ako nije dat
            if seed is None:
                seed = random.randint(0, 2**32 - 1)

            generator = torch.Generator(device=self.device).manual_seed(seed)

            print(f"Generating img2img with ControlNet {self.current_controlnet}...")
            print(f"Prompt: {prompt}")
            print(f"Seed: {seed}")

            # Generiši sliku
            result = self.controlnet_pipeline(
                prompt=prompt,
                image=control_image,
                negative_prompt=negative_prompt,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                controlnet_conditioning_scale=controlnet_conditioning_scale,
                generator=generator,
                width=width,
                height=height,
            ).images[0]

            self.generation_in_progress = False
            return (
                result,
                f"Image generated successfully with ControlNet {self.current_controlnet}",
            )

        except Exception as e:
            self.generation_in_progress = False
            print(f"Error in img2img generation: {e}")
            return None, f"Error generating image: {str(e)}"


class ImageUpscaler:
    """Klasa za upscaling slika koristeći ESRGAN i druge upscaler modele"""

    def __init__(self):
        self.available_upscalers = {
            "RealESRGAN 4x": {
                "model_id": "xinntao/realesrgan-x4plus",
                "scale": 4,
                "description": "Opšti upscaling 4x - dobar za fotografije",
            },
            "RealESRGAN Anime": {
                "model_id": "xinntao/realesrgan-x4plus-anime",
                "scale": 4,
                "description": "Anime/manga upscaling 4x",
            },
            "SD Upscaler": {
                "model_id": "stabilityai/stable-diffusion-x4-upscaler",
                "scale": 4,
                "description": "SD upscaler - najbolji za AI generisane slike",
            },
        }

        self.upscaler_loaded = False
        self.upscaler_pipeline = None
        self.current_upscaler = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def load_upscaler(self, upscaler_name):
        """Učitava upscaler model"""
        if upscaler_name in self.available_upscalers:
            upscaler_info = self.available_upscalers[upscaler_name]
            try:
                if self.current_upscaler == upscaler_name and self.upscaler_loaded:
                    print(f"Upscaler {upscaler_name} already loaded")
                    return True

                # Unload previous upscaler
                if self.upscaler_loaded:
                    self.unload_upscaler()

                print(f"Loading upscaler: {upscaler_name}")
                print(f"Model ID: {upscaler_info['model_id']}")

                if "realesrgan" in upscaler_info["model_id"]:
                    # Koristi Real-ESRGAN
                    if not CV2_AVAILABLE:
                        print(
                            "Error: cv2 not available. Cannot load Real-ESRGAN upscaler."
                        )
                        print("Please install opencv-python: pip install opencv-python")
                        return False

                    try:
                        from realesrgan import RealESRGANer
                        from basicsr.archs.rrdbnet_arch import RRDBNet

                        model = RRDBNet(
                            num_in_ch=3,
                            num_out_ch=3,
                            num_feat=64,
                            num_block=23,
                            num_grow_ch=32,
                            scale=4,
                        )
                        self.upscaler_pipeline = RealESRGANer(
                            scale=4,
                            model_path=f"https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
                            model=model,
                            tile=0,
                            tile_pad=10,
                            pre_pad=0,
                            half=True if self.device == "cuda" else False,
                        )
                    except ImportError as e:
                        print(f"Error: Real-ESRGAN dependencies not available: {e}")
                        print("Please install: pip install realesrgan basicsr")
                        return False
                else:
                    # Koristi SD upscaler
                    from diffusers import StableDiffusionUpscalePipeline

                    self.upscaler_pipeline = (
                        StableDiffusionUpscalePipeline.from_pretrained(
                            upscaler_info["model_id"],
                            torch_dtype=(
                                torch.float16
                                if self.device == "cuda"
                                else torch.float32
                            ),
                        )
                    )
                    self.upscaler_pipeline = self.upscaler_pipeline.to(self.device)

                self.upscaler_loaded = True
                self.current_upscaler = upscaler_name
                print(f"Upscaler {upscaler_name} loaded successfully")
                return True

            except Exception as e:
                print(f"Error loading upscaler {upscaler_name}: {e}")
                return False
        return False

    def unload_upscaler(self):
        """Uklanja upscaler model"""
        try:
            if self.upscaler_loaded:
                del self.upscaler_pipeline
                self.upscaler_pipeline = None
                self.upscaler_loaded = False
                self.current_upscaler = None
                torch.cuda.empty_cache()
                print("Upscaler unloaded")
                return True
        except Exception as e:
            print(f"Error unloading upscaler: {e}")
            return False

    def upscale_image(self, image, prompt="", num_inference_steps=20):
        """Povećava rezoluciju slike"""
        if not self.upscaler_loaded:
            print("Upscaler not loaded")
            return None

        try:
            print(f"Upscaling image with {self.current_upscaler}")

            if "realesrgan" in self.current_upscaler.lower():
                # Real-ESRGAN upscaling
                if not CV2_AVAILABLE:
                    print("Error: cv2 not available. Cannot use Real-ESRGAN upscaling.")
                    print("Please install opencv-python: pip install opencv-python")
                    return None

                # Konvertuj PIL u OpenCV format
                img_array = np.array(image)
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

                # Upscale
                output, _ = self.upscaler_pipeline.enhance(img_array, outscale=4)

                # Konvertuj nazad u PIL
                output = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
                result = Image.fromarray(output)

            else:
                # SD upscaler
                result = self.upscaler_pipeline(
                    prompt=prompt, image=image, num_inference_steps=num_inference_steps
                ).images[0]

            print(f"Image upscaled successfully: {image.size} -> {result.size}")
            return result

        except Exception as e:
            print(f"Error upscaling image: {e}")
            return None

    def is_model_loaded(self):
        """Proverava da li je model učitan"""
        return self.model_loaded

    def unload_model(self):
        """Oslobađa memoriju modela"""
        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None
            self.model_loaded = False
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("Stable Diffusion XL model unloaded")


class OllamaAPI:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.session = requests.Session()

    def is_ollama_running(self):
        """Proverava da li je Ollama server pokrenut"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

    def get_models(self):
        """Dobija listu dostupnih modela"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except:
            return []

    def generate_response_stream(
        self, model, prompt, context=None, callback=None, images=None
    ):
        """Generiše odgovor od modela sa streaming"""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True,
            }

            # Dodaj context samo ako nije None i nije prazan
            if context is not None and context:
                payload["context"] = context

            # Dodaj slike ako postoje
            if images and len(images) > 0:
                payload["images"] = images
                print(f"Sending {len(images)} image(s) to model {model}")
                print(f"Image size: {len(images[0])} characters (base64)")
                print(f"Full payload size: {len(str(payload))} characters")

            response = self.session.post(
                f"{self.base_url}/api/generate", json=payload, stream=True, timeout=7200
            )

            if response.status_code == 200:
                full_response = ""
                new_context = None

                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode("utf-8"))
                            if "response" in data:
                                chunk = data["response"]
                                full_response += chunk
                                if callback:
                                    callback(chunk)
                            if "context" in data:
                                new_context = data["context"]
                            if data.get("done", False):
                                print(
                                    f"LLaVA response completed. Total length: {len(full_response)}"
                                )
                                break
                            if "error" in data:
                                print(f"LLaVA error: {data['error']}")
                        except json.JSONDecodeError:
                            continue

                if not full_response.strip():
                    print("WARNING: LLaVA returned empty response!")
                    return (
                        "LLaVA model returned empty response. The model might not be properly loaded or the image format is not supported.",
                        new_context,
                    )

                return full_response, new_context
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"Ollama API error: {error_msg}")
                return f"Greška pri generisanju odgovora: {error_msg}", ""
        except Exception as e:
            error_msg = f"Greška: {str(e)}"
            return error_msg, ""


class OllamaWorker(QThread):
    response_received = Signal(str, str)  # response, context
    response_chunk = Signal(str)  # streaming chunk
    error_occurred = Signal(str)

    def __init__(self, ollama_api, model, prompt, context=None, images=None):
        super().__init__()
        self.ollama_api = ollama_api
        self.model = model
        self.prompt = prompt
        self.context = context
        self.images = images

    def run(self):
        try:

            def chunk_callback(chunk):
                self.response_chunk.emit(chunk)

            response, new_context = self.ollama_api.generate_response_stream(
                self.model,
                self.prompt,
                self.context,
                chunk_callback,
                self.images,
            )
            self.response_received.emit(response, new_context)
        except Exception as e:
            self.error_occurred.emit(str(e))


class ChatBubble(QFrame):
    def __init__(self, message="", is_user=True, is_streaming=False, image_path=None):
        super().__init__()
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.is_streaming = is_streaming
        self.current_text = message
        self.image_path = image_path

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Dodaj sliku ako postoji
        if image_path and os.path.exists(image_path):
            self.image_label = QLabel()
            self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.image_label.setMaximumHeight(300)  # Ograniči visinu slike
            self.image_label.setMaximumWidth(400)  # Ograniči širinu slike
            self.image_label.setScaledContents(False)  # Ne razvlači sliku

            # Učitaj i prikaži sliku
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # Skaliraj sliku da se uklopi u maksimalne dimenzije zadržavajući aspect ratio
                if pixmap.height() > 300 or pixmap.width() > 400:
                    # Izračunaj novu veličinu zadržavajući aspect ratio
                    aspect_ratio = pixmap.width() / pixmap.height()
                    if pixmap.height() > 300:
                        new_height = 300
                        new_width = int(new_height * aspect_ratio)
                        if new_width > 400:
                            new_width = 400
                            new_height = int(new_width / aspect_ratio)
                    else:
                        new_width = 400
                        new_height = int(new_width / aspect_ratio)

                    pixmap = pixmap.scaled(
                        new_width,
                        new_height,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                self.image_label.setPixmap(pixmap)
                layout.addWidget(self.image_label)
            else:
                self.image_label = None

        self.label = QLabel(message)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label.setMargin(12)

        if is_user:
            self.setStyleSheet(
                """
                QFrame {
                    background: #1a1a1a;
                    border: 2px solid #00FF00;
                    border-radius: 0px;
                    margin: 8px 0px 8px 60px;
                }
                QLabel {
                    color: #00FF00;
                    font-size: 14px;
                    font-weight: 500;
                    font-family: 'Courier New', monospace;
                    line-height: 1.4;
                }
            """
            )
            self.label.setAlignment(Qt.AlignmentFlag.AlignRight)
        else:
            self.setStyleSheet(
                """
                QFrame {
                    background: #1a1a1a;
                    border: 2px solid #00FF00;
                    border-radius: 0px;
                    margin: 8px 60px 8px 0px;
                }
                QLabel {
                    color: #00FF00;
                    font-size: 14px;
                    font-weight: 400;
                    font-family: 'Courier New', monospace;
                    line-height: 1.4;
                }
            """
            )
            self.label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(self.label)
        self.setLayout(layout)

    def add_text(self, text):
        """Dodaje tekst u bubble tokom streaming-a"""
        self.current_text += text
        self.label.setText(self.current_text)

        # Scroll na dno
        parent_scroll = self.parent()
        while parent_scroll and not isinstance(parent_scroll, QScrollArea):
            parent_scroll = parent_scroll.parent()
        if parent_scroll:
            scrollbar = parent_scroll.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def finish_streaming(self):
        """Završava streaming"""
        self.is_streaming = False


class ImageGenerationWorker(QThread):
    image_generated = Signal(str, str)  # filepath, success_msg
    generation_error = Signal(str)  # error_msg
    progress_updated = Signal(int)  # progress percentage

    def __init__(
        self, image_generator, prompt, image_settings, conversation_history=None
    ):
        super().__init__()
        self.image_generator = image_generator
        self.prompt = prompt
        self.image_settings = image_settings
        self.conversation_history = conversation_history

    def run(self):
        try:
            start_time = time.time()

            # Progress callback funkcija
            def worker_progress_callback(step, timestep, latents):
                progress = int((step / self.image_settings["steps"]) * 100)
                self.progress_updated.emit(progress)

                # Monitor GPU memory every 10 steps
                if step % 10 == 0 and torch.cuda.is_available():
                    allocated = torch.cuda.memory_allocated() / 1024**3
                    print(f"GPU memory allocated: {allocated:.2f} GB")

                print(
                    f"Generation progress: {progress}% (step {step}/{self.image_settings['steps']})"
                )

            # Generiši sliku sa sačuvanim postavkama
            result = self.image_generator.generate_image(
                prompt=self.prompt,
                negative_prompt=self.image_settings["negative_prompt"],
                width=self.image_settings["width"],
                height=self.image_settings["height"],
                steps=self.image_settings["steps"],
                guidance_scale=self.image_settings["guidance_scale"],
                seed=self.image_settings["seed"],
                progress_callback=worker_progress_callback,
                conversation_history=self.conversation_history,
            )

            if result[0] is not None:  # result je (image, error) tuple
                # Sačuvaj sliku
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"generated_image_{timestamp}.png"
                filepath = os.path.join(os.getcwd(), filename)
                result[0].save(filepath)

                # Dodaj sliku u LLM kontekst
                self.image_generator.add_image_to_llm_context(
                    filepath,
                    self.prompt,
                    self.image_settings,
                    self.conversation_history,
                )

                # Kratka poruka o uspehu
                success_msg = f"✅ Image generated in {time.time() - start_time:.1f}s"
                self.image_generated.emit(filepath, success_msg)
            else:
                self.generation_error.emit(f"Greška pri generisanju slike: {result[1]}")

        except Exception as e:
            self.generation_error.emit(f"Greška u worker thread-u: {str(e)}")


class AIAssistantApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ollama_api = OllamaAPI()
        self.current_context = None
        self.ollama_process = None

        # Napredno pamćenje
        self.conversation_history = []  # Lista svih poruka u razgovoru
        self.max_history = 20  # Maksimalno 20 poruka u istoriji
        self.system_prompt = "You are a helpful AI assistant."

        # Kontrola generisanja
        self.is_generating = False
        self.current_worker = None

        # News reader
        self.news_reader = NewsReader()

        # Edge TTS
        self.tts = EdgeTTS()
        self.tts.app = self  # Dodaj referencu na app za UI ažuriranje

        # Image processor
        self.image_processor = ImageProcessor()

        # Image generator
        self.image_generator = ImageGenerator()

        # Image upscaler
        self.image_upscaler = ImageUpscaler()

        # Upload fajlovi
        self.uploaded_files = []  # Lista učitanih fajlova
        self.uploaded_images = []  # Lista učitanih slika
        self.max_file_content_length = -1  # Neograničena dužina fajla za AI

        # Postavke za generisanje slika
        self.image_settings = {
            "prompt": "a single beautiful cat, high quality, detailed, photorealistic, one cat only",
            "negative_prompt": "blurry, low quality, distorted, ugly, bad anatomy, duplicate, multiple, two, double, repeated, extra",
            "width": 1024,
            "height": 1024,
            "steps": 50,  # Povećano sa 30 na 50 za bolje rezultate
            "guidance_scale": 7.5,  # Smanjeno sa 8.0 na 7.5 za bolje rezultate
            "seed": None,  # Dodaj seed parametar
            "selected_model": "SDXL Base (1024x1024)",
        }

        self.init_ui()
        self.check_ollama_status()

        # Timer za proveru statusa Ollama
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_ollama_status)
        self.status_timer.start(5000)  # Proverava svakih 5 sekundi

    def get_button_style(self, normal_color, hover_color, disabled=False):
        """Kreira retro terminal stil za dugmad"""
        if disabled:
            return f"""
                QPushButton {{
                    background: #1a1a1a;
                    color: #666666;
                    border: 1px solid #00FF00;
                    padding: 8px 16px;
                    border-radius: 0px;
                    font-weight: bold;
                    font-size: 10px;
                    font-family: 'Courier New', monospace;
                    min-width: 30px;
                }}
                QPushButton:hover {{
                    background: #2d2d2d;
                }}
                QPushButton:disabled {{
                    background: #1a1a1a;
                    color: #444444;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background: #1a1a1a;
                    color: #00FF00;
                    border: 1px solid #00FF00;
                    padding: 8px 16px;
                    border-radius: 0px;
                    font-weight: bold;
                    font-size: 10px;
                    font-family: 'Courier New', monospace;
                    min-width: 30px;
                }}
                QPushButton:hover {{
                    background: #2d2d2d;
                    border: 2px solid #00FF00;
                }}
                QPushButton:pressed {{
                    background: #0a0a0a;
                    transform: translateY(1px);
                }}
            """

    def create_custom_title_bar(self):
        """Kreira custom title bar sa crnom pozadinom"""
        # Title bar widget
        title_bar = QFrame()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet(
            """
            QFrame {
                background: #000000;
                border: none;
                border-bottom: 2px solid #00FF00;
            }
        """
        )

        # Omogući drag funkcionalnost
        title_bar.mousePressEvent = self.title_bar_mouse_press
        title_bar.mouseMoveEvent = self.title_bar_mouse_move

        # Title bar layout
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(10, 5, 10, 5)

        # Title label
        title_label = QLabel("RETRO AI ASSISTANT v2.0")
        title_label.setStyleSheet(
            """
            QLabel {
                background: transparent;
                color: #00FF00;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                font-weight: bold;
            }
        """
        )

        # Spacer
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(25, 25)
        close_btn.setStyleSheet(
            """
            QPushButton {
                background: #1a1a1a;
                color: #00FF00;
                border: 1px solid #00FF00;
                border-radius: 0px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #ff0000;
                color: #ffffff;
            }
        """
        )
        close_btn.clicked.connect(self.close)

        # Minimize button
        min_btn = QPushButton("−")
        min_btn.setFixedSize(25, 25)
        min_btn.setStyleSheet(
            """
            QPushButton {
                background: #1a1a1a;
                color: #00FF00;
                border: 1px solid #00FF00;
                border-radius: 0px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2d2d2d;
            }
        """
        )
        min_btn.clicked.connect(self.showMinimized)

        # Add to layout
        title_layout.addWidget(title_label)
        title_layout.addItem(spacer)
        title_layout.addWidget(min_btn)
        title_layout.addWidget(close_btn)

        title_bar.setLayout(title_layout)

        # Add to main layout
        main_layout = self.centralWidget().layout()
        main_layout.insertWidget(0, title_bar)

    def title_bar_mouse_press(self, event):
        """Handle mouse press on title bar for dragging"""
        if event.button() == Qt.LeftButton:
            self.drag_position = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def title_bar_mouse_move(self, event):
        """Handle mouse move on title bar for dragging"""
        if event.buttons() == Qt.LeftButton and hasattr(self, "drag_position"):
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def init_ui(self):
        self.setWindowTitle("RETRO AI ASSISTANT v2.0")
        self.setGeometry(100, 100, 1200, 800)

        # Ukloni Windows title bar i napravi custom
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)

        # Postavi crni title bar
        self.setStyleSheet(
            """
            QMainWindow {
                background: #000000;
                color: #00FF00;
                font-family: 'Courier New', monospace;
                border: 2px solid #00FF00;
            }
        """
        )

        # Glavni widget
        central_widget = QWidget()
        central_widget.setStyleSheet(
            "background: #1a1a1a; color: #00FF00; font-family: 'Courier New', monospace;"
        )
        self.setCentralWidget(central_widget)

        # Glavni layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Custom title bar
        self.create_custom_title_bar()

        # Dark header sekcija sa grupiranim kontrolama
        header_container = QFrame()
        header_container.setStyleSheet(
            """
            QFrame {
                background: #1a1a1a;
                border: 2px solid #00FF00;
                border-radius: 0px;
                margin: 5px;
                padding: 15px;
            }
        """
        )
        header_layout = QVBoxLayout(header_container)
        header_layout.setSpacing(10)

        # Gornji red - Model i Status
        top_row = QHBoxLayout()
        top_row.setSpacing(15)

        # Model selection sa dark stilom
        model_group = QFrame()
        model_group.setStyleSheet(
            """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2d2d2d, stop:1 #404040);
                border: 1px solid #606060;
                border-radius: 8px;
                padding: 10px;
                box-shadow: 0 0 5px #000000;
            }
        """
        )
        model_layout = QHBoxLayout(model_group)
        model_layout.setContentsMargins(8, 4, 8, 4)

        model_label = QLabel("■ NEURAL MODEL:")
        model_label.setStyleSheet(
            "color: #00FF00; font-weight: bold; font-size: 12px; font-family: 'Courier New', monospace; background: #1a1a1a;"
        )
        model_layout.addWidget(model_label)

        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(180)
        self.model_combo.setMaximumWidth(200)
        available_models = self.ollama_api.get_models()
        if available_models:
            self.model_combo.addItems(available_models)
        else:
            self.model_combo.addItems(["mixtral:latest"])
        self.model_combo.setStyleSheet(
            """
            QComboBox {
                background: #1a1a1a;
                color: #00FF00;
                border: 2px solid #00FF00;
                padding: 8px 12px;
                border-radius: 0px;
                font-weight: bold;
                font-size: 11px;
                font-family: 'Courier New', monospace;
            }
            QComboBox:hover {
                border-color: #00FF00;
                background: #2d2d2d;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #00FF00;
            }
            QComboBox QAbstractItemView {
                background: #1a1a1a;
                color: #00FF00;
                border: 1px solid #00FF00;
                selection-background-color: #2d2d2d;
                font-family: 'Courier New', monospace;
            }
        """
        )
        model_layout.addWidget(self.model_combo)
        top_row.addWidget(model_group)

        # Status sa dark indikatorom
        status_group = QFrame()
        status_group.setStyleSheet(
            """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2d2d2d, stop:1 #404040);
                border: 1px solid #606060;
                border-radius: 8px;
                padding: 10px;
                box-shadow: 0 0 5px #000000;
            }
        """
        )
        status_layout = QHBoxLayout(status_group)
        status_layout.setContentsMargins(8, 4, 8, 4)

        self.status_label = QLabel("● SYSTEM OFFLINE")
        self.status_label.setStyleSheet(
            "color: #FF0000; font-weight: bold; font-size: 12px; font-family: 'Courier New', monospace; background: #1a1a1a;"
        )
        status_layout.addWidget(self.status_label)
        top_row.addWidget(status_group)

        # WIPE i EXPORT dugmići u gornjem redu
        wipe_export_group = QFrame()
        wipe_export_group.setStyleSheet(
            """
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2d2d2d, stop:1 #404040);
                border: 1px solid #606060;
                border-radius: 8px;
                padding: 8px;
                box-shadow: 0 0 5px #000000;
            }
        """
        )
        wipe_export_layout = QHBoxLayout(wipe_export_group)
        wipe_export_layout.setContentsMargins(6, 4, 6, 4)
        wipe_export_layout.setSpacing(8)

        self.clear_history_btn = QPushButton("■ WIPE")
        self.clear_history_btn.clicked.connect(self.clear_conversation_history)
        self.clear_history_btn.setStyleSheet(
            self.get_button_style("#1a1a1a", "#2d2d2d")
        )
        wipe_export_layout.addWidget(self.clear_history_btn)

        self.export_btn = QPushButton("■ EXPORT")
        self.export_btn.clicked.connect(self.export_conversation)
        self.export_btn.setStyleSheet(self.get_button_style("#1a1a1a", "#2d2d2d"))
        wipe_export_layout.addWidget(self.export_btn)

        self.debug_context_btn = QPushButton("■ DEBUG")
        self.debug_context_btn.clicked.connect(self.debug_context)
        self.debug_context_btn.setStyleSheet(
            self.get_button_style("#1a1a1a", "#2d2d2d")
        )
        wipe_export_layout.addWidget(self.debug_context_btn)

        self.unload_models_btn = QPushButton("■ UNLOAD MODELS")
        self.unload_models_btn.clicked.connect(self.unload_ollama_models)
        self.unload_models_btn.setStyleSheet(
            self.get_button_style("#1a1a1a", "#2d2d2d")
        )
        wipe_export_layout.addWidget(self.unload_models_btn)

        # Dodaj logo na desnu stranu
        wipe_export_layout.addStretch()  # Push dugmiće levo, logo desno

        # Logo ikonica
        logo_label = QLabel()
        logo_pixmap = QPixmap("logo.png")
        if not logo_pixmap.isNull():
            # Skali logo na 32x32 piksela
            logo_pixmap = logo_pixmap.scaled(
                32,
                32,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_label.setPixmap(logo_pixmap)
            logo_label.setToolTip("Click for image prompt suggestion")
        else:
            # Fallback ako logo ne postoji
            logo_label.setText("AI")
            logo_label.setStyleSheet(
                "color: #00FF00; font-weight: bold; font-size: 16px;"
            )
            logo_label.setToolTip("Click for image prompt suggestion")

        # Dodaj click handler za logo
        logo_label.mousePressEvent = lambda event: self.logo_clicked()
        logo_label.setCursor(Qt.CursorShape.PointingHandCursor)

        wipe_export_layout.addWidget(logo_label)

        top_row.addWidget(wipe_export_group)

        top_row.addStretch()
        header_layout.addLayout(top_row)

        # Glavni toolbar sa dugmićima - svi u jednom redu
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(8)

        # Grupa 1: Osnovne kontrole
        basic_group = QFrame()
        basic_group.setStyleSheet(
            """
            QFrame {
                background: #1a1a1a;
                border: 1px solid #00FF00;
                border-radius: 0px;
                padding: 8px;
            }
        """
        )
        basic_layout = QHBoxLayout(basic_group)
        basic_layout.setContentsMargins(6, 4, 6, 4)
        basic_layout.setSpacing(6)

        self.start_ollama_btn = QPushButton("■ INIT SYSTEM")
        self.start_ollama_btn.clicked.connect(self.start_ollama)
        self.start_ollama_btn.setStyleSheet(self.get_button_style("#1a1a1a", "#2d2d2d"))
        basic_layout.addWidget(self.start_ollama_btn)

        self.stop_btn = QPushButton("■ KILL PROCESS")
        self.stop_btn.clicked.connect(self.stop_generation)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(
            self.get_button_style("#1a1a1a", "#2d2d2d", disabled=True)
        )
        basic_layout.addWidget(self.stop_btn)

        toolbar_layout.addWidget(basic_group)

        # Grupa 2: TTS kontrole
        tts_group = QFrame()
        tts_group.setStyleSheet(
            """
            QFrame {
                background: #1a1a1a;
                border: 1px solid #00FF00;
                border-radius: 0px;
                padding: 8px;
            }
        """
        )
        tts_layout = QHBoxLayout(tts_group)
        tts_layout.setContentsMargins(6, 4, 6, 4)
        tts_layout.setSpacing(6)

        self.tts_language_combo = QComboBox()
        self.tts_language_combo.addItems(
            [
                "engleski",
                "jenny",
                "davis",
                "emma",
                "brian",
                "srpski",
                "britanski",
                "australijski",
            ]
        )
        self.tts_language_combo.setCurrentText("engleski")
        self.tts_language_combo.currentTextChanged.connect(self.switch_tts_language)
        self.tts_language_combo.setStyleSheet(
            """
            QComboBox {
                background: #1a1a1a;
                color: #00FF00;
                border: 1px solid #00FF00;
                padding: 6px 10px;
                border-radius: 0px;
                font-weight: bold;
                font-size: 10px;
                font-family: 'Courier New', monospace;
                min-width: 80px;
            }
            QComboBox:hover {
                border-color: #00FF00;
                background: #2d2d2d;
            }
            QComboBox::drop-down {
                border: none;
                width: 15px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 3px solid #00FF00;
            }
            QComboBox QAbstractItemView {
                background: #1a1a1a;
                color: #00FF00;
                border: 1px solid #00FF00;
                selection-background-color: #2d2d2d;
                font-family: 'Courier New', monospace;
            }
        """
        )
        tts_layout.addWidget(self.tts_language_combo)

        self.tts_btn = QPushButton("SPEAK")
        self.tts_btn.clicked.connect(self.speak_last_message)
        self.tts_btn.setStyleSheet(self.get_button_style("#1a1a1a", "#2d2d2d"))
        tts_layout.addWidget(self.tts_btn)

        self.tts_pause_btn = QPushButton("PAUSE")
        self.tts_pause_btn.clicked.connect(self.pause_tts)
        self.tts_pause_btn.setEnabled(False)
        self.tts_pause_btn.setStyleSheet(
            self.get_button_style("#1a1a1a", "#2d2d2d", disabled=True)
        )
        tts_layout.addWidget(self.tts_pause_btn)

        self.tts_stop_btn = QPushButton("STOP")
        self.tts_stop_btn.clicked.connect(self.stop_tts)
        self.tts_stop_btn.setEnabled(False)
        self.tts_stop_btn.setStyleSheet(
            self.get_button_style("#1a1a1a", "#2d2d2d", disabled=True)
        )
        tts_layout.addWidget(self.tts_stop_btn)

        toolbar_layout.addWidget(tts_group)

        # Grupa 3: Fajl operacije
        file_group = QFrame()
        file_group.setStyleSheet(
            """
            QFrame {
                background: #1a1a1a;
                border: 1px solid #00FF00;
                border-radius: 0px;
                padding: 8px;
            }
        """
        )
        file_layout = QHBoxLayout(file_group)
        file_layout.setContentsMargins(6, 4, 6, 4)
        file_layout.setSpacing(6)

        self.upload_btn = QPushButton("■ UPLOAD")
        self.upload_btn.clicked.connect(self.upload_file)
        self.upload_btn.setStyleSheet(self.get_button_style("#1a1a1a", "#2d2d2d"))
        file_layout.addWidget(self.upload_btn)

        self.upload_image_btn = QPushButton("■ IMAGE")
        self.upload_image_btn.clicked.connect(self.upload_image)
        self.upload_image_btn.setStyleSheet(self.get_button_style("#1a1a1a", "#2d2d2d"))
        file_layout.addWidget(self.upload_image_btn)

        self.generate_image_btn = QPushButton("■ IMAGE OPTIONS")
        self.generate_image_btn.clicked.connect(self.show_image_options)
        self.generate_image_btn.setStyleSheet(
            self.get_button_style("#1a1a1a", "#2d2d2d")
        )
        file_layout.addWidget(self.generate_image_btn)

        self.img2img_btn = QPushButton("■ IMG2IMG")
        self.img2img_btn.clicked.connect(self.show_img2img_options)
        self.img2img_btn.setStyleSheet(self.get_button_style("#1a1a1a", "#2d2d2d"))
        file_layout.addWidget(self.img2img_btn)

        self.advanced_image_btn = QPushButton("■ ADVANCED")
        self.advanced_image_btn.clicked.connect(self.show_advanced_image_settings)
        self.advanced_image_btn.setStyleSheet(
            self.get_button_style("#1a1a1a", "#2d2d2d")
        )
        file_layout.addWidget(self.advanced_image_btn)

        self.upscale_btn = QPushButton("■ UPSCALE")
        self.upscale_btn.clicked.connect(self.upscale_last_image)
        self.upscale_btn.setStyleSheet(self.get_button_style("#1a1a1a", "#2d2d2d"))
        file_layout.addWidget(self.upscale_btn)

        self.clear_uploads_btn = QPushButton("CLEAR")
        self.clear_uploads_btn.clicked.connect(self.clear_uploaded_files)
        self.clear_uploads_btn.setStyleSheet(
            self.get_button_style("#1a1a1a", "#2d2d2d")
        )
        file_layout.addWidget(self.clear_uploads_btn)

        self.file_limit_btn = QPushButton("LIMIT")
        self.file_limit_btn.clicked.connect(self.change_file_limit)
        self.file_limit_btn.setStyleSheet(self.get_button_style("#1a1a1a", "#2d2d2d"))
        file_layout.addWidget(self.file_limit_btn)

        toolbar_layout.addWidget(file_group)

        toolbar_layout.addStretch()
        header_layout.addLayout(toolbar_layout)

        main_layout.addWidget(header_container)

        # Upload sekcija uklonjena - informacije su sada u header-u

        # Chat area sa dark stilom
        chat_container = QFrame()
        chat_container.setStyleSheet(
            """
            QFrame {
                background: #1a1a1a;
                border: 2px solid #00FF00;
                border-radius: 0px;
                margin: 5px;
            }
        """
        )
        chat_layout_container = QVBoxLayout(chat_container)
        chat_layout_container.setContentsMargins(0, 0, 0, 0)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.chat_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.chat_scroll.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a1a1a, stop:1 #2d2d2d);
                width: 12px;
                border-radius: 6px;
                border: 1px solid #606060;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #404040, stop:1 #606060);
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2196F3, stop:1 #1976D2);
            }
        """
        )

        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout()
        self.chat_layout.setContentsMargins(15, 15, 15, 15)
        self.chat_layout.setSpacing(10)
        self.chat_widget.setLayout(self.chat_layout)
        self.chat_scroll.setWidget(self.chat_widget)

        chat_layout_container.addWidget(self.chat_scroll)
        main_layout.addWidget(chat_container)

        # Input area sa dark stilom
        input_container = QFrame()
        input_container.setStyleSheet(
            """
            QFrame {
                background: #1a1a1a;
                border: 2px solid #00FF00;
                border-radius: 0px;
                margin: 5px;
                padding: 12px;
            }
        """
        )
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(12)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("■ ENTER NEURAL QUERY...")
        self.message_input.returnPressed.connect(self.send_message)
        self.message_input.setStyleSheet(
            """
            QLineEdit {
                padding: 12px 16px;
                border: 2px solid #00FF00;
                border-radius: 0px;
                font-size: 14px;
                font-family: 'Courier New', monospace;
                background: #1a1a1a;
                color: #00FF00;
            }
            QLineEdit:focus {
                border-color: #00FF00;
                border-width: 3px;
                background: #2d2d2d;
            }
            QLineEdit:hover {
                border-color: #00FF00;
                background: #2d2d2d;
            }
        """
        )
        input_layout.addWidget(self.message_input)

        self.send_btn = QPushButton("■ EXECUTE")
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setStyleSheet(
            """
            QPushButton {
                background: #1a1a1a;
                color: #00FF00;
                border: 2px solid #00FF00;
                padding: 12px 24px;
                border-radius: 0px;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Courier New', monospace;
                min-width: 100px;
            }
            QPushButton:hover {
                background: #2d2d2d;
                border: 3px solid #00FF00;
            }
            QPushButton:pressed {
                background: #0a0a0a;
                color: #00FF00;
            }
            QPushButton:disabled {
                background: #1a1a1a;
                color: #666666;
                border-color: #404040;
            }
        """
        )
        input_layout.addWidget(self.send_btn)

        # Seed kontrolu pored Generate dugmeta
        self.seed_input = QLineEdit()
        self.seed_input.setPlaceholderText("Seed (empty=random)")
        self.seed_input.setMaximumWidth(100)
        self.seed_input.setStyleSheet(
            """
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #FF6600;
                border-radius: 0px;
                font-size: 12px;
                font-family: 'Courier New', monospace;
                background: #1a1a1a;
                color: #FF6600;
            }
            QLineEdit:focus {
                border-color: #FF6600;
                border-width: 3px;
                background: #2d2d2d;
            }
            QLineEdit:hover {
                border-color: #FF6600;
                background: #2d2d2d;
            }
        """
        )
        input_layout.addWidget(self.seed_input)

        # Generate dugme pored Execute dugmeta
        self.generate_btn = QPushButton("■ GENERATE")
        self.generate_btn.clicked.connect(self.generate_image_from_prompt)
        self.generate_btn.setStyleSheet(
            """
            QPushButton {
                background: #1a1a1a;
                color: #FF6600;
                border: 2px solid #FF6600;
                padding: 12px 24px;
                border-radius: 0px;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Courier New', monospace;
                min-width: 100px;
            }
            QPushButton:hover {
                background: #2d2d2d;
                border: 3px solid #FF6600;
            }
            QPushButton:pressed {
                background: #0a0a0a;
                color: #FF6600;
            }
            QPushButton:disabled {
                background: #1a1a1a;
                color: #666666;
                border-color: #404040;
            }
        """
        )
        input_layout.addWidget(self.generate_btn)

        main_layout.addWidget(input_container)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("■ RETRO AI ASSISTANT READY ■")

        # Progress bar za generisanje slika
        self.image_progress_bar = QProgressBar()
        self.image_progress_bar.setVisible(False)
        self.image_progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid #00FF00;
                border-radius: 0px;
                background: #1a1a1a;
                text-align: center;
                color: #00FF00;
                font-family: 'Courier New', monospace;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background: #00FF00;
                border: none;
            }
        """
        )
        self.status_bar.addPermanentWidget(self.image_progress_bar)

        # Dodaj pozdravnu poruku
        # Uklonjen welcome bubble

    def check_ollama_status(self):
        """Checks Ollama server status"""
        if self.ollama_api.is_ollama_running():
            self.status_label.setText("● SYSTEM ONLINE")
            self.status_label.setStyleSheet(
                "color: #00FF00; font-weight: bold; font-family: 'Courier New', monospace;"
            )
            self.start_ollama_btn.setEnabled(False)
            self.send_btn.setEnabled(True)
            self.status_bar.showMessage("■ NEURAL NETWORK ACTIVE ■")
        else:
            self.status_label.setText("● SYSTEM OFFLINE")
            self.status_label.setStyleSheet(
                "color: #FF0000; font-weight: bold; font-family: 'Courier New', monospace;"
            )
            self.start_ollama_btn.setEnabled(True)
            self.send_btn.setEnabled(False)
            self.status_bar.showMessage("■ NEURAL NETWORK OFFLINE ■")

            # Automatically try to start Ollama if not running
            if not hasattr(self, "auto_start_attempted"):
                self.auto_start_attempted = True
                self.status_bar.showMessage("Starting Ollama automatically...")
                self.start_ollama()

    def start_ollama(self):
        """Starts Ollama server"""
        try:
            self.status_bar.showMessage("Starting Ollama server...")
            self.ollama_process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=(
                    subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
                ),
            )

            # Wait for server to start
            time.sleep(3)
            self.check_ollama_status()

            if self.ollama_api.is_ollama_running():
                QMessageBox.information(
                    self, "Success", "Ollama server started successfully!"
                )
            else:
                QMessageBox.warning(self, "Error", "Unable to start Ollama server.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error starting Ollama: {str(e)}")

    def send_message(self):
        """Sends message to model"""
        message = self.message_input.text().strip()
        if not message:
            return

        # Stop previous generation if in progress
        if self.is_generating:
            self.stop_generation()

        # Add user message to history
        self.conversation_history.append({"role": "user", "content": message})

        # Maintain maximum history length
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history :]

        # Add user message to chat (bez slika - slike se prikazuju samo kada se upload-uju)
        user_bubble = ChatBubble(message, True)
        self.chat_layout.addWidget(user_bubble)

        # Clear input
        self.message_input.clear()

        # Mark generation as in progress
        self.is_generating = True

        # Disable button during generation
        self.send_btn.setEnabled(False)
        self.send_btn.setText("Generating...")
        self.stop_btn.setEnabled(True)
        self.status_bar.showMessage("Generating response...")

        # Create AI bubble for streaming
        self.current_ai_bubble = ChatBubble("", False, True)
        self.chat_layout.addWidget(self.current_ai_bubble)

        # Create contextual prompt with history
        contextual_prompt = self.build_contextual_prompt(message)

        # Debug: show how many files and images are loaded
        if self.uploaded_files or self.uploaded_images:
            files_count = len(self.uploaded_files)
            images_count = len(self.uploaded_images)
            status_msg = f"Generating response with {files_count} files"
            if images_count > 0:
                status_msg += f" and {images_count} image(s)"
            status_msg += "..."
            self.status_bar.showMessage(status_msg)

        # Pripremi slike za slanje
        images_for_model = []
        if self.uploaded_images:
            for img_info in self.uploaded_images:
                base64_image = self.image_processor.image_to_base64(img_info["path"])
                if base64_image:
                    images_for_model.append(base64_image)

        # Start worker thread for response generation
        model = self.model_combo.currentText()
        self.current_worker = OllamaWorker(
            self.ollama_api,
            model,
            contextual_prompt,
            self.current_context,
            images_for_model,
        )
        self.current_worker.response_chunk.connect(self.handle_chunk)
        self.current_worker.response_received.connect(self.handle_response)
        self.current_worker.error_occurred.connect(self.handle_error)
        self.current_worker.start()

    def get_news_data(self, message):
        """Analizira poruku i vraća relevantne vesti"""
        message_lower = message.lower()

        # Proveri da li traži vesti
        if any(
            word in message_lower
            for word in [
                "vesti",
                "novosti",
                "šta se dešava",
                "najnovije",
                "danas",
                "sutra",
            ]
        ):
            return self.news_reader.get_latest_news(hours=24, max_news=5)

        # Proveri da li traži specifične vesti
        elif any(
            word in message_lower
            for word in ["politika", "sport", "tehnologija", "ekonomija", "kultura"]
        ):
            keyword = next(
                word
                for word in ["politika", "sport", "tehnologija", "ekonomija", "kultura"]
                if word in message_lower
            )
            return self.news_reader.search_news(keyword)

        return None

    def build_contextual_prompt(self, current_message):
        """Creates contextual prompt with conversation history, news and uploaded files"""
        prompt_parts = [self.system_prompt]

        # Add news if needed
        news_data = self.get_news_data(current_message)
        if news_data:
            news_text = "Latest news:\n"
            for item in news_data:
                news_text += f"- {item['title']} ({item['source']})\n"
                if item["summary"] and item["summary"] != "Nema opisa":
                    news_text += f"  {item['summary'][:100]}...\n"
            prompt_parts.append(news_text)

        # Add uploaded files
        upload_context = self.get_uploaded_files_context()
        if upload_context:
            prompt_parts.append(upload_context)

        # Add entire conversation history
        recent_history = self.conversation_history

        for msg in recent_history:
            if msg["role"] == "user":
                prompt_parts.append(f"User: {msg['content']}")
            else:
                prompt_parts.append(f"Assistant: {msg['content']}")

        # Add current message (it's already in conversation_history, so we don't need to add it again)
        prompt_parts.append("Assistant:")

        return "\n\n".join(prompt_parts)

    def speak_last_message(self):
        """Reads last AI message"""
        if self.conversation_history:
            last_message = self.conversation_history[-1]
            if last_message["role"] == "assistant":
                self.tts.speak(last_message["content"])
                tts_name = "Edge TTS"
                self.status_bar.showMessage(f"Reading last message ({tts_name})...")
                # Enable control buttons
                self.tts_pause_btn.setEnabled(True)
                self.tts_stop_btn.setEnabled(True)
            else:
                self.status_bar.showMessage("No AI message to read!")
        else:
            self.status_bar.showMessage("No messages to read!")

    def switch_tts_language(self, language):
        """Switches TTS language"""
        if hasattr(self, "tts") and self.tts.switch_language(language):
            self.status_bar.showMessage(f"TTS switched to {language}")
        else:
            self.status_bar.showMessage(f"Error switching to {language}")

    def pause_tts(self):
        """Pauses TTS"""
        if hasattr(self, "tts") and self.tts.is_speaking:
            if self.tts.is_paused:
                self.tts.resume()
                self.tts_pause_btn.setText("⏸️ Pause")
                self.status_bar.showMessage("TTS resumed")
            else:
                self.tts.pause()
                self.tts_pause_btn.setText("▶️ Resume")
                self.status_bar.showMessage("TTS paused")

    def stop_tts(self):
        """Stops TTS"""
        if hasattr(self, "tts"):
            self.tts.stop()
            self.tts_pause_btn.setEnabled(False)
            self.tts_stop_btn.setEnabled(False)
            self.tts_pause_btn.setText("⏸️ Pause")
            self.status_bar.showMessage("TTS stopped")

    def stop_generation(self):
        """Stops current generation"""
        if self.is_generating and self.current_worker:
            # Stop worker thread
            self.current_worker.terminate()
            self.current_worker.wait()

            # Remove streaming bubble if exists
            if hasattr(self, "current_ai_bubble") and self.current_ai_bubble:
                self.current_ai_bubble.setParent(None)
                self.current_ai_bubble = None

            # Reset state
            self.is_generating = False
            self.current_worker = None

            # Enable sending again
            self.send_btn.setEnabled(True)
            self.send_btn.setText("Send")
            self.stop_btn.setEnabled(False)
            self.status_bar.showMessage("Generation stopped")

    def clear_conversation_history(self):
        """Clears conversation history"""
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Are you sure you want to delete the entire conversation history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Delete all chat bubbles except welcome message
            for i in reversed(range(self.chat_layout.count())):
                widget = self.chat_layout.itemAt(i).widget()
                if isinstance(widget, ChatBubble):
                    widget.setParent(None)

            # Reset history
            self.conversation_history = []
            self.current_context = None

            # Removed welcome bubble

            self.status_bar.showMessage("Conversation history cleared")

    def export_conversation(self):
        """Exports conversation to text file"""
        from datetime import datetime
        import os

        if not self.conversation_history:
            QMessageBox.information(self, "Info", "No conversation to export!")
            return

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"conversation_{timestamp}.txt"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("=== AI ASSISTANT - CONVERSATION EXPORT ===\n")
                f.write(f"Date: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")

                for msg in self.conversation_history:
                    role = "USER" if msg["role"] == "user" else "ASSISTANT"
                    f.write(f"[{role}]: {msg['content']}\n\n")

            QMessageBox.information(
                self, "Success", f"Conversation exported to file: {filename}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export error: {str(e)}")

    def logo_clicked(self):
        """Handles logo click - sets image prompt suggestion"""
        prompt_text = "give me a prompt for image generator for crazy good pic of ur choice, in one sentence"
        self.message_input.setText(prompt_text)
        self.message_input.setFocus()  # Focus na input polje
        self.status_bar.showMessage("Image prompt suggestion loaded!")

    def handle_chunk(self, chunk):
        """Handles streaming chunk"""
        if hasattr(self, "current_ai_bubble") and self.current_ai_bubble:
            self.current_ai_bubble.add_text(chunk)

    def handle_response(self, response, context):
        """Handles final response from model"""
        # Finish streaming
        if hasattr(self, "current_ai_bubble") and self.current_ai_bubble:
            self.current_ai_bubble.finish_streaming()
            self.current_ai_bubble = None

        # Add AI response to history
        self.conversation_history.append({"role": "assistant", "content": response})

        # Maintain maximum history length
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history :]

        # Update context
        self.current_context = context

        # Reset generation state
        self.is_generating = False
        self.current_worker = None

        # Enable sending again
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send")
        self.stop_btn.setEnabled(False)
        self.status_bar.showMessage(
            f"Response generated (History: {len(self.conversation_history)} messages)"
        )

    def handle_error(self, error):
        """Handles errors"""
        # Remove streaming bubble if exists
        if hasattr(self, "current_ai_bubble") and self.current_ai_bubble:
            self.current_ai_bubble.setParent(None)
            self.current_ai_bubble = None

        # Reset generation state
        self.is_generating = False
        self.current_worker = None

        error_bubble = ChatBubble(f"Error: {error}", False)
        self.chat_layout.addWidget(error_bubble)

        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send")
        self.stop_btn.setEnabled(False)
        self.status_bar.showMessage("Error generating response")

    def upload_file(self):
        """Upload file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select file to upload", "", "All files (*.*)"
        )

        if file_path:
            try:
                # Read file content
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Add file to list
                file_info = {
                    "path": file_path,
                    "name": os.path.basename(file_path),
                    "content": content,
                }
                self.uploaded_files.append(file_info)

                self.status_bar.showMessage(
                    f"File {file_info['name']} uploaded successfully!"
                )

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error reading file: {str(e)}")

    def upload_image(self):
        """Upload image file"""
        # Prvo proveri da li je Ollama pokrenut
        if not self.ollama_api.is_ollama_running():
            QMessageBox.warning(
                self,
                "Ollama Not Running",
                "Ollama server is not running. Please start Ollama first using 'INIT SYSTEM' button.",
            )
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select image to upload",
            "",
            "Image files (*.jpg *.jpeg *.png *.bmp *.gif *.tiff);;All files (*.*)",
        )

        if file_path:
            # Proveri da li je podržan format slike
            if not self.image_processor.is_supported_image(file_path):
                QMessageBox.warning(
                    self,
                    "Unsupported Format",
                    "Please select a supported image format (JPG, PNG, BMP, GIF, TIFF).",
                )
                return

            try:
                # Dobij informacije o slici
                img_info = self.image_processor.get_image_info(file_path)
                if not img_info:
                    QMessageBox.critical(
                        self, "Error", "Could not read image information."
                    )
                    return

                # Proveri veličinu fajla (maksimalno 50MB)
                if img_info["file_size_mb"] > 50:
                    QMessageBox.warning(
                        self,
                        "File Too Large",
                        f"Image file is too large ({img_info['file_size_mb']}MB). Maximum size is 50MB.",
                    )
                    return

                # Dodaj sliku u listu
                image_info = {
                    "path": file_path,
                    "name": os.path.basename(file_path),
                    "width": img_info["width"],
                    "height": img_info["height"],
                    "format": img_info["format"],
                    "file_size_mb": img_info["file_size_mb"],
                }
                self.uploaded_images.append(image_info)

                self.status_bar.showMessage(
                    f"Image {image_info['name']} uploaded successfully! "
                    f"({img_info['width']}x{img_info['height']}, {img_info['file_size_mb']}MB)"
                )

                # Prikaži sliku odmah u chat-u
                upload_msg = f"📁 Uploaded image: {image_info['name']} ({img_info['width']}x{img_info['height']}, {img_info['file_size_mb']}MB)"
                upload_bubble = ChatBubble(upload_msg, False, image_path=file_path)
                self.chat_layout.addWidget(upload_bubble)
                self.scroll_to_bottom()

                # Automatski postavi model na llava ako nije već postavljen
                current_model = self.model_combo.currentText()
                if "llava" not in current_model.lower():
                    # Proveri da li je llava model dostupan
                    available_models = self.ollama_api.get_models()
                    print(f"Available models: {available_models}")  # Debug
                    llava_models = [m for m in available_models if "llava" in m.lower()]
                    print(f"LLaVA models found: {llava_models}")  # Debug

                    if llava_models:
                        self.model_combo.setCurrentText(llava_models[0])
                        self.status_bar.showMessage(
                            f"Image uploaded! Model switched to {llava_models[0]} for image analysis."
                        )
                    else:
                        # Dodaj dugme za automatsko preuzimanje LLaVA
                        reply = QMessageBox.question(
                            self,
                            "LLaVA Model Required",
                            "For image analysis, you need LLaVA model.\n\n"
                            "Available models: "
                            + (
                                ", ".join(available_models)
                                if available_models
                                else "None"
                            )
                            + "\n\n"
                            "Do you want to install LLaVA model now?\n"
                            "(This will run: ollama pull llava)",
                            QMessageBox.StandardButton.Yes
                            | QMessageBox.StandardButton.No,
                            QMessageBox.StandardButton.Yes,
                        )

                        if reply == QMessageBox.StandardButton.Yes:
                            self.install_llava_model()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error processing image: {str(e)}")

    def test_llava_model(self):
        """Testira da li LLaVA model radi"""
        try:
            self.status_bar.showMessage("Testing LLaVA model...")

            # Kreiraj test sliku (1x1 bela slika)
            from PIL import Image

            test_img = Image.new("RGB", (1, 1), color="white")
            buffer = io.BytesIO()
            test_img.save(buffer, format="JPEG")
            try:
                test_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            except UnicodeDecodeError:
                test_base64 = base64.b64encode(buffer.getvalue()).decode("latin-1")
            # Ollama očekuje samo base64 string
            test_image_data = test_base64

            # Test prompt
            test_prompt = "What do you see in this image? Answer briefly."

            # Test poziv
            response = self.ollama_api.generate_response_stream(
                "llava:latest", test_prompt, images=[test_image_data]
            )

            if response[0] and len(response[0].strip()) > 0:
                QMessageBox.information(
                    self,
                    "LLaVA Test Success",
                    f"LLaVA model is working!\n\nResponse: {response[0][:100]}...",
                )
                self.status_bar.showMessage("LLaVA model is working correctly!")
                return True
            else:
                QMessageBox.warning(
                    self,
                    "LLaVA Test Failed",
                    "LLaVA model returned empty response. Try restarting Ollama or reinstalling the model.",
                )
                self.status_bar.showMessage("LLaVA model test failed")
                return False

        except Exception as e:
            QMessageBox.critical(
                self, "LLaVA Test Error", f"Error testing LLaVA model: {str(e)}"
            )
            self.status_bar.showMessage("LLaVA model test error")
            return False

    def install_llava_model(self):
        """Automatski instalira LLaVA model"""
        try:
            self.status_bar.showMessage(
                "Installing LLaVA model... This may take several minutes."
            )

            # Pokreni ollama pull llava u background thread-u
            def install_llava():
                try:
                    result = subprocess.run(
                        ["ollama", "pull", "llava"],
                        capture_output=True,
                        text=True,
                        timeout=1800,  # 30 minuta timeout
                    )

                    if result.returncode == 0:
                        # Uspešno instaliran
                        QMessageBox.information(
                            self,
                            "Success",
                            "LLaVA model installed successfully!\n\n"
                            "You can now use image analysis features.",
                        )
                        # Refresh model list
                        self.check_ollama_status()
                        self.status_bar.showMessage(
                            "LLaVA model ready for image analysis!"
                        )
                    else:
                        QMessageBox.critical(
                            self,
                            "Installation Failed",
                            f"Failed to install LLaVA model:\n\n{result.stderr}",
                        )
                        self.status_bar.showMessage("LLaVA installation failed")

                except subprocess.TimeoutExpired:
                    QMessageBox.warning(
                        self,
                        "Timeout",
                        "LLaVA installation timed out. Please try again or install manually:\n\n"
                        "ollama pull llava",
                    )
                    self.status_bar.showMessage("LLaVA installation timed out")
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Error installing LLaVA: {str(e)}\n\n"
                        "Please install manually:\n"
                        "ollama pull llava",
                    )
                    self.status_bar.showMessage("LLaVA installation error")

            # Pokreni u background thread-u
            install_thread = threading.Thread(target=install_llava, daemon=True)
            install_thread.start()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error starting LLaVA installation: {str(e)}"
            )

    def clear_uploaded_files(self):
        """Clears all uploaded files and images"""
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Are you sure you want to delete all uploaded files and images?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.uploaded_files.clear()
            self.uploaded_images.clear()
            self.status_bar.showMessage("All uploaded files and images cleared!")

    def get_uploaded_files_context(self):
        """Returns context of uploaded files for AI"""
        if not self.uploaded_files:
            return ""

        context = "\n\n=== UPLOADED FILES ===\n"
        context += f"Total uploaded files: {len(self.uploaded_files)}\n"
        context += "AI has access to content of all these files:\n\n"

        for i, file_info in enumerate(self.uploaded_files, 1):
            context += f"FILE {i}: {file_info['name']}\n"
            context += f"Path: {file_info['path']}\n"
            context += f"Content:\n{file_info['content']}"
            context += "\n" + "=" * 50 + "\n"

        context += (
            "\nWhen user asks about files, use content from all uploaded files.\n"
        )
        context += "If the question refers to a specific file, indicate which file you're using.\n"
        context += "If the question refers to multiple files, compare and analyze them together.\n"

        return context

    def debug_context(self):
        """Shows context that is sent to AI"""
        if not self.uploaded_files:
            QMessageBox.information(self, "Debug", "No uploaded files!")
            return

        # Create test prompt
        test_prompt = self.build_contextual_prompt("Test message for debug")

        # Show in dialog
        from PySide6.QtWidgets import QDialog, QTextEdit, QVBoxLayout, QPushButton

        dialog = QDialog(self)
        dialog.setWindowTitle("Debug Context")
        dialog.setGeometry(200, 200, 800, 600)

        layout = QVBoxLayout()

        text_edit = QTextEdit()
        text_edit.setPlainText(test_prompt)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def change_file_limit(self):
        """Changes file length limit for AI"""
        from PySide6.QtWidgets import QInputDialog

        current_limit = self.max_file_content_length
        if current_limit == -1:
            current_display = "∞ (unlimited)"
        else:
            current_display = str(current_limit)

        new_limit, ok = QInputDialog.getInt(
            self,
            "Change File Limit",
            f"Enter new character limit (current: {current_display}):\n-1 = unlimited",
            current_limit if current_limit != -1 else 10000,
            -1,
            1000000,
            1000,
        )

        if ok and new_limit != current_limit:
            self.max_file_content_length = new_limit
            if new_limit == -1:
                self.file_limit_btn.setText("📏 ∞")
                self.status_bar.showMessage("File limit set to unlimited")
            else:
                self.file_limit_btn.setText(f"📏 {new_limit}")
                self.status_bar.showMessage(
                    f"File limit changed to {new_limit} characters"
                )

    def closeEvent(self, event):
        """Cleanup when closing application"""
        # Stop TTS
        if hasattr(self, "tts"):
            self.tts.stop()

        # Stop Ollama
        if self.ollama_process:
            self.ollama_process.terminate()

        event.accept()

    def show_img2img_options(self):
        """Prikazuje dialog za image-to-image generaciju"""
        from PySide6.QtWidgets import QMessageBox

        try:
            if not CONTROLNET_AVAILABLE:
                QMessageBox.warning(
                    self,
                    "ControlNet Not Available",
                    "ControlNet libraries are not installed. Please install controlnet-aux to use image-to-image functionality.",
                )
                return

            if not self.uploaded_images:
                QMessageBox.warning(
                    self,
                    "No Image Uploaded",
                    "Please upload an image first using the IMAGE button before using image-to-image.",
                )
                return

            from PySide6.QtWidgets import (
                QDialog,
                QVBoxLayout,
                QHBoxLayout,
                QLabel,
                QLineEdit,
                QTextEdit,
                QSpinBox,
                QDoubleSpinBox,
                QPushButton,
                QMessageBox,
                QComboBox,
                QGroupBox,
                QSlider,
                QCheckBox,
            )
            from PySide6.QtCore import Qt

            dialog = QDialog(self)
            dialog.setWindowTitle("Image-to-Image Settings")
            dialog.setModal(True)
            dialog.resize(700, 600)
            dialog.setStyleSheet(
                """
                QDialog {
                    background-color: #1a1a1a;
                    color: #00ff00;
                }
                QLabel {
                    color: #00ff00;
                }
                QGroupBox {
                    color: #00ff00;
                    border: 2px solid #00ff00;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QComboBox {
                    background-color: #2d2d2d;
                    color: #00ff00;
                    border: 1px solid #00ff00;
                    padding: 5px;
                    border-radius: 3px;
                }
                QLineEdit, QTextEdit {
                    background-color: #2d2d2d;
                    color: #00ff00;
                    border: 1px solid #00ff00;
                    padding: 5px;
                    border-radius: 3px;
                }
                QSpinBox, QDoubleSpinBox {
                    background-color: #2d2d2d;
                    color: #00ff00;
                    border: 1px solid #00ff00;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton {
                    background-color: #2d2d2d;
                    color: #00ff00;
                    border: 1px solid #00ff00;
                    padding: 8px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #3d3d3d;
                    border: 1px solid #00ff88;
                }
                QPushButton:pressed {
                    background-color: #1d1d1d;
                }
                """
            )

            layout = QVBoxLayout(dialog)

            # Input image selection
            input_group = QGroupBox("Input Image")
            input_layout = QVBoxLayout(input_group)

            input_image_combo = QComboBox()
            for i, img_info in enumerate(self.uploaded_images):
                input_image_combo.addItem(
                    f"{img_info['name']} ({img_info['width']}x{img_info['height']})"
                )
            input_layout.addWidget(QLabel("Select input image:"))
            input_layout.addWidget(input_image_combo)

            layout.addWidget(input_group)

            # ControlNet selection
            controlnet_group = QGroupBox("ControlNet Settings")
            controlnet_layout = QVBoxLayout(controlnet_group)

            controlnet_combo = QComboBox()
            for name, info in self.image_generator.available_controlnets.items():
                controlnet_combo.addItem(f"{name} - {info['description']}")
            controlnet_layout.addWidget(QLabel("ControlNet type:"))
            controlnet_layout.addWidget(controlnet_combo)

            # ControlNet strength
            controlnet_strength_label = QLabel("ControlNet Strength: 1.0")
            controlnet_strength_slider = QSlider()
            controlnet_strength_slider.setOrientation(
                Qt.Orientation.Vertical
            )  # Vertical
            controlnet_strength_slider.setRange(0, 200)  # 0.0 to 2.0
            controlnet_strength_slider.setValue(100)  # 1.0
            controlnet_strength_slider.setToolTip(
                "ControlNet conditioning scale (0.0 to 2.0)"
            )

            def update_controlnet_strength(value):
                strength = value / 100.0
                controlnet_strength_label.setText(
                    f"ControlNet Strength: {strength:.1f}"
                )

            controlnet_strength_slider.valueChanged.connect(update_controlnet_strength)

            controlnet_layout.addWidget(controlnet_strength_label)
            controlnet_layout.addWidget(controlnet_strength_slider)

            layout.addWidget(controlnet_group)

            # Prompt settings
            prompt_group = QGroupBox("Prompt Settings")
            prompt_layout = QVBoxLayout(prompt_group)

            prompt_input = QTextEdit()
            prompt_input.setPlaceholderText(
                "Enter your prompt for image transformation..."
            )
            prompt_input.setMaximumHeight(80)
            prompt_layout.addWidget(QLabel("Prompt:"))
            prompt_layout.addWidget(prompt_input)

            negative_prompt_input = QTextEdit()
            negative_prompt_input.setPlaceholderText(
                "Enter negative prompt (optional)..."
            )
            negative_prompt_input.setMaximumHeight(60)
            prompt_layout.addWidget(QLabel("Negative prompt:"))
            prompt_layout.addWidget(negative_prompt_input)

            layout.addWidget(prompt_group)

            # Generation settings
            settings_group = QGroupBox("Generation Settings")
            settings_layout = QVBoxLayout(settings_group)

            # Steps
            steps_layout = QHBoxLayout()
            steps_layout.addWidget(QLabel("Steps:"))
            steps_spin = QSpinBox()
            steps_spin.setRange(1, 100)
            steps_spin.setValue(20)
            steps_layout.addWidget(steps_spin)
            settings_layout.addLayout(steps_layout)

            # Guidance scale
            guidance_layout = QHBoxLayout()
            guidance_layout.addWidget(QLabel("Guidance Scale:"))
            guidance_spin = QDoubleSpinBox()
            guidance_spin.setRange(1.0, 20.0)
            guidance_spin.setValue(7.5)
            guidance_spin.setSingleStep(0.1)
            guidance_layout.addWidget(guidance_spin)
            settings_layout.addLayout(guidance_layout)

            # Seed
            seed_layout = QHBoxLayout()
            seed_layout.addWidget(QLabel("Seed (0 for random):"))
            seed_spin = QSpinBox()
            seed_spin.setRange(0, 2147483647)
            seed_spin.setValue(0)
            seed_layout.addWidget(seed_spin)
            settings_layout.addLayout(seed_layout)

            layout.addWidget(settings_group)

            # Buttons
            button_layout = QHBoxLayout()

            load_controlnet_btn = QPushButton("Load ControlNet")
            generate_btn = QPushButton("Generate Image")
            cancel_btn = QPushButton("Cancel")

            button_layout.addWidget(load_controlnet_btn)
            button_layout.addWidget(generate_btn)
            button_layout.addWidget(cancel_btn)

            layout.addLayout(button_layout)

            # Button connections
            def load_controlnet():
                controlnet_name = controlnet_combo.currentText().split(" - ")[0]
                if self.image_generator.load_controlnet(controlnet_name):
                    QMessageBox.information(
                        dialog,
                        "Success",
                        f"ControlNet {controlnet_name} loaded successfully!",
                    )
                else:
                    QMessageBox.warning(
                        dialog, "Error", f"Failed to load ControlNet {controlnet_name}"
                    )

            def generate_image():
                if not self.image_generator.controlnet_loaded:
                    QMessageBox.warning(
                        dialog, "Error", "Please load a ControlNet model first!"
                    )
                    return

                prompt = prompt_input.toPlainText().strip()
                if not prompt:
                    QMessageBox.warning(dialog, "Error", "Please enter a prompt!")
                    return

                # Get selected image
                selected_idx = input_image_combo.currentIndex()
                if selected_idx < 0 or selected_idx >= len(self.uploaded_images):
                    QMessageBox.warning(
                        dialog, "Error", "Please select an input image!"
                    )
                    return

                img_info = self.uploaded_images[selected_idx]
                input_image_path = img_info["path"]

                # Get settings
                controlnet_type = controlnet_combo.currentText().split(" - ")[0].lower()
                controlnet_strength = controlnet_strength_slider.value() / 100.0
                steps = steps_spin.value()
                guidance = guidance_spin.value()
                seed = seed_spin.value() if seed_spin.value() > 0 else None
                negative_prompt = negative_prompt_input.toPlainText().strip()

                # Generate image
                dialog.accept()

                # Show progress
                self.status_bar.showMessage("Generating image-to-image...")

                def generate_thread():
                    try:
                        result, message = self.image_generator.generate_image_to_image(
                            prompt=prompt,
                            input_image=input_image_path,
                            controlnet_type=controlnet_type,
                            negative_prompt=negative_prompt,
                            steps=steps,
                            guidance_scale=guidance,
                            controlnet_conditioning_scale=controlnet_strength,
                            seed=seed,
                        )

                        if result:
                            # Save and display result
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"img2img_{timestamp}.png"
                            filepath = os.path.join(os.getcwd(), filename)
                            result.save(filepath)

                            # Add to chat - use QTimer to safely add to main thread
                            def add_to_chat():
                                ai_bubble = ChatBubble(
                                    f"🎨 Generated image-to-image: {filename}",
                                    False,
                                    image_path=filepath,
                                )
                                self.chat_layout.addWidget(ai_bubble)

                            QTimer.singleShot(0, add_to_chat)
                            self.status_bar.showMessage(
                                f"Image-to-image generated: {filename}"
                            )
                        else:

                            def add_error_to_chat():
                                error_bubble = ChatBubble(f"❌ Error: {message}", False)
                                self.chat_layout.addWidget(error_bubble)

                            QTimer.singleShot(0, add_error_to_chat)
                            self.status_bar.showMessage(
                                "Image-to-image generation failed"
                            )

                    except Exception as e:

                        def add_exception_to_chat():
                            error_bubble = ChatBubble(f"❌ Error: {str(e)}", False)
                            self.chat_layout.addWidget(error_bubble)

                        QTimer.singleShot(0, add_exception_to_chat)
                        self.status_bar.showMessage("Image-to-image generation failed")

                # Start generation in thread
                import threading

                thread = threading.Thread(target=generate_thread)
                thread.daemon = True
                thread.start()

            load_controlnet_btn.clicked.connect(load_controlnet)
            generate_btn.clicked.connect(generate_image)
            cancel_btn.clicked.connect(dialog.reject)

            dialog.exec()

        except Exception as e:
            print(f"Error in show_img2img_options: {e}")
            QMessageBox.critical(
                self, "Error", f"Error opening img2img dialog: {str(e)}"
            )

    def show_advanced_image_settings(self):
        """Prikazuje napredne postavke za slike (LoRA, TI, upscaling)"""
        try:

            dialog = QDialog(self)
            dialog.setWindowTitle("Napredne postavke slika")
            dialog.setModal(True)
            dialog.resize(700, 600)
            dialog.setStyleSheet(
                """
                QDialog {
                    background-color: #1a1a1a;
                    color: #00ff00;
                }
                QLabel {
                    color: #00ff00;
                }
                QGroupBox {
                    color: #00ff00;
                    border: 2px solid #00ff00;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QListWidget {
                    background-color: #2d2d2d;
                    color: #00ff00;
                    border: 1px solid #00ff00;
                    padding: 5px;
                    border-radius: 3px;
                }
                QListWidget::item {
                    padding: 5px;
                }
                QListWidget::item:selected {
                    background-color: #3d3d3d;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #00ff00;
                    height: 8px;
                    background: #2d2d2d;
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: #00ff00;
                    border: 1px solid #00ff00;
                    width: 18px;
                    margin: -2px 0;
                    border-radius: 9px;
                }
                QComboBox {
                    background-color: #2d2d2d;
                    color: #00ff00;
                    border: 1px solid #00ff00;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton {
                    background-color: #2d2d2d;
                    color: #00ff00;
                    border: 1px solid #00ff00;
                    padding: 8px 16px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #3d3d3d;
                    border: 1px solid #00ff88;
                }
                QCheckBox {
                    color: #00ff00;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                }
                QCheckBox::indicator:unchecked {
                    border: 1px solid #00ff00;
                    background-color: #2d2d2d;
                }
                QCheckBox::indicator:checked {
                    border: 1px solid #00ff00;
                    background-color: #00ff00;
                }
            """
            )

            layout = QVBoxLayout(dialog)

            # LoRA sekcija
            lora_group = QGroupBox("LoRA modeli")
            lora_layout = QVBoxLayout(lora_group)

            lora_list = QListWidget()
            for lora_name in self.image_generator.available_loras.keys():
                lora_list.addItem(lora_name)
            lora_list.setMaximumHeight(120)

            def update_lora_info():
                selected_items = lora_list.selectedItems()
                if selected_items:
                    lora_name = selected_items[0].text()
                    if lora_name in self.image_generator.available_loras:
                        lora_data = self.image_generator.available_loras[lora_name]
                        trigger = lora_data.get("trigger", "")
                        strength = lora_data.get("strength", 0.8)
                        description = lora_data.get("description", "")
                        base_model = lora_data.get("base_model", "SDXL Base")

                        # Automatski podesi preporučenu snagu
                        recommended_strength = int(strength * 100)
                        lora_strength_slider.setValue(recommended_strength)
                        update_strength_value()  # Ažuriraj prikaz vrednosti

                        # Postavi tooltip umesto velikog info panela
                        tooltip_text = f"{lora_name}\n"
                        tooltip_text += f"Opis: {description}\n"
                        if trigger:
                            tooltip_text += f"Trigger: {trigger}\n"
                        else:
                            tooltip_text += f"Trigger: Nema (automatski radi)\n"
                        tooltip_text += f"Preporučena snaga: {strength}\n"
                        tooltip_text += f"Base model: {base_model}"

                        lora_list.setToolTip(tooltip_text)
                else:
                    lora_list.setToolTip("Izaberi LoRA da vidiš informacije")

            lora_list.itemSelectionChanged.connect(update_lora_info)

            lora_strength_label = QLabel("Snaga LoRA:")
            lora_strength_slider = QSlider()
            lora_strength_slider.setOrientation(Qt.Orientation.Horizontal)
            lora_strength_slider.setRange(-300, 300)  # -3.0 do +3.0
            lora_strength_slider.setValue(80)  # 0.8
            lora_strength_slider.setToolTip("LoRA snaga (-3.0 do +3.0)")

            # Label za prikaz trenutne vrednosti
            lora_strength_value_label = QLabel("0.8")
            lora_strength_value_label.setMinimumWidth(40)
            lora_strength_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lora_strength_value_label.setStyleSheet(
                """
                QLabel {
                    background-color: #2d2d2d;
                    border: 1px solid #555;
                    border-radius: 3px;
                    padding: 2px;
                    font-weight: bold;
                    color: #ffffff;
                }
            """
            )

            def update_strength_value():
                value = lora_strength_slider.value() / 100.0  # Konvertuj u decimalni
                lora_strength_value_label.setText(f"{value:.1f}")

            lora_strength_slider.valueChanged.connect(update_strength_value)
            update_strength_value()  # Inicijalno podešavanje

            lora_buttons_layout = QHBoxLayout()
            load_lora_btn = QPushButton("Učitaj LoRA")
            unload_lora_btn = QPushButton("Ukloni LoRA")
            unload_all_lora_btn = QPushButton("Ukloni sve LoRA")

            lora_buttons_layout.addWidget(load_lora_btn)
            lora_buttons_layout.addWidget(unload_lora_btn)
            lora_buttons_layout.addWidget(unload_all_lora_btn)

            lora_layout.addWidget(QLabel("Dostupni LoRA modeli:"))
            lora_layout.addWidget(lora_list)
            # Layout za snagu LoRA sa slajderom i vrednošću
            lora_strength_layout = QHBoxLayout()
            lora_strength_layout.addWidget(lora_strength_label)
            lora_strength_layout.addWidget(lora_strength_slider)
            lora_strength_layout.addWidget(lora_strength_value_label)

            lora_layout.addLayout(lora_strength_layout)
            lora_layout.addLayout(lora_buttons_layout)

            # TI Embeddings sekcija
            ti_group = QGroupBox("Textual Inversion Embeddings")
            ti_layout = QVBoxLayout(ti_group)

            ti_list = QListWidget()
            for ti_name in self.image_generator.available_embeddings.keys():
                ti_list.addItem(ti_name)
            ti_list.setMaximumHeight(120)

            ti_buttons_layout = QHBoxLayout()
            load_ti_btn = QPushButton("Učitaj Embedding")
            unload_ti_btn = QPushButton("Ukloni Embedding")
            unload_all_ti_btn = QPushButton("Ukloni sve Embeddings")

            ti_buttons_layout.addWidget(load_ti_btn)
            ti_buttons_layout.addWidget(unload_ti_btn)
            ti_buttons_layout.addWidget(unload_all_ti_btn)

            ti_layout.addWidget(QLabel("Dostupni Embeddings:"))
            ti_layout.addWidget(ti_list)
            ti_layout.addLayout(ti_buttons_layout)

            # Upscaling sekcija
            upscale_group = QGroupBox("Upscaling")
            upscale_layout = QVBoxLayout(upscale_group)

            upscale_combo = QComboBox()
            for upscale_name in self.image_upscaler.available_upscalers.keys():
                upscale_combo.addItem(upscale_name)

            upscale_buttons_layout = QHBoxLayout()
            load_upscale_btn = QPushButton("Učitaj Upscaler")
            unload_upscale_btn = QPushButton("Ukloni Upscaler")

            upscale_buttons_layout.addWidget(load_upscale_btn)
            upscale_buttons_layout.addWidget(unload_upscale_btn)

            upscale_layout.addWidget(QLabel("Upscaler model:"))
            upscale_layout.addWidget(upscale_combo)
            upscale_layout.addLayout(upscale_buttons_layout)

            # Status sekcija
            status_group = QGroupBox("Status")
            status_layout = QVBoxLayout(status_group)

            active_loras_label = QLabel("Aktivni LoRA modeli: Nema")
            active_embeddings_label = QLabel("Aktivni Embeddings: Nema")
            upscaler_status_label = QLabel("Upscaler: Nije učitan")

            status_layout.addWidget(active_loras_label)
            status_layout.addWidget(active_embeddings_label)
            status_layout.addWidget(upscaler_status_label)

            # Dodaj grupe u glavni layout
            layout.addWidget(lora_group)
            layout.addWidget(ti_group)
            layout.addWidget(upscale_group)
            layout.addWidget(status_group)

            # Dugmad
            button_layout = QHBoxLayout()
            close_btn = QPushButton("Zatvori")
            button_layout.addWidget(close_btn)
            layout.addLayout(button_layout)

            # Funkcije za dugmad
            def update_status():
                active_loras = [
                    lora["name"] for lora in self.image_generator.active_loras
                ]
                active_embeddings = self.image_generator.active_embeddings
                upscaler_status = self.image_upscaler.current_upscaler or "Nije učitan"

                active_loras_label.setText(
                    f"Aktivni LoRA modeli: {', '.join(active_loras) if active_loras else 'Nema'}"
                )
                active_embeddings_label.setText(
                    f"Aktivni Embeddings: {', '.join(active_embeddings) if active_embeddings else 'Nema'}"
                )
                upscaler_status_label.setText(f"Upscaler: {upscaler_status}")

            def load_lora():
                current_item = lora_list.currentItem()
                if current_item:
                    lora_name = current_item.text()
                    strength = lora_strength_slider.value() / 100.0
                    if self.image_generator.load_lora(lora_name, strength):
                        # Kopiraj trigger reči u clipboard
                        if lora_name in self.image_generator.available_loras:
                            lora_data = self.image_generator.available_loras[lora_name]
                            trigger = lora_data.get("trigger", "")
                            if trigger:
                                from PySide6.QtGui import QGuiApplication

                                clipboard = QGuiApplication.clipboard()
                                clipboard.setText(trigger)
                                QMessageBox.information(
                                    dialog,
                                    "Uspeh",
                                    f"LoRA {lora_name} je uspešno učitan!\nTrigger reči su kopirane u clipboard: {trigger}",
                                )
                            else:
                                QMessageBox.information(
                                    dialog,
                                    "Uspeh",
                                    f"LoRA {lora_name} je uspešno učitan!\n(Nema trigger reči)",
                                )
                        else:
                            QMessageBox.information(
                                dialog, "Uspeh", f"LoRA {lora_name} je uspešno učitan!"
                            )
                        update_status()
                    else:
                        QMessageBox.warning(
                            dialog, "Greška", f"Neuspešno učitavanje LoRA {lora_name}"
                        )

            def unload_lora():
                current_item = lora_list.currentItem()
                if current_item:
                    lora_name = current_item.text()
                    if self.image_generator.unload_lora(lora_name):
                        QMessageBox.information(
                            dialog, "Uspeh", f"LoRA {lora_name} je uspešno uklonjen!"
                        )
                        update_status()
                    else:
                        QMessageBox.warning(
                            dialog, "Greška", f"Neuspešno uklanjanje LoRA {lora_name}"
                        )

            def unload_all_lora():
                for lora in self.image_generator.active_loras.copy():
                    self.image_generator.unload_lora(lora["name"])
                QMessageBox.information(
                    dialog, "Uspeh", "Svi LoRA modeli su uklonjeni!"
                )
                update_status()

            def load_ti():
                current_item = ti_list.currentItem()
                if current_item:
                    ti_name = current_item.text()
                    if self.image_generator.load_embedding(ti_name):
                        QMessageBox.information(
                            dialog, "Uspeh", f"Embedding {ti_name} je uspešno učitan!"
                        )
                        update_status()
                    else:
                        QMessageBox.warning(
                            dialog,
                            "Greška",
                            f"Neuspešno učitavanje embedding {ti_name}",
                        )

            def unload_ti():
                current_item = ti_list.currentItem()
                if current_item:
                    ti_name = current_item.text()
                    if self.image_generator.unload_embedding(ti_name):
                        QMessageBox.information(
                            dialog, "Uspeh", f"Embedding {ti_name} je uspešno uklonjen!"
                        )
                        update_status()
                    else:
                        QMessageBox.warning(
                            dialog,
                            "Greška",
                            f"Neuspešno uklanjanje embedding {ti_name}",
                        )

            def unload_all_ti():
                for embedding in self.image_generator.active_embeddings.copy():
                    # Pronađi ime embedding-a po trigger-u
                    for name, info in self.image_generator.available_embeddings.items():
                        if info["trigger"] == embedding:
                            self.image_generator.unload_embedding(name)
                            break
                QMessageBox.information(dialog, "Uspeh", "Svi Embeddings su uklonjeni!")
                update_status()

            def load_upscale():
                upscale_name = upscale_combo.currentText()
                if self.image_upscaler.load_upscaler(upscale_name):
                    QMessageBox.information(
                        dialog, "Uspeh", f"Upscaler {upscale_name} je uspešno učitan!"
                    )
                    update_status()
                else:
                    QMessageBox.warning(
                        dialog,
                        "Greška",
                        f"Neuspešno učitavanje upscaler {upscale_name}",
                    )

            def unload_upscale():
                if self.image_upscaler.unload_upscaler():
                    QMessageBox.information(
                        dialog, "Uspeh", "Upscaler je uspešno uklonjen!"
                    )
                    update_status()
                else:
                    QMessageBox.warning(
                        dialog, "Greška", "Neuspešno uklanjanje upscaler"
                    )

            # Poveži dugmad sa funkcijama
            load_lora_btn.clicked.connect(load_lora)
            unload_lora_btn.clicked.connect(unload_lora)
            unload_all_lora_btn.clicked.connect(unload_all_lora)
            load_ti_btn.clicked.connect(load_ti)
            unload_ti_btn.clicked.connect(unload_ti)
            unload_all_ti_btn.clicked.connect(unload_all_ti)
            load_upscale_btn.clicked.connect(load_upscale)
            unload_upscale_btn.clicked.connect(unload_upscale)
            close_btn.clicked.connect(dialog.accept)

            # Inicijalno ažuriranje statusa
            update_status()

            dialog.exec()

        except Exception as e:
            print(f"Error showing advanced image settings: {e}")
            QMessageBox.critical(
                self, "Greška", f"Greška pri prikazivanju naprednih postavki: {str(e)}"
            )

    def scroll_to_bottom(self):
        """Scrolluje chat na dno"""
        try:
            scrollbar = self.chat_scroll.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            print(f"Error scrolling to bottom: {e}")

    def upscale_last_image(self):
        """Upscale poslednje generisane slike"""
        try:
            if not self.image_upscaler.upscaler_loaded:
                QMessageBox.warning(
                    self,
                    "Upscaler nije učitan",
                    "Molimo učitajte upscaler model u naprednim postavkama pre upscaling-a.",
                )
                return

            # Pronađi poslednju generisanu sliku
            last_image_path = None
            for i in range(self.chat_layout.count() - 1, -1, -1):
                widget = self.chat_layout.itemAt(i).widget()
                if isinstance(widget, ChatBubble) and widget.image_path:
                    last_image_path = widget.image_path
                    break

            if not last_image_path or not os.path.exists(last_image_path):
                QMessageBox.warning(
                    self,
                    "Nema slike za upscaling",
                    "Nije pronađena poslednja generisana slika za upscaling.",
                )
                return

            # Učitaj sliku
            from PIL import Image

            image = Image.open(last_image_path)

            # Prikaži poruku o početku upscaling-a
            upscale_msg = (
                f"🔍 Upscaling slike sa {self.image_upscaler.current_upscaler}..."
            )
            upscale_bubble = ChatBubble(upscale_msg, False)
            self.chat_layout.addWidget(upscale_bubble)
            self.scroll_to_bottom()

            # Upscale sliku
            upscaled_image = self.image_upscaler.upscale_image(image)

            if upscaled_image:
                # Sačuvaj upscaled sliku
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                upscaled_filename = f"upscaled_image_{timestamp}.png"
                upscaled_filepath = os.path.join(os.getcwd(), upscaled_filename)
                upscaled_image.save(upscaled_filepath)

                # Prikaži upscaled sliku
                success_msg = f"✅ Slika je uspešno upscaled!\n📁 Sačuvana kao: {upscaled_filename}\n📏 Originalna: {image.size} -> Upscaled: {upscaled_image.size}"
                success_bubble = ChatBubble(
                    success_msg, False, image_path=upscaled_filepath
                )
                self.chat_layout.addWidget(success_bubble)
                self.scroll_to_bottom()

                print(f"Upscaled image saved as: {upscaled_filepath}")
            else:
                error_msg = "❌ Greška pri upscaling-u slike. Proverite da li je upscaler model ispravno učitan."
                error_bubble = ChatBubble(error_msg, False)
                self.chat_layout.addWidget(error_bubble)
                self.scroll_to_bottom()

        except Exception as e:
            print(f"Error upscaling image: {e}")
            error_msg = f"❌ Greška pri upscaling-u: {str(e)}"
            error_bubble = ChatBubble(error_msg, False)
            self.chat_layout.addWidget(error_bubble)
            self.scroll_to_bottom()

    def show_image_options(self):
        """Prikazuje dialog sa opcijama za generisanje slike"""
        try:
            # Auto-unload Ollama models before generation
            if hasattr(self, "unload_ollama_models_silent"):
                print("Auto-unloading Ollama models to free GPU memory...")
                self.unload_ollama_models_silent()

            print(
                f"Before generation - CUDA memory: {torch.cuda.memory_allocated()/1024**3:.2f} GB"
            )
            # Kreiraj dialog za unos prompt-a
            from PySide6.QtWidgets import (
                QDialog,
                QVBoxLayout,
                QHBoxLayout,
                QLabel,
                QLineEdit,
                QTextEdit,
                QSpinBox,
                QDoubleSpinBox,
                QPushButton,
                QMessageBox,
                QComboBox,
            )

            dialog = QDialog(self)
            dialog.setWindowTitle("Image Generation Settings")
            dialog.setModal(True)
            dialog.resize(600, 500)
            dialog.setStyleSheet(
                """
                QDialog {
                    background-color: #1a1a1a;
                    color: #00ff00;
                }
                QLabel {
                    color: #00ff00;
                }
                QComboBox {
                    background-color: #2d2d2d;
                    color: #00ff00;
                    border: 1px solid #00ff00;
                    padding: 5px;
                    border-radius: 3px;
                }
                QComboBox:hover {
                    background-color: #3d3d3d;
                    border: 1px solid #00ff88;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 5px solid #00ff00;
                }
                QSpinBox, QDoubleSpinBox {
                    background-color: #2d2d2d;
                    color: #00ff00;
                    border: 1px solid #00ff00;
                    padding: 5px;
                    border-radius: 3px;
                }
                QSpinBox:hover, QDoubleSpinBox:hover {
                    background-color: #3d3d3d;
                    border: 1px solid #00ff88;
                }
                QPushButton {
                    background-color: #2d2d2d;
                    color: #00ff00;
                    border: 1px solid #00ff00;
                    padding: 8px 16px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #3d3d3d;
                    border: 1px solid #00ff88;
                }
                QPushButton:pressed {
                    background-color: #1d1d1d;
                    border: 1px solid #00ff44;
                }
            """
            )

            layout = QVBoxLayout(dialog)

            # Model selection
            model_label = QLabel("Model:")
            model_combo = QComboBox()
            for model_name in self.image_generator.available_models.keys():
                model_combo.addItem(model_name)
            model_combo.setCurrentText(self.image_settings["selected_model"])
            model_combo.setToolTip(
                "SDXL: Najbolji kvalitet, Juggernaut: Fotorealistični, DynaVision: 3D stilizovani\nOmnigenXL: Versatile SFW/NSFW, SD 2.1: Brži, SD 1.5: Najbrži\nPornVision: Specialized adult content\nIzaberite prema potrebi za brzinu vs kvalitet"
            )

            # Model description
            model_desc_label = QLabel("")
            model_desc_label.setStyleSheet(
                "color: #00ff88; font-size: 11px; margin: 5px 0;"
            )
            model_desc_label.setWordWrap(True)

            # Negative prompt
            neg_prompt_label = QLabel("Negative Prompt (optional):")
            neg_prompt_input = QLineEdit()
            neg_prompt_input.setPlaceholderText("What you don't want in the image...")
            neg_prompt_input.setText(self.image_settings["negative_prompt"])

            # Define update function after width_input and height_input are created
            def update_model_description():
                current_model = model_combo.currentText()
                if current_model in self.image_generator.available_models:
                    model_info = self.image_generator.available_models[current_model]
                    description = model_info["description"]
                    model_desc_label.setText(description)

                    # Automatski promeni negative prompt na preporučeni za model
                    if "default_negative" in model_info:
                        neg_prompt_input.setText(model_info["default_negative"])

                    # Update width/height based on model
                    default_size = model_info["default_size"]
                    width_input.setValue(default_size[0])
                    height_input.setValue(default_size[1])

                    # Update steps and guidance based on model
                    if "default_steps" in model_info:
                        steps_input.setValue(model_info["default_steps"])
                    if "default_guidance" in model_info:
                        guidance_input.setValue(model_info["default_guidance"])

                    # Update range based on model type
                    if model_info["type"] == "xl":
                        # SDXL mora biti 1024x1024 ili veći kvadrat
                        width_input.setRange(1024, 2048)
                        height_input.setRange(1024, 2048)
                    else:
                        # SD 2.1 i SD 1.5 mogu biti 512x512 ili veći
                        width_input.setRange(512, 1024)
                        height_input.setRange(512, 1024)

            # Connect the function after it's defined
            model_combo.currentTextChanged.connect(update_model_description)

            # Settings section
            settings_label = QLabel("Settings:")
            settings_label.setStyleSheet(
                "font-weight: bold; margin-top: 15px; margin-bottom: 10px; color: #00ff00;"
            )

            # Resolution settings
            resolution_layout = QHBoxLayout()
            resolution_layout.addWidget(QLabel("Resolution:"))

            # Width
            width_label = QLabel("Width:")
            width_input = QSpinBox()
            width_input.setRange(512, 2048)
            width_input.setValue(self.image_settings["width"])
            width_input.setSingleStep(128)

            # Height
            height_label = QLabel("Height:")
            height_input = QSpinBox()
            height_input.setRange(512, 2048)
            height_input.setValue(self.image_settings["height"])
            height_input.setSingleStep(128)

            # Dodaj validaciju za SDXL
            def validate_resolution():
                current_model = model_combo.currentText()
                if "SDXL" in current_model:
                    # SDXL mora biti kvadrat
                    width = width_input.value()
                    height = height_input.value()
                    if width != height:
                        # Automatski postavi na kvadrat
                        size = max(width, height)
                        width_input.setValue(size)
                        height_input.setValue(size)
                        print(f"SDXL: Auto-corrected to {size}x{size} (must be square)")

            width_input.valueChanged.connect(validate_resolution)
            height_input.valueChanged.connect(validate_resolution)

            resolution_layout.addWidget(width_label)
            resolution_layout.addWidget(width_input)
            resolution_layout.addWidget(height_label)
            resolution_layout.addWidget(height_input)
            resolution_layout.addStretch()

            # Quality settings
            quality_layout = QHBoxLayout()
            quality_layout.addWidget(QLabel("Quality:"))

            # Steps
            steps_label = QLabel("Steps:")
            steps_input = QSpinBox()
            steps_input.setRange(10, 150)  # Povećano sa 100 na 150
            steps_input.setValue(self.image_settings["steps"])
            steps_input.setToolTip(
                "10-30: Brzo, 50-100: Dobro, 100-150: Najbolje kvalitet\nViše koraka = bolji detalji, ali sporije generisanje"
            )

            # Guidance scale
            guidance_label = QLabel("Guidance:")
            guidance_input = QDoubleSpinBox()
            guidance_input.setRange(1.0, 20.0)
            guidance_input.setValue(self.image_settings["guidance_scale"])
            guidance_input.setSingleStep(0.5)
            guidance_input.setToolTip(
                "7-9: Standardno, 10-12: Kreativno, 15+: Ekstremno\nViše = bolje prati prompt, ali može biti previše"
            )

            # Seed
            seed_label = QLabel("Seed (optional):")
            seed_input = QLineEdit()
            seed_input.setPlaceholderText("Enter number (empty=random, 0=random)")
            if self.image_settings["seed"] is not None:
                seed_input.setText(str(self.image_settings["seed"]))
            seed_input.setToolTip(
                "Isti seed = ista slika\nRazličit seed = različite varijacije\nPrazno ili 0 = slučajni seed"
            )

            # Seed buttons
            seed_button_layout = QHBoxLayout()
            random_seed_btn = QPushButton("Random")
            random_seed_btn.clicked.connect(lambda: seed_input.clear())
            random_seed_btn.setStyleSheet(self.get_button_style("#1a1a1a", "#2d2d2d"))

            clear_seed_btn = QPushButton("Clear")
            clear_seed_btn.clicked.connect(lambda: seed_input.clear())
            clear_seed_btn.setStyleSheet(self.get_button_style("#1a1a1a", "#2d2d2d"))

            seed_button_layout.addWidget(random_seed_btn)
            seed_button_layout.addWidget(clear_seed_btn)
            seed_button_layout.addStretch()

            quality_layout.addWidget(steps_label)
            quality_layout.addWidget(steps_input)
            quality_layout.addWidget(guidance_label)
            quality_layout.addWidget(guidance_input)
            quality_layout.addWidget(seed_label)
            quality_layout.addWidget(seed_input)
            quality_layout.addLayout(seed_button_layout)
            quality_layout.addStretch()

            # Now call the function after all elements are created
            update_model_description()  # Set initial description

            # Buttons
            button_layout = QHBoxLayout()
            save_btn = QPushButton("Save Settings")
            cancel_btn = QPushButton("Cancel")

            save_btn.clicked.connect(
                lambda: self.save_image_settings(
                    dialog,
                    neg_prompt_input,
                    width_input,
                    height_input,
                    steps_input,
                    guidance_input,
                    model_combo,
                    seed_input,
                )
            )
            cancel_btn.clicked.connect(dialog.reject)

            button_layout.addWidget(save_btn)
            button_layout.addWidget(cancel_btn)

            # Add to main layout
            layout.addWidget(model_label)
            layout.addWidget(model_combo)
            layout.addWidget(model_desc_label)
            layout.addWidget(neg_prompt_label)
            layout.addWidget(neg_prompt_input)
            layout.addWidget(settings_label)
            layout.addLayout(resolution_layout)
            layout.addLayout(quality_layout)
            layout.addStretch()
            layout.addLayout(button_layout)

            # Show dialog
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error setting up image options: {str(e)}"
            )

    def save_image_settings(
        self,
        dialog,
        neg_prompt_input,
        width_input,
        height_input,
        steps_input,
        guidance_input,
        model_combo,
        seed_input,
    ):
        """Sačuva postavke za generisanje slika"""
        try:
            # Parse seed value
            seed_text = seed_input.text().strip()
            seed_value = None
            if seed_text:
                try:
                    seed_value = int(seed_text)
                except ValueError:
                    QMessageBox.warning(
                        self,
                        "Invalid Seed",
                        "Seed must be a number. Using random seed instead.",
                    )
                    seed_value = None

            # Sačuvaj postavke
            self.image_settings.update(
                {
                    "negative_prompt": neg_prompt_input.text().strip(),
                    "width": width_input.value(),
                    "height": height_input.value(),
                    "steps": steps_input.value(),
                    "guidance_scale": guidance_input.value(),
                    "selected_model": model_combo.currentText(),
                    "seed": seed_value,
                }
            )

            # Samo sačuvaj postavke - model će se učitati kada se generiše slika

            # Prikaži poruku o uspehu
            seed_info = (
                f"Seed: {self.image_settings['seed']}"
                if self.image_settings["seed"] is not None
                else "Seed: Random"
            )
            QMessageBox.information(
                self,
                "Settings Saved",
                f"Image generation settings saved!\n\n"
                f"Size: {self.image_settings['width']}x{self.image_settings['height']}\n"
                f"Steps: {self.image_settings['steps']}\n"
                f"Guidance: {self.image_settings['guidance_scale']}\n"
                f"{seed_info}",
            )

            # Zatvori dialog
            dialog.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving settings: {str(e)}")

    def unload_ollama_models(self):
        """Unload-uje sve Ollama modele iz VRAM-a"""
        try:
            import subprocess
            import sys

            # Unload sve modele
            models_to_unload = ["llava", "mixtral", "llama", "codellama", "mistral"]

            for model in models_to_unload:
                try:
                    result = subprocess.run(
                        ["ollama", "stop", model],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if result.returncode == 0:
                        print(f"Model {model} unloaded successfully")
                    else:
                        print(f"Model {model} not loaded or already unloaded")
                except subprocess.TimeoutExpired:
                    print(f"Timeout unloading {model}")
                except Exception as e:
                    print(f"Error unloading {model}: {e}")

            # Proveri status
            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                loaded_models = result.stdout.strip()
                if not loaded_models or "NAME" not in loaded_models:
                    self.status_bar.showMessage("All Ollama models unloaded from VRAM!")
                    QMessageBox.information(
                        self,
                        "Models Unloaded",
                        "All Ollama models have been unloaded from VRAM.\n\nGPU memory should be freed now.",
                    )
                else:
                    self.status_bar.showMessage(
                        f"Some models still loaded:\n{loaded_models}"
                    )
                    QMessageBox.warning(
                        self,
                        "Partial Unload",
                        f"Some models are still loaded:\n\n{loaded_models}",
                    )
            else:
                self.status_bar.showMessage("Could not check model status")

        except Exception as e:
            error_msg = f"Error unloading models: {str(e)}"
            self.status_bar.showMessage(error_msg)
            QMessageBox.critical(self, "Unload Error", error_msg)

    def unload_ollama_models_silent(self):
        """Silent unload Ollama models without UI messages"""
        try:
            import subprocess

            # Unload sve modele
            models_to_unload = ["llava", "mixtral", "llama", "codellama", "mistral"]

            for model in models_to_unload:
                try:
                    subprocess.run(
                        ["ollama", "stop", model],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                except:
                    pass  # Silent fail

            print("Ollama models unloaded silently")

        except Exception as e:
            print(f"Silent unload error: {e}")

    def generate_image_from_prompt(self):
        """Generiše sliku na osnovu teksta iz input polja"""
        try:
            # Uzmi prompt iz input polja
            prompt = self.message_input.text().strip()
            if not prompt:
                QMessageBox.warning(
                    self, "No Prompt", "Please enter a prompt in the input field first!"
                )
                return

            # Uzmi seed iz seed input polja
            seed_text = self.seed_input.text().strip()
            seed_value = None
            if seed_text and seed_text != "0":  # 0 nije random!
                try:
                    seed_value = int(seed_text)
                    print(f"Using seed: {seed_value}")
                except ValueError:
                    QMessageBox.warning(
                        self,
                        "Invalid Seed",
                        "Seed must be a number. Using random seed instead.",
                    )
                    seed_value = None
            else:
                print("Using random seed (no seed or seed=0)")

            # Auto-unload Ollama models before generation
            if hasattr(self, "unload_ollama_models_silent"):
                print("Auto-unloading Ollama models to free GPU memory...")
                self.unload_ollama_models_silent()

            # Prebaci na selektovani model ako je potrebno
            selected_model = self.image_settings.get(
                "selected_model", "SDXL Base (1024x1024)"
            )
            if selected_model != self.image_generator.current_model:
                print(f"Switching to model: {selected_model}")
                self.image_generator.switch_model(selected_model)
                # Učitaj novi model nakon prebacivanja
                if not self.image_generator.load_model():
                    QMessageBox.critical(
                        self, "Error", f"Failed to load model: {selected_model}"
                    )
                    return

            print(f"Generating image with prompt from input: '{prompt}'")
            print(f"Using model: {self.image_generator.current_model}")
            print(
                f"Before generation - CUDA memory: {torch.cuda.memory_allocated()/1024**3:.2f} GB"
            )

            # Dodaj poruku u chat da je generisanje počelo
            start_msg = f"🎨 Generating image with prompt: {prompt}"
            user_bubble = ChatBubble(start_msg, True)
            self.chat_layout.addWidget(user_bubble)

            # Ažuriraj image_settings sa seed-om iz UI-a
            current_settings = self.image_settings.copy()
            current_settings["seed"] = seed_value

            # Kreiraj i pokreni worker
            self.image_worker = ImageGenerationWorker(
                self.image_generator,
                prompt,
                current_settings,
                self.conversation_history,
            )

            # Poveži signale
            self.image_worker.image_generated.connect(self.on_image_generated)
            self.image_worker.generation_error.connect(self.on_generation_error)
            self.image_worker.progress_updated.connect(self.on_progress_updated)

            # Pokreni worker
            self.image_worker.start()

        except Exception as e:
            error_msg = f"Error starting image generation: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Error", error_msg)

    def on_image_generated(self, filepath, success_msg):
        """Handler za kada je slika uspešno generisana"""
        try:
            # Sakrij progress bar
            self.image_progress_bar.setVisible(False)

            # Dodaj u uploaded images
            filename = os.path.basename(filepath)
            self.uploaded_images.append(
                {
                    "path": filepath,
                    "name": filename,
                    "size": os.path.getsize(filepath),
                }
            )

            # Dodaj sliku u LLM kontekst
            self.image_generator.add_image_to_llm_context(
                filepath,
                "Generated image",
                self.image_settings,
                self.conversation_history,
            )

            # Prikaži kratku poruku o uspehu
            self.status_bar.showMessage(f"Image saved: {filename}")

            # Kreiraj chat bubble sa slikom (AI poruka, ne korisnička)
            ai_bubble = ChatBubble(success_msg, False, image_path=filepath)
            self.chat_layout.addWidget(ai_bubble)

            # Scroll na dno
            scrollbar = self.chat_scroll.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        except Exception as e:
            print(f"Error in on_image_generated: {e}")

    def on_generation_error(self, error_msg):
        """Handler za greške u generisanju slike"""
        try:
            # Sakrij progress bar
            self.image_progress_bar.setVisible(False)

            # Prikaži grešku u chat-u
            user_bubble = ChatBubble(error_msg, True)
            self.chat_layout.addWidget(user_bubble)

            # Prikaži grešku u status bar-u
            self.status_bar.showMessage(f"Error: {error_msg}")

        except Exception as e:
            print(f"Error in on_generation_error: {e}")

    def on_progress_updated(self, progress):
        """Handler za ažuriranje progress bar-a"""
        try:
            # Prikaži progress bar
            self.image_progress_bar.setVisible(True)
            self.image_progress_bar.setValue(progress)

            # Ažuriraj status bar
            self.status_bar.showMessage(f"Generating image... {progress}%")

            # Kada je završeno, sakrij progress bar
            if progress >= 100:
                self.image_progress_bar.setVisible(False)

        except Exception as e:
            print(f"Error in on_progress_updated: {e}")


def main():
    app = QApplication(sys.argv)

    # Postavi retro terminal stil aplikacije
    app.setStyleSheet(
        """
        QMainWindow {
            background: #000000;
            color: #00FF00;
            font-family: 'Courier New', monospace;
        }
        QMainWindow::title {
            background: #000000;
            color: #00FF00;
            font-family: 'Courier New', monospace;
        }
        QScrollArea {
            border: none;
            background-color: #000000;
        }
        QStatusBar {
            background: #000000;
            border-top: 2px solid #00FF00;
            color: #00FF00;
            font-size: 11px;
            font-family: 'Courier New', monospace;
        }
        QStatusBar::item {
            border: none;
        }
        QTextEdit, QLineEdit {
            background: #000000;
            color: #00FF00;
            border: 1px solid #00FF00;
            font-family: 'Courier New', monospace;
        }
        QPushButton {
            background: #000000;
            color: #00FF00;
            border: 1px solid #00FF00;
            font-family: 'Courier New', monospace;
            font-weight: bold;
        }
        QPushButton:hover {
            background: #001100;
            border: 2px solid #00FF00;
        }
        QComboBox {
            background: #000000;
            color: #00FF00;
            border: 1px solid #00FF00;
            font-family: 'Courier New', monospace;
        }
        QComboBox::drop-down {
            border: 1px solid #00FF00;
        }
        QComboBox QAbstractItemView {
            background: #000000;
            color: #00FF00;
            border: 1px solid #00FF00;
        }
        """
    )

    window = AIAssistantApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
