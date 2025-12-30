# SD Img2Vid - Informacije i Integracija

## ✅ Odgovor: DA, radi sa vašim bibliotekama!

Vaša trenutna konfiguracija već ima sve potrebno:
- ✅ `diffusers >= 0.35.0` - podržava Stable Video Diffusion
- ✅ `torch >= 2.0.0` - potreban za video generaciju
- ✅ `transformers >= 4.56.0` - potreban za modele
- ✅ SDXL već radi u vašoj aplikaciji

## Kako funkcionira

**Radni tok:**
1. Generirajte sliku sa SDXL (već imate ovo)
2. Koristite tu sliku kao input za Stable Video Diffusion (SVD)
3. SVD generira kratki video (14 ili 25 frame-ova)

## Stable Video Diffusion (SVD) Modeli

### Dostupni modeli u diffusers:

1. **SVD** (14 frame-ova):
   - Model: `stabilityai/stable-video-diffusion-img2vid`
   - Rezolucija: 576x1024
   - Frame-ovi: 14

2. **SVD-XT** (25 frame-ova):
   - Model: `stabilityai/stable-video-diffusion-img2vid-xt`
   - Rezolucija: 576x1024
   - Frame-ovi: 25

## Primjer koda za integraciju

```python
from diffusers import StableVideoDiffusionPipeline
from diffusers.utils import load_image, export_to_video
import torch
from PIL import Image

# Učitaj pipeline (slično kao vaš ImageGenerator)
def load_video_pipeline(model_name="stabilityai/stable-video-diffusion-img2vid-xt"):
    pipe = StableVideoDiffusionPipeline.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        variant="fp16"
    )
    
    if torch.cuda.is_available():
        pipe = pipe.to("cuda")
        # Ili koristite sequential CPU offload kao u vašem kodu
        # pipe.enable_sequential_cpu_offload()
    
    return pipe

# Generiraj video iz slike
def generate_video_from_image(
    pipeline,
    image: Image.Image,  # Vaša SDXL generirana slika
    num_frames: int = 25,
    num_inference_steps: int = 25,
    motion_bucket_id: int = 127,
    fps: int = 7
):
    # Resize sliku na 576x1024 (SVD zahtijeva ovu rezoluciju)
    image = image.resize((576, 1024))
    
    # Generiraj video
    frames = pipeline(
        image,
        decode_chunk_size=8,
        generator=torch.manual_seed(42),
        num_frames=num_frames,
        num_inference_steps=num_inference_steps,
        motion_bucket_id=motion_bucket_id,
    ).frames[0]
    
    # Exportuj u video fajl
    export_to_video(frames, "generated_video.mp4", fps=fps)
    
    return frames
```

## Zahtjevi za memoriju

- **SVD**: ~8-10 GB VRAM
- **SVD-XT**: ~10-12 GB VRAM
- Preporučeno: 16+ GB VRAM za optimalno funkcioniranje

## Integracija u vašu aplikaciju

Možete dodati `VideoGenerator` klasu slično vašoj `ImageGenerator`:

```python
# lokai/core/video_generator.py
class VideoGenerator:
    def __init__(self, storage_path: Optional[str] = None):
        # Slično kao ImageGenerator
        self.pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
    def generate_video_from_image(
        self, 
        image: Image.Image,
        num_frames: int = 25,
        ...
    ):
        # Implementacija
```

## Napomene

1. **Rezolucija**: SVD zahtijeva točno 576x1024 piksela (ili 1024x576)
2. **Frame-ovi**: SVD generira 14 frame-ova, SVD-XT generira 25
3. **FPS**: Tipično 7 fps za prirodan izgled
4. **Memorija**: Zahtijeva više VRAM-a nego SDXL za slike

## Korisni linkovi

- [Stable Video Diffusion na Hugging Face](https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt)
- [Diffusers dokumentacija](https://huggingface.co/docs/diffusers/api/pipelines/stable_video_diffusion)
- [Primjer koda](https://github.com/huggingface/diffusers/tree/main/examples/community#stable-video-diffusion)

## Zaključak

**DA, može se integrirati!** Vaše biblioteke su kompatibilne. Trebate samo:
1. Dodati `VideoGenerator` klasu (slično `ImageGenerator`)
2. Učitati SVD model
3. Koristiti SDXL generirane slike kao input

