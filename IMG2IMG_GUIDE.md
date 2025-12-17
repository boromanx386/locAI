# Image-to-Image (img2img) Vodič

## 🎨 Šta je Image-to-Image?

Image-to-Image (img2img) je funkcionalnost koja omogućava transformaciju postojeće slike na osnovu tekstualnog opisa. Koristi ControlNet tehnologiju za precizno vođenje procesa generisanja.

## 🚀 Kako koristiti img2img:

### 1. **Upload slike**
- Kliknite na **"■ IMAGE"** dugme
- Izaberite sliku koju želite transformisati
- Slika će se pojaviti u chat-u

### 2. **Otvorite img2img opcije**
- Kliknite na **"■ IMG2IMG"** dugme
- Otvoriće se dialog sa svim opcijama

### 3. **Izaberite ControlNet tip**
- **Canny**: Edge detection - dobro za konture i oblike
- **Depth**: Depth map - dobro za 3D strukture  
- **OpenPose**: Pose detection - dobro za ljude i figure

### 4. **Postavite parametre**
- **ControlNet Strength**: 0.0-2.0 (koliko da prati originalnu sliku)
- **Prompt**: Opis kako želite da transformišete sliku
- **Negative Prompt**: Šta ne želite u rezultatu
- **Steps**: 1-100 (kvalitet generacije)
- **Guidance Scale**: 1.0-20.0 (koliko da prati prompt)
- **Seed**: 0 za random, ili fiksni broj za konzistentnost

### 5. **Generiši sliku**
- Kliknite **"Load ControlNet"** da učitate model
- Kliknite **"Generate Image"** da počnete generaciju

## 🔧 Kompatibilnost

### **Modeli koji rade sa img2img:**
- ✅ **Juggernaut XL** (preporučeno)
- ✅ **SDXL Base**
- ✅ **DynaVision XL**
- ✅ **OmnigenXL**
- ✅ **epiCRealism XL**
- ✅ **ZavyChromaXL**

### **LoRA kombinacije:**
- ✅ **MS Paint LoRA** + img2img = Smešni rezultati!
- ✅ **JuggerCine XL** + img2img = Cinematički stil
- ✅ **Cinematic Style** + img2img = Film look
- ✅ **Svi LoRA modeli** rade sa img2img

## 💡 Saveti za bolje rezultate:

### **Za Canny ControlNet:**
```
Prompt: "MSPaint portrait of a person, crude drawing style"
ControlNet Strength: 1.2-1.5
```

### **Za Depth ControlNet:**
```
Prompt: "3D rendered scene, cinematic lighting"
ControlNet Strength: 0.8-1.2
```

### **Za OpenPose ControlNet:**
```
Prompt: "person in dynamic pose, action scene"
ControlNet Strength: 1.0-1.3
```

## ⚙️ Memorija i performanse:

- **Memorija potreba**: ~8-9GB VRAM (sa ControlNet)
- **Vreme generacije**: 30-60 sekundi (zavisi od steps)
- **Preporučeno**: Koristite Juggernaut XL + MS Paint LoRA za najbolje rezultate

## 🎯 Primeri korišćenja:

1. **Upload fotografiju** → **Canny ControlNet** → **"MSPaint portrait"** = Smešna MS Paint verzija
2. **Upload skicu** → **Canny ControlNet** → **"realistic photo"** = Realistična verzija
3. **Upload osobu** → **OpenPose ControlNet** → **"superhero pose"** = Superhero poziranje

## ❗ Napomene:

- **Prvo upload sliku** pre korišćenja img2img
- **Učitajte ControlNet model** pre generacije
- **Koristite Juggernaut XL** za najbolje rezultate
- **MS Paint LoRA** daje najsmešnije rezultate!

---

*Image-to-Image funkcionalnost je sada dostupna u vašem AI asistentu!* 🎨✨
