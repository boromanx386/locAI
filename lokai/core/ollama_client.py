"""
Ollama Client for locAI.
Handles API communication with Ollama server for LLM interactions.
"""

import json
import requests
from typing import Optional, Callable, List, Tuple
import threading


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
        self._active_requests = {}  # Track active streaming requests for cancellation
        self._request_lock = threading.Lock()  # Lock for thread-safe request tracking
        self._last_response_metrics = None  # Metrics from most recent completed response

    def get_last_response_metrics(self) -> Optional[dict]:
        """Get metrics from the latest completed Ollama response."""
        with self._request_lock:
            if self._last_response_metrics is None:
                return None
            return dict(self._last_response_metrics)

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
        thinking_callback: Optional[Callable[[str], None]] = None,
        images: Optional[List[str]] = None,
        num_ctx: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        repeat_penalty: Optional[float] = None,
        num_predict: Optional[int] = None,
        seed: Optional[int] = None,
        tools: Optional[List[dict]] = None,
        think: Optional[bool] = None,
        request_id: Optional[str] = None,
    ) -> Tuple[str, Optional[List[int]]]:
        """
        Generate response from model with streaming support.

        Args:
            model: Model name to use
            prompt: User prompt
            context: Previous conversation context
            callback: Optional callback function for streaming chunks
            thinking_callback: Optional callback function for thinking chunks
            images: Optional list of base64-encoded images (for vision models)
            num_ctx: Context window size (optional)
            temperature: Temperature for sampling (optional)
            top_p: Top-p sampling parameter (optional)
            top_k: Top-k sampling parameter (optional)
            repeat_penalty: Repeat penalty (optional)
            num_predict: Maximum tokens to generate, -1 for unlimited (optional)
            seed: Seed for reproducibility, -1 for random (optional)
            tools: Optional list of tools for function calling (optional)
            think: Enable/disable model thinking output when supported (optional)
            request_id: Optional request ID for cancellation tracking

        Returns:
            Tuple of (full_response, new_context)
        """
        # Generate request ID if not provided
        if request_id is None:
            import uuid
            request_id = str(uuid.uuid4())
        
        # Track this request
        with self._request_lock:
            self._active_requests[request_id] = {"cancelled": False, "response": None}
        
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True,
            }
            if think is not None:
                payload["think"] = think

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
            
            # Store response for cancellation
            with self._request_lock:
                if request_id in self._active_requests:
                    self._active_requests[request_id]["response"] = response

            if response.status_code == 200:
                full_response = ""
                new_context = None
                final_metrics = None

                for line in response.iter_lines():
                    # Check for cancellation
                    with self._request_lock:
                        if request_id in self._active_requests and self._active_requests[request_id]["cancelled"]:
                            print(f"Request {request_id} cancelled, closing stream...")
                            response.close()
                            return "", None
                    
                    if line:
                        try:
                            data = json.loads(line.decode("utf-8"))

                            # Handle response chunks
                            if "response" in data:
                                chunk = data["response"]
                                full_response += chunk
                                if callback:
                                    callback(chunk)
                            # Handle thinking chunks (some models stream reasoning separately)
                            if "thinking" in data and thinking_callback:
                                thinking_chunk = data["thinking"]
                                if thinking_chunk:
                                    thinking_callback(thinking_chunk)

                            # Store context for next request
                            if "context" in data:
                                new_context = data["context"]

                            # Check if generation is done
                            if data.get("done", False):
                                final_metrics = {
                                    "prompt_eval_count": data.get("prompt_eval_count"),
                                    "eval_count": data.get("eval_count"),
                                    "total_duration": data.get("total_duration"),
                                    "eval_duration": data.get("eval_duration"),
                                    "model": model,
                                }
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

                with self._request_lock:
                    self._last_response_metrics = final_metrics
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
        finally:
            # Clean up request tracking
            with self._request_lock:
                if request_id in self._active_requests:
                    del self._active_requests[request_id]

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
        thinking_callback: Optional[Callable[[str], None]] = None,
        think: Optional[bool] = None,
        request_id: Optional[str] = None,
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
            thinking_callback: Callback for thinking chunks (optional)
            think: Enable/disable model thinking output when supported (optional)
            request_id: Optional request ID for cancellation tracking
            
        Returns:
            Dict with response message and tool_calls if any
        """
        # Generate request ID if not provided
        if request_id is None:
            import uuid
            request_id = str(uuid.uuid4())
        
        # Track this request
        with self._request_lock:
            self._active_requests[request_id] = {"cancelled": False, "response": None}
        
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": stream,
            }
            if think is not None:
                payload["think"] = think
            
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
            
            # Store response for cancellation
            with self._request_lock:
                if request_id in self._active_requests:
                    self._active_requests[request_id]["response"] = response
            
            if response.status_code == 200:
                if stream:
                    # Streaming mode
                    full_message = {"role": "assistant", "content": ""}
                    tool_calls = []
                    final_metrics = None
                    
                    for line in response.iter_lines():
                        # Check for cancellation
                        with self._request_lock:
                            if request_id in self._active_requests and self._active_requests[request_id]["cancelled"]:
                                print(f"Request {request_id} cancelled, closing stream...")
                                response.close()
                                return {"error": "Request cancelled"}
                        
                        if line:
                            try:
                                data = json.loads(line.decode("utf-8"))
                                
                                if "message" in data:
                                    msg = data["message"]
                                    # Thinking chunks can arrive either in message.thinking or top-level thinking
                                    thinking_chunk = msg.get("thinking", "")
                                    if not thinking_chunk and "thinking" in data:
                                        thinking_chunk = data.get("thinking", "")
                                    if thinking_chunk and thinking_callback:
                                        thinking_callback(thinking_chunk)
                                    
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
                                    final_metrics = {
                                        "prompt_eval_count": data.get("prompt_eval_count"),
                                        "eval_count": data.get("eval_count"),
                                        "total_duration": data.get("total_duration"),
                                        "eval_duration": data.get("eval_duration"),
                                        "model": model,
                                    }
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                    
                    result = {"message": full_message}
                    if tool_calls:
                        result["message"]["tool_calls"] = tool_calls
                    with self._request_lock:
                        self._last_response_metrics = final_metrics
                    return result
                else:
                    # Non-streaming
                    data = response.json()
                    with self._request_lock:
                        self._last_response_metrics = {
                            "prompt_eval_count": data.get("prompt_eval_count"),
                            "eval_count": data.get("eval_count"),
                            "total_duration": data.get("total_duration"),
                            "eval_duration": data.get("eval_duration"),
                            "model": model,
                        }
                    return data
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_msg = error_data.get("error", response.text)
                return {"error": f"HTTP {response.status_code}: {error_msg}"}
                
        except Exception as e:
            return {"error": f"Error: {str(e)}"}
        finally:
            # Clean up request tracking
            with self._request_lock:
                if request_id in self._active_requests:
                    del self._active_requests[request_id]

    def cancel_all_requests(self):
        """Cancel all active streaming requests."""
        with self._request_lock:
            for request_id, request_info in self._active_requests.items():
                request_info["cancelled"] = True
                if request_info["response"] is not None:
                    try:
                        request_info["response"].close()
                    except:
                        pass
            self._active_requests.clear()
    
    def stop_model(self, model_name: str) -> bool:
        """
        Stop/unload a running Ollama model via API (keep_alive=0).

        Args:
            model_name: Name of the model to stop

        Returns:
            True if successful, False otherwise
        """
        return self._unload_via_api(model_name)

    def unload_model(self, model_name: str) -> bool:
        """
        Unload a specific Ollama model from VRAM via API (keep_alive=0).

        Args:
            model_name: Name of the model to unload

        Returns:
            True if successful, False otherwise
        """
        return self._unload_via_api(model_name)

    def _unload_via_api(self, model_name: str) -> bool:
        """
        Unload a model by sending keep_alive=0 to /api/generate.
        This is the official Ollama way to immediately free VRAM.
        Falls back to subprocess 'ollama stop' if the API call fails.
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json={"model": model_name, "prompt": "", "keep_alive": 0},
                timeout=15,
            )
            if response.status_code == 200:
                print(f"[VRAM] Model '{model_name}' unloaded via API (keep_alive=0)")
                return True
            else:
                print(f"[VRAM] API unload failed for '{model_name}': HTTP {response.status_code}, trying subprocess...")
        except Exception as e:
            print(f"[VRAM] API unload error for '{model_name}': {e}, trying subprocess...")

        # Fallback: subprocess ollama stop
        try:
            import subprocess
            result = subprocess.run(
                ["ollama", "stop", model_name],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                print(f"[VRAM] Model '{model_name}' stopped via subprocess")
                return True
            else:
                print(f"[VRAM] subprocess stop failed for '{model_name}': {result.stderr.strip()}")
                return False
        except Exception as e2:
            print(f"[VRAM] Both API and subprocess failed for '{model_name}': {e2}")
            return False

    def unload_all_models_silent(self) -> None:
        """
        Silently unload all loaded Ollama models to free GPU memory.
        Uses /api/ps to get models currently in VRAM, then unloads each via keep_alive=0.
        Verifies unload by checking /api/ps again after.
        """
        try:
            loaded_models = []

            # /api/ps returns only models currently loaded in memory
            try:
                response = self.session.get(
                    f"{self.base_url}/api/ps", timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    for m in data.get("models", []):
                        name = m.get("name") or m.get("model", "")
                        if name and name not in loaded_models:
                            loaded_models.append(name)
                    vram_total = sum(
                        m.get("size_vram", 0) for m in data.get("models", [])
                    )
                    print(f"[VRAM] Found {len(loaded_models)} loaded model(s), ~{vram_total / 1024**3:.1f} GB in VRAM: {loaded_models}")
            except Exception as e:
                print(f"[VRAM] Error querying /api/ps: {e}")

            for model in loaded_models:
                self._unload_via_api(model)

            if loaded_models:
                # Verify unload worked
                import time
                time.sleep(0.5)
                try:
                    response = self.session.get(
                        f"{self.base_url}/api/ps", timeout=5
                    )
                    if response.status_code == 200:
                        data = response.json()
                        still_loaded = [
                            m.get("name", "?") for m in data.get("models", [])
                        ]
                        if still_loaded:
                            print(f"[VRAM] WARNING: Models still loaded after unload: {still_loaded}")
                        else:
                            print(f"[VRAM] Verified: all models unloaded successfully")
                except Exception:
                    pass
            else:
                print("[VRAM] No Ollama models were loaded in memory")

        except Exception as e:
            print(f"[VRAM] Error in silent unload: {e}")
