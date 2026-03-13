import uuid
import threading
import time
import random
from datetime import datetime, UTC
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Callable, Any
from flask import Flask
from task_center.models import Task, TaskStatus

class TaskContext:
    def __init__(self, task_id: str, app: Flask = None):
        self.task_id = task_id
        self._cancelled = False
        self._lock = threading.Lock()
        self._app = app
        self._current_stage = None
        self._current_progress = 0
    
    def is_cancelled(self) -> bool:
        with self._lock:
            return self._cancelled
    
    def cancel(self):
        with self._lock:
            self._cancelled = True
    
    def update_progress(self, progress: int, stage: str = None):
        if progress < 0 or progress > 100:
            raise ValueError("Progress must be between 0 and 100")
        
        self._current_progress = progress
        if stage:
            self._current_stage = stage
        
        if not self._app:
            from task_center import create_app
            self._app = create_app()
        
        with self._app.app_context():
            from task_center import db
            task = Task.query.get(self.task_id)
            if task and task.status not in [TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.progress = progress
                if stage:
                    task.stage = stage
                db.session.commit()
    
    def log(self, message: str, level: str = "info"):
        import logging
        
        if not self._app:
            from task_center import create_app
            self._app = create_app()
        
        with self._app.app_context():
            log_level = getattr(logging, level.upper(), logging.INFO)
            extra = {
                'task_id': self.task_id,
                'stage': self._current_stage,
                'progress': self._current_progress
            }
            self._app.logger.log(log_level, message, extra=extra)

class TaskExecutor:
    def __init__(self):
        self._executor: ThreadPoolExecutor = None
        self._task_contexts: Dict[str, TaskContext] = {}
        self._app: Flask = None
        self._task_handlers: Dict[str, Callable] = {}
    
    def init_app(self, app: Flask):
        self._app = app
        max_workers = app.config.get('TASK_EXECUTOR_MAX_WORKERS', 4)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._register_default_tasks()
    
    def _register_default_tasks(self):
        self.register_task_handler('long_running_task', self._long_running_task_handler)
    
    def register_task_handler(self, task_type: str, handler: Callable):
        self._task_handlers[task_type] = handler
    
    def submit_task(self, task_id: str, task_type: str, payload: Dict = None) -> bool:
        if task_type not in self._task_handlers:
            raise ValueError(f"No handler registered for task type: {task_type}")
        
        context = TaskContext(task_id, self._app)
        self._task_contexts[task_id] = context
        
        future = self._executor.submit(
            self._task_wrapper,
            task_id,
            task_type,
            payload,
            context
        )
        return True
    
    def _task_wrapper(self, task_id: str, task_type: str, payload: Dict, context: TaskContext):
        app = self._app
        with app.app_context():
            from task_center import db
            task = Task.query.get(task_id)
            if not task:
                app.logger.error(f"Task {task_id} not found", extra={'task_id': task_id})
                return
            
            if task.status == TaskStatus.CANCELLED:
                app.logger.info(f"Task {task_id} was cancelled before starting", extra={'task_id': task_id})
                return
            
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(UTC)
            db.session.commit()
            
            app.logger.info(f"Starting task {task_id} of type {task_type}", extra={'task_id': task_id})
        
        try:
            handler = self._task_handlers[task_type]
            result = handler(context, payload)
            
            with app.app_context():
                from task_center import db
                task = Task.query.get(task_id)
                if task:
                    if result and isinstance(result, dict) and result.get('cancelled'):
                        if task.status != TaskStatus.CANCELLED:
                            task.status = TaskStatus.CANCELLED
                            task.cancelled_at = datetime.now(UTC)
                            task.set_result(result)
                            db.session.commit()
                        app.logger.info(f"Task {task_id} was cancelled during execution", extra={'task_id': task_id})
                    elif task.status == TaskStatus.CANCELLED:
                        app.logger.info(f"Task {task_id} was cancelled during execution", extra={'task_id': task_id})
                    else:
                        task.status = TaskStatus.SUCCEEDED
                        task.progress = 100
                        task.set_result(result)
                        task.completed_at = datetime.now(UTC)
                        db.session.commit()
                        app.logger.info(f"Task {task_id} completed successfully", extra={'task_id': task_id})
        
        except Exception as e:
            with app.app_context():
                from task_center import db
                task = Task.query.get(task_id)
                if task and task.status != TaskStatus.CANCELLED:
                    task.status = TaskStatus.FAILED
                    task.set_error({'message': str(e), 'type': type(e).__name__})
                    task.completed_at = datetime.now(UTC)
                    db.session.commit()
                    app.logger.error(f"Task {task_id} failed: {str(e)}", extra={'task_id': task_id})
        
        finally:
            self._task_contexts.pop(task_id, None)
    
    def cancel_task(self, task_id: str) -> bool:
        context = self._task_contexts.get(task_id)
        cancelled = False
        
        if context:
            context.cancel()
            cancelled = True
        
        with self._app.app_context():
            from task_center import db
            task = Task.query.get(task_id)
            if task and task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                task.status = TaskStatus.CANCELLED
                task.cancelled_at = datetime.now(UTC)
                db.session.commit()
                self._app.logger.info(f"Task {task_id} cancelled", extra={'task_id': task_id})
                cancelled = True
        
        return cancelled
    
    def get_task_context(self, task_id: str) -> TaskContext:
        return self._task_contexts.get(task_id)
    
    def _long_running_task_handler(self, context: TaskContext, payload: Dict) -> Dict:
        duration = payload.get('duration', random.randint(10, 30)) if payload else random.randint(10, 30)
        steps = 10
        step_duration = duration / steps
        
        context.log(f"Starting long running task, duration: {duration}s")
        
        for i in range(steps):
            if context.is_cancelled():
                context.log("Task cancelled during execution", "warning")
                return {'cancelled': True, 'progress': i * 10}
            
            progress = (i + 1) * 10
            stage = f"Processing step {i + 1}/{steps}"
            context.update_progress(progress, stage)
            context.log(f"Stage: {stage}, Progress: {progress}%")
            
            time.sleep(step_duration)
        
        context.log("Long running task completed")
        return {
            'duration': duration,
            'steps_completed': steps,
            'message': 'Task completed successfully'
        }
