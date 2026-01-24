from typing import Annotated, Any, Dict, List
import asyncio
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
import shutil
import tempfile
from pathlib import Path
import json

from app.Retriever.advanced_rag import AdvancedRAGPipeline
from app.Retriever.llm import LLM
from app.Retriever.rag_retriever import RAGRetriever
from app.Loaders.document_loader import DocumentLoader
from app.Loaders.website_loader import WebLoader
from app.Embedding.chunking import Chunking
from app.Embedding.embedding import EmbeddingManager
from app.Embedding.vector_store import VectorStore
from app.api.helper_functions import process_and_index, process_pdf_background, process_pdfs_background, process_recursive_background, process_sitemap_background, process_webpage_background, process_webpages_background
from app.dependencies import (
    get_llm, get_rag, get_document_loader, get_chunk_loader, 
    get_embedding_manager, get_vector_store, get_web_loader, get_adv_rag,
    get_task_manager
)
from app.models import MultiUrlRequest,QueryRequest,RecursiveUrlRequest, TaskStatus,UrlRequest,SitemapRequest
from app.task_manager import TaskManager
from werkzeug.utils import secure_filename

router = APIRouter()


# --- Dependency Annotations ---
RagDep = Annotated[RAGRetriever, Depends(get_rag)]
LlmDep = Annotated[LLM, Depends(get_llm)]
AdvRagDep = Annotated[AdvancedRAGPipeline, Depends(get_adv_rag)]

DocLoaderDep = Annotated[DocumentLoader, Depends(get_document_loader)]
WebLoaderDep = Annotated[WebLoader, Depends(get_web_loader)]
ChunkDep = Annotated[Chunking, Depends(get_chunk_loader)]
EmbedDep = Annotated[EmbeddingManager, Depends(get_embedding_manager)]
StoreDep = Annotated[VectorStore, Depends(get_vector_store)]
TaskManagerDep = Annotated[TaskManager, Depends(get_task_manager)]





@router.get("/tasks/{task_id}")
def get_task_status(task_id: str, task_manager: TaskManagerDep):
    """Get the status of a background task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task.to_dict()


@router.get("/tasks/{task_id}/stream")
async def stream_task_progress(task_id: str, task_manager: TaskManagerDep):
    """
    Server-Sent Events endpoint for real-time task progress updates.
    
    Usage (JavaScript):
    const eventSource = new EventSource('/api/tasks/{task_id}/stream');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data.progress);
    };
    """
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        task_manager.subscribe(task_id, queue)
        
        try:
            # Send initial state
            current_task = task_manager.get_task(task_id)
            if current_task:
                yield f"data: {json.dumps(current_task.to_dict())}\n\n"
            
            # Stream updates until task completes
            while True:
                try:
                    update = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(update)}\n\n"
                    
                    # Stop if task is done
                    if update.get("status") in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                        break
                        
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f": heartbeat\n\n"
                    
                    # Check if task is done
                    current = task_manager.get_task(task_id)
                    if current and current.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                        yield f"data: {json.dumps(current.to_dict())}\n\n"
                        break
                        
        finally:
            task_manager.unsubscribe(task_id, queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/tasks")
def get_all_tasks(task_manager: TaskManagerDep):
    """Get all tasks (for debugging/admin)."""
    return task_manager.get_all_tasks()


# @router.get("/components/status")
# def get_components_status():
#     """Get initialization status of heavy components."""
#     return get_initialization_status()


# --- Query Endpoints (Synchronous - no change needed) ---

@router.get("/rag_search", response_model=List[Dict[str, Any]])
def rag_search(query: str, rag: RagDep):
    return rag.retrieve(query) or []

@router.get("/llm_search")
def llm_search(query: str, llm: LlmDep):
    return llm.llm_rag_retrive(query)

@router.get("/advanced_query")
def query_advanced_rag(query:str, adv_rag: AdvRagDep):
    results = adv_rag.query(query)
    return {"response": results}


# --- Async Upload Endpoints (Background Processing) ---

@router.post("/upload/pdf/async")
async def upload_pdf_async(
    background_tasks: BackgroundTasks,
    task_manager: TaskManagerDep,
    file: UploadFile = File(...),
):
    """
    Upload and process PDF in background.
    Returns immediately with a task_id for tracking progress.
    """
    if not file:
         raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    if not file.filename:
         raise HTTPException(status_code=400, detail="Filename is missing")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Create task
    task = task_manager.create_task("pdf_upload")
    
    # Save file to temp directory (will be cleaned up by background task)
    temp_dir = tempfile.mkdtemp()
    safe_filename = f"{uuid.uuid4()}.pdf" 
    temp_path = Path(temp_dir) / safe_filename
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Schedule background processing
    background_tasks.add_task(
        process_pdf_background,
        temp_dir,
        file.filename,
        task.id,
        task_manager
    )
    
    return {
        "task_id": task.id,
        "status": "pending",
        "message": "PDF upload started. Use /api/tasks/{task_id} to check progress.",
        "stream_url": f"/api/tasks/{task.id}/stream"
    }


@router.post("/upload/pdfs/async")
async def upload_multiple_pdfs_async(
    background_tasks: BackgroundTasks,
    task_manager: TaskManagerDep,
    files: List[UploadFile] = File(...)
):
    """
    Upload and process multiple PDFs in background.
    Returns immediately with a task_id for tracking progress.
    """
    # Create task
    task = task_manager.create_task("pdfs_upload")
    
    # Save files to temp directory
    temp_dir = tempfile.mkdtemp()
    filenames = []
    
    for file in files:
        if not file.filename:
            raise ValueError("Error in Filename")
        
        if file.filename.endswith('.pdf'):
            safe_filename = secure_filename(file.filename) 
            
            temp_path = Path(temp_dir) / safe_filename
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            filenames.append(file.filename)
    
    if not filenames:
        raise HTTPException(status_code=400, detail="No valid PDF files found.")
    
    # Schedule background processing
    background_tasks.add_task(
        process_pdfs_background,
        temp_dir,
        filenames,
        task.id,
        task_manager
    )
    
    return {
        "task_id": task.id,
        "status": "pending",
        "files_received": len(filenames),
        "message": "PDFs upload started. Use /api/tasks/{task_id} to check progress.",
        "stream_url": f"/api/tasks/{task.id}/stream"
    }


@router.post("/ingest/webpage/async")
async def ingest_webpage_async(
    request: UrlRequest,
    background_tasks: BackgroundTasks,
    task_manager: TaskManagerDep,
):
    """Ingest webpage in background."""
    task = task_manager.create_task("webpage_ingest")
    
    background_tasks.add_task(
        process_webpage_background,
        request.url,
        task.id,
        task_manager
    )
    
    return {
        "task_id": task.id,
        "status": "pending",
        "message": "Webpage ingestion started. Use /api/tasks/{task_id} to check progress.",
        "stream_url": f"/api/tasks/{task.id}/stream"
    }


@router.post("/ingest/webpages/async")
async def ingest_multiple_webpages_async(
    request: MultiUrlRequest,
    background_tasks: BackgroundTasks,
    task_manager: TaskManagerDep,
):
    """Ingest multiple webpages in background."""
    task = task_manager.create_task("webpages_ingest")
    
    background_tasks.add_task(
        process_webpages_background,
        request.urls,
        task.id,
        task_manager
    )
    
    return {
        "task_id": task.id,
        "status": "pending",
        "urls_count": len(request.urls),
        "message": "Webpages ingestion started. Use /api/tasks/{task_id} to check progress.",
        "stream_url": f"/api/tasks/{task.id}/stream"
    }


@router.post("/ingest/sitemap/async")
async def ingest_sitemap_async(
    request: SitemapRequest,
    background_tasks: BackgroundTasks,
    task_manager: TaskManagerDep,
):
    """Ingest sitemap in background."""
    task = task_manager.create_task("sitemap_ingest")
    
    background_tasks.add_task(
        process_sitemap_background,
        request.sitemap_url,
        request.filter_urls or [],
        task.id,
        task_manager
    )
    
    return {
        "task_id": task.id,
        "status": "pending",
        "message": "Sitemap ingestion started. Use /api/tasks/{task_id} to check progress.",
        "stream_url": f"/api/tasks/{task.id}/stream"
    }


@router.post("/ingest/recursive/async")
async def ingest_recursive_async(
    request: RecursiveUrlRequest,
    background_tasks: BackgroundTasks,
    task_manager: TaskManagerDep,
):
    """Recursively crawl and ingest website in background."""
    task = task_manager.create_task("recursive_crawl")
    
    background_tasks.add_task(
        process_recursive_background,
        request.base_url,
        request.max_depth,
        task.id,
        task_manager
    )
    
    return {
        "task_id": task.id,
        "status": "pending",
        "message": "Website crawling started. Use /api/tasks/{task_id} to check progress.",
        "stream_url": f"/api/tasks/{task.id}/stream"
    }


# --- Synchronous Endpoints (Keep for simple use cases) ---

@router.post("/upload/pdf")
async def upload_pdf(
    doc_loader: DocLoaderDep,
    chunk_loader: ChunkDep,
    embed_manager: EmbedDep,
    vector_store: StoreDep,
    file: UploadFile = File(...),
):

    if not file:
        raise ValueError("No files found")
    
    if not file.filename:
        raise ValueError("No file found with this name")
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        safe_filename = secure_filename(file.filename) 
        temp_path = temp / safe_filename
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            docs = doc_loader.load_pdfs(pdf_dir=temp_dir)
            # Reusing the helper function
            count = process_and_index(docs, chunk_loader, embed_manager, vector_store)
            
            return {
                "message": "PDF uploaded and ingested successfully",
                "filename": file.filename,
                "chunks_created": count
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@router.post("/upload/pdfs")
async def upload_multiple_pdfs(
    doc_loader: DocLoaderDep,
    chunk_loader: ChunkDep,
    embed_manager: EmbedDep,
    vector_store: StoreDep,
    files: List[UploadFile] = File(...)
):
    total_chunks = 0
    processed_files = []
    
    with tempfile.TemporaryDirectory() as temp_dir:
        for file in files:
            if not file:
                raise ValueError("No files found")
    
            if not file.filename:
                raise ValueError("No file found with this name")
            
            if file.filename.endswith('.pdf'):
                temp = Path(temp_dir)
                safe_filename = secure_filename(file.filename) 
                temp_path = temp / safe_filename

                with open(temp_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                processed_files.append(file.filename)
        
        if not processed_files:
             raise HTTPException(status_code=400, detail="No valid PDF files found.")

        try:
            # Load ALL pdfs in the directory at once
            docs = doc_loader.load_pdfs(pdf_dir=temp_dir)
            total_chunks = process_and_index(docs, chunk_loader, embed_manager, vector_store)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing PDFs: {str(e)}")
    
    return {
        "message": "PDFs uploaded and ingested successfully",
        "files_processed": len(processed_files),
        "total_chunks_created": total_chunks
    }

@router.post("/upload/csv")
async def upload_csv(
    doc_loader: DocLoaderDep,
    chunk_loader: ChunkDep,
    embed_manager: EmbedDep,
    vector_store: StoreDep,
    file: UploadFile = File(...),
    delimiter: str = Form(default=","),
):
    if not file:
        raise ValueError("No files found")
    if not file.filename:
        raise ValueError("No file found with this name")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        safe_filename = secure_filename(file.filename) 
        temp_path = temp / safe_filename
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            docs = doc_loader.load_csvs(csv_dir=temp_dir, delimiter=delimiter)
            count = process_and_index(docs, chunk_loader, embed_manager, vector_store)
            
            return {
                "message": "CSV uploaded and ingested successfully",
                "filename": file.filename,
                "chunks_created": count
            }
        except Exception as e:
             raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")

@router.post("/ingest/webpage")
async def ingest_webpage(
    request: UrlRequest,
    web_loader: WebLoaderDep,
    chunk_loader: ChunkDep,
    embed_manager: EmbedDep,
    vector_store: StoreDep,
):
    try:
        docs = web_loader.load_single_page(request.url)
        count = process_and_index(docs, chunk_loader, embed_manager, vector_store)
        
        return {
            "message": "Webpage ingested successfully",
            "url": request.url,
            "chunks_created": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing webpage: {str(e)}")

@router.post("/ingest/webpages")
async def ingest_multiple_webpages(
    request: MultiUrlRequest,
    web_loader: WebLoaderDep,
    chunk_loader: ChunkDep,
    embed_manager: EmbedDep,
    vector_store: StoreDep,
):
    try:
        docs = web_loader.load_async_urls(request.urls)
        count = process_and_index(docs, chunk_loader, embed_manager, vector_store)
        
        return {
            "message": "Webpages ingested successfully",
            "urls_processed": len(request.urls),
            "chunks_created": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing webpages: {str(e)}")

@router.post("/ingest/sitemap")
async def ingest_sitemap(
    request: SitemapRequest,
    web_loader: WebLoaderDep,
    chunk_loader: ChunkDep,
    embed_manager: EmbedDep,
    vector_store: StoreDep,
):
    try:
        docs = web_loader.load_sitemap(request.sitemap_url, filter_urls=request.filter_urls)
        count = process_and_index(docs, chunk_loader, embed_manager, vector_store)
        
        return {
            "message": "Sitemap ingested successfully",
            "sitemap_url": request.sitemap_url,
            "chunks_created": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing sitemap: {str(e)}")

@router.post("/ingest/recursive")
async def ingest_recursive_crawl(
    request: RecursiveUrlRequest,
    web_loader: WebLoaderDep,
    chunk_loader: ChunkDep,
    embed_manager: EmbedDep,
    vector_store: StoreDep,
):
    try:
        docs = web_loader.load_recursive(request.base_url, max_depth=request.max_depth)
        count = process_and_index(docs, chunk_loader, embed_manager, vector_store)
        
        return {
            "message": "Website crawled and ingested successfully",
            "base_url": request.base_url,
            "max_depth": request.max_depth,
            "chunks_created": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing website: {str(e)}")

@router.get("/stats")
def get_stats(vector_store: StoreDep, doc_loader: DocLoaderDep):
    count = max(0,vector_store.collection.count())
    return {
        "vector_store_count": count,
        "document_loader_stats": doc_loader.get_stats()
    }

@router.delete("/clear")
def clear_vector_store(vector_store: StoreDep):
    try:
        count = max(0,vector_store.collection.count())
        if count > 0:
            all_data = vector_store.collection.get()
            if all_data['ids']:
                vector_store.collection.delete(ids=all_data['ids'])
        return {"message": "Vector store cleared successfully", "documents_deleted": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing vector store: {str(e)}")