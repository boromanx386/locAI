"""
Ollama Detector for locAI.
Detects Ollama installation, checks server status, and retrieves installed models.
"""

import subprocess
import requests
from typing import List, Optional, Tuple, Dict


class OllamaDetector:
    """Detects and checks Ollama installation and status."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        Initialize OllamaDetector.

        Args:
            base_url: Base URL for Ollama API
        """
        self.base_url = base_url
        self.timeout = 5

    def check_ollama_installed(self) -> Tuple[bool, Optional[str]]:
        """
        Check if Ollama is installed in the system PATH.

        Returns:
            Tuple of (is_installed, version_string or error_message)
        """
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                return True, version
            else:
                return False, "Ollama command returned non-zero exit code"
        except FileNotFoundError:
            return (
                False,
                "Ollama not found in PATH. Please install Ollama from https://ollama.com",
            )
        except subprocess.TimeoutExpired:
            return False, "Ollama version check timed out"
        except Exception as e:
            return False, f"Error checking Ollama installation: {str(e)}"

    def check_ollama_running(self) -> Tuple[bool, Optional[str]]:
        """
        Check if Ollama server is running.

        Returns:
            Tuple of (is_running, error_message if not running)
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)

            if response.status_code == 200:
                return True, None
            else:
                return (
                    False,
                    f"Ollama server returned status code {response.status_code}",
                )
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to Ollama server. Please start Ollama."
        except requests.exceptions.Timeout:
            return False, "Connection to Ollama server timed out"
        except Exception as e:
            return False, f"Error checking Ollama server: {str(e)}"

    def get_installed_models(self) -> Tuple[List[str], Optional[str]]:
        """
        Get list of installed Ollama models.

        Returns:
            Tuple of (list_of_models, error_message if failed)
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                return models, None
            else:
                return [], f"Failed to get models: status code {response.status_code}"
        except requests.exceptions.ConnectionError:
            return [], "Cannot connect to Ollama server"
        except requests.exceptions.Timeout:
            return [], "Request to Ollama server timed out"
        except KeyError as e:
            return [], f"Unexpected response format: {str(e)}"
        except Exception as e:
            return [], f"Error getting models: {str(e)}"

    def get_ollama_version(self) -> Optional[str]:
        """
        Get Ollama version string.

        Returns:
            Version string or None if not available
        """
        is_installed, version_info = self.check_ollama_installed()
        if is_installed:
            return version_info
        return None

    def get_status_summary(self) -> dict:
        """
        Get comprehensive status summary.

        Returns:
            Dictionary with status information
        """
        is_installed, install_info = self.check_ollama_installed()
        is_running, run_info = self.check_ollama_running()
        models, model_info = self.get_installed_models()

        return {
            "installed": is_installed,
            "install_info": install_info,
            "running": is_running,
            "run_info": run_info,
            "models": models,
            "model_info": model_info,
            "base_url": self.base_url,
        }

    def get_model_details(self, model_name: str) -> Optional[Dict]:
        """
        Get detailed information about a specific model using /api/show.

        Args:
            model_name: Name of the model

        Returns:
            Dictionary with model details or None if failed
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"model": model_name},
                timeout=self.timeout,
            )

            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            print(f"Error getting model details for {model_name}: {e}")
            return None

    def get_model_type(self, model_name: str, use_api: bool = False) -> str:
        """
        Determine model type (llm, vision, or embedding).

        Args:
            model_name: Name of the model
            use_api: If True, use API to get model details (may load model). Default False to avoid loading models at startup.

        Returns:
            Model type: 'llm', 'vision', or 'embedding'
        """
        # Check model name for common patterns first (faster)
        model_lower = model_name.lower()

        # Embedding models typically have "embed" in the name
        if "embed" in model_lower:
            return "embedding"

        # Vision models typically have "vision", "llava", "bakllava", "moondream" in the name
        if any(
            keyword in model_lower
            for keyword in ["llava", "vision", "bakllava", "moondream", "cogvlm"]
        ):
            return "vision"

        # Only use API if explicitly requested (to avoid loading models at startup)
        if use_api:
            # Try to get model details from API
            details = self.get_model_details(model_name)
            if details:
                # Check capabilities field
                capabilities = details.get("capabilities", [])
                if "vision" in capabilities:
                    return "vision"
                # If it has completion but not vision, it's likely an LLM
                if "completion" in capabilities:
                    return "llm"

        # Default to LLM if we can't determine
        return "llm"

    def get_categorized_models(self) -> Tuple[Dict[str, List[str]], Optional[str]]:
        """
        Get all models categorized by type.

        Returns:
            Tuple of (dict with keys 'llm', 'vision', 'embedding', error_message if failed)
        """
        all_models, error = self.get_installed_models()
        if error:
            return {"llm": [], "vision": [], "embedding": []}, error

        categorized = {"llm": [], "vision": [], "embedding": []}

        for model in all_models:
            # Use name-based detection only (no API calls to avoid loading models)
            model_type = self.get_model_type(model, use_api=False)
            categorized[model_type].append(model)

        return categorized, None

    def get_llm_models(self) -> Tuple[List[str], Optional[str]]:
        """
        Get list of LLM models only (excludes vision and embedding models).

        Returns:
            Tuple of (list_of_llm_models, error_message if failed)
        """
        categorized, error = self.get_categorized_models()
        if error:
            return [], error
        return categorized["llm"], None

    def get_embedding_models(self) -> Tuple[List[str], Optional[str]]:
        """
        Get list of embedding models only.

        Returns:
            Tuple of (list_of_embedding_models, error_message if failed)
        """
        categorized, error = self.get_categorized_models()
        if error:
            return [], error
        return categorized["embedding"], None

    def get_vision_models(self) -> Tuple[List[str], Optional[str]]:
        """
        Get list of vision models only.

        Returns:
            Tuple of (list_of_vision_models, error_message if failed)
        """
        categorized, error = self.get_categorized_models()
        if error:
            return [], error
        return categorized["vision"], None
    
    def get_llm_and_vision_models(self) -> Tuple[List[str], Optional[str]]:
        """
        Get list of LLM and Vision models (excludes embedding models).

        Returns:
            Tuple of (list_of_llm_and_vision_models, error_message if failed)
        """
        categorized, error = self.get_categorized_models()
        if error:
            return [], error
        # Combine LLM and Vision models
        all_models = categorized["llm"] + categorized["vision"]
        return all_models, None
