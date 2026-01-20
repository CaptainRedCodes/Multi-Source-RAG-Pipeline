from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5

class UrlRequest(BaseModel):
    url: str

class MultiUrlRequest(BaseModel):
    urls: List[str]

class SitemapRequest(BaseModel):
    sitemap_url: str
    filter_urls: List[str] = []

class RecursiveUrlRequest(BaseModel):
    base_url: str
    max_depth: int = 2



class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class TaskProgress:
    """Represents the progress of a task."""
    current_step: str = ""
    percentage: float = 0.0
    items_processed: int = 0
    total_items: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_step": self.current_step,
            "percentage": round(self.percentage, 2),
            "items_processed": self.items_processed,
            "total_items": self.total_items
        }

@dataclass
class Task:
    """Represents a background task."""
    id: str
    task_type: str
    status: TaskStatus = TaskStatus.PENDING
    progress: TaskProgress = field(default_factory=TaskProgress)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_type": self.task_type,
            "status": self.status.value,
            "progress": self.progress.to_dict(),
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
