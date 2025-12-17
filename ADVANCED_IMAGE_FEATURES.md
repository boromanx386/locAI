# Napredne funkcionalnosti za generisanje slika

Vaš AI asistent sada podržava napredne funkcionalnosti za generisanje slika:

## 🎯 Dostupni Modeli

### Osnovni Modeli
- **SDXL Base (1024x1024)** - Najbolji kvalitet, veća memorija (~6GB)
- **Juggernaut XL (832x1216)** - Fotorealistični model za logo dizajn, treniran na 200+ vektorskih slika
- **SD 2.1 Base (512x512)** - Brži, manje memorije (~5GB)  
- **SD 1.5 (512x512)** - Najbrži, najmanje memorije (~4GB)

## 🎨 LoRA modeli

LoRA (Low-Rank Adaptation) modeli dodaju specifične stilove i karakteristike:

### Dostupni LoRA modeli:
- **ArtGerm Style** - Umetnički stil
- **Fashion Photography** - Moda fotografija  
- **Logo Design** - Dizajn logotipa
- **Anime Style** - Anime/manga stil
- **Realistic Photography** - Realistična fotografija

### Kako koristiti:
1. Kliknite "■ ADVANCED" dugme
2. U LoRA sekciji izaberite model
3. Podesite snagu (0-100%)
4. Kliknite "Učitaj LoRA"
5. Generiši sliku - LoRA će se automatski primeniti

## 🔤 Textual Inversion (TI) Embeddings

TI embeddings omogućavaju učenje specifičnih stilova iz vaših slika:

### Dostupni Embeddings:
- **My Art Style** - Vaš umetnički stil
- **Logo Style** - Stil za logotipe
- **Portrait Style** - Stil za portrete

### Kako koristiti:
1. Kliknite "■ ADVANCED" dugme
2. U TI Embeddings sekciji izaberite embedding
3. Kliknite "Učitaj Embedding"
4. Generiši sliku - embedding će se automatski primeniti

## 🔍 Upscaling (Povećanje rezolucije)

Upscaling poboljšava kvalitet postojećih slika:

### Dostupni Upscaler modeli:
- **RealESRGAN 4x** - Opšti upscaling 4x (dobar za fotografije)
- **RealESRGAN Anime** - Anime/manga upscaling 4x
- **SD Upscaler** - SD upscaler (najbolji za AI generisane slike)

### Kako koristiti:
1. Kliknite "■ ADVANCED" dugme
2. U Upscaling sekciji izaberite upscaler
3. Kliknite "Učitaj Upscaler"
4. Generiši sliku
5. Kliknite "■ UPSCALE" dugme za upscaling poslednje slike

## 📁 Struktura fajlova

Svi modeli se čuvaju na Q: particiji za uštedu prostora:

```
Q:\huggingface_cache\
├── loras\
│   ├── artgerm.safetensors (~200 MB)
│   ├── fashion.safetensors (~200 MB)
│   ├── logo.safetensors (~200 MB)
│   ├── anime.safetensors (~200 MB)
│   └── realistic.safetensors (~200 MB)
├── embeddings\
│   ├── my_art_style.bin (~5 MB)
│   ├── logo_style.bin (~5 MB)
│   └── portrait_style.bin (~5 MB)
├── models--stabilityai--stable-diffusion-xl-base-1.0\ (~6.9 GB)
├── models--stabilityai--stable-diffusion-2-1-base\ (~5.2 GB)
├── models--runwayml--stable-diffusion-v1-5\ (~4.3 GB)
├── models--stabilityai--stable-diffusion-x4-upscaler\ (~4.1 GB)
├── models--xinntao--realesrgan-x4plus\ (~67 MB)
└── models--xinntao--realesrgan-x4plus-anime\ (~67 MB)
```

**Ukupno na Q: particiji: ~21.6 GB**

## 🚀 Instalacija dependencies

### Osnovne funkcionalnosti (uvek dostupne):
- SDXL, SD 2.1, SD 1.5 generisanje slika
- SD Upscaler upscaling

### Potrebne dependencies za LoRA funkcionalnost:

**Opcija 1: Automatska instalacija**
```bash
# Pokrenite batch fajl
install_peft.bat
```

**Opcija 2: Ručna instalacija**
```bash
pip install peft>=0.7.0
```

### Opcione funkcionalnosti (za Real-ESRGAN upscaling):

**Opcija 1: Automatska instalacija**
```bash
# Pokrenite batch fajl
install_optional_dependencies.bat
```

**Opcija 2: Ručna instalacija**
```bash
pip install opencv-python>=4.8.0
pip install realesrgan>=0.3.0
pip install basicsr>=1.4.2
```

**Napomena**: 
- PEFT je potreban za LoRA funkcionalnost
- Real-ESRGAN dependencies su opcioni
- Ako ne instalirate opcione dependencies, Real-ESRGAN upscaling neće biti dostupan

## 💡 Saveti za korišćenje

### Za logotipe:
1. Učitajte "Logo Design" LoRA
2. Učitajte "Logo Style" embedding
3. Koristite prompt: "logo_style logo design, minimalist, modern, corporate identity"
4. Nakon generisanja, upscale-ujte sa SD Upscaler

### Za umetnost:
1. Učitajte "ArtGerm Style" LoRA
2. Koristite prompt: "artgerm portrait, detailed, high quality"
3. Upscale-ujte sa RealESRGAN 4x

### Za anime:
1. Učitajte "Anime Style" LoRA
2. Koristite prompt: "anime character, detailed, high quality"
3. Upscale-ujte sa RealESRGAN Anime

## ⚠️ Napomene

- LoRA i TI modeli se učitavaju u memoriju i ostaju aktivni dok se ne uklone
- Upscaler modeli takođe zauzimaju memoriju
- Za bolje performanse, učitajte samo potrebne modele
- Koristite "Ukloni sve" dugmad za čišćenje memorije

## 🔧 Troubleshooting

### LoRA se ne učitava:
- Proverite da li fajl postoji u `models/loras/` direktorijumu
- Proverite da li je fajl u .safetensors formatu

### TI Embedding se ne učitava:
- Proverite da li fajl postoji u `models/embeddings/` direktorijumu
- Proverite da li je fajl u .bin formatu

### Upscaler se ne učitava:
- Instalirajte potrebne dependencies
- Proverite da li imate dovoljno memorije

### Greška "Model not loaded":
- Učitajte osnovni image generation model pre LoRA/TI modela
- Proverite da li je CUDA dostupna
