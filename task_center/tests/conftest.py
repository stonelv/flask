"""
Test Configuration and Fixtures
"""
import os
import tempfile
import pytest
from task_center.models import TaskRepository, Task, TaskStatus
from task_center.executor import TaskExecutor, TaskHandler, TaskContext
from task_center.service import TaskService
from task_center.app import create_app


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def repository(temp_db):
    """创建任务仓库"""
    return TaskRepository(temp_db)


@pytest.fixture
def executor(repository):
    """创建任务执行器"""
    exec = TaskExecutor(repository, max_workers=2)
    yield exec
    exec.shutdown(wait=False)


@pytest.fixture
def service(repository, executor):
    """创建任务服务"""
    return TaskService(repository, executor)


@pytest.fixture
def app(temp_db):
    """创建测试Flask应用"""
    test_config = {
        "DATABASE": temp_db,
        "MAX_WORKERS": 2,
        "TESTING": True,
    }
    app = create_app(test_config)
    yield app
    # 清理
    app.executor.shutdown(wait=False)


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


class QuickTaskHandler(TaskHandler):
    """快速任务处理器 - 用于测试"""
    
    @property
    def task_type(self) -> str:
        return "quick_task"
    
    def execute(self, context: TaskContext, payload: dict) -> dict:
        import time
        duration = payload.get("duration", 0.1)
        context.info("Quick task started", duration=duration)
        time.sleep(duration)
        context.set_progress(100, "Completed")
        return {"executed": True, "duration": duration}


class CancellableTaskHandler(TaskHandler):
    """可取消任务处理器 - 用于测试取消功能"""
    
    @property
    def task_type(self) -> str:
        return "cancellable_task"
    
    def execute(self, context: TaskContext, payload: dict) -> dict:
        import time
        steps = payload.get("steps", 10)
        
        for i in range(steps):
            context.check_cancelled()
            context.set_progress((i + 1) * 100 // steps, f"Step {i+1}/{steps}")
            time.sleep(0.2)
        
        return {"completed_steps": steps}


class FailingTaskHandler(TaskHandler):
    """失败任务处理器 - 用于测试错误处理"""
    
    @property
    def task_type(self) -> str:
        return "failing_task"
    
    def execute(self, context: TaskContext, payload: dict) -> dict:
        error_message = payload.get("error", "Task failed as requested")
        raise RuntimeError(error_message)


@pytest.fixture
def executor_with_handlers(repository):
    """创建带有测试处理器的执行器"""
    exec = TaskExecutor(repository, max_workers=2)
    exec.register_handler(QuickTaskHandler())
    exec.register_handler(CancellableTaskHandler())
    exec.register_handler(FailingTaskHandler())
    yield exec
    exec.shutdown(wait=False)
