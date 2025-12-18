"""
Image Processor for locAI.
Handles image conversion to base64 for Ollama vision models.
"""
import os
import base64
import io
from pathlib import Path
from typing import Optional, Dict
from PIL import Image


class ImageProcessor:
    """Klasa za obradu slika za LLaVA model"""

    def __init__(self):
        self.max_image_size = 1024  # Maksimalna veličina slike u pikselima
        self.supported_formats = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff"]

    def is_supported_image(self, file_path: str) -> bool:
        """
        Proverava da li je format slike podržan.
        
        Args:
            file_path: Putanja do slike
            
        Returns:
            True ako je format podržan
        """
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_formats

    def resize_image_if_needed(self, img: Image.Image) -> Image.Image:
        """
        Resize-uje sliku ako je veća od maksimalne veličine.
        
        Args:
            img: PIL Image objekat
            
        Returns:
            Resized PIL Image objekat
        """
        width, height = img.size
        if width <= self.max_image_size and height <= self.max_image_size:
            return img

        # Izračunaj novu veličinu zadržavajući aspect ratio
        if width > height:
            new_width = self.max_image_size
            new_height = int(height * (self.max_image_size / width))
        else:
            new_height = self.max_image_size
            new_width = int(width * (self.max_image_size / height))

        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def image_to_base64(self, image_path: str) -> Optional[str]:
        """
        Konvertuje sliku u base64 string za Ollama API.
        
        Args:
            image_path: Putanja do slike
            
        Returns:
            Base64 string (bez data URL prefixa) ili None ako ne uspe
        """
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
            print(f"Error converting image {image_path} to base64: {e}")
            return None

    def get_image_info(self, image_path: str) -> Optional[Dict]:
        """
        Dobija informacije o slici.
        
        Args:
            image_path: Putanja do slike
            
        Returns:
            Dictionary sa informacijama o slici ili None ako ne uspe
        """
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
            print(f"Error getting image info for {image_path}: {e}")
            return None

