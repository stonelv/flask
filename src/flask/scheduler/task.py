from datetime import datetime, timezone, timedelta
from typing import Callable, Optional
from flask.scheduler.cron_parser import CronParser

class Task:
    """Task data structure for scheduler jobs."""
    
    def __init__(
        self,
        name: str,
        func: Callable,
        task_type: str,
        interval_seconds: Optional[int] = None,
        delay_seconds: Optional[int] = None,
        cron_expr: Optional[str] = None,
        args: Optional[list] = None,
        kwargs: Optional[dict] = None
    ):
        self.name = name
        self.func = func
        self.task_type = task_type
        self.interval_seconds = interval_seconds
        self.delay_seconds = delay_seconds
        self.cron_expr = cron_expr
        self.args = args or []
        self.kwargs = kwargs or {}
        
        # Task execution metadata
        self.next_run: Optional[datetime] = None
        self.last_run: Optional[datetime] = None
        self.run_count = 0
        self.last_duration_ms: Optional[float] = None
        self.last_error: Optional[str] = None
        self.status = 'pending'
        
        # Initialize next_run based on task type
        now = datetime.now(timezone.utc)
        if task_type == 'interval':
            self.next_run = now + timedelta(seconds=interval_seconds)
        elif task_type == 'delay':
            self.next_run = now + timedelta(seconds=delay_seconds)
        elif task_type == 'cron':
            self.next_run = CronParser.get_next_run(cron_expr, now)
    
    def run(self) -> None:
        """Execute the task function with its arguments."""
        self.func(*self.args, **self.kwargs)
