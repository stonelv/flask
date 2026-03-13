import asyncio
import logging
import random
import threading
import uuid
from datetime import datetime, UTC
from typing import Dict, Any, Optional, Callable
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker


logger = logging.getLogger(__name__)


class TaskCancelledError(Exception):
    """Raised when a task is cancelled"""
    pass


class TaskExecutor:
    def __init__(self):
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._cancel_events: Dict[str, asyncio.Event] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._engine = None
        self._start_background_loop()

    def set_engine(self, engine):
        """Set the database engine - must be called after init_db"""
        self._engine = engine

    def _start_background_loop(self):
        """Start a background event loop for running async tasks"""
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_forever()
            finally:
                self._loop.close()

        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()

        # Wait for loop to be ready
        while self._loop is None:
            threading.Event().wait(0.1)

    def _get_session(self):
        """Create a new session for this thread"""
        if not self._engine:
            from .database import get_engine
            self._engine = get_engine()
        return sessionmaker(bind=self._engine)()

    async def execute_task(self, task_id: str, task_func: Callable):
        """Execute a task asynchronously"""
        cancel_event = asyncio.Event()
        self._cancel_events[task_id] = cancel_event

        session = None
        try:
            from .database import Task, TaskStatus

            # Mark task as RUNNING
            session = self._get_session()
            task = session.get(Task, task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            if task.status == TaskStatus.CANCELLED:
                logger.info(f"Task {task_id} is already cancelled")
                session.close()
                return

            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(UTC)
            session.commit()
            session.close()

            logger.info(f"Starting task {task_id}")

            async def progress_callback(progress: int, stage: str):
                if cancel_event.is_set():
                    raise TaskCancelledError()
                # Run update_progress in a thread to not block the event loop
                await asyncio.to_thread(self.update_progress, task_id, progress, stage)

            try:
                # Get payload from a fresh session
                session = self._get_session()
                task = session.get(Task, task_id)
                payload = task.payload
                session.close()

                result = await task_func(payload, progress_callback, cancel_event)
                
                # Update task with result
                session = self._get_session()
                task = session.get(Task, task_id)
                task.status = TaskStatus.SUCCEEDED
                task.result = result
                task.progress = 100
                task.stage = "completed"
                task.completed_at = datetime.now(UTC)
                session.commit()
                session.close()
            except TaskCancelledError:
                session = self._get_session()
                task = session.get(Task, task_id)
                task.status = TaskStatus.CANCELLED
                task.error = "Task was cancelled"
                task.completed_at = datetime.now(UTC)
                session.commit()
                session.close()
                logger.info(f"Task {task_id} was cancelled")
            except Exception as e:
                session = self._get_session()
                task = session.get(Task, task_id)
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = datetime.now(UTC)
                session.commit()
                session.close()
                logger.exception(f"Task {task_id} failed")

            logger.info(f"Task {task_id} completed")

        except Exception as e:
            logger.exception(f"Error in task execution {task_id}: {e}")
            if session:
                session.rollback()
                session.close()
        finally:
            self._running_tasks.pop(task_id, None)
            self._cancel_events.pop(task_id, None)

    def update_progress(self, task_id: str, progress: int, stage: str):
        """Update task progress"""
        session = None
        try:
            from .database import Task, TaskStatus
            session = self._get_session()
            task = session.get(Task, task_id)
            if task and task.status not in [TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.progress = max(0, min(100, progress))
                task.stage = stage
                task.updated_at = datetime.now(UTC)
                session.commit()
                logger.debug(f"Task {task_id} progress: {progress}% - {stage}")
        except Exception as e:
            logger.exception(f"Failed to update progress for task {task_id}")
            if session:
                session.rollback()
        finally:
            if session:
                session.close()

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        session = None
        try:
            from .database import Task, TaskStatus
            session = self._get_session()
            task = session.get(Task, task_id)
            if not task:
                return False

            if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                return False

            if task_id in self._cancel_events:
                async def set_cancel():
                    self._cancel_events[task_id].set()
                asyncio.run_coroutine_threadsafe(set_cancel(), self._loop)

            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now(UTC)
            session.commit()
            return True
        except Exception as e:
            logger.exception(f"Failed to cancel task {task_id}")
            if session:
                session.rollback()
            return False
        finally:
            if session:
                session.close()

    def submit_task(self, task_id: str, task_func: Callable):
        """Submit a task for execution"""
        if task_id in self._running_tasks:
            logger.warning(f"Task {task_id} is already running")
            return

        if self._loop is None:
            logger.error("Event loop not initialized")
            return

        async_task = asyncio.run_coroutine_threadsafe(
            self.execute_task(task_id, task_func),
            self._loop
        )
        self._running_tasks[task_id] = async_task

    def wait_for_all_tasks(self, timeout: int = 10):
        """Wait for all running tasks to complete"""
        import concurrent.futures
        tasks = list(self._running_tasks.values())
        if tasks:
            concurrent.futures.wait(tasks, timeout=timeout)

    def clear(self):
        """Clear all running tasks (for testing)"""
        # Cancel all running tasks
        for task_id in list(self._running_tasks.keys()):
            if task_id in self._cancel_events:
                self._cancel_events[task_id].set()
        
        # Wait a bit for tasks to acknowledge cancellation
        import time
        time.sleep(0.1)
        
        # Cancel the asyncio futures
        for task_id, future in list(self._running_tasks.items()):
            try:
                future.cancel()
            except:
                pass
        
        self._running_tasks.clear()
        self._cancel_events.clear()


# Example long running task (10-30 seconds)
async def example_long_task(
    payload: Dict[str, Any],
    progress_callback: Callable[[int, str], None],
    cancel_event: asyncio.Event
) -> Dict[str, Any]:
    """Example long running task with stages and progress updates"""
    total_duration = random.randint(10, 30)
    stages = [
        ("initializing", 0.1),
        ("processing_data", 0.3),
        ("transforming", 0.3),
        ("finalizing", 0.2),
        ("cleaning_up", 0.1),
    ]

    start_time = asyncio.get_event_loop().time()
    elapsed = 0

    for stage_name, stage_ratio in stages:
        stage_duration = total_duration * stage_ratio
        stage_start = elapsed

        while elapsed < stage_start + stage_duration:
            if cancel_event.is_set():
                raise TaskCancelledError()

            elapsed = asyncio.get_event_loop().time() - start_time
            progress = min(100, int((elapsed / total_duration) * 100))
            await progress_callback(progress, stage_name)

            await asyncio.sleep(0.5)

    return {
        "duration": elapsed,
        "payload": payload,
        "message": "Task completed successfully"
    }


# Task type registry
_task_registry: Dict[str, Callable] = {
    "example_long_task": example_long_task,
}


def register_task_type(task_type: str, func: Callable):
    """Register a new task type"""
    _task_registry[task_type] = func


def get_task_func(task_type: str) -> Optional[Callable]:
    """Get the task function for a given type"""
    return _task_registry.get(task_type)


# Global executor instance
executor = TaskExecutor()
