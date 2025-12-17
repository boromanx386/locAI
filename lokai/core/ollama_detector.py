"""
Ollama Detector for locAI.
Detects Ollama installation, checks server status, and retrieves installed models.
"""
import subprocess
import requests
from typing import List, Optional, Tuple


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
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, version
            else:
                return False, "Ollama command returned non-zero exit code"
        except FileNotFoundError:
            return False, "Ollama not found in PATH. Please install Ollama from https://ollama.com"
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
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return True, None
            else:
                return False, f"Ollama server returned status code {response.status_code}"
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
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=self.timeout
            )
            
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
            "base_url": self.base_url
        }

