# Z-Image Pipeline Setup - Specifična Konfiguracija

Ovaj dokument opisuje tačnu konfiguraciju Z-Image pipeline-a sa specifičnim fajlovima koji se koriste u projektu.

## 📦 Korišćeni Fajlovi

### Model Fajlovi
1. **Transformer**: `ckpts/ZImageTurbo_bf16.safetensors`
2. **VAE**: `ckpts/ZImageTurbo_VAE_bf16.safetensors`
3. **Text Encoder**: `ckpts/Qwen3/qwen3_quanto_bf16_int8.safetensors` (quantized int8 verzija)

### Konfiguracijski Fajlovi
- `ckpts/ZImageTurbo_VAE_bf16_config.json` - VAE konfiguracija
- `ckpts/ZImageTurbo_scheduler_config.json` - Scheduler konfiguracija
- `models/z_image/configs/z_image.json` - Transformer konfiguracija
- `ckpts/Qwen3/tokenizer.json` i ostali tokenizer fajlovi

---

## 🔧 Pipeline Komponente

### 1. Transformer (ZImageTransformer2DModel)
- **Fajl**: `ZImageTurbo_bf16.safetensors`
- **Klasa**: `ZImageTransformer2DModel`
- **Dtype**: `torch.bfloat16`
- **Učitavanje**: `mmgp.offload.load_model_data()`
- **Memory Management**: 
  - Pinning u reserved RAM
  - Async loading sa circular shuttle
  - Base size: ~0.01 MB preloaded
  - Async shuttle: ~345.06 MB

### 2. Text Encoder (Qwen3ForCausalLM)
- **Fajl**: `Qwen3/qwen3_quanto_bf16_int8.safetensors`
- **Klasa**: `Qwen3ForCausalLM`
- **Quantization**: int8 (quanto_bf16_int8)
- **Učitavanje**: `mmgp.offload.fast_load_transformers_model()`
- **Memory Management**:
  - Base size: ~741.88 MB preloaded
  - Async shuttle: ~96.32 MB

### 3. VAE (AutoencoderKL)
- **Fajl**: `ZImageTurbo_VAE_bf16.safetensors`
- **Klasa**: `AutoencoderKL` (custom implementacija)
- **Dtype**: `torch.float32`
- **Config**: `ZImageTurbo_VAE_bf16_config.json`
- **Učitavanje**: `mmgp.offload.fast_load_transformers_model()`

### 4. Scheduler
- **Klasa**: `FlowMatchEulerDiscreteScheduler`
- **Config**: `ZImageTurbo_scheduler_config.json`

### 5. Tokenizer
- **Tip**: AutoTokenizer (Qwen3)
- **Putanja**: `ckpts/Qwen3/`
- **Fajlovi**: `tokenizer.json`, `tokenizer_config.json`, `vocab.json`, `merges.txt`, `config.json`

---

## 🚀 Kompletan Pipeline Setup

### Importi
```python
import torch
from mmgp import offload
from shared.utils import files_locator as fl
from transformers import AutoTokenizer, Qwen3ForCausalLM
from diffusers import FlowMatchEulerDiscreteScheduler
from models.z_image.z_image_transformer2d import ZImageTransformer2DModel
from models.z_image.autoencoder_kl import AutoencoderKL
from models.z_image.pipeline_z_image import ZImagePipeline
import json
import os
```

### Učitavanje Pipeline-a
```python
def load_z_image_pipeline(
    checkpoint_dir="ckpts",
    dtype=torch.bfloat16,
    VAE_dtype=torch.float32,
):
    """
    Učitava Z-Image pipeline sa specifičnim fajlovima.
    """
    
    # 1. Učitaj Transformer
    transformer_filename = fl.locate_file("ZImageTurbo_bf16.safetensors")
    transformer_config_path = os.path.join(
        os.path.dirname(__file__), 
        "models/z_image/configs/z_image.json"
    )
    
    with open(transformer_config_path, "r") as f:
        config = json.load(f)
    config.pop("_class_name", None)
    config.pop("_diffusers_version", None)
    
    from accelerate import init_empty_weights
    with init_empty_weights():
        transformer = ZImageTransformer2DModel(**config)
    
    # Preprocess state dict za fused layers
    def preprocess_sd(state_dict, verboseLevel=1):
        from models.z_image.z_image_main import conv_state_dict, _split_nunchaku_fused
        state_dict = conv_state_dict(state_dict)
        return _split_nunchaku_fused(state_dict, verboseLevel=verboseLevel)
    
    kwargs_light = {
        "writable_tensors": False,
        "preprocess_sd": preprocess_sd
    }
    
    offload.load_model_data(transformer, transformer_filename, **kwargs_light)
    transformer.to(dtype)
    
    # 2. Učitaj Text Encoder (quantized int8)
    text_encoder_filename = fl.locate_file("Qwen3/qwen3_quanto_bf16_int8.safetensors")
    text_encoder = offload.fast_load_transformers_model(
        text_encoder_filename,
        writable_tensors=True,
        modelClass=Qwen3ForCausalLM,
    )
    
    # 3. Učitaj Tokenizer
    tokenizer_path = os.path.dirname(text_encoder_filename)
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, trust_remote_code=True)
    
    # 4. Učitaj VAE
    vae_filename = fl.locate_file("ZImageTurbo_VAE_bf16.safetensors")
    vae_config_path = os.path.join(
        os.path.dirname(vae_filename),
        "ZImageTurbo_VAE_bf16_config.json"
    )
    
    vae = offload.fast_load_transformers_model(
        vae_filename,
        writable_tensors=True,
        modelClass=AutoencoderKL,
        defaultConfigPath=vae_config_path,
        default_dtype=VAE_dtype,
    )
    
    # 5. Učitaj Scheduler
    scheduler_config_path = fl.locate_file("ZImageTurbo_scheduler_config.json")
    with open(scheduler_config_path, "r", encoding="utf-8") as f:
        scheduler_config = json.load(f)
    
    scheduler = FlowMatchEulerDiscreteScheduler(**scheduler_config)
    
    # 6. Kreiraj Pipeline
    pipeline = ZImagePipeline(
        scheduler=scheduler,
        vae=vae,
        text_encoder=text_encoder,
        tokenizer=tokenizer,
        transformer=transformer
    )
    
    return pipeline, {
        "transformer": transformer,
        "text_encoder": text_encoder,
        "tokenizer": tokenizer,
        "vae": vae,
        "scheduler": scheduler,
        "pipeline": pipeline
    }
```

---

## 🎯 Generisanje Slika

### Osnovno Generisanje
```python
# Učitaj pipeline
pipeline, components = load_z_image_pipeline()

# Generiši sliku
generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu")
generator.manual_seed(42)

images = pipeline(
    prompt="A beautiful sunset over mountains",
    negative_prompt=None,
    num_inference_steps=8,  # Standard za Turbo
    guidance_scale=0.0,  # Z-Image ne koristi guidance
    num_images_per_prompt=1,
    generator=generator,
    height=1024,
    width=1024,
    max_sequence_length=512,
    output_type="pt",  # Vraća torch tensor
    return_dict=True,
)

# Konvertuj u PIL Image
from shared.utils.utils import convert_tensor_to_image
pil_image = convert_tensor_to_image(images.images[0])
pil_image.save("output.png")
```

### Sa Callback-om
```python
def callback(step, timestep, latents):
    print(f"Step {step}/{8}, timestep: {timestep}")

images = pipeline(
    prompt="A beautiful landscape",
    num_inference_steps=8,
    callback_on_step_end=callback,
    # ... ostali parametri
)
```

---

## ⚙️ Memory Management (MMGP 3.6.11)

### Transformer Memory Setup
```
Pinning data of 'transformer' to reserved RAM
The whole model was pinned to reserved RAM: 52 large blocks spread across 11796.03 MB
Async loading plan for model 'transformer':
  - Base size: 0.01 MB preloaded
  - Async circular shuttle: 345.06 MB
```

### Text Encoder Memory Setup
```
Hooked to model 'text_encoder' (Qwen3ForCausalLM)
Async loading plan for model 'text_encoder':
  - Base size: 741.88 MB preloaded
  - Async circular shuttle: 96.32 MB
```

### VAE Memory Setup
```
Hooked to model 'vae' (AutoencoderKL)
```

### Memory Optimizacije
- **Transformer**: Pinned u reserved RAM za brži pristup
- **Text Encoder**: Preloaded base + async shuttle za optimizaciju
- **VAE**: Standardno učitavanje
- **Offloading**: Automatski sa mmgp.offload

---

## 🔑 Ključni Parametri

### Generisanje Parametri
```python
{
    "num_inference_steps": 8,        # Standard za Turbo
    "guidance_scale": 0.0,           # Uvek 0.0 za Z-Image
    "height": 1024,                   # Standardna rezolucija
    "width": 1024,                    # Standardna rezolucija
    "max_sequence_length": 512,      # Max dužina prompta
    "sample_solver": "default",       # ili "unified", "twinflow"
    "batch_size": 1,                  # Broj slika po batch-u
}
```

### VAE Tiling (za veće rezolucije)
```python
# Ako generišeš veće slike, možeš koristiti VAE tiling
if VAE_tile_size is not None and hasattr(components["vae"], "use_tiling"):
    components["vae"].use_tiling = True
    components["vae"].tile_latent_min_height = VAE_tile_size
    components["vae"].tile_latent_min_width = VAE_tile_size
```

---

## 📊 Performance Karakteristike

### Učitavanje Modela
- **Transformer**: ~11.8 GB pinned RAM
- **Text Encoder**: ~742 MB preloaded (quantized int8)
- **VAE**: Standardno učitavanje
- **Ukupno VRAM**: Zavisi od aktivnih komponenti

### Generisanje
- **Steps**: 8 koraka (standard za Turbo)
- **Speed**: ~0.43 steps/s (iz outputa: 0/8 [00:43<?])
- **Resolution**: 1024x1024 standardno

---

## 🔍 Debugging i Troubleshooting

### Provera Fajlova
```python
from shared.utils import files_locator as fl

# Proveri da li fajlovi postoje
transformer_file = fl.locate_file("ZImageTurbo_bf16.safetensors")
vae_file = fl.locate_file("ZImageTurbo_VAE_bf16.safetensors")
text_encoder_file = fl.locate_file("Qwen3/qwen3_quanto_bf16_int8.safetensors")

print(f"Transformer: {transformer_file}")
print(f"VAE: {vae_file}")
print(f"Text Encoder: {text_encoder_file}")
```

### Provera Memory Status
```python
import torch

if torch.cuda.is_available():
    print(f"GPU Memory Allocated: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
    print(f"GPU Memory Reserved: {torch.cuda.memory_reserved() / 1024**3:.2f} GB")
```

### Common Issues

1. **Fajl nije pronađen**
   - Proveri da li su fajlovi u `ckpts/` folderu
   - Proveri `files_locator` konfiguraciju

2. **Out of Memory**
   - Koristi VAE tiling za veće rezolucije
   - Smanji batch_size
   - Proveri da li su modeli pravilno offload-ovani

3. **Quantization Error**
   - Proveri da li je `qwen3_quanto_bf16_int8.safetensors` pravilno učitana
   - Proveri mmgp verziju (mora biti 3.6.11)

---

## 📝 Kompletan Primer

```python
import torch
from models.z_image.z_image_handler import family_handler

# Učitaj pipeline sa quantized text encoder-om
pipe_processor, pipe = family_handler.load_model(
    model_filename=["ZImageTurbo_bf16.safetensors"],
    base_model_type="z_image",
    model_def={},
    quantizeTransformer=False,
    text_encoder_quantization="int8",  # Koristi quantized verziju
    dtype=torch.bfloat16,
    VAE_dtype=torch.float32,
    mixed_precision_transformer=False,
    save_quantized=False,
)

# Generiši sliku
generator = torch.Generator(device="cuda")
generator.manual_seed(42)

images = pipe_processor.generate(
    seed=42,
    input_prompt="A beautiful sunset over mountains, cinematic lighting",
    n_prompt=None,
    sampling_steps=8,
    sample_solver="default",
    width=1024,
    height=1024,
    guide_scale=0.0,
    batch_size=1,
    callback=None,
    max_sequence_length=512,
    VAE_tile_size=None,
)

# Konvertuj i sačuvaj
from shared.utils.utils import convert_tensor_to_image
pil_image = convert_tensor_to_image(images[0])
pil_image.save("output.png")
```

---

## ✅ Checklist za Setup

- [ ] Instaliran `mmgp==3.6.11`
- [ ] Fajl `ZImageTurbo_bf16.safetensors` u `ckpts/`
- [ ] Fajl `ZImageTurbo_VAE_bf16.safetensors` u `ckpts/`
- [ ] Fajl `qwen3_quanto_bf16_int8.safetensors` u `ckpts/Qwen3/`
- [ ] Konfiguracijski fajlovi na mestu
- [ ] Tokenizer fajlovi u `ckpts/Qwen3/`
- [ ] Testirano učitavanje pipeline-a
- [ ] Testirano generisanje sa 8 koraka
- [ ] Proveren memory usage

---

**Napomena**: Ovaj setup koristi quantized int8 text encoder za smanjenje memory footprint-a. Za non-quantized verziju, koristi `qwen3_bf16.safetensors` i postavi `text_encoder_quantization=None`.
