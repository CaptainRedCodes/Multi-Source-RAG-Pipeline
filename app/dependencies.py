import threading
import logging
from typing import Optional, Dict, Any

from app.Embedding.chunking import Chunking
from app.Embedding.embedding import EmbeddingManager
from app.Embedding.vector_store import VectorStore
from app.Loaders.document_loader import DocumentLoader
from app.Loaders.website_loader import WebLoader
from app.Retriever.advanced_rag import AdvancedRAGPipeline
from app.Retriever.llm import LLM
from app.Retriever.rag_retriever import RAGRetriever
from app.task_manager import TaskManager

# Configure logging
logger = logging.getLogger(__name__)

class ComponentManager:
    """
    Singleton manager to handle lazy loading and dependency injection 
    of all application components.
    """
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        # Raw Components
        self._vector_store: Optional[VectorStore] = None
        self._document_loader: Optional[DocumentLoader] = None
        self._web_loader: Optional[WebLoader] = None
        self._chunk_loader: Optional[Chunking] = None
        self._embedding_manager: Optional[EmbeddingManager] = None
        self._task_manager: Optional[TaskManager] = None
        
        # Complex Components (depend on others)
        self._rag_retriever: Optional[RAGRetriever] = None
        self._llm: Optional[LLM] = None
        self._advanced_rag: Optional[AdvancedRAGPipeline] = None

        # Status tracking
        self.status: Dict[str, Any] = {
            "vector_store": "pending",
            "embedding_manager": "pending",
            "llm": "pending",
            "rag": "pending"
        }

    @classmethod
    def get_instance(cls):
        """Standard Singleton Pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_task_manager(self) -> TaskManager:
        if self._task_manager is None:
            with self._lock:
                if self._task_manager is None:
                    self._task_manager = TaskManager()
        return self._task_manager

    def get_vector_store(self) -> VectorStore:
        if self._vector_store is None:
            with self._lock:
                if self._vector_store is None:
                    try:
                        logger.info("Initializing VectorStore...")
                        self._vector_store = VectorStore()
                        self.status["vector_store"] = "ready"
                    except Exception as e:
                        self.status["vector_store"] = f"error: {str(e)}"
                        logger.error(f"Failed to load VectorStore: {e}")
                        raise
        return self._vector_store

    def get_embedding_manager(self) -> EmbeddingManager:
        if self._embedding_manager is None:
            with self._lock:
                if self._embedding_manager is None:
                    try:
                        logger.info("Initializing EmbeddingManager (Heavy Load)...")
                        self._embedding_manager = EmbeddingManager()
                        self.status["embedding_manager"] = "ready"
                    except Exception as e:
                        self.status["embedding_manager"] = f"error: {str(e)}"
                        raise
        return self._embedding_manager

    def get_rag(self) -> RAGRetriever:
        if self._rag_retriever is None:
            # Get dependencies first (outside the lock if possible, or inside if thread safety is critical)
            vs = self.get_vector_store()
            em = self.get_embedding_manager()
            
            with self._lock:
                if self._rag_retriever is None:
                    logger.info("Initializing RAGRetriever...")
                    self._rag_retriever = RAGRetriever(vs, em)
                    self.status["rag"] = "ready"
        return self._rag_retriever

    def get_llm(self) -> LLM:
        if self._llm is None:
            # Ensure RAG is ready before creating LLM
            rag = self.get_rag()
            
            with self._lock:
                if self._llm is None:
                    try:
                        logger.info("Initializing LLM (Heavy Load)...")
                        # 
                        self._llm = LLM(rag) 
                        self.status["llm"] = "ready"
                        logger.info("LLM Successfully Initialized")
                    except Exception as e:
                        self.status["llm"] = f"error: {str(e)}"
                        logger.error(f"Failed to initialize LLM: {e}")
                        raise
        return self._llm

    def get_adv_rag(self) -> AdvancedRAGPipeline:
        if self._advanced_rag is None:
            rag = self.get_rag()
            llm = self.get_llm()
            
            with self._lock:
                if self._advanced_rag is None:
                    logger.info("Initializing AdvancedRAGPipeline...")
                    self._advanced_rag = AdvancedRAGPipeline(rag, llm)
        return self._advanced_rag

    # Lightweight Loaders
    def get_document_loader(self) -> DocumentLoader:
        if self._document_loader is None:
            self._document_loader = DocumentLoader()
        return self._document_loader

    def get_web_loader(self) -> WebLoader:
        if self._web_loader is None:
            self._web_loader = WebLoader()
        return self._web_loader

    def get_chunk_loader(self) -> Chunking:
        if self._chunk_loader is None:
            self._chunk_loader = Chunking()
        return self._chunk_loader

# --- Public Accessors for FastAPI Dependencies ---

# Create the global instance
manager = ComponentManager.get_instance()

def get_vector_store(): return manager.get_vector_store()
def get_embedding_manager(): return manager.get_embedding_manager()
def get_rag(): return manager.get_rag()
def get_llm(): return manager.get_llm()
def get_adv_rag(): return manager.get_adv_rag()
def get_task_manager(): return manager.get_task_manager()
def get_status(): return manager.status
def get_document_loader(): return manager.get_document_loader()
def get_chunk_loader():return manager.get_chunk_loader()
def get_web_loader():return manager.get_web_loader()
#def get_initialization_status():return manager.get_initialization_status()
# --- Startup Helper ---
def preload_components():
    """Call this on app startup to warm up caches"""
    logger.info("--- Starting Component Preload ---")
    manager.get_adv_rag() # This chain loads everything: LLM -> RAG -> VectorStore/Embeddings
    logger.info("--- Component Preload Complete ---")