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
        self._model = DefaultEmbeddingFunction()
    
    def __call__(self, input: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts (ChromaDB callable interface)."""
        return self._model(input)
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        return self._model(texts)
    
    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        return self._model([text])[0]
    
    def name(self) -> str:
        """Return the name of the embedding function (required by ChromaDB)."""
        return "default"
    
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