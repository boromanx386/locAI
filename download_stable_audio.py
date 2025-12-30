"""
Skripta za preuzimanje Stable Audio Open 1.0 modela na Q particiju.
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
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    print(f"[OK] Cache ce biti na: {hf_cache}")
    print(f"   Diffusers cache: {os.environ['DIFFUSERS_CACHE']}")
else:
    print("[WARN] Q: particija nije dostupna! Koristit ce se default lokacija.")
    print("   Modeli će biti u: ~/.cache/huggingface/")

# Provjeri da li su potrebne biblioteke instalirane
try:
    import torch
    from diffusers import StableAudioPipeline
    from huggingface_hub import HfFolder, login

    print(f"[OK] PyTorch verzija: {torch.__version__}")
    print(f"[OK] CUDA dostupna: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
        )

    # Proveri da li je token postavljen
    token = None
    try:
        token = HfFolder.get_token()
        if token:
            print(f"[OK] Hugging Face token je postavljen")
        else:
            print(f"[WARN] Hugging Face token NIJE postavljen!")
    except:
        print(f"[WARN] Nije moguce proveriti token")

    # Proveri environment varijablu za token
    if not token:
        token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
        if token:
            print(f"[OK] Token pronadjen u environment varijabli")
            try:
                login(token=token, add_to_git_credential=False)
                print(f"[OK] Ulogovan koristeci environment token")
            except Exception as e:
                print(f"[WARN] Greska pri login-u sa environment token: {e}")
                token = None
except ImportError as e:
    print(f"[ERROR] Greska: {e}")
    print("\nMolimo instalirajte potrebne biblioteke:")
    print("  pip install diffusers transformers torch torchaudio")
    print("\nIli ažurirajte diffusers na najnoviju verziju:")
    print("  pip install -U diffusers")
    sys.exit(1)


def download_model(model_name: str):
    """
    Preuzmi Stable Audio Open model.

    Args:
        model_name: Ime modela na Hugging Face
    """
    print(f"\n{'='*60}")
    print(f"Preuzimanje modela: {model_name}")
    print(f"{'='*60}\n")

    try:
        # Kreiraj direktorije ako ne postoje
        cache_path = Path(
            os.environ.get("DIFFUSERS_CACHE", "Q:\\huggingface_cache\\diffusers")
        )
        cache_path.mkdir(parents=True, exist_ok=True)

        print(f"[DOWNLOAD] Preuzimanje modela...")
        print(f"   Ovo moze potrajati nekoliko minuta")
        print(f"   Ukupna velicina: ~5.5-6 GB (model + VAE + komponente)\n")
        print(f"   [WARN] VAZNO: Model zahteva prihvatanje licence!")
        print(f"      Ako dobijete grešku, prihvatite licencu na:")
        print(f"      https://huggingface.co/stabilityai/stable-audio-open-1.0\n")

        # Preuzmi model
        pipeline = StableAudioPipeline.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            cache_dir=cache_path,
        )

        print(f"\n[OK] Model uspesno preuzet!")
        print(f"   Lokacija: {cache_path}")

        # Provjeri veličinu
        model_size = 0
        model_files = []
        if cache_path.exists():
            # Pronađi fajlove za ovaj model
            for file_path in cache_path.rglob("*"):
                if (
                    file_path.is_file()
                    and "stable-audio-open" in str(file_path).lower()
                ):
                    size = file_path.stat().st_size
                    model_size += size
                    model_files.append(file_path)

        if model_size > 0:
            print(f"   Veličina: {model_size / (1024**3):.2f} GB")
        else:
            print(
                f"   [WARN] Nije moguce tacno izracunati velicinu (fajlovi mozda jos nisu u cache-u)"
            )

        return True

    except Exception as e:
        print(f"\n[ERROR] Greska pri preuzimanju: {e}")
        import traceback

        traceback.print_exc()

        # Ako je greška zbog autentifikacije ili licence
        error_str = str(e).lower()
        if any(
            keyword in error_str
            for keyword in [
                "authentication",
                "login",
                "gated",
                "license",
                "agreement",
                "accept",
            ]
        ):
            print("\n[INFO] Resenje:")
            print("   Model zahteva prihvatanje licence!")
            print("\n   Opcija 1 (PREPORUCENO - bez login-a):")
            print("   1. Otvorite browser i idite na:")
            print("      https://huggingface.co/stabilityai/stable-audio-open-1.0")
            print("   2. Kliknite 'Agree' da prihvatite licencu")
            print("   3. Pokrenite skriptu ponovo")
            print("\n   Opcija 2 (sa login-om):")
            print("   1. Generisite token na: https://huggingface.co/settings/tokens")
            print("      (Tip: Read token je dovoljno)")
            print("   2. Pokrenite: hf auth login")
            print("   3. Zalepite token kada se zatrazi (Right-Click za paste)")
            print(
                "   4. Prihvatite licencu na: https://huggingface.co/stabilityai/stable-audio-open-1.0"
            )
            print("   5. Pokrenite skriptu ponovo")
            print("\n   VAZNO: Morate i prihvatiti licencu I biti ulogovani!")

        return False


def main():
    """Glavna funkcija."""
    print("=" * 60)
    print("Stable Audio Open 1.0 Model Downloader")
    print("=" * 60)

    model_name = "stabilityai/stable-audio-open-1.0"

    print(f"\nModel: {model_name}")
    print(f"   - Generise audio do 47 sekundi")
    print(f"   - 44.1 kHz stereo audio")
    print(f"   - Text-to-Audio generacija")

    # Proveri token i ponudi opciju da se unese
    from huggingface_hub import HfFolder, login

    token = None
    try:
        token = HfFolder.get_token()
    except:
        pass

    if not token:
        token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")

    if not token:
        print("\n[WARN] Token nije postavljen!")
        print("   Opcije:")
        print("   1. Pokrenite: hf auth login")
        print("   2. Ili postavite environment varijablu: $env:HF_TOKEN='your_token'")
        print("   3. Ili unesite token ovde (bice sacuvan)")

        try:
            user_token = input("\nUnesite token (ili Enter za preskakanje): ").strip()
            if user_token:
                try:
                    # Pokušaj login
                    login(token=user_token, add_to_git_credential=False)
                    print("[OK] Ulogovan sa unetim tokenom")

                    # Takođe sačuvaj token u fajl za buduće korišćenje
                    try:
                        token_dir = Path.home() / ".huggingface"
                        token_dir.mkdir(exist_ok=True)
                        token_file = token_dir / "token"
                        token_file.write_text(user_token, encoding="utf-8")
                        print(f"[OK] Token sacuvan u: {token_file}")
                    except Exception as save_error:
                        print(f"[WARN] Token nije sacuvan u fajl: {save_error}")
                        print("   Ali login je uspeo, mozete nastaviti")

                    token = user_token
                except Exception as e:
                    print(f"[ERROR] Greska pri login-u: {e}")
                    print("\n[INFO] Probajte:")
                    print("   1. Proverite da li je token validan")
                    print("   2. Proverite da li ste prihvatili licencu na:")
                    print(
                        "      https://huggingface.co/stabilityai/stable-audio-open-1.0"
                    )
                    print("   3. Pokrenite: hf auth login")
        except (EOFError, KeyboardInterrupt):
            print("\n[INFO] Preskace se unos tokena...")
            print("[ERROR] Token je obavezan za ovaj model!")
            print("   Pokrenite: hf auth login")
            sys.exit(1)

    # Auto-confirm ako je pokrenuto iz terminala bez interakcije
    try:
        confirm = (
            input("\nNastaviti sa preuzimanjem? (d/n, default d): ").strip().lower()
        )
        if confirm and confirm != "d" and confirm != "da":
            print("Preuzimanje otkazano.")
            return
    except (EOFError, KeyboardInterrupt):
        # Ako nema interakcije, automatski nastavi
        print("\n[Nastavlja se automatski...]")

    # Preuzmi model
    success = download_model(model_name)

    if success:
        print("\n" + "=" * 60)
        print("[OK] Preuzimanje zavrseno!")
        print("=" * 60)
        print("\nModel je spreman za korištenje.")
        print("Možete ga koristiti u vašoj aplikaciji.")
    else:
        print("\n" + "=" * 60)
        print("[ERROR] Preuzimanje nije uspelo.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
