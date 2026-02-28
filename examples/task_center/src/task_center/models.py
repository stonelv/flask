import enum
import json
import threading
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class Task:
    id: str
    type: str
    status: TaskStatus
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: int = 0
    stage: str = ""
    idempotency_key: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    logs: List[str] = field(default_factory=list)

    _cancel_requested: bool = field(default=False, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        for key in ("_cancel_requested",):
            d.pop(key, None)
        return d

    def is_cancelled(self) -> bool:
        return self._cancel_requested or self.status == TaskStatus.CANCELLED


class TaskStorage:
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._idempotency_map: Dict[str, str] = {}
        self._lock = threading.RLock()

    def create(
        self,
        task_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Task:
        with self._lock:
            if idempotency_key and idempotency_key in self._idempotency_map:
                return self._tasks[self._idempotency_map[idempotency_key]]

            task_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            task = Task(
                id=task_id,
                type=task_type,
                status=TaskStatus.PENDING,
                payload=payload,
                idempotency_key=idempotency_key,
                created_at=now,
                updated_at=now,
            )
            self._tasks[task_id] = task
            if idempotency_key:
                self._idempotency_map[idempotency_key] = task_id
            return task

    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple:
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]
        if task_type:
            tasks = [t for t in tasks if t.type == task_type]

        tasks = sorted(tasks, key=lambda t: t.created_at, reverse=True)

        total = len(tasks)
        start = (page - 1) * per_page
        end = start + per_page
        return tasks[start:end], total

    def update(self, task_id: str, **kwargs) -> Optional[Task]:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None

            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)

            task.updated_at = datetime.now(timezone.utc)
            return task

    def add_log(self, task_id: str, message: str) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                timestamp = datetime.now(timezone.utc).isoformat()
                task.logs.append(f"[{timestamp}] {message}")
                task.updated_at = datetime.now(timezone.utc)

    def request_cancel(self, task_id: str) -> Optional[Task]:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None

            if task.status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return task

            task._cancel_requested = True
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                task.finished_at = datetime.now(timezone.utc)
            return task
