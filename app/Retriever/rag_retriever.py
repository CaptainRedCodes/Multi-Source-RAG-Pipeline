from typing import Any, Dict, List

from app.Embedding.embedding import EmbeddingManager
from app.Embedding.vector_store import VectorStore

class RAGRetriever:

    def __init__(self,vector_store:VectorStore,embedding_manager:EmbeddingManager):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager

    def retrieve(self,query:str,top_k:int = 5,score_threshold:float = 0.25)->List[Dict[str,Any]]:
        """
        Retrieve relevant documents for a query
        """
        print("Starting RAG Retriever")
        query_embeddings = self.embedding_manager.generate_embedding([query])
        try:
            results = self.vector_store.collection.query(
                query_embeddings=query_embeddings,
                n_results=top_k)
            
            retrieved_docs = []
            if results['documents'] and results['documents'][0]:
                documents = results['documents'][0]
                metadatas = results['metadatas'][0]
                distances = results['distances'][0]
                ids = results['ids'][0]


                for i,(doc_id,distance,metadata,document) in enumerate(zip(ids,distances,metadatas,documents)):
                    similarity_score = 1-distance
                    
                    if similarity_score >= score_threshold:
                        retrieved_docs.append({
                            'id': doc_id,
                            'content': document,
                            'metadata': metadata,
                            'similarity_score': similarity_score,
                            'distance': distance,
                            'rank': i + 1
                        })
                
                print(f"Retrieved {len(retrieved_docs)} documents (after filtering)")
            else:
                print("No documents found")
            
            return retrieved_docs
            
        except Exception as e:
            print(f"Error during retrieval: {e}")
            return []
        


