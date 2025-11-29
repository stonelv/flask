from typing import Callable, List, Any, Optional
from .scheduler import Task
from flask import current_app


def interval_seconds(seconds: int, name: Optional[str] = None, args: List[Any] = None, kwargs: dict = None) -> Callable:
    """Decorator to schedule a task to run at regular intervals"""
    def decorator(func: Callable) -> Callable:
        # Store task info in the function itself
        func._scheduler_task = {
            'name': name or func.__name__,
            'task_type': 'interval',
            'interval_seconds': seconds,
            'args': args,
            'kwargs': kwargs
        }
        return func
    return decorator


def delay_seconds(seconds: int, name: Optional[str] = None, args: List[Any] = None, kwargs: dict = None) -> Callable:
    """Decorator to schedule a task to run once after a delay"""
    def decorator(func: Callable) -> Callable:
        # Store task info in the function itself
        func._scheduler_task = {
            'name': name or func.__name__,
            'task_type': 'delay',
            'delay_seconds': seconds,
            'args': args,
            'kwargs': kwargs
        }
        return func
    return decorator


def cron(cron_expr: str, name: Optional[str] = None, args: List[Any] = None, kwargs: dict = None) -> Callable:
    """Decorator to schedule a task to run on a cron schedule"""
    def decorator(func: Callable) -> Callable:
        # Store task info in the function itself
        func._scheduler_task = {
            'name': name or func.__name__,
            'task_type': 'cron',
            'cron_expr': cron_expr,
            'args': args,
            'kwargs': kwargs
        }
        return func
    return decorator
