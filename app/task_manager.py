import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
import uuid


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


class TaskManager:
    """
    Manages background tasks with progress tracking.
    
    Thread-safe singleton that stores task state in memory.
    For production, consider using Redis or a database.
    """
    
    _instance: Optional["TaskManager"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tasks: Dict[str, Task] = {}
            cls._instance._subscribers: Dict[str, list] = {}
        return cls._instance
    
    def create_task(self, task_type: str) -> Task:
        """Create a new task and return it."""
        task_id = str(uuid.uuid4())[:8]
        task = Task(id=task_id, task_type=task_type)
        self._tasks[task_id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self._tasks.get(task_id)
    
    def update_progress(
        self, 
        task_id: str, 
        step: str, 
        percentage: float,
        items_processed: int = 0,
        total_items: int = 0
    ):
        """Update task progress."""
        task = self._tasks.get(task_id)
        if task:
            task.progress.current_step = step
            task.progress.percentage = min(percentage, 100.0)
            task.progress.items_processed = items_processed
            task.progress.total_items = total_items
            task.status = TaskStatus.PROCESSING
            task.updated_at = datetime.now()
            
            # Notify subscribers
            self._notify_subscribers(task_id, task)
    
    def complete_task(self, task_id: str, result: Dict[str, Any]):
        """Mark task as completed with result."""
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.progress.percentage = 100.0
            task.result = result
            task.updated_at = datetime.now()
            self._notify_subscribers(task_id, task)
    
    def fail_task(self, task_id: str, error: str):
        """Mark task as failed with error message."""
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.error = error
            task.updated_at = datetime.now()
            self._notify_subscribers(task_id, task)
    
    def subscribe(self, task_id: str, queue: asyncio.Queue):
        """Subscribe to task updates."""
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        self._subscribers[task_id].append(queue)
    
    def unsubscribe(self, task_id: str, queue: asyncio.Queue):
        """Unsubscribe from task updates."""
        if task_id in self._subscribers:
            try:
                self._subscribers[task_id].remove(queue)
            except ValueError:
                pass
    
    def _notify_subscribers(self, task_id: str, task: Task):
        """Notify all subscribers of task updates."""
        if task_id in self._subscribers:
            for queue in self._subscribers[task_id]:
                try:
                    queue.put_nowait(task.to_dict())
                except asyncio.QueueFull:
                    pass
    
    def get_all_tasks(self) -> Dict[str, Dict]:
        """Get all tasks (for debugging/admin)."""
        return {tid: t.to_dict() for tid, t in self._tasks.items()}
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Remove tasks older than max_age_hours."""
        now = datetime.now()
        to_remove = []
        for task_id, task in self._tasks.items():
            age = (now - task.created_at).total_seconds() / 3600
            if age > max_age_hours:
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self._tasks[task_id]
            if task_id in self._subscribers:
                del self._subscribers[task_id]


# Singleton instance
task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """Dependency injection for FastAPI."""
    return task_manager
