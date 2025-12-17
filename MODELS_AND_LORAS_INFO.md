# AI Assistant - Modeli i LoRA dokumentacija

## 📋 Pregled
Ovaj fajl sadrži detaljne informacije o svim SDXL modelima i LoRA-ama koji su instalirani u AI asistentu.

---

## 🎨 SDXL MODELI

### 1. SDXL Base (1024x1024)
- **Fajl**: `stabilityai/stable-diffusion-xl-base-1.0` (Hugging Face)
- **Tip**: Osnovni SDXL model
- **Veličina**: 1024x1024
- **Steps**: 50 (preporučeno)
- **Guidance**: 7.5
- **Memorija**: ~6GB VRAM
- **Opis**: Najbolji kvalitet, veća memorija - optimizovano
- **Korišćenje**: Opšta upotreba, najbolji kvalitet

### 2. Juggernaut XL (832x1216)
- **Fajl**: `juggernautXL_ragnarokBy.safetensors`
- **Tip**: SDXL checkpoint
- **Veličina**: 832x1216 (portrait)
- **Steps**: 30-40
- **Guidance**: 3-6 (manje je realističnije)
- **Negative**: Prazan (preporučeno)
- **Opis**: Fotorealistični model - poboljšane poze, ruke, noge, digitalno slikanje
- **Korišćenje**: Fotorealistične slike, portreti, digitalno slikanje
- **Izvor**: [CivitAI](https://civitai.com/models/133005/juggernaut-xl)

### 3. DynaVision XL (1024x1024)
- **Fajl**: `dynavisionXLAllInOneStylized_releaseV0610Bakedvae.safetensors`
- **Tip**: SDXL checkpoint
- **Veličina**: 1024x1024
- **Steps**: 20-40
- **Guidance**: 6-8
- **Negative**: `realistic, photorealistic` + standardni
- **Opis**: 3D stilizovani model - Pixar/Dreamworks/Disney stil, SFW i NSFW
- **Korišćenje**: 3D stilizovane slike, animirani stil, kreativni sadržaj
- **⚠️ VAŽNO**: NE KORISTI SDXL REFINER - nekompatibilan!
- **Izvor**: [CivitAI](https://civitai.com/models/122606/dynavision-xl-all-in-one-stylized-3d-sfw-and-nsfw-output-no-refiner-needed)

### 4. OmnigenXL (1024x1024)
- **Fajl**: `omnigenxlNSFWSFW_v10.safetensors`
- **Tip**: SDXL checkpoint
- **Veličina**: 1024x1024
- **Steps**: 20-40 (SFW), 20-30 (NSFW)
- **Guidance**: 5-9 (SFW), 6-8 (NSFW)
- **Opis**: Versatile SFW/NSFW model - perfekcija bez refiner-a
- **Korišćenje**: Raznovrsni sadržaj, SFW i NSFW, visok kvalitet
- **Izvor**: [CivitAI](https://civitai.com/models/203014/omnigenxl-nsfw-and-sfw)

### 5. epiCRealism XL (1024x1024)
- **Fajl**: `epicrealismXL_vxviiCrystalclear.safetensors`
- **Tip**: SDXL checkpoint
- **Veličina**: 1024x1024
- **Steps**: 20-40
- **Guidance**: 6-8
- **Negative**: `anime, cartoon` + standardni
- **Opis**: Fotorealistični model - poboljšane lica i ruke, crisp output
- **Korišćenje**: Fotorealistične slike, portreti, profesionalna fotografija
- **Clip Skip**: 1 (obavezno!)
- **Izvor**: [CivitAI](https://civitai.com/models/277058/epicrealism-xl)

### 6. PornVision (512x512)
- **Fajl**: `pornvision_final.safetensors`
- **Tip**: SD 1.5 checkpoint
- **Veličina**: 512x512
- **Steps**: 30
- **Guidance**: 7.5
- **Opis**: Specialized adult content model - NSFW
- **Korišćenje**: Adult content, NSFW slike

### 7. ZavyChromaXL (1024x1024)
- **Fajl**: `zavychromaxl_v100.safetensors`
- **Tip**: SDXL checkpoint
- **Veličina**: 1024x1024
- **Steps**: 25
- **Guidance**: 6.5
- **Opis**: Fotorealistični model - poboljšana saturacija, bolje zube, oči, ruke i noge
- **Korišćenje**: Fotorealistične slike, portreti, bolje lica i ruke
- **Izvor**: [CivitAI](https://civitai.com/models/119229/zavychromaxl)
Introduction
A model line that should be a continuance of the ZavyMix SD1.5 model for SDXL. The primary focus is to get a similar feeling in style and uniqueness that model had, where it's good at merging magic with realism, really merging them together seamlessly. Of course with the evolution to SDXL this model should have better quality and coherance for a lot of things, including the eyes and teeth than the SD1.5 models. This model has no need to use the refiner for great results, in fact it usually is preferable to not use the refiner. Recommended to use ultimate SD upscaler to get the most amazing results.

Continue reading for more information and some tips and tricks.

I kindly request that you share your creations both here and on my Discord server, as I would greatly appreciate the opportunity to see them and motivate me to spend more time in further ventures here.



Pros and cons
Pros
Much better saturation than base model.

Much better teeth, eyes, hands and feet.

Increased realism.

Less blurry edges but still keeps a certain pleasing softness to the image.

Better looking people.

Great texture and tonality.

Cons
NSFW much better than base, but still somewhat lacking without LORAs.

Roadmap
Training the SDXL model continuously.

Pioneering uncharted LORA subjects (withholding specifics to prevent preemption).

Tips
To better understand the preferences of the model, individuals are encouraged to utilise the provided prompts as a foundation and then customise, modify, or expand upon them according to their desired objectives.

Ditch the refiner, an img2img ultimate SD upscaler gets better results when you select this model for it.

For photorealism, use nmkdSiaxCX_200k for initial upscale, consider using ultramix_balanced for final upscale/pass to lessen grainy pictures.

Consider using face restoration techniques when the result for the face is subpar, but the rest of the image is interesting.

If you find that the details in your work are lacking, consider using wowifier if you’re unable to fix it with prompt alone. wowifier or similar tools can enhance and enrich the level of detail, resulting in a more compelling output.

ComfyUI is the UI I use for my SDXL images.

Your 1.5 LORAs won't work in SDXL.

Consider finding new prompts, don't use the standard 1.5 ones. SDXL likes a combination of a natural sentence with some keywords added behind.

To maintain optimal results and avoid excessive duplication of subjects, limit the generated image size to a maximum of 1024x1024 pixels or 640x1536 (or vice versa). If you require higher resolutions, it is recommended to utilise the Hires fix, followed by the img2img upscale technique, with particular emphasis on the controlnet tile upscale method. This approach will help you achieve superior results when aiming for higher resolution outputs. However, as this workflow doesn't work with SDXL yet, you may want to use an SD1.5 model for the img2img step.

Prompts
Recommended positive prompts for specifically photorealism: 2000s vintage RAW photo, photorealistic, film grain, candid camera, color graded cinematic, eye catchlights, atmospheric lighting, macro shot, skin pores, imperfections, natural, shallow dof, or other photography related tokens.

Recommended negative prompts: As few negative prompts as you can, only use it when it does something you do not want, like watermarks. Consider using high contrast, oily skin, plastic skin if the skin is too contrasting or too oily/plastic. Also make sure to add anime to negative prompt if you want better photorealism, and more mature looking characters.

You are further encouraged to include additional specific details regarding the desired output. This should involve specifying the preferred style, camera angle, lighting techniques, poses, color schemes, and other relevant factors.

Recommended settings
sdxl_vae.safetensors (baked in).

DPM++ 3M SDE Exponential, DPM++ SDE Karras, DPM++ 2M SDE Karras, DPM++ 2M Karras, Euler A

Steps 20~40 (lower range for DPM, higher range for Euler).

Hires upscaler: nmkdSiaxCX_200k, UltraMix_Balanced.

Hires upscale: Whatever maximum your GPU is capable of, but preferably between 1.5x~2x.

CFG scale 4-10 (preferably somewhere around cfg 6-7)

Lightning LoRA specific settings:

Euler sampler with SGM Uniform as Scheduler.

Steps 4 (use the 4 steps LoRA)

CFG scale 1-2 (CFG 1 at the higher weights for the LoRA)

LoRA weight 0.6-1
---

## 🔧 LoRA MODELI (INSTALIRANI)

### 1. Logo.Redmond
- **Fajl**: `LogoRedmondV2-Logo-LogoRedmAF.safetensors`
- **Base Model**: SDXL Base
- **Trigger**: `logologoredmaf`
- **Snaga**: 0.8
- **Opis**: Logo generacija - Logo.Redmond LoRA za SDXL
- **Korišćenje**: Profesionalni logotipi, brand dizajn
- **Preporučeno**: 1024x1024 veličina

### 2. Add Detail XL
- **Fajl**: `add-detail-xl.safetensors`
- **Base Model**: SDXL Base
- **Trigger**: `adddetail`
- **Snaga**: 0.6
- **Opis**: Dodaje detalje i oštrinu u slike - SDXL
- **Korišćenje**: Poboljšanje detalja, oštrije slike, bolji kvalitet

### 3. Logo Maker 9000
- **Fajl**: `logo.safetensors`
- **Base Model**: SDXL Base
- **Trigger**: `logomkrdsxlvectorlogo`
- **Snaga**: 0.9
- **Opis**: Logo Maker 9000 SDXL - vector quality logotipi u beskonačnom broju stilova
- **Korišćenje**: "logo of a (business type)" + trigger reči, vector stilovi
- **Izvor**: [CivitAI](https://civitai.com/models/436281/logo-maker-9000-sdxl-concept)

### 4. Bad Quality v02
- **Fajl**: `badquality_v02.safetensors`
- **Base Model**: Juggernaut XL
- **Trigger**: `badquality`
- **Snaga**: 0.7
- **Opis**: Poboljšava kvalitet slika - uklanja artifacts i noise
- **Korišćenje**: Poboljšanje kvaliteta, uklanjanje šuma, čišći output

### 5. Colossus Project XL
- **Fajl**: `FF.102.colossusProjectXLSFW_49bExperimental.LORA.safetensors`
- **Base Model**: SDXL Base
- **Trigger**: *(bez trigger reči)*
- **Snaga**: 1.2 (preporučeno), do 2.2 za vibrantne detalje
- **Opis**: Colossus Project XL 4.9b - FFusionAI ekstraktovana LoRA iz 400GB repository
- **Korišćenje**: Poboljšava vizuelni kvalitet, može se kombinovati sa 6+ LoRA-a (0.3-1.0 snaga)
- **Napomene**: Research-focused LoRA, ekstraktovana iz originalnog modela
- **Izvor**: [CivitAI](https://civitai.com/models/143636/400gb-lora-xl-repository)

### 6. JuggerCine XL
- **Fajl**: `JuggerCineXL2.safetensors`
- **Base Model**: Juggernaut XL
- **Trigger**: `juggercine`
- **Snaga**: 0.7
- **Opis**: JuggerCine XL - cinematički stil za film-like slike
- **Korišćenje**: Cinematički stil, film-like atmosfera, profesionalni izgled

### 7. Cinematic Style v1
- **Fajl**: `CinematicStyle_v1.safetensors`
- **Base Model**: Juggernaut XL
- **Trigger**: `cinematicstyle`
- **Snaga**: 0.8
- **Opis**: Cinematički stil - profesionalni film look sa dramskim osvetljenjem
- **Korišćenje**: Film look, dramsko osvetljenje, cinematografija

### 8. Super Eye Detailer
- **Fajl**: `Super_Eye_Detailer_By_Stable_Yogi_SDPD0.safetensors`
- **Base Model**: Juggernaut XL
- **Trigger**: `supereye`
- **Snaga**: 0.7
- **Opis**: Poboljšava detalje očiju - realistične i izražajne oči
- **Korišćenje**: Poboljšanje očiju u portretima, realistični pogled

### 9. Disney Princess XL
- **Fajl**: `princess_xl_v2.safetensors`
- **Base Model**: SDXL Base
- **Trigger**: `Anna`, `Ariel`, `Aurora`, `Belle`, `Cinderella`, `Elsa`, `Jasmine`, `Merida`, `Moana`, `Mulan`, `Pocahontas`, `Rapunzel`, `Snow White`, `Tiana`
- **Snaga**: 0.6-0.7 (close-up), 0.3-0.5 (full-body)
- **Opis**: All Disney Princess XL - sve Disney princeze iz Ralph Breaks the Internet
- **Korišćenje**: Generisanje Disney princeza direktno po imenu
- **Izvor**: [CivitAI](https://civitai.com/models/212532/all-disney-princess-xl-lora-model-from-ralph-breaks-the-internet)

### 10. Pixel Art XL
- **Fajl**: `pixel-art-xl-v1.1.safetensors`
- **Base Model**: SDXL Base
- **Trigger**: *(bez trigger reči - NE koristi "pixel art" u promptu)*
- **Snaga**: 0.9-1.0
- **Opis**: Pixel Art XL - generiše pixel art stil, kompatibilan sa izometrijskim i neizometrijskim stilovima
- **Korišćenje**: Pixel art slike, downscale 8x za pixel perfect rezultat
- **Napomene**: Ne koristi refiner, radi odlično sa samo 1 text encoder
- **Izvor**: [CivitAI](https://civitai.com/models/120096/pixel-art-xl)

### 11. Extremely Detailed
- **Fajl**: `detailed_notrigger.safetensors`
- **Base Model**: SDXL Base
- **Trigger**: *(bez trigger reči)*
- **Snaga**: 1.0 (opseg -1 do +1)
- **Opis**: Extremely detailed slider - pravi sve detaljnije bez trigger reči
- **Korišćenje**: Slider kontrola detalja, negativne vrednosti za manje detalja
- **Napomene**: v2.0 verzija sa ispravkama, trenirana 6000 koraka
- **Izvor**: [CivitAI](https://civitai.com/models/229213/extremely-detailed-no-trigger-slidersntcaixyz)

### 12. Real Humans
- **Fajl**: `real-humans-PublicPrompts.safetensors`
- **Base Model**: SDXL Base
- **Trigger**: `photo`, `portrait photo`
- **Snaga**: 1.0 (za opštu upotrebu), 1.5 (za selfie)
- **Opis**: Real Humans - fotorealistični ljudi, odličan za selfie portrete
- **Korišćenje**: Fotorealistični portreti, "selfie portrait photo of..."
- **Napomene**: "portrait photo" forsira close-up, posebno na višim vrednostima
- **Izvor**: [CivitAI](https://civitai.com/models/232746/real-humans)

### 13. Hand Fine Tuning XL
- **Fajl**: `HandFineTuning_XL.safetensors`
- **Base Model**: SDXL Base
- **Trigger**: *(bez trigger reči)*
- **Snaga**: 0.8
- **Opis**: Hand Fine Tuning - poboljšava renderovanje ruku, kompatibilan sa realističnim i anime modelima
- **Korišćenje**: Poboljšanje ruku u portretima i scenama
- **Napomene**: Ne garantuje savršene ruke svaki put, ali značajno poboljšava rezultate
- **Izvor**: [CivitAI](https://civitai.com/models/278497/hand-fine-tuning)

### 14. ParchartXL CODA
- **Fajl**: `ParchartXL_CODA.safetensors`
- **Base Model**: SDXL Base
- **Trigger**: `on parchment`
- **Snaga**: 1.0
- **Opis**: ParchartXL - ilustracije na pergamentu sa teksturom i anotacijama
- **Korišćenje**: Dodaj "on parchment" u bilo koji prompt za pergament efekat
- **Napomene**: Clip Skip: 1, finalna CODA verzija sa savršenom teksturom
- **Izvor**: [CivitAI](https://civitai.com/models/141471/parchartxl)

### 15. Dolls Kill Collection
- **Fajl**: `Dollskill_Downbeat_Spiked.safetensors`
- **Base Model**: SDXL Base
- **Trigger**: `dollskill`
- **Snaga**: 0.8
- **Opis**: Dolls Kill Collection - kolekcija outfita od različitih brendova
- **Kategorije**: Streetwear, Clubwear, Cute Dresses, Lingerie
- **Korišćenje**: Dodaj "dollskill" + naziv outfita (npr. "Downbeat Spiked", "Techno", "Mystery Machine")
- **Napomene**: Clip Skip: 2, trenirana 1200 koraka, 9 epoha
- **Izvor**: [CivitAI](https://civitai.com/models/245126/dolls-kill-collection-sdxl)

### 16. Sketchit
- **Fajl**: `sketch_it.safetensors`
- **Base Model**: SDXL Base
- **Trigger**: *(bez trigger reči)*
- **Snaga**: 1.0
- **Opis**: Sketchit - crno-beli crtež u ink wash stilu sa ekspresivnim linijama
- **Korišćenje**: "a black and white drawing of (subject)"
- **Negative prompt**: "photo, colors"
- **Napomene**: Ink wash tehnika, ekspresivne linije, spontanost i kontrola
- **Izvor**: [CivitAI](https://civitai.com/models/303330/sketchit)

### 17. XL More Art Enhancer
- **Fajl**: `xl_more_art-full_v1.safetensors`
- **Base Model**: SDXL Base
- **Trigger**: `Aerial` (za aerial fotografije)
- **Snaga**: 0.8-1.0 (može i više za manje detaljne slike)
- **Opis**: XL More Art Enhancer - poboljšava estetiku, artistički i kreativni izgled, detaljnije slike
- **Korišćenje**: Automatski poboljšava slike, dodaj "Aerial" za aerial fotografije
- **Napomene**: V1 verzija, malo više fotorealistična od beta verzija, radi i sa anime/ilustracijama
- **Izvor**: [CivitAI](https://civitai.com/models/124347/xlmoreart-full-xlreal-enhancer)

### 18. MS Paint Portraits
- **Fajl**: `SDXL_MSPaint_Portrait.safetensors`
- **Base Model**: SDXL Base
- **Trigger**: `MSPaint portrait`, `MSPaint drawing`
- **Snaga**: 1.0
- **Opis**: SDXL MS Paint Portraits - loš kvalitet MS Paint stil (namerno!)
- **Korišćenje**: "MSPaint portrait of {subject}" ili "MSPaint drawing of {scene}"
- **Napomene**: Teško za kontrolu, proizvodi neočekivane i smešne rezultate
- **Izvor**: [CivitAI](https://civitai.com/models/183354/sdxl-ms-paint-portraits)

### 19. Greg Rutkowski Style
- **Fajl**: `greg_rutkowski_xl_2.safetensors`
- **Base Model**: SDXL Base (preporučeno DreamShaper XL)
- **Trigger**: `greg rutkowski`
- **Snaga**: 1.0
- **Opis**: Greg Rutkowski inspired style - fantasy art u ArtStation stilu
- **Korišćenje**: Dodaj "greg rutkowski" u prompt za fantasy art stil
- **Napomene**: Treniran na DreamShaper XL1.0, najbolji rezultati na tom modelu
- **Izvor**: [CivitAI](https://civitai.com/models/117635/greg-rutkowski-inspired-style-lora-sdxl)

### 20. Eldritch Comics
- **Fajl**: `EldritchComicsXL1.2.safetensors`
- **Base Model**: SDXL Base
- **Trigger**: `comic book`
- **Snaga**: 1.0
- **Opis**: Eldritch Comics - comic book stil sa oštrim konturama
- **Korišćenje**: Dodaj "comic book" za comic book ilustracije
- **Napomene**: Clip Skip: 2, v1.2 sa poboljšanim space elementima
- **Izvor**: [CivitAI](https://civitai.com/models/262880/eldritch-comics-comic-book-style-illustration)

### 21. Sarah Miller TLOU
- **Fajl**: `sarah_tlou_sdxl_v3-000088.safetensors`
- **Base Model**: SDXL Base
- **Trigger**: `sarah miller`
- **Snaga**: 0.8
- **Opis**: Sarah Miller iz The Last of Us - karakter LoRA
- **Korišćenje**: Dodaj "sarah miller" za generisanje ovog karaktera
- **Napomene**: Adult content model, možda blokiran u nekim slučajevima

---

## ⚙️ Preporučene postavke

### Za fotorealistične slike:
- **Model**: epiCRealism XL ili Juggernaut XL
- **Steps**: 30-50
- **Guidance**: 6.0-7.0
- **Size**: 1024x1024

### Za logo dizajn:
- **Model**: Juggernaut XL
- **LoRA**: Logo.Redmond
- **Steps**: 35
- **Guidance**: 4.5
- **Size**: 1024x1024

### Za 3D stilizovane slike:
- **Model**: DynaVision XL
- **Steps**: 30
- **Guidance**: 6.0
- **Size**: 1024x1024

### Za anime stil:
- **Model**: SDXL Base
- **LoRA**: Anime Style
- **Steps**: 30-40
- **Guidance**: 7.0-8.0

---

## 📝 Napomene

- **Memorija**: SDXL modeli zahtevaju ~6GB VRAM
- **Veličina**: SDXL modeli moraju biti kvadrat (1024x1024)
- **Seed**: Koristi fiksni seed za konzistentnost
- **LoRA**: Možeš kombinovati više LoRA-a istovremeno
- **Trigger**: Uvek koristi trigger reči u promptu za LoRA-e
- **Base Model**: LoRA-e rade samo sa odgovarajućim base modelom (SDXL LoRA = SDXL model)

---

## 🔗 Korisni linkovi

- [CivitAI](https://civitai.com/) - Glavna platforma za SDXL modele
- [Hugging Face](https://huggingface.co/) - Alternativni izvor modela
- [Stable Diffusion XL](https://stability.ai/news/stable-diffusion-xl) - Oficijalna dokumentacija

---

*Poslednje ažuriranje: 16. januar 2025*
