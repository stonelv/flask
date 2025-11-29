import time
import threading
import logging
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from flask import Blueprint, jsonify, request, current_app
from werkzeug.exceptions import BadRequest
from .cron_parser import CronParser

# Configure logging
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class Task:
    """Task class representing a scheduled task"""
    def __init__(
        self,
        name: str,
        func: Callable,
        interval: Optional[int] = None,
        delay: Optional[int] = None,
        cron: Optional[str] = None,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None
    ):
        self.name = name
        self.func = func
        self.interval = interval  # in seconds
        self.delay = delay  # in seconds
        self.cron = cron
        self.args = args or []
        self.kwargs = kwargs or {}
        self.next_run: Optional[datetime] = None
        self.status = TaskStatus.PENDING
        self.last_run: Optional[datetime] = None
        self.last_completed: Optional[datetime] = None
        self.last_failed: Optional[datetime] = None
        self.exception: Optional[Exception] = None
        self.retries: int = 0

    def run(self) -> None:
        """Execute the task"""
        self.status = TaskStatus.RUNNING
        self.last_run = datetime.utcnow()
        try:
            result = self.func(*self.args, **self.kwargs)
            self.status = TaskStatus.COMPLETED
            self.last_completed = datetime.utcnow()
            self.exception = None
            logger.info(f"Task {self.name} completed successfully")
            return result
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.last_failed = datetime.utcnow()
            self.exception = e
            self.retries += 1
            logger.error(f"Task {self.name} failed: {str(e)}")
            raise


class Scheduler:
    """Main scheduler class"""
    def __init__(self, app=None):
        self.app = app
        self.tasks: Dict[str, Task] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.tick_interval = 1  # default tick interval in seconds
        self.auto_start = True

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the scheduler with a Flask app"""
        # Configure default settings
        app.config.setdefault('SCHEDULER_ENABLED', True)
        app.config.setdefault('SCHEDULER_AUTOSTART', True)
        app.config.setdefault('SCHEDULER_TICK_INTERVAL', 1)

        self.tick_interval = app.config['SCHEDULER_TICK_INTERVAL']
        self.auto_start = app.config['SCHEDULER_AUTOSTART']

        # Register extension with app
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['scheduler'] = self

        # Register management blueprint
        app.register_blueprint(management_bp, url_prefix='/internal')

        # Discover and add tasks
        self._discover_tasks(app)

        # Auto-start if enabled
        if app.config['SCHEDULER_ENABLED'] and self.auto_start:
            # Use app.before_request as before_first_request is deprecated
            @app.before_request
            def start_scheduler():
                if not self.running:
                    self.start()

    def add_task(self, task: Task) -> None:
        """Add a task to the scheduler"""
        self.tasks[task.name] = task
        # Calculate next run time
        self._calculate_next_run(task)
        logger.info(f"Added task: {task.name}")

    def remove_task(self, name: str) -> None:
        """Remove a task from the scheduler"""
        if name in self.tasks:
            del self.tasks[name]
            logger.info(f"Removed task: {name}")

    def _calculate_next_run(self, task: Task) -> None:
        """Calculate the next run time for a task"""
        now = datetime.utcnow()
        if task.delay:
            task.next_run = now + timedelta(seconds=task.delay)
            # Reset delay to None after first run
            task.delay = None
        elif task.interval:
            if task.next_run is None:
                task.next_run = now
            else:
                task.next_run += timedelta(seconds=task.interval)
        elif task.cron:
            task.next_run = CronParser.get_next_run(task.cron)

    def _run_pending_tasks(self) -> None:
        """Run all pending tasks"""
        now = datetime.utcnow()
        for task in self.tasks.values():
            if task.next_run and task.next_run <= now and task.status != TaskStatus.RUNNING:
                # Run task in a separate thread
                thread = threading.Thread(target=task.run, name=f"Task-{task.name}")
                thread.start()

    def _scheduler_loop(self) -> None:
        """Main scheduler loop"""
        logger.info("Scheduler loop started")
        while self.running:
            self._run_pending_tasks()
            time.sleep(self.tick_interval)
        logger.info("Scheduler loop stopped")

    def start(self) -> None:
        """Start the scheduler"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._scheduler_loop, name="Scheduler")
            self.thread.start()
            logger.info("Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler"""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join()
            logger.info("Scheduler stopped")

    def _discover_tasks(self, app) -> None:
        """Discover tasks decorated with @interval, @delay, or @cron"""
        # Import the app module to discover tasks
        import sys
        module = sys.modules.get(app.import_name)
        if module:
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and hasattr(attr, '_scheduler_task'):
                    task_info = attr._scheduler_task
                    task = Task(**task_info)
                    self.add_task(task)

    def reload(self) -> None:
        """Reload the scheduler"""
        logger.info("Reloading scheduler...")
        self.stop()
        # Clear existing tasks and rediscover
        self.tasks.clear()
        self._discover_tasks(self.app)
        self.start()
        logger.info("Scheduler reloaded")


# Create management blueprint
management_bp = Blueprint('scheduler_management', __name__)


@management_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """Get scheduler metrics"""
    scheduler = current_app.extensions.get('scheduler')
    if not scheduler:
        return jsonify({'error': 'Scheduler not initialized'}), 500

    metrics = {
        'running': scheduler.running,
        'task_count': len(scheduler.tasks),
        'tasks': {}
    }

    for name, task in scheduler.tasks.items():
        metrics['tasks'][name] = {
            'status': task.status.value,
            'last_run': task.last_run.isoformat() if task.last_run else None,
            'last_completed': task.last_completed.isoformat() if task.last_completed else None,
            'last_failed': task.last_failed.isoformat() if task.last_failed else None,
            'retries': task.retries,
            'next_run': task.next_run.isoformat() if task.next_run else None
        }

    return jsonify(metrics)


@management_bp.route('/tasks/<name>/run', methods=['POST'])
def run_task(name: str):
    """Run a task immediately"""
    scheduler = current_app.extensions.get('scheduler')
    if not scheduler:
        return jsonify({'error': 'Scheduler not initialized'}), 500

    if name not in scheduler.tasks:
        return jsonify({'error': f'Task {name} not found'}), 404

    task = scheduler.tasks[name]
    # Run task in a separate thread
    thread = threading.Thread(target=task.run, name=f"Task-{name}-manual")
    thread.start()

    return jsonify({'status': 'Task started', 'task_name': name})


@management_bp.route('/reload', methods=['POST'])
def reload_scheduler():
    """Reload the scheduler"""
    scheduler = current_app.extensions.get('scheduler')
    if not scheduler:
        return jsonify({'error': 'Scheduler not initialized'}), 500

    scheduler.reload()
    return jsonify({'status': 'Scheduler reloaded'})
