Write-Host "Setting Hugging Face cache to Q: drive..." -ForegroundColor Green

# Set all Hugging Face environment variables
$env:HF_HOME = "Q:\huggingface_cache"
$env:TRANSFORMERS_CACHE = "Q:\huggingface_cache"
$env:HF_DATASETS_CACHE = "Q:\huggingface_cache"
$env:HF_HUB_CACHE = "Q:\huggingface_cache"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"

Write-Host "Environment variables set:" -ForegroundColor Yellow
Write-Host "HF_HOME: $env:HF_HOME"
Write-Host "TRANSFORMERS_CACHE: $env:TRANSFORMERS_CACHE"
Write-Host "HF_DATASETS_CACHE: $env:HF_DATASETS_CACHE"
Write-Host "HF_HUB_CACHE: $env:HF_HUB_CACHE"

# Create directory if it doesn't exist
if (!(Test-Path "Q:\huggingface_cache")) {
    New-Item -ItemType Directory -Path "Q:\huggingface_cache" -Force
    Write-Host "Created Q:\huggingface_cache directory" -ForegroundColor Green
}

Write-Host "Starting AI Assistant..." -ForegroundColor Cyan
python ai_assistant.py
