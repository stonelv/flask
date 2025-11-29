import threading
import time
import inspect
import importlib
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Type, Callable
from flask import Flask
from flask.scheduler.storage import TaskStorage
from flask.scheduler.task import Task
from flask.scheduler.metrics import Metrics
from flask.scheduler.blueprint import scheduler_blueprint

class Scheduler:
    """Core scheduler implementation for Flask applications."""
    
    def __init__(self, app: Optional[Flask] = None, tick_interval: int = 1):
        self.app = app
        self.tick_interval = tick_interval
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.storage = TaskStorage()
        self.metrics = Metrics()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Initialize the scheduler with a Flask application."""
        self.app = app
        
        # Configure scheduler
        self.app.config.setdefault('SCHEDULER_ENABLED', True)
        self.app.config.setdefault('SCHEDULER_AUTOSTART', True)
        self.app.config.setdefault('SCHEDULER_TICK_INTERVAL', 1)
        self.app.config.setdefault('SCHEDULER_TASK_MODULES', ['tasks'])
        
        self.tick_interval = self.app.config['SCHEDULER_TICK_INTERVAL']
        self.task_modules = self.app.config['SCHEDULER_TASK_MODULES']
        
        # Register blueprint
        self.app.register_blueprint(scheduler_blueprint, url_prefix='/_internal')
        
        # Store scheduler in app extensions
        if 'scheduler' not in self.app.extensions:
            self.app.extensions['scheduler'] = self
        
        # Discover and register tasks
        self.discover_tasks()
        
        # Start scheduler if enabled and autostart is True
        if self.app.config['SCHEDULER_ENABLED'] and self.app.config['SCHEDULER_AUTOSTART']:
            self.start()
    
    def start(self) -> None:
        """Start the scheduler thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._tick_loop, daemon=True)
            self.thread.start()
            self.app.logger.info('Scheduler started')
    
    def stop(self) -> None:
        """Stop the scheduler thread."""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join()
            self.app.logger.info('Scheduler stopped')
    
    def _tick_loop(self) -> None:
        """Main scheduler loop that runs every tick interval."""
        while self.running:
            try:
                self._run_pending_tasks()
            except Exception as e:
                self.app.logger.error(f'Scheduler tick loop error: {e}')
            time.sleep(self.tick_interval)
    
    def _run_pending_tasks(self) -> None:
        """Run all tasks that are due to run now."""
        now = datetime.now(timezone.utc)
        tasks = self.storage.get_all_tasks()
        
        for task in tasks:
            if task.next_run and task.next_run <= now and task.status != 'running':
                # Update task status to running
                with self.storage.lock:
                    task.status = 'running'
                
                # Run task in a separate thread
                threading.Thread(
                    target=self._execute_task,
                    args=(task, now),
                    daemon=True
                ).start()
    
    def discover_tasks(self) -> None:
        """Discover tasks from configured modules."""
        if not self.app:
            return
            
        for module_name in self.task_modules:
            try:
                # Import the module
                module = importlib.import_module(module_name)
                
                # Iterate through all objects in the module
                for name, obj in inspect.getmembers(module):
                    # Check if the object is a function with _scheduler_task attribute
                    if inspect.isfunction(obj) and hasattr(obj, '_scheduler_task'):
                        task_info = obj._scheduler_task
                        
                        # Create a Task instance
                        task = Task(
                            name=task_info['name'],
                            func=obj,
                            task_type=task_info['task_type'],
                            interval_seconds=task_info.get('interval_seconds'),
                            delay_seconds=task_info.get('delay_seconds'),
                            cron_expr=task_info.get('cron_expr'),
                            args=task_info.get('args', []),
                            kwargs=task_info.get('kwargs', {})
                        )
                        
                        # Add the task to storage
                        self.storage.add_task(task)
                        
                        self.app.logger.info(f'Discovered task: {task.name}')
            except ImportError:
                self.app.logger.warning(f'Could not import task module: {module_name}')
                continue
            except Exception as e:
                self.app.logger.error(f'Error discovering tasks in module {module_name}: {e}')
                continue

    def _execute_task(self, task: Task, run_time: datetime) -> None:
        """Execute a task and update its status."""
        task.last_run = run_time
        task.run_count += 1
        start_time = time.perf_counter()
        
        try:
            # Execute the task
            task.run()
            task.status = 'completed'
        except Exception as e:
            task.status = 'failed'
            task.last_error = self._truncate_error(str(e), max_length=500)
            self.storage.add_recent_exception(task.name, run_time, task.last_error)
            self.app.logger.error(f'Task {task.name} failed: {task.last_error}')
        
        # Calculate duration
        end_time = time.perf_counter()
        task.last_duration_ms = round((end_time - start_time) * 1000)
        
        # Update next_run based on task type
        with self.storage.lock:
            if task.task_type == 'interval':
                task.next_run = task.last_run + timedelta(seconds=task.interval_seconds)
            elif task.task_type == 'cron':
                task.next_run = task.get_next_run(now=task.last_run)
            elif task.task_type == 'delay':
                task.next_run = None  # Delay tasks run only once
    
    def _truncate_error(self, error: str, max_length: int = 500) -> str:
        """Truncate error message to max length."""
        if len(error) <= max_length:
            return error
        return error[:max_length] + '...'
    
    def reload(self) -> None:
        """Reload the scheduler: stop the thread, re-discover tasks, and start again."""
        self.stop()
        self.storage.clear()
        self.discover_tasks()
        self.start()
    
    def _discover_tasks(self) -> None:
        """Discover tasks decorated with scheduler decorators."""
        if not self.app:
            return
        
        # Clear existing tasks
        self.storage.clear_tasks()
        
        # Discover tasks in the application's modules
        for module_name, module in list(self.app.blueprints.items()):
            self._discover_tasks_in_module(module)
        
        # Discover tasks in the main application module
        self._discover_tasks_in_module(self.app.import_name)
    
    def _discover_tasks_in_module(self, module_name: str) -> None:
        """Discover tasks in a specific module."""
        try:
            module = __import__(module_name, fromlist=[''])
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and hasattr(attr, '_scheduler_task'):
                    task_info = attr._scheduler_task
                    task = Task(
                        name=task_info.get('name', attr_name),
                        func=attr,
                        task_type=task_info.get('task_type'),
                        interval_seconds=task_info.get('interval_seconds'),
                        delay_seconds=task_info.get('delay_seconds'),
                        cron_expr=task_info.get('cron_expr')
                    )
                    self.storage.add_task(task)
        except ImportError:
            pass
