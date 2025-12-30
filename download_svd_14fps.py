"""
Skripta za preuzimanje Stable Video Diffusion (SVD) modela - 14 frame-ova.
Model će biti preuzet na Q particiju.
"""

import sys
import os
from pathlib import Path

# Set Hugging Face cache environment variables BEFORE importing anything
# Koristi Q: particiju kao u main.py
if os.path.exists("Q:\\"):
    hf_cache = "Q:\\huggingface_cache"
    os.environ.setdefault("DIFFUSERS_CACHE", os.path.join(hf_cache, "diffusers"))
    os.environ.setdefault("HF_DIFFUSERS_CACHE", os.path.join(hf_cache, "diffusers"))
    os.environ.setdefault("HF_HOME", hf_cache)
    os.environ.setdefault("TRANSFORMERS_CACHE", hf_cache)
    os.environ.setdefault("HF_DATASETS_CACHE", hf_cache)
    os.environ.setdefault("HF_HUB_CACHE", hf_cache)
    
    print(f"[OK] Cache ce biti na: {hf_cache}")
    print(f"   Diffusers cache: {os.environ['DIFFUSERS_CACHE']}")
else:
    print("[WARNING] Q: particija nije dostupna! Koristit ce se default lokacija.")
    print("   Modeli ce biti u: ~/.cache/huggingface/")

# Provjeri da li su potrebne biblioteke instalirane
try:
    import torch
    from diffusers import StableVideoDiffusionPipeline
    print(f"[OK] PyTorch verzija: {torch.__version__}")
    print(f"[OK] CUDA dostupna: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
except ImportError as e:
    print(f"[ERROR] Greska: {e}")
    print("\nMolimo instalirajte potrebne biblioteke:")
    print("  pip install diffusers transformers torch")
    sys.exit(1)

def download_svd_model():
    """Preuzmi SVD model (14 frame-ova)."""
    model_name = "stabilityai/stable-video-diffusion-img2vid"
    
    print(f"\n{'='*60}")
    print(f"Preuzimanje modela: {model_name}")
    print(f"Variant: fp16 (float16)")
    print(f"Frame-ovi: 14")
    print(f"{'='*60}\n")
    
    try:
        # Kreiraj direktorije ako ne postoje
        cache_path = Path(os.environ.get("DIFFUSERS_CACHE", "Q:\\huggingface_cache\\diffusers"))
        cache_path.mkdir(parents=True, exist_ok=True)
        
        print(f"[DOWNLOAD] Preuzimanje modela...")
        print(f"   Ovo moze potrajati nekoliko minuta (model je ~5-6 GB)")
        print(f"   Model ce biti spremljen na: {cache_path}\n")
        
        # Preuzmi model
        pipeline = StableVideoDiffusionPipeline.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            variant="fp16",
            cache_dir=cache_path,
        )
        
        print(f"\n[OK] Model uspjesno preuzet!")
        print(f"   Lokacija: {cache_path}")
        
        # Provjeri veličinu
        model_size = 0
        if cache_path.exists():
            for file_path in cache_path.rglob("*"):
                if file_path.is_file():
                    model_size += file_path.stat().st_size
        
        print(f"   Veličina: {model_size / (1024**3):.2f} GB")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Greska pri preuzimanju: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Glavna funkcija."""
    print("="*60)
    print("Stable Video Diffusion (SVD) Model Downloader")
    print("14 frame-ova verzija")
    print("="*60)
    
    # Preuzmi model
    success = download_svd_model()
    
    if success:
        print("\n" + "="*60)
        print("[OK] Preuzimanje zavrseno!")
        print("="*60)
        print("\nModel je spreman za koristenje.")
        print("Mozete ga koristiti u vasoj aplikaciji.")
    else:
        print("\n" + "="*60)
        print("[ERROR] Preuzimanje nije uspjelo.")
        print("="*60)
        sys.exit(1)

if __name__ == "__main__":
    main()

