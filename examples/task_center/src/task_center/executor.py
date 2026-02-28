import random
import threading
import time
from typing import Any
from typing import Callable
from typing import Optional

import structlog

from . import TaskStatus
from . import TaskStore


logger = structlog.get_logger()


class CancellationToken:
    def __init__(self):
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled


class TaskExecutor:
    def __init__(self, app, task_store: TaskStore):
        self.app = app
        self.task_store = task_store
        self._cancellation_tokens: dict[str, CancellationToken] = {}
        self._handlers: dict[str, Callable] = {}

    def register_handler(self, task_type: str, handler: Callable):
        self._handlers[task_type] = handler

    def submit(self, task_id: str) -> bool:
        task = self.task_store.get_by_id(task_id)
        if not task:
            return False

        handler = self._handlers.get(task.type)
        if not handler:
            self.task_store.update_task(
                task_id,
                status=TaskStatus.FAILED,
                error=f"No handler registered for task type: {task.type}",
            )
            return False

        token = CancellationToken()
        self._cancellation_tokens[task_id] = token

        def run():
            with self.app.app_context():
                try:
                    self.task_store.update_task(
                        task_id, status=TaskStatus.RUNNING, stage="starting"
                    )
                    logger.info("task_started", task_id=task_id, task_type=task.type)

                    def progress_callback(progress: int, stage: str = ""):
                        if token.is_cancelled:
                            raise TaskCancelledError(task_id)
                        self.task_store.update_task(task_id, progress=progress, stage=stage)
                        logger.info(
                            "task_progress",
                            task_id=task_id,
                            progress=progress,
                            stage=stage,
                        )

                    result = handler(task.payload or {}, progress_callback, token)

                    if token.is_cancelled:
                        self.task_store.update_task(
                            task_id,
                            status=TaskStatus.CANCELLED,
                            progress=100,
                            stage="cancelled",
                        )
                        logger.info("task_cancelled", task_id=task_id)
                    else:
                        self.task_store.update_task(
                            task_id,
                            status=TaskStatus.SUCCEEDED,
                            progress=100,
                            stage="completed",
                            result=result,
                        )
                        logger.info("task_completed", task_id=task_id, result=result)

                except TaskCancelledError:
                    self.task_store.update_task(
                        task_id,
                        status=TaskStatus.CANCELLED,
                        progress=100,
                        stage="cancelled",
                    )
                    logger.info("task_cancelled", task_id=task_id)

                except Exception as e:
                    self.task_store.update_task(
                        task_id,
                        status=TaskStatus.FAILED,
                        error=str(e),
                        stage="failed",
                    )
                    logger.error("task_failed", task_id=task_id, error=str(e))

                finally:
                    self._cancellation_tokens.pop(task_id, None)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return True

    def cancel(self, task_id: str) -> bool:
        token = self._cancellation_tokens.get(task_id)
        if token:
            token.cancel()
            logger.info("task_cancellation_requested", task_id=task_id)
            return True
        return False


class TaskCancelledError(Exception):
    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(f"Task {task_id} was cancelled")


def sample_long_task(
    payload: dict[str, Any],
    progress_callback: Callable[[int, str], None],
    token: CancellationToken,
) -> dict[str, Any]:
    total_duration = random.randint(10, 30)
    stages = [
        (0, 20, "initializing", "Initializing resources"),
        (20, 40, "processing", "Processing data"),
        (40, 60, "validating", "Validating results"),
        (60, 80, "finalizing", "Finalizing output"),
        (80, 100, "cleanup", "Cleaning up"),
    ]

    for start_progress, end_progress, stage_name, stage_desc in stages:
        if token.is_cancelled:
            raise TaskCancelledError("sample_task")

        stage_duration = total_duration * (end_progress - start_progress) / 100
        steps = max(1, int(stage_duration))

        for i in range(steps):
            if token.is_cancelled:
                raise TaskCancelledError("sample_task")

            progress = start_progress + int((end_progress - start_progress) * (i + 1) / steps)
            progress_callback(progress, f"{stage_name}: {stage_desc}")
            time.sleep(1)

    return {
        "message": "Task completed successfully",
        "duration_seconds": total_duration,
        "processed_items": random.randint(100, 1000),
    }
