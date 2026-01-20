
from typing import Optional
import threading

from app.Embedding.chunking import Chunking
from app.Embedding.embedding import EmbeddingManager
from app.Embedding.vector_store import VectorStore
from app.Loaders.document_loader import DocumentLoader
from app.Loaders.website_loader import WebLoader
from app.Retriever.advanced_rag import AdvancedRAGPipeline
from app.Retriever.llm import LLM
from app.Retriever.rag_retriever import RAGRetriever
from app.task_manager import TaskManager


# Thread-safe lazy initialization lock
_lock = threading.Lock()

# Lazy singletons (None until first access)
_vector_store: Optional[VectorStore] = None
_document_loader: Optional[DocumentLoader] = None
_web_loader: Optional[WebLoader] = None
_chunk_loader: Optional[Chunking] = None
_embedding_manager: Optional[EmbeddingManager] = None
_rag_retriever: Optional[RAGRetriever] = None
_llm_retriever: Optional[LLM] = None
_advanced_rag: Optional[AdvancedRAGPipeline] = None
_task_manager: Optional[TaskManager] = None



_initialization_status = {
    "vector_store": {"initialized": False, "error": None},
    "embedding_manager": {"initialized": False, "error": None},
    "llm": {"initialized": False, "error": None},
}

def get_task_manager() -> TaskManager:
    """Dependency injection for FastAPI."""
    global _task_manager
    if _task_manager is None:
        with _lock:
            if _task_manager is None:
                _task_manager = TaskManager()
    return _task_manager

def get_vector_store() -> VectorStore:
    """Get or create VectorStore singleton."""
    global _vector_store
    if _vector_store is None:
        with _lock:
            if _vector_store is None:
                print("Lazy loading VectorStore...")
                try:
                    _vector_store = VectorStore()
                    _initialization_status["vector_store"]["initialized"] = True
                    print("VectorStore initialized")
                except Exception as e:
                    _initialization_status["vector_store"]["error"] = str(e)
                    raise
    return _vector_store


def get_document_loader() -> DocumentLoader:
    """Get or create DocumentLoader singleton (lightweight, no lazy loading needed)."""
    global _document_loader
    if _document_loader is None:
        with _lock:
            if _document_loader is None:
                _document_loader = DocumentLoader()
    return _document_loader


def get_web_loader() -> WebLoader:
    """Get or create WebLoader singleton (lightweight, no lazy loading needed)."""
    global _web_loader
    if _web_loader is None:
        with _lock:
            if _web_loader is None:
                _web_loader = WebLoader()
    return _web_loader


def get_chunk_loader() -> Chunking:
    """Get or create Chunking singleton (lightweight, no lazy loading needed)."""
    global _chunk_loader
    if _chunk_loader is None:
        with _lock:
            if _chunk_loader is None:
                _chunk_loader = Chunking()
    return _chunk_loader


def get_embedding_manager() -> EmbeddingManager:
    """Get or create EmbeddingManager singleton (HEAVY - downloads model on first use)."""
    global _embedding_manager
    if _embedding_manager is None:
        with _lock:
            if _embedding_manager is None:
                print("Lazy loading EmbeddingManager (this may take a while on first run)...")
                try:
                    _embedding_manager = EmbeddingManager()
                    _initialization_status["embedding_manager"]["initialized"] = True
                    print("EmbeddingManager initialized")
                except Exception as e:
                    _initialization_status["embedding_manager"]["error"] = str(e)
                    raise
    return _embedding_manager


def get_rag() -> RAGRetriever:
    """Get or create RAGRetriever singleton."""
    global _rag_retriever
    if _rag_retriever is None:
        with _lock:
            if _rag_retriever is None:
                print("Lazy loading RAGRetriever...")
                _rag_retriever = RAGRetriever(
                    get_vector_store(), 
                    get_embedding_manager()
                )
                print("RAGRetriever initialized")
    return _rag_retriever


def get_llm() -> LLM:
    """Get or create LLM singleton."""
    global _llm_retriever
    if _llm_retriever is None:
        with _lock:
            if _llm_retriever is None:
                print("Lazy loading LLM...")
                try:
                    _llm_retriever = LLM(get_rag())
                    _initialization_status["llm"]["initialized"] = True
                    print("LLM initialized")
                except Exception as e:
                    _initialization_status["llm"]["error"] = str(e)
                    raise
    return _llm_retriever


def get_adv_rag() -> AdvancedRAGPipeline:
    """Get or create AdvancedRAGPipeline singleton."""
    global _advanced_rag
    if _advanced_rag is None:
        with _lock:
            if _advanced_rag is None:
                print("Lazy loading AdvancedRAGPipeline...")
                _advanced_rag = AdvancedRAGPipeline(get_rag(), get_llm())
                print("AdvancedRAGPipeline initialized")
    return _advanced_rag


def get_initialization_status() -> dict:
    """Get the initialization status of all heavy components."""
    return _initialization_status.copy()


def preload_components():
    """
    Preload all components in background.
    Call this in a background task if you want to warm up the cache.
    """
    print("Preloading all components...")
    get_vector_store()
    get_embedding_manager()
    get_rag()
    get_llm()
    get_adv_rag()
    get_task_manager()


