# Pocket TTS Test Checklist

## Pre testiranja

- [ ] Aplikacija lokai je pokrenuta
- [ ] Hugging Face token je postavljen (za voice cloning)
- [ ] Prihvaćeni uslovi na https://huggingface.co/kyutai/pocket-tts

## Test 1: Kokoro TTS (Provera da stari TTS radi)

- [ ] Otvori Settings (Ctrl+,)
- [ ] Idi na TTS tab
- [ ] Proveri da je **TTS Engine** postavljen na **"Kokoro-82M"**
- [ ] Odaberi jezik (npr. American English)
- [ ] Odaberi glas (npr. af_heart)
- [ ] Klikni OK
- [ ] Napiši poruku i dobij odgovor
- [ ] Klikni TTS Play button u Status Panel-u
- [ ] Audio bi trebalo da se reprodukuje sa Kokoro glasom

## Test 2: Pocket TTS sa ugrađenim glasovima

- [ ] Otvori Settings (Ctrl+,)
- [ ] Idi na TTS tab
- [ ] Promeni **TTS Engine** na **"Pocket TTS"**
- [ ] Language dropdown bi trebalo da bude disabled (Pocket TTS samo engleski)
- [ ] Voice dropdown bi trebalo da prikaže Pocket TTS glasove: alba, marius, itd.
- [ ] Odaberi glas (npr. alba)
- [ ] Klikni OK
- [ ] Napiši poruku i dobij odgovor
- [ ] Klikni TTS Play button u Status Panel-u
- [ ] Audio bi trebalo da se reprodukuje sa Pocket TTS glasom

## Test 3: Promena glasa u Status Panel-u

- [ ] U Status Panel-u (gore desno), odaberi drugi glas iz dropdown-a (npr. marius)
- [ ] Klikni TTS Play button
- [ ] Audio bi trebalo da se reprodukuje sa novim glasom

## Test 4: Voice Cloning sa lokalnim fajlom

- [ ] Pripremi audio fajl (WAV, MP3, OGG) sa jasnim govorom (3-30 sekundi)
- [ ] Otvori Settings (Ctrl+,)
- [ ] Idi na TTS tab
- [ ] TTS Engine bi trebalo da bude **"Pocket TTS"**
- [ ] U sekciji **"Voice Cloning"**:
  - [ ] Uključi checkbox **"Enable Voice Cloning"**
  - [ ] Klikni **"Browse..."**
  - [ ] Odaberi audio fajl
  - [ ] Putanja do fajla bi trebalo da se pojavi u text edit polju
- [ ] Klikni OK
- [ ] U Status Panel-u voice dropdown-u bi trebalo da se pojavi **"Clone Voice"** opcija
- [ ] Odaberi **"Clone Voice"** iz dropdown-a
- [ ] Napiši poruku i dobij odgovor
- [ ] Klikni TTS Play button
- [ ] Audio bi trebalo da se reprodukuje sa kloniranim glasom (sličan originalnom fajlu)

## Test 5: Prebacivanje između kloniranog i ugrađenog glasa

- [ ] U Status Panel-u voice dropdown-u, odaberi neki ugrađeni glas (npr. marius)
- [ ] Klikni TTS Play button
- [ ] Audio bi trebalo da se reprodukuje sa odabranim ugrađenim glasom (ne kloniranim)
- [ ] Ponovo odaberi **"Clone Voice"** iz dropdown-a
- [ ] Klikni TTS Play button
- [ ] Audio bi trebalo da se reprodukuje sa kloniranim glasom

## Test 6: Prebacivanje između engine-a

- [ ] Otvori Settings (Ctrl+,)
- [ ] Promeni TTS Engine na **"Kokoro-82M"**
- [ ] Voice Cloning sekcija bi trebalo da bude sakrivena
- [ ] Language dropdown bi trebalo da bude enabled
- [ ] Voice dropdown bi trebalo da prikaže Kokoro glasove
- [ ] Klikni OK
- [ ] U Status Panel-u voice dropdown-u bi trebalo da prikaže samo Kokoro glasove (bez "Clone Voice")
- [ ] Klikni TTS Play button
- [ ] Audio bi trebalo da se reprodukuje sa Kokoro glasom

## Test 7: Perzistencija konfiguracije

- [ ] Zatvori aplikaciju
- [ ] Ponovo pokreni aplikaciju
- [ ] Proveri da su TTS podešavanja sačuvana (engine, glas, voice cloning)
- [ ] Testirati TTS Play button ponovo

## Očekivani rezultati

- Kokoro TTS radi kao pre (backward compatibility)
- Pocket TTS radi sa ugrađenim glasovima
- Voice cloning radi sa lokalnim audio fajlovima
- "Clone Voice" opcija se prikazuje u dropdown-u kada je voice cloning enabled
- Prebacivanje između engine-a radi
- Konfiguracija se čuva i učitava

## Poznati problemi

- Pocket TTS podržava samo engleski jezik
- Speed control ne radi za Pocket TTS
- Audio fajl mora biti u ispravnom formatu (aplikacija automatski konvertuje)
