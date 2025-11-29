from typing import Callable, List, Any, Optional
from .scheduler import Task
from flask import current_app


def interval(seconds: int, name: Optional[str] = None, args: List[Any] = None, kwargs: dict = None) -> Callable:
    """Decorator to schedule a task to run at regular intervals"""
    def decorator(func: Callable) -> Callable:
        # Store task info in the function itself
        func._scheduler_task = {
            'name': name or func.__name__,
            'func': func,
            'interval': seconds,
            'args': args,
            'kwargs': kwargs
        }
        return func
    return decorator


def delay(seconds: int, name: Optional[str] = None, args: List[Any] = None, kwargs: dict = None) -> Callable:
    """Decorator to schedule a task to run once after a delay"""
    def decorator(func: Callable) -> Callable:
        # Store task info in the function itself
        func._scheduler_task = {
            'name': name or func.__name__,
            'func': func,
            'delay': seconds,
            'args': args,
            'kwargs': kwargs
        }
        return func
    return decorator


def cron(expr: str, name: Optional[str] = None, args: List[Any] = None, kwargs: dict = None) -> Callable:
    """Decorator to schedule a task to run on a cron schedule"""
    def decorator(func: Callable) -> Callable:
        # Store task info in the function itself
        func._scheduler_task = {
            'name': name or func.__name__,
            'func': func,
            'cron': expr,
            'args': args,
            'kwargs': kwargs
        }
        return func
    return decorator
