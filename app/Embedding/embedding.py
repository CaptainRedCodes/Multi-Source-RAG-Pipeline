from typing import List, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from functools import lru_cache


class EmbeddingManager:

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self._load_model()
        # Simple query cache for repeated queries
        self._query_cache = {}
        self._cache_max_size = 100

    def _load_model(self):
        try:
            self.model = SentenceTransformer(self.model_name)
            print(f"✅ Loaded embedding model: {self.model_name}")
            print(f"📐 Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
        except Exception as e:
            raise ValueError(f"Error loading model: {e}")
    
    def generate_embedding(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings with caching for single queries."""
        if not self.model:
            raise ValueError("Model not initiated")
        
        # For single query, try cache first
        if len(texts) == 1:
            cache_key = texts[0]
            if cache_key in self._query_cache:
                return np.array([self._query_cache[cache_key]])
        
        print(f"🔄 Generating embeddings for {len(texts)} text(s)...")
        embeddings = self.model.encode(texts, show_progress_bar=len(texts) > 5)
        
        # Cache single queries
        if len(texts) == 1:
            if len(self._query_cache) >= self._cache_max_size:
                # Remove oldest entry
                self._query_cache.pop(next(iter(self._query_cache)))
            self._query_cache[texts[0]] = embeddings[0]
        
        return embeddings

