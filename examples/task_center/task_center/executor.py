import asyncio
import json
import logging
import random
import time
import traceback
from datetime import datetime, UTC
from typing import Dict, Any, Callable, Coroutine, Set
from threading import Thread
from queue import Queue
import weakref

from flask import Flask
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from . import db
from .models import Task, TaskStatus

logger = logging.getLogger("task_center")


class TaskContext:
    def __init__(self, task_id: str, app: Flask):
        self.task_id = task_id
        self._app = app
        self._cancelled = False
        self._progress = 0
        self._stage = None

    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True

    def update_progress(self, progress: int, stage: str | None = None) -> None:
        self._progress = max(0, min(100, progress))
        self._stage = stage
        self._update_task_in_db()

    def _update_task_in_db(self) -> None:
        try:
            with self._app.app_context():
                stmt = select(Task).where(Task.id == self.task_id).with_for_update()
                task = db.session.execute(stmt).scalar_one_or_none()
                if task:
                    task.progress = self._progress
                    task.stage = self._stage
                    task.updated_at = datetime.now(UTC)
                    db.session.commit()
                    
                    logger.info(
                        "Task progress updated",
                        extra={
                            "task_id": self.task_id,
                            "stage": self._stage,
                            "progress": self._progress,
                        },
                    )
        except SQLAlchemyError as e:
            logger.error(
                f"Failed to update task progress: {e}",
                extra={"task_id": self.task_id, "stage": None, "progress": 0},
            )
            try:
                with self._app.app_context():
                    db.session.rollback()
            except:
                pass

    def log(self, message: str, extra: Dict[str, Any] | None = None) -> None:
        log_extra = {"task_id": self.task_id, "stage": self._stage, "progress": self._progress}
        if extra:
            log_extra.update(extra)
        logger.info(message, extra=log_extra)


class TaskExecutor:
    def __init__(self):
        self._app: Flask | None = None
        self._task_handlers: Dict[str, Callable[[TaskContext, Dict[str, Any]], Coroutine[Any, Any, Any]]] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._task_contexts: Dict[str, TaskContext] = {}
        self._cancellation_requests: Set[str] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: Thread | None = None
        self._command_queue = Queue()
        self._stopped = False
        self._thread_stopped = False

    def init_app(self, app: Flask) -> None:
        self._app = app
        self.register_task_handler("example_long_task", self._example_long_task)
        if not self._thread or not self._thread.is_alive():
            self._stopped = False
            self._thread_stopped = False
            self._start_worker_thread()

    def _start_worker_thread(self) -> None:
        def worker():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._stop_event = asyncio.Event()
            
            async def process_commands():
                while not self._stop_event.is_set():
                    try:
                        while not self._command_queue.empty():
                            cmd, args = self._command_queue.get_nowait()
                            if cmd == "run":
                                # Use create_task to avoid blocking command processing
                                self._loop.create_task(self._run_task(*args))
                            elif cmd == "cancel":
                                self._cancel_task(*args)
                            elif cmd == "stop":
                                self._stop_event.set()
                                break
                        await asyncio.sleep(0.01)
                    except Exception as e:
                        logger.error(f"Command processing error: {e}", extra={"task_id": None, "stage": None, "progress": 0})
                
                # After stop event is set, wait for all running tasks to complete
                for task in list(self._running_tasks.values()):
                    task.cancel()
                if self._running_tasks:
                    await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
            
            try:
                self._loop.run_until_complete(process_commands())
            finally:
                # Clean up remaining tasks
                try:
                    pending = asyncio.all_tasks(self._loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except RuntimeError:
                    # Ignore "Event loop is running" errors during cleanup
                    pass
                finally:
                    try:
                        self._loop.close()
                    except:
                        pass
                    self._thread_stopped = True

        self._thread = Thread(target=worker, daemon=False)
        self._thread.start()

    def stop(self, timeout: int = 5) -> None:
        if self._stopped:
            return
            
        self._command_queue.put(("stop", ()))
        self._stopped = True
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        
        self._running_tasks.clear()
        self._task_contexts.clear()
        self._cancellation_requests.clear()
    
    def reset(self) -> None:
        self.stop(timeout=5)
        # Wait for thread to fully stop
        for _ in range(50):
            if self._thread_stopped:
                break
            time.sleep(0.1)
        self._app = None
        self._loop = None
        self._thread = None
        self._stopped = False
        self._thread_stopped = False
        self._command_queue = Queue()
        self._running_tasks.clear()
        self._task_contexts.clear()
        self._cancellation_requests.clear()

    def register_task_handler(
        self,
        task_type: str,
        handler: Callable[[TaskContext, Dict[str, Any]], Coroutine[Any, Any, Any]],
    ) -> None:
        self._task_handlers[task_type] = handler

    def submit_task(self, task_id: str) -> None:
        self._command_queue.put(("run", (task_id,)))

    def request_cancel(self, task_id: str) -> None:
        self._command_queue.put(("cancel", (task_id,)))

    def _cancel_task(self, task_id: str) -> None:
        self._cancellation_requests.add(task_id)
        if task_id in self._task_contexts:
            self._task_contexts[task_id].cancel()
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
            logger.info(
                f"Task cancellation requested",
                extra={"task_id": task_id, "stage": None, "progress": 0},
            )

    async def _run_task(self, task_id: str) -> None:
        if not self._app:
            return

        context: TaskContext | None = None
        
        try:
            # Create context first for cancellation tracking
            context = TaskContext(task_id, self._app)
            self._task_contexts[task_id] = context
            
            with self._app.app_context():
                stmt = select(Task).where(Task.id == task_id).with_for_update()
                task = db.session.execute(stmt).scalar_one_or_none()
                
                if not task:
                    logger.error(
                        f"Task not found: {task_id}",
                        extra={"task_id": task_id, "stage": None, "progress": 0},
                    )
                    return

                if task.status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    logger.warning(
                        f"Task already in terminal state: {task.status}",
                        extra={"task_id": task_id, "stage": None, "progress": 0},
                    )
                    return

                if task_id in self._cancellation_requests:
                    task.status = TaskStatus.CANCELLED
                    db.session.commit()
                    return

                handler = self._task_handlers.get(task.type)
                if not handler:
                    raise ValueError(f"No handler registered for task type: {task.type}")

                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now(UTC)
                db.session.commit()

                self._running_tasks[task_id] = asyncio.current_task()

                if task_id in self._cancellation_requests:
                    context.cancel()

                payload = json.loads(task.payload) if task.payload else {}
                
                result = await handler(context, payload)
                
                # Task completed successfully - check if cancelled during execution
                with self._app.app_context():
                    stmt = select(Task).where(Task.id == task_id).with_for_update()
                    task = db.session.execute(stmt).scalar_one_or_none()
                    
                    if context.is_cancelled() or task_id in self._cancellation_requests:
                        task.status = TaskStatus.CANCELLED
                    else:
                        task.status = TaskStatus.SUCCEEDED
                        task.result = json.dumps(result) if result is not None else None
                    
                    task.progress = 100
                    task.completed_at = datetime.now(UTC)
                    db.session.commit()

                    logger.info(
                        f"Task completed: {task.status.value}",
                        extra={"task_id": task_id, "stage": "completed", "progress": 100},
                    )

        except asyncio.CancelledError:
            logger.info(
                "Task cancelled via asyncio.CancelledError",
                extra={"task_id": task_id, "stage": "cancelling", "progress": 0},
            )
            # Ensure task is marked as cancelled in database
            try:
                with self._app.app_context():
                    stmt = select(Task).where(Task.id == task_id).with_for_update()
                    task = db.session.execute(stmt).scalar_one_or_none()
                    if task and task.status not in (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                        task.status = TaskStatus.CANCELLED
                        task.completed_at = datetime.now(UTC)
                        db.session.commit()
                        logger.info(
                            "Task cancelled",
                            extra={"task_id": task_id, "stage": "cancelled", "progress": task.progress},
                        )
            except Exception as e:
                logger.error(
                    f"Failed to update cancelled task status: {e}",
                    extra={"task_id": task_id, "stage": None, "progress": 0},
                )
            raise  # Re-raise to properly propagate cancellation

        except Exception as e:
            logger.error(
                f"Task failed: {e}",
                extra={"task_id": task_id, "stage": "failed", "progress": 0},
            )
            try:
                with self._app.app_context():
                    stmt = select(Task).where(Task.id == task_id).with_for_update()
                    task = db.session.execute(stmt).scalar_one_or_none()
                    if task and task.status not in (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                        task.status = TaskStatus.FAILED
                        task.error = json.dumps({
                            "message": str(e),
                            "traceback": traceback.format_exc(),
                        })
                        task.completed_at = datetime.now(UTC)
                        db.session.commit()
            except Exception as db_e:
                logger.error(
                    f"Failed to update failed task status: {db_e}",
                    extra={"task_id": task_id, "stage": None, "progress": 0},
                )
        finally:
            self._running_tasks.pop(task_id, None)
            self._task_contexts.pop(task_id, None)
            self._cancellation_requests.discard(task_id)

    async def _example_long_task(self, context: TaskContext, payload: Dict[str, Any]) -> Dict[str, Any]:
        min_duration = payload.get("min_duration", 10)
        max_duration = payload.get("max_duration", 30)
        total_duration = random.uniform(min_duration, max_duration)
        
        stages = [
            ("initializing", 0.1),
            ("processing_data", 0.3),
            ("computing", 0.4),
            ("finalizing", 0.15),
            ("cleaning_up", 0.05),
        ]

        context.log(f"Starting long task, expected duration: {total_duration:.1f}s")

        start_time = time.time()
        elapsed = 0
        for stage_name, stage_ratio in stages:
            if context.is_cancelled():
                context.log("Task cancellation detected, stopping")
                break

            stage_duration = total_duration * stage_ratio
            
            context.update_progress(int((elapsed / total_duration) * 100), stage_name)
            context.log(f"Entering stage: {stage_name}")

            check_interval = 0.1
            stage_elapsed = 0
            while stage_elapsed < stage_duration and not context.is_cancelled():
                await asyncio.sleep(check_interval)
                stage_elapsed += check_interval
                elapsed = time.time() - start_time
                progress = int(min((elapsed / total_duration) * 100, 100))
                context.update_progress(progress, stage_name)

        if context.is_cancelled():
            raise asyncio.CancelledError()

        context.update_progress(100, "completed")
        return {
            "duration": total_duration,
            "stages_completed": len(stages),
            "message": "Task completed successfully",
        }


_executor = TaskExecutor()


def init_app(app: Flask) -> None:
    _executor.init_app(app)


def get_executor() -> TaskExecutor:
    return _executor
