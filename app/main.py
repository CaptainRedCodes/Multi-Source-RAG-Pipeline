from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


@asynccontextmanager
async def lifespan(app: FastAPI):
    import threading
    
    def background_preload():
        """Preload heavy components in background thread."""
        try:
            print("Background preloading heavy components...")
            from app.dependencies import preload_components
            preload_components()
            print("All components preloaded successfully!")
        except Exception as e:
            print(f"Preloading warning: {e}")
    
    # Start preloading in background thread (non-blocking)
    preload_thread = threading.Thread(target=background_preload, daemon=True)
    preload_thread.start()
    
    print("App startup: Multi-Source RAG API is ready")
    print( "API docs available at: http://127.0.0.1:8000/docs")
    
    yield

    print(" App shutdown complete")


app = FastAPI(
    title="Multi-Source RAG API",
    description="A multi-source RAG pipeline API supporting PDF, CSV, and web content ingestion",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {
        "message": "Multi-Source RAG API is running",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


app.include_router(router, prefix="/api")
