# Plan za Lokalni TTS u locAI

## Pregled
Trenutno koristimo Edge TTS koji je online servis. Potrebno je zameniti sa potpuno lokalnim TTS rešenjem.

---

## Opcije za Lokalni TTS

### 1. **Coqui TTS** (PREPORUČENO) ⭐
**Prednosti:**
- Najbolji kvalitet zvuka (neural TTS)
- Potpuno lokalno (bez interneta)
- Podržava više jezika (uključujući srpski)
- Aktivno održavan
- Lako se integriše u Python

**Nedostaci:**
- Veći modeli (100-500MB po glasu)
- Sporiji od drugih opcija
- Zahteva GPU za najbolje performanse (ali radi i na CPU)

**Instalacija:**
```bash
pip install TTS
```

**Primer korišćenja:**
```python
from TTS.api import TTS

# Inicijalizacija
tts = TTS("tts_models/en/ljspeech/tacotron2-DDC", gpu=False)

# Generisanje govora
tts.tts_to_file("Hello, this is locAI", file_path="output.wav")
```

**Dostupni modeli:**
- Engleski: `tts_models/en/ljspeech/tacotron2-DDC`
- Višejezični: `tts_models/multilingual/multi-dataset/your_tts`
- Srpski: Treba proveriti dostupnost

---

### 2. **piper-tts** (ALTERNATIVA)
**Prednosti:**
- Brz (optimizovan za CPU)
- Mali modeli (10-50MB)
- Dobar kvalitet
- Jednostavan za korišćenje
- Podržava više jezika

**Nedostaci:**
- Manje opcija za prilagođavanje
- Možda slabiji kvalitet od Coqui TTS

**Instalacija:**
```bash
pip install piper-tts
# Ili preko piper-phonemize
```

**Primer:**
```python
from piper import PiperVoice

voice = PiperVoice.load("en_US-lessac-medium")
voice.synthesize("Hello", output_file="output.wav")
```

---

### 3. **pyttsx3** (SISTEMSKI)
**Prednosti:**
- Veoma brz
- Nema dodatnih modela (koristi sistemske)
- Jednostavan

**Nedostaci:**
- Loš kvalitet (robotičan zvuk)
- Zavisi od OS-a (Windows SAPI, Linux espeak, macOS say)
- Ograničene opcije

**Instalacija:**
```bash
pip install pyttsx3
```

**Primer:**
```python
import pyttsx3
engine = pyttsx3.init()
engine.say("Hello")
engine.runAndWait()
```

---

## Preporuka za locAI

### **Coqui TTS** je najbolji izbor jer:
1. ✅ Najbolji kvalitet zvuka
2. ✅ Potpuno lokalno
3. ✅ Podržava više jezika
4. ✅ Aktivno održavan projekat
5. ✅ Lako se integriše

### Plan implementacije:

#### Faza 1: Osnovna integracija
1. Zameniti `edge_tts` sa `TTS` (Coqui)
2. Kreirati novi `TTSEngine` koji koristi Coqui TTS
3. Dodati opciju za preuzimanje modela (prvi put)
4. Implementirati osnovne funkcije (speak, stop, pause)

#### Faza 2: UI integracija
1. Dodati TTS toggle u chat widget
2. Dodati opcije za glas u Settings
3. Dodati indikator tokom generisanja
4. Opcija za auto-play AI odgovora

#### Faza 3: Optimizacija
1. Cache modela (ne učitavati svaki put)
2. Streaming TTS (ne čekati ceo tekst)
3. Background thread za TTS (ne blokirati UI)
4. Opcija za brzinu/pitch/volume

#### Faza 4: Napredne opcije
1. Višejezična podrška
2. Različiti glasovi
3. SSML podrška (ako je dostupno)
4. Export u audio fajl

---

## Tehnički detalji

### Struktura fajlova:
```
lokai/
  core/
    tts_engine.py          # Glavni TTS engine (Coqui TTS)
  utils/
    tts_manager.py         # Manager za TTS modele (download, cache)
  config/
    default_config.json    # TTS settings
```

### Config opcije:
```json
{
  "tts": {
    "enabled": true,
    "engine": "coqui",  // "coqui" | "piper" | "pyttsx3"
    "model": "tts_models/en/ljspeech/tacotron2-DDC",
    "voice": "default",
    "speed": 1.0,
    "pitch": 0,
    "volume": 1.0,
    "auto_play": false,
    "model_cache_path": "~/.lokai/tts_models"
  }
}
```

### Dependencies:
```txt
# requirements.txt
TTS>=0.20.0  # Coqui TTS
# ili
piper-tts>=1.0.0  # Piper TTS
```

---

## Migracija sa Edge TTS

1. **Zadržati isti API** - `TTSEngine` klasa sa istim metodama
2. **Zameniti implementaciju** - umesto `edge_tts.Communicate` koristiti `TTS.api.TTS`
3. **Dodati model download** - prvi put kada se koristi
4. **Testirati** - proveriti kvalitet i performanse

---

## Testiranje

1. Test sa kratkim tekstom (< 100 karaktera)
2. Test sa dugim tekstom (> 1000 karaktera)
3. Test sa različitim jezicima
4. Test performansi (CPU vs GPU)
5. Test sa različitim glasovima

---

## Alternativni pristup: Hibridni

Moguće je implementirati hibridni pristup:
- **Offline mode**: Coqui TTS (kada nema interneta)
- **Online mode**: Edge TTS (kada ima interneta, opciono)

Korisnik bira u Settings da li želi lokalni ili online TTS.

---

## Zaključak

**Preporuka: Coqui TTS** za najbolji kvalitet i potpunu lokalnost.

**Plan implementacije:**
1. Zameniti `tts_engine.py` sa Coqui TTS implementacijom
2. Dodati model downloader
3. Integrisati u UI
4. Testirati i optimizovati

**Vreme implementacije:** ~2-3 sata za osnovnu verziju

