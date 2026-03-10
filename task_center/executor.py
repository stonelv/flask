import threading
import time
import random
from datetime import datetime, UTC
from concurrent.futures import ThreadPoolExecutor
from task_center import db
from task_center.models import Task, TaskStatus

class TaskExecutor:
    def __init__(self, max_workers=4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_futures = {}
        self.cancellation_events = {}
        self._lock = threading.Lock()

    def submit_task(self, task_id, task_func, *args, **kwargs):
        with self._lock:
            if task_id in self.task_futures:
                return False
            
            cancellation_event = threading.Event()
            self.cancellation_events[task_id] = cancellation_event
            
            future = self.executor.submit(
                self._task_wrapper, task_id, task_func, cancellation_event, *args, **kwargs
            )
            self.task_futures[task_id] = future
            return True

    def _task_wrapper(self, task_id, task_func, cancellation_event, *args, **kwargs):
        from flask import current_app
        with current_app.app_context():
            task = db.session.get(Task, task_id)
            if not task:
                return

            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(UTC)
            db.session.commit()

            try:
                result = task_func(task_id, cancellation_event, *args, **kwargs)
                task = db.session.get(Task, task_id)
                if task and task.status != TaskStatus.CANCELLED:
                    task.status = TaskStatus.SUCCEEDED
                    task.result = result
                    task.progress = 100
                    task.completed_at = datetime.now(UTC)
                    db.session.commit()
            except Exception as e:
                task = db.session.get(Task, task_id)
                if task:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    task.completed_at = datetime.now(UTC)
                    db.session.commit()
            finally:
                with self._lock:
                    self.task_futures.pop(task_id, None)
                    self.cancellation_events.pop(task_id, None)

    def cancel_task(self, task_id):
        with self._lock:
            if task_id in self.cancellation_events:
                self.cancellation_events[task_id].set()
                task = db.session.get(Task, task_id)
                if task and task.status == TaskStatus.RUNNING:
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.now(UTC)
                    db.session.commit()
                return True
            return False

    def is_task_cancelled(self, task_id):
        return task_id in self.cancellation_events and self.cancellation_events[task_id].is_set()

def sample_long_task(task_id, cancellation_event, *args, **kwargs):
    from flask import current_app
    stages = ['Initializing', 'Processing data', 'Generating report', 'Finalizing']
    total_duration = random.randint(10, 30)
    stage_duration = total_duration / len(stages)

    for i, stage in enumerate(stages):
        if cancellation_event.is_set():
            current_app.logger.info(f"Task {task_id} cancelled at stage: {stage}")
            return None

        task = db.session.get(Task, task_id)
        if task:
            task.stage = stage
            task.progress = int((i / len(stages)) * 100)
            db.session.commit()
            current_app.logger.info(f"Task {task_id} - {stage}: {task.progress}%")

        for _ in range(int(stage_duration)):
            if cancellation_event.is_set():
                current_app.logger.info(f"Task {task_id} cancelled during: {stage}")
                return None
            time.sleep(1)

    task = db.session.get(Task, task_id)
    if task:
        task.stage = 'Completed'
        task.progress = 100
        db.session.commit()

    return {'message': 'Task completed successfully', 'duration': total_duration}

executor = TaskExecutor()
