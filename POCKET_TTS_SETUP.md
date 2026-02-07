# Pocket TTS Setup Guide

Pocket TTS je dodat u lokai aplikaciju kao alternativa Kokoro-82M TTS engine-u, sa podrškom za voice cloning.

## Instalacija

```bash
pip install pocket-tts scipy
```

**NAPOMENA:** Pocket TTS zahteva PyTorch 2.5+. Ako koristiš stariju verziju, ažuriraj PyTorch.

## Osnovne karakteristike

- **CPU-optimizovan**: Radi brzo na CPU (~2-6x real-time)
- **Nizak latency**: ~200ms za prvi audio chunk
- **Voice cloning**: Kloniranje glasova sa lokalnim audio fajlovima
- **Mala memorija**: ~100M parametara
- **Samo engleski**: Trenutno podržava samo engleski jezik

## Dostupni glasovi (ugrađeni)

- `alba` - Ženski glas
- `marius` - Muški glas
- `javert` - Muški glas
- `jean` - Muški glas
- `fantine` - Ženski glas
- `cosette` - Ženski glas
- `eponine` - Ženski glas
- `azelma` - Ženski glas

## Voice Cloning Setup

### Korak 1: Hugging Face Token

Za korišćenje voice cloning-a potreban je Hugging Face token sa dozvolom za gated repos:

1. Idi na: https://huggingface.co/settings/tokens
2. Kreiraj novi token ili ažuriraj postojeći
3. Uključi opciju: **"Read access to contents of all public gated repos you can access"**
4. Kopiraj token

### Korak 2: Prihvati uslove

1. Idi na: https://huggingface.co/kyutai/pocket-tts
2. Klikni **"Agree and access repository"**

### Korak 3: Uloguj se

```bash
hf auth login
```

Ili:

```bash
uvx hf auth login
```

Zalepi token kada se zatraži.

### Korak 4: Preuzmi model sa voice cloning-om

Model se automatski preuzima pri prvom pokretanju voice cloning-a. Ako želiš da ga preuzimaš ručno:

```bash
python -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='kyutai/pocket-tts', filename='tts_b6369a24.safetensors')"
```

## Korišćenje u lokai aplikaciji

### 1. Odabir TTS Engine-a

1. Otvori Settings (File > Preferences ili Ctrl+,)
2. Idi na **TTS** tab
3. U dropdown-u **"TTS Engine"** odaberi **"Pocket TTS"**
4. Odaberi glas iz dropdown-a (alba, marius, itd.)
5. Klikni **OK**

### 2. Korišćenje ugrađenih glasova

Nakon odabira Pocket TTS engine-a, glasovi se prikazuju u Status Panel-u (gore desno).

- Odaberi glas iz dropdown-a
- Klikni TTS Play button da reprodukuješ odgovor

### 3. Korišćenje Voice Cloning-a

1. Otvori Settings > TTS tab
2. Odaberi **"Pocket TTS"** engine
3. U sekciji **"Voice Cloning"**:
   - Uključi **"Enable Voice Cloning"** checkbox
   - Klikni **"Browse..."** i odaberi audio fajl (WAV, MP3, OGG, FLAC)
   - Fajl će biti automatski konvertovan u ispravan format
4. Klikni **OK**

Nakon toga, u Status Panel-u (gore desno) voice dropdown-u će se pojaviti opcija **"Clone Voice"**:
- Odaberi **"Clone Voice"** iz dropdown-a da koristiš klonirani glas
- Odaberi neki drugi glas (alba, marius, itd.) da koristiš ugrađeni glas

## Napomene

### Audio fajl za voice cloning

- **Format**: WAV, MP3, OGG, FLAC
- **Dužina**: 3-30 sekundi preporučeno
- **Kvalitet**: Što čistiji audio, bolji rezultat
- **Sadržaj**: Samo jedan govornik, bez pozadinskog zvuka

### Performanse

- **CPU**: ~2-6x real-time generisanje (zavisi od CPU-a)
- **GPU**: Ne daje značajno ubrzanje zbog male veličine modela
- **Memorija**: ~500MB RAM

### Ograničenja

- **Jezik**: Samo engleski (za sada)
- **Speed control**: Ne podržava kontrolu brzine (speed setting se ignoriše)

## Troubleshooting

### Voice cloning ne radi

**Problem**: "We could not download the weights for the model with voice cloning"

**Rešenje**:
1. Proveri da li si prihvatio uslove na: https://huggingface.co/kyutai/pocket-tts
2. Proveri da li si ulogovan: `hf whoami`
3. Proveri da li token ima dozvolu za gated repos
4. Ponovo se uloguj: `hf auth login`

### Audio fajl ne radi

**Problem**: "unknown format: 3" ili greška pri učitavanju

**Rešenje**: Audio fajl je u float32 formatu. Aplikacija automatski konvertuje u PCM int16, ali ako problem persista, konvertuj ručno:

```python
import scipy.io.wavfile as wav
import numpy as np

sr, data = wav.read('input.wav')
data_int16 = (data * 32767).astype(np.int16) if data.dtype == np.float32 else data
wav.write('output_pcm.wav', sr, data_int16)
```

### Model se ne učitava

**Problem**: Model se ne preuzima ili učitava

**Rešenje**:
1. Proveri HF_HOME i HF_HUB_CACHE environment varijable
2. Ručno preuzmi model (vidi Korak 4 iznad)
3. Proveri da li imaš dovoljno prostora na disku (~500MB)

## Reference

- [Pocket TTS Hugging Face](https://huggingface.co/kyutai/pocket-tts)
- [Pocket TTS GitHub](https://github.com/kyutai-labs/pocket-tts)
- [Dokumentacija](https://huggingface.co/kyutai/pocket-tts)
