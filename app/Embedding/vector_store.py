import os
from pathlib import Path
from typing import Any, List
import chromadb
import uuid
import numpy as np

class VectorStore:

    def __init__(self,collection_name:str="pdf_documents",persist_dir:str = "../data/vector_store"):
        self.collection_name = collection_name
        
        if persist_dir is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.persist_dir = base_dir / "data" / "vector_store"
        else:
            self.persist_dir = Path(persist_dir).resolve()

        self.client = None
        self.collection = None
        self._initialize_store()
    
    def _initialize_store(self):
        try:
            os.makedirs(self.persist_dir,exist_ok = True)
            self.client = chromadb.PersistentClient(path=self.persist_dir)

            self.collection=self.client.get_or_create_collection(
                name = self.collection_name,
                metadata={"description":"PDF embeddings for RAG"})
            print("Vector store has been Initialized for Collection:",{self.collection_name})

        except Exception as e:
            raise ValueError("error in Vector Store initializing",e)
        
    def add_documents(self,documents:List[Any],embeddings:np.ndarray):

        if(len(documents)!=len(embeddings)):
            raise ValueError("Error")
        
        ids = []
        metadatas=[]
        document_text = []
        embedding_list = []

        for i,(doc,embed) in enumerate(zip(documents,embeddings)):
            doc_id = f"doc_{uuid.uuid4().hex[:8]}_{i}"
            ids.append(doc_id)

            metadata = dict(doc.metadata)
            metadata['doc_index'] = i
            metadata['content_length'] = len(doc.page_content)

            metadatas.append(metadata)
            document_text.append(doc.page_content)
            
            embedding_list.append(embed.tolist())

        if not documents or not embedding_list:
            raise ValueError("Documents or embeddings are empty")

        if not ids and not metadatas and not documents and not embedding_list:
            raise ValueError("Error")
        try:
            self.collection.add(
                ids = ids,
                metadatas=metadatas,
                documents=document_text,
                embeddings=embedding_list

            )
        except Exception as e:
            raise ValueError(e)
    

