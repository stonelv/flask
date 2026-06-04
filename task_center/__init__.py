"""
Task Center - 后台任务中心

提供可复用的异步任务能力：
- 创建任务（支持幂等性去重）
- 查询任务（支持分页和过滤）
- 取消任务（协作式取消）
- 进度上报与日志可观测
"""
from .models import Task, TaskRepository, TaskStatus
from .executor import TaskExecutor, TaskHandler, TaskContext, TaskCancelledError
from .service import TaskService
from .app import create_app

__version__ = "1.0.0"
__all__ = [
    "Task",
    "TaskRepository",
    "TaskStatus",
    "TaskExecutor",
    "TaskHandler",
    "TaskContext",
    "TaskCancelledError",
    "TaskService",
    "create_app",
]
