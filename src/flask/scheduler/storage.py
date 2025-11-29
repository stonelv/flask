import threading
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional
from flask.scheduler.task import Task

class TaskStorage:
    """Thread-safe storage for tasks and recent exceptions."""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.recent_exceptions: deque = deque(maxlen=5)
        self.lock = threading.RLock()
    
    def add_task(self, task: Task) -> None:
        """Add a task to storage."""
        with self.lock:
            self.tasks[task.name] = task
    
    def get_task(self, name: str) -> Optional[Task]:
        """Get a task by name."""
        with self.lock:
            return self.tasks.get(name)
    
    def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        with self.lock:
            return list(self.tasks.values())
    
    def clear_tasks(self) -> None:
        """Clear all tasks."""
        with self.lock:
            self.tasks.clear()
    
    def add_recent_exception(self, task_name: str, timestamp: datetime, error: str) -> None:
        """Add a recent exception."""
        with self.lock:
            self.recent_exceptions.append({
                'task_name': task_name,
                'timestamp': timestamp.isoformat(),
                'error': error
            })
    
    def get_recent_exceptions(self) -> List[Dict]:
        """Get recent exceptions."""
        with self.lock:
            return list(self.recent_exceptions)
