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
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
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
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
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
        seed: Optional[int] = None,
        tools: Optional[List[dict]] = None,
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
            tools: Optional list of tools for function calling (optional)

        Returns:
            Tuple of (full_response, new_context)
        """
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True,
            }

            # Add context if provided (check like in old code)
            if context is not None and context:
                payload["context"] = context

            # Build options object - this overrides server/model settings
            # Using options object ensures parameters are applied regardless of Ollama server config
            options = {}
            if num_ctx is not None:
                options["num_ctx"] = num_ctx
            if temperature is not None:
                options["temperature"] = temperature
            if top_p is not None:
                options["top_p"] = top_p
            if top_k is not None:
                options["top_k"] = top_k
            if repeat_penalty is not None:
                options["repeat_penalty"] = repeat_penalty
            if num_predict is not None:
                options["num_predict"] = num_predict
            if seed is not None and seed != -1:
                options["seed"] = seed

            # Only add options if we have at least one parameter
            # This ensures we override server settings when parameters are provided
            if options:
                payload["options"] = options

            # Add tools for function calling (if supported by model)
            if tools is not None and len(tools) > 0:
                payload["tools"] = tools

            # Add images if provided (for vision models like LLaVA)
            if images and len(images) > 0:
                payload["images"] = images
                print(f"Sending {len(images)} image(s) to model {model}")

            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=self.timeout,
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
                        new_context,
                    )

                return full_response, new_context
            else:
                # Try to parse error response
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", response.text)
                except:
                    error_msg = response.text

                full_error = f"HTTP {response.status_code}: {error_msg}"
                print(f"Ollama API error: {full_error}")

                # Provide more helpful error messages
                if response.status_code == 500:
                    if (
                        "model runner" in error_msg.lower()
                        or "unexpectedly stopped" in error_msg.lower()
                    ):
                        return (
                            "Model runner stopped unexpectedly. This may be due to:\n"
                            "- Insufficient GPU/CPU memory\n"
                            "- Model not properly loaded\n"
                            "- Image too large or in unsupported format\n\n"
                            "Try:\n"
                            "1. Restart Ollama server\n"
                            "2. Use a smaller image\n"
                            "3. Ensure you're using a vision model (llava, llama3.2-vision, etc.)",
                            None,
                        )

                return f"Error generating response: {full_error}", None

        except requests.exceptions.Timeout:
            return (
                "Request timed out. The model might be taking too long to respond.",
                None,
            )
        except requests.exceptions.ConnectionError:
            return (
                "Cannot connect to Ollama server. Please ensure Ollama is running.",
                None,
            )
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
        seed: Optional[int] = None,
        tools: Optional[List[dict]] = None,
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
            tools: Optional list of tools for function calling (optional)

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
            seed=seed,
            tools=tools,
        )

        return response, new_context

    def chat_with_tools(
        self,
        model: str,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        num_ctx: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        repeat_penalty: Optional[float] = None,
        num_predict: Optional[int] = None,
        seed: Optional[int] = None,
        stream: bool = False,
        callback: Optional[Callable[[str], None]] = None,
    ) -> dict:
        """
        Chat API endpoint koji bolje podržava tools/function calling.
        
        Args:
            model: Model name to use
            messages: List of messages in format [{"role": "user", "content": "..."}]
            tools: Optional list of tools for function calling
            num_ctx: Context window size (optional)
            temperature: Temperature for sampling (optional)
            top_p: Top-p sampling parameter (optional)
            top_k: Top-k sampling parameter (optional)
            repeat_penalty: Repeat penalty (optional)
            num_predict: Maximum tokens to generate (optional)
            seed: Seed for reproducibility (optional)
            stream: Enable streaming (optional)
            callback: Callback for streaming chunks (optional)
            
        Returns:
            Dict with response message and tool_calls if any
        """
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": stream,
            }
            
            # Build options object
            options = {}
            if num_ctx is not None:
                options["num_ctx"] = num_ctx
            if temperature is not None:
                options["temperature"] = temperature
            if top_p is not None:
                options["top_p"] = top_p
            if top_k is not None:
                options["top_k"] = top_k
            if repeat_penalty is not None:
                options["repeat_penalty"] = repeat_penalty
            if num_predict is not None:
                options["num_predict"] = num_predict
            if seed is not None and seed != -1:
                options["seed"] = seed
                
            if options:
                payload["options"] = options
                
            # Add tools
            if tools is not None and len(tools) > 0:
                payload["tools"] = tools
            
            response = self.session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=stream,
                timeout=self.timeout,
            )
            
            if response.status_code == 200:
                if stream:
                    # Streaming mode
                    full_message = {"role": "assistant", "content": ""}
                    tool_calls = []
                    
                    for line in response.iter_lines():
                        if line:
                            try:
                                data = json.loads(line.decode("utf-8"))
                                
                                if "message" in data:
                                    msg = data["message"]
                                    
                                    # Content chunks
                                    if "content" in msg and msg["content"]:
                                        chunk = msg["content"]
                                        full_message["content"] += chunk
                                        if callback:
                                            callback(chunk)
                                    
                                    # Tool calls
                                    if "tool_calls" in msg and msg["tool_calls"]:
                                        for tool_call in msg["tool_calls"]:
                                            existing = next((tc for tc in tool_calls if tc.get("id") == tool_call.get("id")), None)
                                            if existing:
                                                if "function" in tool_call and "arguments" in tool_call["function"]:
                                                    if "function" not in existing:
                                                        existing["function"] = {}
                                                    if "arguments" not in existing["function"]:
                                                        existing["function"]["arguments"] = ""
                                                    existing["function"]["arguments"] += tool_call["function"]["arguments"]
                                            else:
                                                tool_calls.append(tool_call)
                                
                                if data.get("done", False):
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                    
                    result = {"message": full_message}
                    if tool_calls:
                        result["message"]["tool_calls"] = tool_calls
                    return result
                else:
                    # Non-streaming
                    data = response.json()
                    return data
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get("error", response.text)
                return {"error": f"HTTP {response.status_code}: {error_msg}"}
                
        except Exception as e:
            return {"error": f"Error: {str(e)}"}

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
                timeout=10,
            )
            
            # Aggressive GPU memory cleanup after unload
            try:
                import torch
                import gc
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                    for _ in range(5):
                        torch.cuda.empty_cache()
                    try:
                        torch.cuda.ipc_collect()
                    except AttributeError:
                        pass
                    try:
                        torch.cuda.reset_peak_memory_stats()
                    except:
                        pass
                    gc.collect()
            except:
                pass
            
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
                    ["ollama", "list"], capture_output=True, text=True, timeout=10
                )

                if result.returncode == 0:
                    # Parse output to get model names
                    lines = result.stdout.strip().split("\n")
                    loaded_models = []
                    for line in lines[1:]:  # Skip header
                        if line.strip():
                            parts = line.split()
                            if len(parts) > 0:
                                model_name = parts[0]
                                # Extract base model name (before ':')
                                if ":" in model_name:
                                    model_name = model_name.split(":")[0]
                                if model_name not in loaded_models:
                                    loaded_models.append(model_name)

                    # Unload all loaded models
                    for model in loaded_models:
                        try:
                            subprocess.run(
                                ["ollama", "stop", model],
                                capture_output=True,
                                text=True,
                                timeout=5,
                            )
                        except:
                            pass  # Silent fail

                    if loaded_models:
                        print(
                            f"Unloaded {len(loaded_models)} Ollama model(s): {', '.join(loaded_models)}"
                        )
                    else:
                        print("No Ollama models were loaded")
                else:
                    # Fallback: try common model names
                    models_to_unload = [
                        "llava",
                        "mixtral",
                        "llama",
                        "codellama",
                        "mistral",
                        "qwen",
                        "phi",
                        "gemma",
                        "neural-chat",
                    ]
                    for model in models_to_unload:
                        try:
                            subprocess.run(
                                ["ollama", "stop", model],
                                capture_output=True,
                                text=True,
                                timeout=5,
                            )
                        except:
                            pass  # Silent fail
                    print("Ollama models unloaded (fallback method)")
            except Exception as e:
                print(f"Error getting model list: {e}")
                # Fallback: try common model names
                models_to_unload = [
                    "llava",
                    "mixtral",
                    "llama",
                    "codellama",
                    "mistral",
                    "qwen",
                    "phi",
                    "gemma",
                    "neural-chat",
                ]
                for model in models_to_unload:
                    try:
                        subprocess.run(
                            ["ollama", "stop", model],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                    except:
                        pass  # Silent fail
                print("Ollama models unloaded (fallback method)")

            # Clear CUDA cache after unloading (aggressive cleanup)
            try:
                import torch
                import gc

                if torch.cuda.is_available():
                    torch.cuda.synchronize()  # Wait for all operations to complete
                    torch.cuda.empty_cache()  # Clear cache
                    torch.cuda.empty_cache()  # Second pass
                    try:
                        torch.cuda.ipc_collect()  # Collect IPC resources
                    except AttributeError:
                        pass
                    gc.collect()  # Force garbage collection
            except:
                pass

        except Exception as e:
            print(f"Error in silent unload: {e}")
