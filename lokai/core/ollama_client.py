"""
Ollama Client for locAI.
Handles API communication with Ollama server for LLM interactions.
"""
import json
import requests
from typing import Optional, Callable, List, Tuple


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        Initialize OllamaClient.
        
        Args:
            base_url: Base URL for Ollama API
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.timeout = 7200  # 2 hours for long generations
    
    def is_running(self) -> bool:
        """
        Check if Ollama server is running.
        
        Returns:
            True if server is accessible
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def get_models(self) -> List[str]:
        """
        Get list of available models.
        
        Returns:
            List of model names
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except:
            return []
    
    def generate_response_stream(
        self,
        model: str,
        prompt: str,
        context: Optional[List[int]] = None,
        callback: Optional[Callable[[str], None]] = None,
        images: Optional[List[str]] = None,
        num_ctx: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        repeat_penalty: Optional[float] = None,
        num_predict: Optional[int] = None,
        seed: Optional[int] = None
    ) -> Tuple[str, Optional[List[int]]]:
        """
        Generate response from model with streaming support.
        
        Args:
            model: Model name to use
            prompt: User prompt
            context: Previous conversation context
            callback: Optional callback function for streaming chunks
            images: Optional list of base64-encoded images (for vision models)
            num_ctx: Context window size (optional)
            temperature: Temperature for sampling (optional)
            top_p: Top-p sampling parameter (optional)
            top_k: Top-k sampling parameter (optional)
            repeat_penalty: Repeat penalty (optional)
            num_predict: Maximum tokens to generate, -1 for unlimited (optional)
            seed: Seed for reproducibility, -1 for random (optional)
            
        Returns:
            Tuple of (full_response, new_context)
        """
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True,
            }
            
            # Add context if provided
            if context is not None and len(context) > 0:
                payload["context"] = context
            
            # Add LLM parameters if provided
            if num_ctx is not None:
                payload["num_ctx"] = num_ctx
            if temperature is not None:
                payload["temperature"] = temperature
            if top_p is not None:
                payload["top_p"] = top_p
            if top_k is not None:
                payload["top_k"] = top_k
            if repeat_penalty is not None:
                payload["repeat_penalty"] = repeat_penalty
            if num_predict is not None:
                payload["num_predict"] = num_predict
            if seed is not None and seed != -1:
                payload["seed"] = seed
            
            # Add images if provided (for vision models like LLaVA)
            if images and len(images) > 0:
                payload["images"] = images
                print(f"Sending {len(images)} image(s) to model {model}")
            
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                full_response = ""
                new_context = None
                
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode("utf-8"))
                            
                            # Handle response chunks
                            if "response" in data:
                                chunk = data["response"]
                                full_response += chunk
                                if callback:
                                    callback(chunk)
                            
                            # Store context for next request
                            if "context" in data:
                                new_context = data["context"]
                            
                            # Check if generation is done
                            if data.get("done", False):
                                break
                            
                            # Handle errors in stream
                            if "error" in data:
                                error_msg = data["error"]
                                print(f"Ollama error in stream: {error_msg}")
                                return f"Error: {error_msg}", new_context
                                
                        except json.JSONDecodeError:
                            continue
                
                # Check for empty response
                if not full_response.strip():
                    return (
                        "Model returned empty response. The model might not be properly loaded.",
                        new_context
                    )
                
                return full_response, new_context
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"Ollama API error: {error_msg}")
                return f"Error generating response: {error_msg}", None
                
        except requests.exceptions.Timeout:
            return "Request timed out. The model might be taking too long to respond.", None
        except requests.exceptions.ConnectionError:
            return "Cannot connect to Ollama server. Please ensure Ollama is running.", None
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"Ollama client error: {error_msg}")
            return f"Error: {error_msg}", None
    
    def generate_response(
        self,
        model: str,
        prompt: str,
        context: Optional[List[int]] = None,
        images: Optional[List[str]] = None,
        num_ctx: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        repeat_penalty: Optional[float] = None,
        num_predict: Optional[int] = None,
        seed: Optional[int] = None
    ) -> Tuple[str, Optional[List[int]]]:
        """
        Generate response without streaming (collects all chunks first).
        
        Args:
            model: Model name to use
            prompt: User prompt
            context: Previous conversation context
            images: Optional list of base64-encoded images
            num_ctx: Context window size (optional)
            temperature: Temperature for sampling (optional)
            top_p: Top-p sampling parameter (optional)
            top_k: Top-k sampling parameter (optional)
            repeat_penalty: Repeat penalty (optional)
            num_predict: Maximum tokens to generate, -1 for unlimited (optional)
            seed: Seed for reproducibility, -1 for random (optional)
            
        Returns:
            Tuple of (full_response, new_context)
        """
        full_response = ""
        
        def collect_chunk(chunk: str):
            nonlocal full_response
            full_response += chunk
        
        response, new_context = self.generate_response_stream(
            model=model,
            prompt=prompt,
            context=context,
            callback=collect_chunk,
            images=images,
            num_ctx=num_ctx,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            repeat_penalty=repeat_penalty,
            num_predict=num_predict,
            seed=seed
        )
        
        return response, new_context
    
    def unload_model(self, model_name: str) -> bool:
        """
        Unload a specific Ollama model from VRAM.
        
        Args:
            model_name: Name of the model to unload
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import subprocess
            result = subprocess.run(
                ["ollama", "stop", model_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(f"Model {model_name} unloaded successfully")
                return True
            else:
                print(f"Model {model_name} not loaded or already unloaded")
                return False
        except Exception as e:
            print(f"Error unloading model {model_name}: {e}")
            return False
    
    def unload_all_models_silent(self) -> None:
        """
        Silently unload all loaded Ollama models to free GPU memory.
        First gets list of actually loaded models, then unloads them.
        """
        try:
            import subprocess
            
            # First, get list of actually loaded models
            try:
                result = subprocess.run(
                    ["ollama", "list"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    # Parse output to get model names
                    lines = result.stdout.strip().split('\n')
                    loaded_models = []
                    for line in lines[1:]:  # Skip header
                        if line.strip():
                            parts = line.split()
                            if len(parts) > 0:
                                model_name = parts[0]
                                # Extract base model name (before ':')
                                if ':' in model_name:
                                    model_name = model_name.split(':')[0]
                                if model_name not in loaded_models:
                                    loaded_models.append(model_name)
                    
                    # Unload all loaded models
                    for model in loaded_models:
                        try:
                            subprocess.run(
                                ["ollama", "stop", model],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                        except:
                            pass  # Silent fail
                    
                    if loaded_models:
                        print(f"Unloaded {len(loaded_models)} Ollama model(s): {', '.join(loaded_models)}")
                    else:
                        print("No Ollama models were loaded")
                else:
                    # Fallback: try common model names
                    models_to_unload = ["llava", "mixtral", "llama", "codellama", "mistral", "qwen", "phi", "gemma", "neural-chat"]
                    for model in models_to_unload:
                        try:
                            subprocess.run(
                                ["ollama", "stop", model],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                        except:
                            pass  # Silent fail
                    print("Ollama models unloaded (fallback method)")
            except Exception as e:
                print(f"Error getting model list: {e}")
                # Fallback: try common model names
                models_to_unload = ["llava", "mixtral", "llama", "codellama", "mistral", "qwen", "phi", "gemma", "neural-chat"]
                for model in models_to_unload:
                    try:
                        subprocess.run(
                            ["ollama", "stop", model],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                    except:
                        pass  # Silent fail
                print("Ollama models unloaded (fallback method)")
            
            # Clear CUDA cache after unloading
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
            
        except Exception as e:
            print(f"Error in silent unload: {e}")

