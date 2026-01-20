
import shutil
from typing import List
from fastapi import HTTPException
from app.Embedding.chunking import Chunking
from app.Embedding.embedding import EmbeddingManager
from app.Embedding.vector_store import VectorStore
from app.dependencies import get_chunk_loader, get_document_loader, get_embedding_manager, get_vector_store, get_web_loader
from app.task_manager import TaskManager


def process_and_index(
    docs: list, 
    chunk_loader: Chunking, 
    embedding_manager: EmbeddingManager, 
    vector_store: VectorStore,
    task_manager: TaskManager = None,
    task_id: str = None
) -> int:
    """
    Centralized Pipeline: Chunk -> Filter -> Embed -> Store
    Returns: Number of chunks created.
    """
    if not docs:
        raise HTTPException(status_code=400, detail="No content extracted from source.")

    # Step 1: Chunking (20%)
    if task_manager and task_id:
        task_manager.update_progress(task_id, "Chunking documents...", 10, 0, len(docs))
    
    chunks = chunk_loader.recursive_text_splitter(docs)
    filtered_chunks = [doc for doc in chunks if doc.page_content.strip()]
    
    if not filtered_chunks:
        raise HTTPException(status_code=400, detail="No valid content after chunking.")
    
    if task_manager and task_id:
        task_manager.update_progress(task_id, "Chunking complete", 30, len(filtered_chunks), len(filtered_chunks))

    # Step 2: Embedding (30% - 80%)
    if task_manager and task_id:
        task_manager.update_progress(task_id, "Generating embeddings...", 40, 0, len(filtered_chunks))
    
    texts = [doc.page_content for doc in filtered_chunks]
    embeddings = embedding_manager.generate_embedding(texts)
    
    if embeddings is None or len(embeddings) == 0:
        raise HTTPException(status_code=500, detail="Embeddings generation failed")
    
    if task_manager and task_id:
        task_manager.update_progress(task_id, "Embeddings generated", 80, len(embeddings), len(filtered_chunks))
    
    # Step 3: Store (80% - 100%)
    if task_manager and task_id:
        task_manager.update_progress(task_id, "Storing in vector database...", 90, 0, len(filtered_chunks))
    
    vector_store.add_documents(filtered_chunks, embeddings)
    
    if task_manager and task_id:
        task_manager.update_progress(task_id, "Complete", 100, len(filtered_chunks), len(filtered_chunks))
    
    return len(filtered_chunks)


# --- Background Processing Functions ---

def process_pdf_background(
    temp_dir: str,
    filename: str,
    task_id: str,
    task_manager: TaskManager
):
    """Background task for PDF processing."""
    try:
        task_manager.update_progress(task_id, "Loading PDF...", 5, 0, 1)
        
        # Get dependencies (lazy loaded)
        doc_loader = get_document_loader()
        chunk_loader = get_chunk_loader()
        embed_manager = get_embedding_manager()
        vector_store = get_vector_store()
        
        task_manager.update_progress(task_id, "Extracting content from PDF...", 15, 0, 1)
        docs = doc_loader.load_pdfs(pdf_dir=temp_dir)
        
        count = process_and_index(
            docs, chunk_loader, embed_manager, vector_store,
            task_manager, task_id
        )
        
        task_manager.complete_task(task_id, {
            "message": "PDF uploaded and ingested successfully",
            "filename": filename,
            "chunks_created": count
        })
        
    except Exception as e:
        task_manager.fail_task(task_id, str(e))
    finally:
        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def process_pdfs_background(
    temp_dir: str,
    filenames: List[str],
    task_id: str,
    task_manager: TaskManager
):
    """Background task for multiple PDF processing."""
    try:
        task_manager.update_progress(task_id, "Loading PDFs...", 5, 0, len(filenames))
        
        doc_loader = get_document_loader()
        chunk_loader = get_chunk_loader()
        embed_manager = get_embedding_manager()
        vector_store = get_vector_store()
        
        task_manager.update_progress(task_id, "Extracting content from PDFs...", 15, 0, len(filenames))
        docs = doc_loader.load_pdfs(pdf_dir=temp_dir)
        
        count = process_and_index(
            docs, chunk_loader, embed_manager, vector_store,
            task_manager, task_id
        )
        
        task_manager.complete_task(task_id, {
            "message": "PDFs uploaded and ingested successfully",
            "files_processed": len(filenames),
            "total_chunks_created": count
        })
        
    except Exception as e:
        task_manager.fail_task(task_id, str(e))
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def process_webpage_background(
    url: str,
    task_id: str,
    task_manager: TaskManager
):
    """Background task for webpage processing."""
    try:
        task_manager.update_progress(task_id, "Loading webpage...", 10, 0, 1)
        
        web_loader = get_web_loader()
        chunk_loader = get_chunk_loader()
        embed_manager = get_embedding_manager()
        vector_store = get_vector_store()
        
        task_manager.update_progress(task_id, "Extracting content...", 20, 0, 1)
        docs = web_loader.load_single_page(url)
        
        count = process_and_index(
            docs, chunk_loader, embed_manager, vector_store,
            task_manager, task_id
        )
        
        task_manager.complete_task(task_id, {
            "message": "Webpage ingested successfully",
            "url": url,
            "chunks_created": count
        })
        
    except Exception as e:
        task_manager.fail_task(task_id, str(e))


def process_webpages_background(
    urls: List[str],
    task_id: str,
    task_manager: TaskManager
):
    """Background task for multiple webpage processing."""
    try:
        task_manager.update_progress(task_id, f"Loading {len(urls)} webpages...", 10, 0, len(urls))
        
        web_loader = get_web_loader()
        chunk_loader = get_chunk_loader()
        embed_manager = get_embedding_manager()
        vector_store = get_vector_store()
        
        task_manager.update_progress(task_id, "Extracting content...", 20, 0, len(urls))
        docs = web_loader.load_async_urls(urls)
        
        count = process_and_index(
            docs, chunk_loader, embed_manager, vector_store,
            task_manager, task_id
        )
        
        task_manager.complete_task(task_id, {
            "message": "Webpages ingested successfully",
            "urls_processed": len(urls),
            "chunks_created": count
        })
        
    except Exception as e:
        task_manager.fail_task(task_id, str(e))


def process_sitemap_background(
    sitemap_url: str,
    filter_urls: List[str],
    task_id: str,
    task_manager: TaskManager
):
    """Background task for sitemap processing."""
    try:
        task_manager.update_progress(task_id, "Loading sitemap...", 10, 0, 1)
        
        web_loader = get_web_loader()
        chunk_loader = get_chunk_loader()
        embed_manager = get_embedding_manager()
        vector_store = get_vector_store()
        
        task_manager.update_progress(task_id, "Extracting pages from sitemap...", 20, 0, 1)
        docs = web_loader.load_sitemap(sitemap_url, filter_urls=filter_urls)
        
        count = process_and_index(
            docs, chunk_loader, embed_manager, vector_store,
            task_manager, task_id
        )
        
        task_manager.complete_task(task_id, {
            "message": "Sitemap ingested successfully",
            "sitemap_url": sitemap_url,
            "chunks_created": count
        })
        
    except Exception as e:
        task_manager.fail_task(task_id, str(e))


def process_recursive_background(
    base_url: str,
    max_depth: int,
    task_id: str,
    task_manager: TaskManager
):
    """Background task for recursive website crawling."""
    try:
        task_manager.update_progress(task_id, f"Crawling website (depth: {max_depth})...", 10, 0, 1)
        
        web_loader = get_web_loader()
        chunk_loader = get_chunk_loader()
        embed_manager = get_embedding_manager()
        vector_store = get_vector_store()
        
        task_manager.update_progress(task_id, "Extracting content from pages...", 20, 0, 1)
        docs = web_loader.load_recursive(base_url, max_depth=max_depth)
        
        count = process_and_index(
            docs, chunk_loader, embed_manager, vector_store,
            task_manager, task_id
        )
        
        task_manager.complete_task(task_id, {
            "message": "Website crawled and ingested successfully",
            "base_url": base_url,
            "max_depth": max_depth,
            "chunks_created": count
        })
        
    except Exception as e:
        task_manager.fail_task(task_id, str(e))


# --- Task Status Endpoints ---