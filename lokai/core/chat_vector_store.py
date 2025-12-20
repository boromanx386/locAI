"""
Chat Vector Store for locAI.
Stores and searches chat message embeddings for semantic memory.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score (0-1)
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


class ChatVectorStore:
    """Vector store for chat message embeddings."""

    def __init__(self, storage_path: Path):
        """
        Initialize ChatVectorStore.

        Args:
            storage_path: Path to JSON file for storing embeddings
        """
        self.storage_path = Path(storage_path)
        self.embeddings: List[List[float]] = []
        self.messages: List[Dict] = []  # List of {"role": "...", "content": "...", "index": N}
        self._load_from_disk()

    def _load_from_disk(self):
        """Load embeddings from disk."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.embeddings = data.get("embeddings", [])
                    self.messages = data.get("messages", [])
                print(f"Loaded {len(self.messages)} embedded messages from disk")
            except Exception as e:
                print(f"Error loading vector store: {e}")
                self.embeddings = []
                self.messages = []

    def _save_to_disk(self):
        """Save embeddings to disk."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "embeddings": self.embeddings,
                "messages": self.messages
            }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving vector store: {e}")

    def add_message(self, message: Dict, embedding: List[float], index: int):
        """
        Add message with embedding.

        Args:
            message: Message dict with "role" and "content"
            embedding: Embedding vector
            index: Index in conversation history
        """
        self.messages.append({
            "role": message["role"],
            "content": message["content"],
            "index": index
        })
        self.embeddings.append(embedding)
        # Save periodically (every 10 messages) to avoid too frequent disk writes
        if len(self.messages) % 10 == 0:
            self._save_to_disk()
    
    def force_save(self):
        """Force save embeddings to disk immediately."""
        self._save_to_disk()
        print(f"Force saved {len(self.messages)} embeddings to {self.storage_path}")

    def search(
        self, query_embedding: List[float], top_k: int = 5, exclude_recent: int = 10
    ) -> List[Dict]:
        """
        Semantic search - returns top-K most relevant messages.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            exclude_recent: Exclude last N messages (they're already included)

        Returns:
            List of message dicts with highest similarity
        """
        if len(self.embeddings) <= exclude_recent:
            return []

        # Search only through older messages
        searchable_indices = list(range(len(self.embeddings) - exclude_recent))
        if not searchable_indices:
            return []

        similarities = []
        for idx in searchable_indices:
            similarity = cosine_similarity(query_embedding, self.embeddings[idx])
            similarities.append((similarity, idx))

        # Sort by similarity (descending)
        similarities.sort(reverse=True, key=lambda x: x[0])

        # Return top-K messages
        results = []
        for similarity, idx in similarities[:top_k]:
            msg = self.messages[idx].copy()
            msg["similarity"] = similarity  # Add similarity score for debugging
            results.append(msg)

        return results

    def clear(self):
        """Clear all embeddings (when starting new chat)."""
        self.embeddings = []
        self.messages = []
        self._save_to_disk()
        print("Chat vector store cleared")

    def get_stats(self) -> Dict:
        """
        Get statistics about stored embeddings.

        Returns:
            Dict with stats
        """
        return {
            "total_messages": len(self.messages),
            "total_embeddings": len(self.embeddings),
            "storage_path": str(self.storage_path)
        }

    def remove_messages_after_index(self, index: int):
        """
        Remove all messages after given index (when user clears chat history).

        Args:
            index: Remove messages with index > this value
        """
        # Filter messages and embeddings
        filtered_messages = []
        filtered_embeddings = []
        
        for msg, emb in zip(self.messages, self.embeddings):
            if msg["index"] <= index:
                filtered_messages.append(msg)
                filtered_embeddings.append(emb)
        
        self.messages = filtered_messages
        self.embeddings = filtered_embeddings
        self._save_to_disk()
        print(f"Removed messages after index {index}, {len(self.messages)} remaining")


