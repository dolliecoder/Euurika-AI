import os
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


class Embedder:
    """
    Embedding wrapper using EmbeddingGemma-300M (quantized GGUF).
    Automatically downloads the model if not available locally.
    """
    
    MODEL_NAME = "TaylorAI/gemma-2-2b-it-mixture-embedding-gguf"
    MODEL_FILE = "gemma-2-2b-itmixtureembedding-q4_k_m.gguf"
    LOCAL_DIR = "./models/gemma-embedding"
    
    def __init__(self):
        self.model = self._load_model()
        # Configure LlamaIndex to use this embedder
        Settings.embed_model = self.model
    
    def _load_model(self):
        """Load the embedding model, downloading if necessary."""
        local_path = os.path.join(self.LOCAL_DIR, self.MODEL_FILE)
        
        if os.path.exists(local_path):
            print(f"Loading model from local cache: {local_path}")
            return HuggingFaceEmbedding(
                model_name=self.MODEL_NAME,
                model_kwargs={"device": "cpu"}
            )
        
        print(f"Model not found locally. Downloading {self.MODEL_NAME}...")
        os.makedirs(self.LOCAL_DIR, exist_ok=True)
        
        # This will download the model from HuggingFace
        model = HuggingFaceEmbedding(
            model_name=self.MODEL_NAME,
            model_kwargs={"device": "cpu"}
        )
        
        return model
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors (each vector is a list of floats)
        """
        return self.model.get_text_embedding_batch(texts)
    
    def embed_single(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            Embedding vector as a list of floats
        """
        return self.model.get_text_embedding(text)
    
    @property
    def embedding_dim(self) -> int:
        """Return the dimension of the embedding vectors."""
        return self.model._embed_dim


# Global embedder instance (lazy initialization)
_embedder = None


def get_embedder() -> Embedder:
    """Get the global embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder