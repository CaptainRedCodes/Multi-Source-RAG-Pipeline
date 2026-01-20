from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer



class EmbeddingManager:

    def __init__(self,model_name="all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
            try:
                self.model=SentenceTransformer(self.model_name)
                print("Loading model",{self.model_name})
                print(self.model.get_sentence_embedding_dimension())
            except Exception as e:
                raise ValueError("error in load_model")
    
    def generate_embedding(self,texts:List[str]) -> np.ndarray:
            print("Generating Embeddings")
            if not self.model:
                raise ValueError("model not initiated")
            
            embeddings = self.model.encode(texts,show_progress_bar=True)
            return embeddings
        
