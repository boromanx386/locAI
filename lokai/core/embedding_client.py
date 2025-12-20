"""
Embedding Client for locAI.
Handles embedding generation via Ollama API (CPU mode for memory efficiency).
"""

import requests
from typing import Optional, List
import json


class EmbeddingClient:
    """Client for generating embeddings via Ollama API (CPU mode)."""

    def __init__(self, base_url: str = "http://localhost:11434", force_cpu: bool = True):
        """
        Initialize EmbeddingClient.

        Args:
            base_url: Ollama base URL
            force_cpu: If True, uses CPU mode (doesn't interfere with GPU LLM models)
        """
        self.base_url = base_url
        self.force_cpu = force_cpu
        self.session = requests.Session()
        self.timeout = 60
        # Get embedding model from config if available, otherwise use default
        self.default_model = "nomic-embed-text:v1.5"  # Default model

    def generate_embedding(self, text: str, model: str = None) -> Optional[List[float]]:
        """
        Generate embedding for text using Ollama API.
        Runs on CPU if force_cpu=True (doesn't interfere with GPU LLM models).

        Args:
            text: Text to embed
            model: Embedding model name (default: nomic-embed-text)

        Returns:
            Embedding vector as list of floats, or None on error
        """
        if not text or not text.strip():
            return None

        model = model or self.default_model

        try:
            payload = {
                "model": model,
                "prompt": text
            }

            # Ollama uses /api/embeddings endpoint
            response = self.session.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                embedding = data.get("embedding")
                if embedding:
                    return embedding
                else:
                    print(f"No embedding in response: {data}")
                    return None
            else:
                print(f"Error generating embedding: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            print("Embedding request timed out")
            return None
        except requests.exceptions.ConnectionError:
            print("Cannot connect to Ollama server for embeddings")
            return None
        except Exception as e:
            print(f"Error in generate_embedding: {e}")
            return None

    def generate_embeddings_batch(self, texts: List[str], model: str = None) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts (sequential, CPU-friendly).

        Args:
            texts: List of texts to embed
            model: Embedding model name

        Returns:
            List of embedding vectors (None for failed embeddings)
        """
        results = []
        for i, text in enumerate(texts):
            embedding = self.generate_embedding(text, model)
            results.append(embedding)
            if (i + 1) % 10 == 0:
                print(f"Embedded {i + 1}/{len(texts)} texts...")
        return results

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

