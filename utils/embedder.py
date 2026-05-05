import os
import chromadb.utils.batch_utils as batch_utils
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


class Embedder:
    """
    Embedding wrapper using ChromaDB's default embedding function.
    Uses sentence-transformers/all-MiniLM-L6-v2 (384 dimensions).
    """
    
    def __init__(self):
        # ChromaDB's default embedding function
        self.model = DefaultEmbeddingFunction()
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        return self.model(texts)
    
    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        return self.model([text])[0]
    
    @property
    def embedding_dim(self) -> int:
        """Return the dimension of the embedding vectors."""
        return 384  # all-MiniLM-L6-v2 dimension


# Global embedder instance (lazy initialization)
_embedder = None


def get_embedder() -> Embedder:
    """Get the global embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder