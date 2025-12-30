"""
Skripta za preuzimanje Stable Video Diffusion (SVD) modela na Q particiju.
Koristi istu konfiguraciju cache-a kao glavna aplikacija.
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
    
    print(f"✅ Cache će biti na: {hf_cache}")
    print(f"   Diffusers cache: {os.environ['DIFFUSERS_CACHE']}")
else:
    print("⚠️  Q: particija nije dostupna! Koristit će se default lokacija.")
    print("   Modeli će biti u: ~/.cache/huggingface/")

# Provjeri da li su potrebne biblioteke instalirane
try:
    import torch
    from diffusers import StableVideoDiffusionPipeline
    print(f"✅ PyTorch verzija: {torch.__version__}")
    print(f"✅ CUDA dostupna: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
except ImportError as e:
    print(f"❌ Greška: {e}")
    print("\nMolimo instalirajte potrebne biblioteke:")
    print("  pip install diffusers transformers torch")
    sys.exit(1)

def download_model(model_name: str, variant: str = "fp16"):
    """
    Preuzmi SVD model.
    
    Args:
        model_name: Ime modela na Hugging Face
        variant: Varijanta modela (fp16 ili fp32)
    """
    print(f"\n{'='*60}")
    print(f"Preuzimanje modela: {model_name}")
    print(f"Variant: {variant}")
    print(f"{'='*60}\n")
    
    try:
        # Kreiraj direktorije ako ne postoje
        cache_path = Path(os.environ.get("DIFFUSERS_CACHE", "Q:\\huggingface_cache\\diffusers"))
        cache_path.mkdir(parents=True, exist_ok=True)
        
        print(f"📥 Preuzimanje modela...")
        print(f"   Ovo može potrajati nekoliko minuta (model je ~5-6 GB)\n")
        
        # Preuzmi model
        pipeline = StableVideoDiffusionPipeline.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            variant=variant,
            cache_dir=cache_path,
        )
        
        print(f"\n✅ Model uspješno preuzet!")
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
        print(f"\n❌ Greška pri preuzimanju: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Glavna funkcija."""
    print("="*60)
    print("Stable Video Diffusion (SVD) Model Downloader")
    print("="*60)
    
    # Odaberi model
    print("\nDostupni modeli:")
    print("1. SVD (14 frame-ova) - stabilityai/stable-video-diffusion-img2vid")
    print("2. SVD-XT (25 frame-ova) - stabilityai/stable-video-diffusion-img2vid-xt [PREPORUČENO]")
    
    choice = input("\nOdaberite model (1 ili 2, default 2): ").strip()
    
    if choice == "1":
        model_name = "stabilityai/stable-video-diffusion-img2vid"
        print("\nOdabran: SVD (14 frame-ova)")
    else:
        model_name = "stabilityai/stable-video-diffusion-img2vid-xt"
        print("\nOdabran: SVD-XT (25 frame-ova)")
    
    # Preuzmi model
    success = download_model(model_name, variant="fp16")
    
    if success:
        print("\n" + "="*60)
        print("✅ Preuzimanje završeno!")
        print("="*60)
        print("\nModel je spreman za korištenje.")
        print("Možete ga koristiti u vašoj aplikaciji.")
    else:
        print("\n" + "="*60)
        print("❌ Preuzimanje nije uspjelo.")
        print("="*60)
        sys.exit(1)

if __name__ == "__main__":
    main()

