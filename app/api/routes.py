from typing import Annotated, Any, Dict, List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
import shutil
import tempfile
from pathlib import Path

from app.Retriever.advanced_rag import AdvancedRAGPipeline
from app.Retriever.llm import LLM
from app.Retriever.rag_retriever import RAGRetriever
from app.Loaders.document_loader import DocumentLoader
from app.Loaders.website_loader import WebLoader
from app.Embedding.chunking import Chunking
from app.Embedding.embedding import EmbeddingManager
from app.Embedding.vector_store import VectorStore
from app.dependencies import (
    get_llm, get_rag, get_document_loader, get_chunk_loader, 
    get_embedding_manager, get_vector_store, get_web_loader, get_adv_rag
)
from app.models import UrlRequest
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


def process_and_index(
    docs: list, 
    chunk_loader: Chunking, 
    embedding_manager: EmbeddingManager, 
    vector_store: VectorStore
) -> int:
    """
    Centralized Pipeline: Chunk -> Filter -> Embed -> Store
    Returns: Number of chunks created.
    """
    if not docs:
        raise HTTPException(status_code=400, detail="No content extracted from source.")

    # Step 1: Chunking
    chunks = chunk_loader.recursive_text_splitter(docs)
    filtered_chunks = [doc for doc in chunks if doc.page_content.strip()]
    
    if not filtered_chunks:
        raise HTTPException(status_code=400, detail="No valid content after chunking.")

    # Step 2: Embedding
    texts = [doc.page_content for doc in filtered_chunks]
    embeddings = embedding_manager.generate_embedding(texts)
    
    if embeddings is None or len(embeddings) == 0:
        raise HTTPException(status_code=500, detail="Embeddings generation failed")
    
    # Step 3: Store
    vector_store.add_documents(filtered_chunks, embeddings)
    
    return len(filtered_chunks)


# --- Query Endpoints ---

@router.get("/rag_search", response_model=List[Dict[str, Any]])
def rag_search(query: str, rag: RagDep):
    """Simple RAG search - returns matching documents."""
    return rag.retrieve(query) or []

@router.get("/llm_search")
def llm_search(query: str, llm: LlmDep):
    """LLM-powered search with generated response."""
    return llm.llm_rag_retrive(query)

@router.get("/advanced_query")
def query_advanced_rag(query: str, adv_rag: AdvRagDep):
    """Advanced RAG query with citations and history."""
    results = adv_rag.query(query)
    return {"response": results}


# --- Upload Endpoints (3 Simple Endpoints) ---

@router.post("/upload/pdf")
async def upload_pdf(
    doc_loader: DocLoaderDep,
    chunk_loader: ChunkDep,
    embed_manager: EmbedDep,
    vector_store: StoreDep,
    file: UploadFile = File(...),
):
    """Upload and process a single PDF file."""
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        safe_filename = secure_filename(file.filename) 
        temp_path = temp / safe_filename
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            docs = doc_loader.load_pdfs(pdf_dir=temp_dir)
            count = process_and_index(docs, chunk_loader, embed_manager, vector_store)
            
            return {
                "message": "PDF uploaded and ingested successfully",
                "filename": file.filename,
                "chunks_created": count
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.post("/upload/csv")
async def upload_csv(
    doc_loader: DocLoaderDep,
    chunk_loader: ChunkDep,
    embed_manager: EmbedDep,
    vector_store: StoreDep,
    file: UploadFile = File(...),
    delimiter: str = Form(default=","),
):
    """Upload and process a single CSV file."""
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not file.filename.lower().endswith('.csv'):
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


@router.post("/upload/website")
async def upload_website(
    request: UrlRequest,
    web_loader: WebLoaderDep,
    chunk_loader: ChunkDep,
    embed_manager: EmbedDep,
    vector_store: StoreDep,
):
    """Ingest content from a single webpage URL."""
    try:
        docs = web_loader.load_single_page(request.url)
        count = process_and_index(docs, chunk_loader, embed_manager, vector_store)
        
        return {
            "message": "Website content ingested successfully",
            "url": request.url,
            "chunks_created": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing website: {str(e)}")


# --- Utility Endpoints ---

@router.get("/stats")
def get_stats(vector_store: StoreDep, doc_loader: DocLoaderDep):
    """Get vector store and document loader statistics."""
    count = max(0, vector_store.collection.count())
    return {
        "vector_store_count": count,
        "document_loader_stats": doc_loader.get_stats()
    }

@router.delete("/clear")
def clear_vector_store(vector_store: StoreDep):
    """Clear all documents from the vector store."""
    try:
        count = max(0, vector_store.collection.count())
        if count > 0:
            all_data = vector_store.collection.get()
            if all_data['ids']:
                vector_store.collection.delete(ids=all_data['ids'])
        return {"message": "Vector store cleared successfully", "documents_deleted": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing vector store: {str(e)}")