import logging
import queue
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional

from .models import Task
from .models import TaskStatus

logger = logging.getLogger(__name__)

TaskHandler = Callable[["TaskContext"], Any]


class TaskContext:
    def __init__(self, task: Task, storage: "TaskStorage", executor: "TaskExecutor"):
        self._task = task
        self._storage = storage
        self._executor = executor

    @property
    def task_id(self) -> str:
        return self._task.id

    @property
    def payload(self) -> Dict[str, Any]:
        return self._task.payload

    def check_cancel(self) -> bool:
        task = self._storage.get(self._task.id)
        return task.is_cancelled() if task else True

    def update_progress(self, progress: int, stage: str = "") -> None:
        if 0 <= progress <= 100:
            self._storage.update(
                self._task.id,
                progress=progress,
                stage=stage or self._task.stage,
            )
            logger.info(
                f"Task {self._task.id} progress: {progress}%",
                extra={"task_id": self._task.id, "progress": progress, "stage": stage},
            )

    def log(self, message: str) -> None:
        self._storage.add_log(self._task.id, message)
        logger.info(message, extra={"task_id": self._task.id})


class TaskExecutor:
    def __init__(self, storage: "TaskStorage", max_workers: int = 4):
        self._storage = storage
        self._max_workers = max_workers
        self._executor: Optional[ThreadPoolExecutor] = None
        self._handlers: Dict[str, TaskHandler] = {}
        self._pending_queue: queue.Queue = queue.Queue()
        self._dispatcher_thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._lock = threading.Lock()

    def register(self, task_type: str) -> Callable[[TaskHandler], TaskHandler]:
        def decorator(handler: TaskHandler) -> TaskHandler:
            self._handlers[task_type] = handler
            logger.info(f"Registered handler for task type: {task_type}")
            return handler

        return decorator

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
            self._dispatcher_thread = threading.Thread(target=self._dispatcher_loop, daemon=True)
            self._dispatcher_thread.start()
            logger.info(f"TaskExecutor started with {self._max_workers} workers")

    def stop(self, wait: bool = True) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False
            if self._dispatcher_thread:
                self._dispatcher_thread.join(timeout=2)
            if self._executor:
                self._executor.shutdown(wait=wait)
            logger.info("TaskExecutor stopped")

    def submit(self, task: Task) -> None:
        if not self._running:
            raise RuntimeError("TaskExecutor is not running")
        self._pending_queue.put(task.id)
        logger.info(f"Task {task.id} submitted for execution", extra={"task_id": task.id})

    def _dispatcher_loop(self) -> None:
        while self._running or not self._pending_queue.empty():
            try:
                task_id = self._pending_queue.get(timeout=0.5)
                task = self._storage.get(task_id)
                if task and task.status == TaskStatus.PENDING:
                    self._executor.submit(self._execute_task, task_id)
            except queue.Empty:
                continue
            except Exception:
                logger.exception("Error in dispatcher loop")

    def _execute_task(self, task_id: str) -> None:
        task = self._storage.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        if task.status != TaskStatus.PENDING:
            logger.warning(f"Task {task_id} is not PENDING, skipping")
            return

        handler = self._handlers.get(task.type)
        if not handler:
            self._storage.update(
                task_id,
                status=TaskStatus.FAILED,
                error=f"No handler registered for task type: {task.type}",
                finished_at=datetime.now(timezone.utc),
            )
            logger.error(f"No handler for task type: {task.type}")
            return

        if task.is_cancelled():
            self._storage.update(task_id, status=TaskStatus.CANCELLED)
            return

        self._storage.update(
            task_id,
            status=TaskStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        logger.info(f"Task {task_id} started", extra={"task_id": task_id})

        ctx = TaskContext(task, self._storage, self)

        try:
            result = handler(ctx)
            task = self._storage.get(task_id)
            if task and task.is_cancelled():
                self._storage.update(
                    task_id,
                    status=TaskStatus.CANCELLED,
                    progress=0,
                    finished_at=datetime.now(timezone.utc),
                )
                logger.info(f"Task {task_id} cancelled", extra={"task_id": task_id})
            else:
                self._storage.update(
                    task_id,
                    status=TaskStatus.SUCCEEDED,
                    result=result if isinstance(result, dict) else {"result": result},
                    progress=100,
                    finished_at=datetime.now(timezone.utc),
                )
                logger.info(
                    f"Task {task_id} completed successfully",
                    extra={"task_id": task_id},
                )
        except InterruptedError as e:
            self._storage.update(
                task_id,
                status=TaskStatus.CANCELLED,
                finished_at=datetime.now(timezone.utc),
            )
            logger.info(
                f"Task {task_id} cancelled by request",
                extra={"task_id": task_id},
            )
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            task = self._storage.get(task_id)
            if task and task.is_cancelled():
                self._storage.update(
                    task_id,
                    status=TaskStatus.CANCELLED,
                    finished_at=datetime.now(timezone.utc),
                )
                logger.info(
                    f"Task {task_id} cancelled (with exception: {error_msg})",
                    extra={"task_id": task_id},
                )
            else:
                self._storage.update(
                    task_id,
                    status=TaskStatus.FAILED,
                    error=error_msg,
                    finished_at=datetime.now(timezone.utc),
                )
                logger.exception(
                    f"Task {task_id} failed: {error_msg}",
                    extra={"task_id": task_id},
                )
