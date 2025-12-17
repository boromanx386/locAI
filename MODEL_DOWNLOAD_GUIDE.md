# 📥 Vodič za preuzimanje modela na Q: particiju

## 🎯 Pregled veličina modela

| Model | Veličina | Opis |
|-------|----------|------|
| **SDXL Base** | 6.9 GB | Najbolji kvalitet, 1024x1024 |
| **SD 2.1 Base** | 5.2 GB | Brži, 512x512 |
| **SD 1.5** | 4.3 GB | Najbrži, 512x512 |
| **SD Upscaler** | 4.1 GB | Upscaling AI slika |
| **Real-ESRGAN** | 67 MB | Upscaling fotografija |
| **LoRA modeli** | ~1 GB | Stilovi (5x ~200 MB) |
| **TI Embeddings** | ~15 MB | Specifični stilovi (3x ~5 MB) |
| **UKUPNO** | **~21.6 GB** | Svi modeli na Q: particiji |

## 🚀 Automatsko preuzimanje

### Opcija 1: Batch fajl (preporučeno)
```bash
# Pokrenite batch fajl
download_models_to_q.bat
```

### Opcija 2: Ručno preuzimanje
```bash
# Postavite environment varijable
set HF_HOME=Q:\huggingface_cache
set TRANSFORMERS_CACHE=Q:\huggingface_cache
set DIFFUSERS_CACHE=Q:\huggingface_cache\diffusers

# Preuzmite modele
python -c "from diffusers import StableDiffusionXLPipeline; StableDiffusionXLPipeline.from_pretrained('stabilityai/stable-diffusion-xl-base-1.0')"
python -c "from diffusers import StableDiffusionPipeline; StableDiffusionPipeline.from_pretrained('stabilityai/stable-diffusion-2-1-base')"
python -c "from diffusers import StableDiffusionPipeline; StableDiffusionPipeline.from_pretrained('runwayml/stable-diffusion-v1-5')"
```

## 📁 Struktura direktorijuma

```
Q:\huggingface_cache\
├── models--stabilityai--stable-diffusion-xl-base-1.0\
├── models--stabilityai--stable-diffusion-2-1-base\
├── models--runwayml--stable-diffusion-v1-5\
├── models--stabilityai--stable-diffusion-x4-upscaler\
├── models--xinntao--realesrgan-x4plus\
├── loras\                    # LoRA modeli (ručno)
└── embeddings\               # TI embeddings (ručno)
```

## 🔧 Ručno preuzimanje LoRA modela

LoRA modeli se moraju preuzeti ručno i postaviti u `Q:\huggingface_cache\loras\`:

### Preporučeni LoRA modeli:
1. **ArtGerm Style** - [Preuzmi sa Civitai](https://civitai.com)
2. **Fashion Photography** - [Preuzmi sa Civitai](https://civitai.com)
3. **Logo Design** - [Preuzmi sa Civitai](https://civitai.com)
4. **Anime Style** - [Preuzmi sa Civitai](https://civitai.com)
5. **Realistic Photography** - [Preuzmi sa Civitai](https://civitai.com)

### Instrukcije:
1. Idite na [Civitai.com](https://civitai.com)
2. Pretražite "LoRA" + stil koji želite
3. Preuzmite .safetensors fajl
4. Preimenujte fajl prema tabeli ispod
5. Postavite u `Q:\huggingface_cache\loras\`

| Ime fajla | Opis |
|-----------|------|
| `artgerm.safetensors` | ArtGerm umetnički stil |
| `fashion.safetensors` | Moda fotografija |
| `logo.safetensors` | Dizajn logotipa |
| `anime.safetensors` | Anime/manga stil |
| `realistic.safetensors` | Realistična fotografija |

## 🔤 Ručno preuzimanje TI Embeddings

TI embeddings se moraju preuzeti ručno i postaviti u `Q:\huggingface_cache\embeddings\`:

### Preporučeni TI Embeddings:
1. **My Art Style** - Vaš umetnički stil
2. **Logo Style** - Stil za logotipe  
3. **Portrait Style** - Stil za portrete

### Instrukcije:
1. Idite na [Hugging Face](https://huggingface.co) ili [Civitai](https://civitai.com)
2. Pretražite "textual inversion" ili "embedding"
3. Preuzmite .bin fajl
4. Preimenujte fajl prema tabeli ispod
5. Postavite u `Q:\huggingface_cache\embeddings\`

| Ime fajla | Opis |
|-----------|------|
| `my_art_style.bin` | Vaš umetnički stil |
| `logo_style.bin` | Stil za logotipe |
| `portrait_style.bin` | Stil za portrete |

## ⚡ Brzina preuzimanja

- **Stable Diffusion modeli**: 10-30 minuta (zavisi od brzine interneta)
- **Upscaler modeli**: 5-10 minuta
- **LoRA modeli**: 1-5 minuta po modelu
- **TI Embeddings**: 30 sekundi po embedding-u

## 💾 Proverite prostor na Q: particiji

Pre preuzimanja, proverite da li imate dovoljno prostora:

```bash
# Windows Command Prompt
dir Q:\

# Ili PowerShell
Get-WmiObject -Class Win32_LogicalDisk | Where-Object {$_.DeviceID -eq "Q:"} | Select-Object Size,FreeSpace
```

**Potrebno**: Najmanje 25 GB slobodnog prostora na Q: particiji.

## 🔍 Proverite da li su modeli uspešno preuzeti

```bash
# Proverite strukturu direktorijuma
dir Q:\huggingface_cache /s

# Ili pokrenite aplikaciju i proverite log-ove
python ai_assistant.py
```

## ❗ Troubleshooting

### "Not enough space" greška:
- Oslobodite prostor na Q: particiji
- Ili promenite putanje u kodu na drugu particiju

### "Model not found" greška:
- Proverite da li su fajlovi u ispravnim direktorijumima
- Proverite imena fajlova (mora biti tačno kako je navedeno)

### "Permission denied" greška:
- Pokrenite kao administrator
- Proverite da li Q: particija nije read-only

## 🎉 Nakon preuzimanja

1. Pokrenite `ai_assistant.py`
2. Kliknite "■ ADVANCED" dugme
3. Učitajte željene LoRA i TI modele
4. Generiši slike sa novim stilovima!
