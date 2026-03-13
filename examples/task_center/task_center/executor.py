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

            # Mark task as RUNNING - atomic update to prevent race conditions
            # Only update if status is still PENDING (not CANCELLED or RUNNING)
            session = self._get_session()
            
            # Use atomic UPDATE ... WHERE to mark task as RUNNING
            update_count = session.query(Task).filter(
                Task.id == task_id,
                Task.status == TaskStatus.PENDING
            ).update({
                Task.status: TaskStatus.RUNNING,
                Task.started_at: datetime.now(UTC)
            }, synchronize_session=False)
            
            session.commit()
            
            if update_count == 0:
                # Task was either not found or already in another state
                task = session.get(Task, task_id)
                if not task:
                    logger.error(f"Task {task_id} not found", extra={"task_id": task_id})
                elif task.status == TaskStatus.CANCELLED:
                    logger.info(f"Task {task_id} is already cancelled, skipping execution", 
                               extra={"task_id": task_id})
                else:
                    logger.info(f"Task {task_id} is already in state {task.status}, skipping", 
                               extra={"task_id": task_id, "status": task.status})
                session.close()
                return
            
            session.close()

            logger.info(f"Starting task {task_id}", 
                       extra={"task_id": task_id, "stage": "starting", "progress": 0})

            async def progress_callback(progress: int, stage: str):
                if cancel_event.is_set():
                    raise TaskCancelledError()
                # Run update_progress in a thread to not block the event loop
                await asyncio.to_thread(self.update_progress, task_id, progress, stage)

            try:
                # Get payload from a fresh session
                session = self._get_session()
                task = session.get(Task, task_id)
                if task.status == TaskStatus.CANCELLED:
                    logger.info(f"Task {task_id} was already cancelled before execution")
                    session.close()
                    return
                payload = task.payload
                session.close()

                result = await task_func(payload, progress_callback, cancel_event)
                
                # Update task with result - atomic update to prevent race conditions
                # Only mark as SUCCEEDED if still in RUNNING state
                session = self._get_session()
                update_count = session.query(Task).filter(
                    Task.id == task_id,
                    Task.status == TaskStatus.RUNNING
                ).update({
                    Task.status: TaskStatus.SUCCEEDED,
                    Task.result: result,
                    Task.progress: 100,
                    Task.stage: "completed",
                    Task.completed_at: datetime.now(UTC)
                }, synchronize_session=False)
                
                session.commit()
                
                if update_count > 0:
                    logger.info(f"Task {task_id} succeeded", 
                               extra={"task_id": task_id, "stage": "completed", "progress": 100})
                else:
                    task = session.get(Task, task_id)
                    if task:
                        logger.info(f"Task {task_id} not marked as succeeded - current state: {task.status}",
                                   extra={"task_id": task_id, "status": task.status})
                session.close()
            except TaskCancelledError:
                # Task was cancelled cooperatively - atomic update
                session = self._get_session()
                update_count = session.query(Task).filter(
                    Task.id == task_id,
                    Task.status.not_in([TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED])
                ).update({
                    Task.status: TaskStatus.CANCELLED,
                    Task.error: "Task was cancelled",
                    Task.cancelled_at: datetime.now(UTC)
                }, synchronize_session=False)
                
                session.commit()
                
                if update_count > 0:
                    task = session.get(Task, task_id)
                    logger.info(f"Task {task_id} was cancelled cooperatively",
                               extra={"task_id": task_id, "stage": task.stage, "progress": task.progress})
                session.close()
            except Exception as e:
                # Task failed - atomic update to prevent race conditions
                session = self._get_session()
                update_count = session.query(Task).filter(
                    Task.id == task_id,
                    Task.status.not_in([TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED])
                ).update({
                    Task.status: TaskStatus.FAILED,
                    Task.error: str(e),
                    Task.completed_at: datetime.now(UTC)
                }, synchronize_session=False)
                
                session.commit()
                
                if update_count > 0:
                    task = session.get(Task, task_id)
                    logger.exception(f"Task {task_id} failed",
                                    extra={"task_id": task_id, "stage": task.stage, "progress": task.progress})
                session.close()

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
        """Update task progress - atomic update"""
        session = None
        try:
            from .database import Task, TaskStatus
            session = self._get_session()
            # Only update if task is still running
            update_count = session.query(Task).filter(
                Task.id == task_id,
                Task.status == TaskStatus.RUNNING
            ).update({
                Task.progress: max(0, min(100, progress)),
                Task.stage: stage,
                Task.updated_at: datetime.now(UTC)
            }, synchronize_session=False)
            
            session.commit()
            
            if update_count > 0:
                logger.debug(f"Task {task_id} progress: {progress}% - {stage}",
                            extra={"task_id": task_id, "stage": stage, "progress": progress})
        except Exception as e:
            logger.exception(f"Failed to update progress for task {task_id}",
                            extra={"task_id": task_id, "stage": stage, "progress": progress})
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
            
            # Atomic update: only cancel if task is in PENDING or RUNNING state
            update_count = session.query(Task).filter(
                Task.id == task_id,
                Task.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING])
            ).update({
                Task.status: TaskStatus.CANCELLED,
                Task.cancelled_at: datetime.now(UTC)
            }, synchronize_session=False)
            
            session.commit()
            
            if update_count == 0:
                # Check if task exists at all
                task = session.get(Task, task_id)
                if not task:
                    logger.warning(f"Cannot cancel non-existent task {task_id}")
                    session.close()
                    return False
                logger.info(f"Task {task_id} is already in state {task.status}, cannot cancel",
                           extra={"task_id": task_id, "status": task.status})
                session.close()
                return False

            # Set cancel event for running tasks
            if task_id in self._cancel_events:
                async def set_cancel():
                    self._cancel_events[task_id].set()
                asyncio.run_coroutine_threadsafe(set_cancel(), self._loop)

            # Get the task to log stage and progress
            task = session.get(Task, task_id)
            logger.info(f"Task {task_id} cancellation requested",
                       extra={"task_id": task_id, "stage": task.stage, "progress": task.progress})
            session.close()
            return True
        except Exception as e:
            logger.exception(f"Failed to cancel task {task_id}",
                            extra={"task_id": task_id})
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
