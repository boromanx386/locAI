# 📥 Ručno preuzimanje LoRA i TI Embedding fajlova

## 🎯 **Gde preuzeti fajlove:**

### **1. Civitai.com (glavni izvor)**
- **URL**: https://civitai.com
- **Registracija**: Besplatna registracija potrebna
- **Pretraga**: Koristite search bar za pretragu modela

### **2. Hugging Face Hub**
- **URL**: https://huggingface.co
- **Registracija**: Besplatna registracija potrebna
- **Pretraga**: Koristite search bar za pretragu modela

---

## 🎨 **LoRA modeli (za stilove):**

### **Potrebni fajlovi:**
```
Q:\huggingface_cache\loras\
├── artgerm.safetensors          # ArtGerm Style
├── fashion.safetensors          # Fashion Photography  
├── logo.safetensors             # Logo Design
├── anime.safetensors            # Anime Style
└── realistic.safetensors        # Realistic Photography
```

### **Kako preuzeti:**

#### **ArtGerm Style LoRA:**
1. Idite na https://civitai.com
2. Pretražite: "artgerm style lora"
3. Preuzmite `.safetensors` fajl
4. Preimenujte u `artgerm.safetensors`
5. Stavite u `Q:\huggingface_cache\loras\`

#### **Fashion Photography LoRA:**
1. Pretražite: "fashion photography lora"
2. Preuzmite `.safetensors` fajl
3. Preimenujte u `fashion.safetensors`
4. Stavite u `Q:\huggingface_cache\loras\`

#### **Logo Design LoRA:**
1. Pretražite: "logo design lora" ili "logo lora"
2. Preuzmite `.safetensors` fajl
3. Preimenujte u `logo.safetensors`
4. Stavite u `Q:\huggingface_cache\loras\`

#### **Anime Style LoRA:**
1. Pretražite: "anime style lora" ili "anime lora"
2. Preuzmite `.safetensors` fajl
3. Preimenujte u `anime.safetensors`
4. Stavite u `Q:\huggingface_cache\loras\`

#### **Realistic Photography LoRA:**
1. Pretražite: "realistic photography lora" ili "realistic lora"
2. Preuzmite `.safetensors` fajl
3. Preimenujte u `realistic.safetensors`
4. Stavite u `Q:\huggingface_cache\loras\`

---

## 🎭 **TI Embeddings (za specifične koncepte):**

### **Potrebni fajlovi:**
```
Q:\huggingface_cache\embeddings\
├── my_art_style.bin             # My Art Style
├── logo_style.bin               # Logo Style
└── portrait_style.bin           # Portrait Style
```

### **Kako preuzeti:**

#### **My Art Style TI:**
1. Idite na https://civitai.com
2. Pretražite: "my art style textual inversion" ili "custom art style ti"
3. Preuzmite `.bin` fajl
4. Preimenujte u `my_art_style.bin`
5. Stavite u `Q:\huggingface_cache\embeddings\`

#### **Logo Style TI:**
1. Pretražite: "logo style textual inversion" ili "logo ti"
2. Preuzmite `.bin` fajl
3. Preimenujte u `logo_style.bin`
4. Stavite u `Q:\huggingface_cache\embeddings\`

#### **Portrait Style TI:**
1. Pretražite: "portrait style textual inversion" ili "portrait ti"
2. Preuzmite `.bin` fajl
3. Preimenujte u `portrait_style.bin`
4. Stavite u `Q:\huggingface_cache\embeddings\`

---

## 🔍 **Saveti za pretragu:**

### **Civitai.com pretraga:**
- **LoRA**: Koristite "lora" u pretrazi
- **TI Embeddings**: Koristite "textual inversion" ili "ti" u pretrazi
- **Filtri**: Koristite "Type" filter za LoRA ili Textual Inversion
- **Sortiranje**: Sortirajte po "Most Downloaded" ili "Highest Rated"

### **Hugging Face pretraga:**
- **LoRA**: Pretražite "lora" + stil (npr. "lora artgerm")
- **TI Embeddings**: Pretražite "textual inversion" + stil
- **Filtri**: Koristite "Model type" filter

---

## ⚠️ **Važne napomene:**

1. **Veličina fajlova**: LoRA fajlovi su obično 10-200 MB, TI embeddings 1-10 MB
2. **Format fajlova**: LoRA koristi `.safetensors`, TI koristi `.bin`
3. **Registracija**: Potrebna je registracija na oba sajta
4. **Kvalitet**: Preuzimajte samo visoko ocenjene modele
5. **Kompatibilnost**: Proverite da li su modeli kompatibilni sa SDXL

---

## 🚀 **Nakon preuzimanja:**

1. **Instalirajte PEFT**: `install_peft.bat`
2. **Pokrenite aplikaciju**: `python ai_assistant.py`
3. **Testirajte**: Kliknite "■ ADVANCED" dugme
4. **Učitajte modele**: Koristite Load dugmad u Advanced dialog-u

---

## 📞 **Pomoć:**

Ako imate problema:
1. Proverite da li su fajlovi u ispravnim direktorijumima
2. Proverite da li su fajlovi preimenovani ispravno
3. Proverite da li je PEFT instaliran
4. Proverite da li su fajlovi kompatibilni sa SDXL
