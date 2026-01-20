
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from app.models import Task, TaskStatus


class TaskManager:
    """
    Manages background tasks with progress tracking.
    Thread-safe singleton.
    """
    
    _instance: Optional["TaskManager"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # Prevents re-initialization if called multiple times
        if self._initialized:
            return
            
        self._tasks: Dict[str, Task] = {}
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._initialized = True
    
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
        percentage: Optional[float]=None,
        items_processed: Optional[int] = None, 
        total_items: Optional[int] = None   
    ):
        """Update task progress."""
        task = self._tasks.get(task_id)
        
        if not task:
            return
        
        if items_processed is not None:
            task.progress.items_processed = items_processed

        if total_items is not None:
            task.progress.total_items = total_items
        
        task.progress.current_step = step

        if percentage is not None:
            task.progress.percentage = max(0.0, min(float(percentage), 100.0))
        elif task.progress.total_items > 0:
            calc_percent = (task.progress.items_processed / task.progress.total_items) * 100.0
            task.progress.percentage = min(calc_percent, 100.0)
        else:
            task.progress.percentage = 0.0
                    
            task.status = TaskStatus.PROCESSING
            task.updated_at = datetime.now()
            
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
            # Iterate over a copy to safely handle potential modifications
            for queue in self._subscribers[task_id][:]: 
                try:
                    queue.put_nowait(task.to_dict())
                except asyncio.QueueFull:
                    pass
                except RuntimeError:
                    pass
    
    def get_all_tasks(self) -> Dict[str, Dict]:
        return {tid: t.to_dict() for tid, t in self._tasks.items()}
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
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





