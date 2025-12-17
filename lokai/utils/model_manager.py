"""
Model Manager for locAI.
Handles model storage location configuration and environment setup.
"""
import os
from pathlib import Path
from typing import Optional, List, Dict


class ModelManager:
    """Manages model storage locations and environment variables."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize ModelManager.
        
        Args:
            storage_path: Optional storage path. If None, uses default location.
        """
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            # Default location: Documents/locAI/models
            documents = Path.home() / "Documents"
            self.storage_path = documents / "locAI" / "models"
        
        self.setup_directories()
    
    def setup_directories(self):
        """Create necessary subdirectories."""
        directories = [
            self.storage_path,
            self.storage_path / "diffusers",
            self.storage_path / "loras",
            self.storage_path / "embeddings",
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def setup_environment_variables(self):
        """
        Set up environment variables for Hugging Face cache.
        This should be called before importing any Hugging Face libraries.
        """
        storage_str = str(self.storage_path)
        diffusers_path = str(self.storage_path / "diffusers")
        
        os.environ["HF_HOME"] = storage_str
        os.environ["TRANSFORMERS_CACHE"] = storage_str
        os.environ["HF_DATASETS_CACHE"] = storage_str
        os.environ["HF_HUB_CACHE"] = storage_str
        os.environ["DIFFUSERS_CACHE"] = diffusers_path
        os.environ["HF_DIFFUSERS_CACHE"] = diffusers_path
    
    def get_storage_path(self) -> Path:
        """Get the storage path."""
        return self.storage_path
    
    def set_storage_path(self, path: str):
        """
        Set new storage path.
        
        Args:
            path: New storage path
        """
        self.storage_path = Path(path)
        self.setup_directories()
        self.setup_environment_variables()
    
    def get_diffusers_path(self) -> Path:
        """Get diffusers cache path."""
        return self.storage_path / "diffusers"
    
    def get_loras_path(self) -> Path:
        """Get LoRA models path."""
        return self.storage_path / "loras"
    
    def get_embeddings_path(self) -> Path:
        """Get embeddings path."""
        return self.storage_path / "embeddings"
    
    def validate_path(self, path: str) -> tuple[bool, Optional[str]]:
        """
        Validate that a path is suitable for model storage.
        
        Args:
            path: Path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            test_path = Path(path)
            
            # Check if path exists or can be created
            if not test_path.exists():
                # Try to create parent directory
                parent = test_path.parent
                if not parent.exists():
                    try:
                        parent.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        return False, f"Cannot create directory: {str(e)}"
            
            # Check if it's a directory (or can be)
            if test_path.exists() and not test_path.is_dir():
                return False, "Path exists but is not a directory"
            
            # Check write permissions
            test_file = test_path / ".lokai_test"
            try:
                test_file.touch()
                test_file.unlink()
            except Exception as e:
                return False, f"No write permission: {str(e)}"
            
            return True, None
            
        except Exception as e:
            return False, f"Invalid path: {str(e)}"
    
    def detect_existing_models(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Detect existing Hugging Face models in storage path.
        
        Returns:
            Dictionary with detected models by type:
            {
                "diffusers": [{"name": "org/model", "path": "...", "display": "..."}],
                "loras": [{"name": "model.safetensors", "path": "...", "display": "..."}],
                "embeddings": [{"name": "embedding.bin", "path": "...", "display": "..."}]
            }
        """
        detected = {
            "diffusers": [],
            "loras": [],
            "embeddings": []
        }
        
        if not self.storage_path.exists():
            return detected
        
        # Helper function to check if a directory contains a diffusers model
        def is_diffusers_model(directory: Path) -> bool:
            """Check if directory contains a diffusers model."""
            # Check for key diffusers files
            if (directory / "model_index.json").exists():
                return True
            if (directory / "unet").exists() and (directory / "unet").is_dir():
                return True
            if (directory / "text_encoder").exists() and (directory / "text_encoder").is_dir():
                return True
            if (directory / "vae").exists() and (directory / "vae").is_dir():
                return True
            return False
        
        # Helper function to recursively scan a directory for models
        def scan_directory_for_models(directory: Path, depth: int = 0, max_depth: int = 10):
            """Recursively scan directory for model folders."""
            models_found = []
            
            if not directory.exists() or not directory.is_dir():
                return models_found
            
            # Prevent infinite recursion
            if depth > max_depth:
                return models_found
            
            try:
                for item in directory.iterdir():
                    if not item.is_dir():
                        continue
                    
                    # Check if this directory itself is a model
                    if is_diffusers_model(item):
                        # Try to extract model name from parent structure
                        model_id = None
                        display_name = item.name
                        
                        # Check if parent is a models-- folder
                        parent = item.parent
                        if parent.name.startswith("models--"):
                            model_id = parent.name.replace("models--", "").replace("--", "/")
                            if "/" in model_id:
                                org, model = model_id.split("/", 1)
                                display_name = f"{org}/{model}"
                            else:
                                display_name = model_id
                        else:
                            # Try to infer from directory name or path
                            # Look for common patterns
                            path_parts = item.parts
                            for i, part in enumerate(path_parts):
                                if part.startswith("models--"):
                                    model_id = part.replace("models--", "").replace("--", "/")
                                    if "/" in model_id:
                                        org, model = model_id.split("/", 1)
                                        display_name = f"{org}/{model}"
                                    else:
                                        display_name = model_id
                                    break
                            
                            # If no model_id found, use directory name
                            if not model_id:
                                model_id = item.name
                                display_name = item.name
                        
                        models_found.append({
                            "name": model_id or item.name,
                            "path": str(item),
                            "display": display_name,
                            "type": "diffusers"
                        })
                    
                    # Check if this is a models-- folder
                    elif item.name.startswith("models--"):
                        # Extract model name from folder name
                        # Format: models--org--model-name
                        model_id = item.name.replace("models--", "").replace("--", "/")
                        
                        # Check snapshots directory
                        snapshots_dir = item / "snapshots"
                        if snapshots_dir.exists():
                            # Check each snapshot folder
                            for snapshot in snapshots_dir.iterdir():
                                if snapshot.is_dir() and is_diffusers_model(snapshot):
                                    # Create display name
                                    display_name = model_id
                                    if "/" in model_id:
                                        org, model = model_id.split("/", 1)
                                        display_name = f"{org}/{model}"
                                    
                                    models_found.append({
                                        "name": model_id,
                                        "path": str(snapshot),
                                        "display": display_name,
                                        "type": "diffusers"
                                    })
                                    break
                        else:
                            # Check if model is stored directly
                            if is_diffusers_model(item):
                                display_name = model_id
                                if "/" in model_id:
                                    org, model = model_id.split("/", 1)
                                    display_name = f"{org}/{model}"
                                
                                models_found.append({
                                    "name": model_id,
                                    "path": str(item),
                                    "display": display_name,
                                    "type": "diffusers"
                                })
                    
                    # Recursively search subdirectories
                    if depth < max_depth:
                        sub_models = scan_directory_for_models(item, depth + 1, max_depth)
                        models_found.extend(sub_models)
                        
            except PermissionError:
                # Skip directories we can't access
                pass
            except Exception as e:
                # Log but continue
                print(f"Error scanning {directory}: {e}")
            
            return models_found
        
        # Recursively scan root directory (this will find models in all subdirectories)
        root_models = scan_directory_for_models(self.storage_path)
        detected["diffusers"].extend(root_models)
        
        # Also scan for standalone .safetensors model files (like in old code)
        # These are direct model files, not diffusers format
        models_dir = self.storage_path / "models"
        if models_dir.exists() and models_dir.is_dir():
            try:
                for item in models_dir.iterdir():
                    if item.is_file() and item.suffix.lower() == ".safetensors":
                        # This is a standalone model file
                        model_name = item.stem  # filename without extension
                        detected["diffusers"].append({
                            "name": str(item),  # Use full path as name for direct loading
                            "path": str(item),
                            "display": model_name,
                            "type": "safetensors"  # Mark as safetensors type
                        })
            except PermissionError:
                pass
            except Exception as e:
                print(f"Error scanning models directory: {e}")
        
        # Also check root directory for .safetensors files
        try:
            for item in self.storage_path.iterdir():
                if item.is_file() and item.suffix.lower() == ".safetensors":
                    model_name = item.stem
                    detected["diffusers"].append({
                        "name": str(item),
                        "path": str(item),
                        "display": model_name,
                        "type": "safetensors"
                    })
        except PermissionError:
            pass
        except Exception as e:
            print(f"Error scanning root directory for safetensors: {e}")
        
        # Remove duplicates (same model name/path)
        seen_paths = set()
        unique_models = []
        for model in detected["diffusers"]:
            model_path = model["path"]
            if model_path not in seen_paths:
                seen_paths.add(model_path)
                unique_models.append(model)
        detected["diffusers"] = unique_models
        
        # Detect LoRA models
        loras_path = self.get_loras_path()
        if loras_path.exists():
            for item in loras_path.iterdir():
                if item.is_file() and item.suffix.lower() in [".safetensors", ".pt", ".bin", ".ckpt"]:
                    detected["loras"].append({
                        "name": item.stem,
                        "path": str(item),
                        "display": item.name,
                        "type": "lora"
                    })
        
        # Detect embeddings
        embeddings_path = self.get_embeddings_path()
        if embeddings_path.exists():
            for item in embeddings_path.iterdir():
                if item.is_file() and item.suffix.lower() in [".bin", ".pt", ".safetensors"]:
                    detected["embeddings"].append({
                        "name": item.stem,
                        "path": str(item),
                        "display": item.name,
                        "type": "embedding"
                    })
        
        return detected
    
    def get_available_diffusers_models(self) -> List[str]:
        """
        Get list of available diffusers model IDs.
        
        Returns:
            List of model IDs (e.g., ["stabilityai/stable-diffusion-xl-base-1.0", ...])
        """
        models = self.detect_existing_models()
        return [m["name"] for m in models["diffusers"]]

