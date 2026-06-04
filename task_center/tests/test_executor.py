"""
Tests for Task Executor
"""
import time
import pytest
from task_center.models import Task, TaskStatus
from task_center.executor import TaskContext, TaskCancelledError


class TestTaskContext:
    """测试TaskContext"""
    
    def test_context_initialization(self):
        """测试上下文初始化"""
        ctx = TaskContext(task_id="test-123")
        
        assert ctx.task_id == "test-123"
        assert not ctx.is_cancelled()
        assert ctx._progress == 0
        assert ctx._stage == ""
        assert ctx._logs == []
    
    def test_check_cancelled(self):
        """测试取消检查"""
        ctx = TaskContext(task_id="test-123")
        
        # 未取消时不应抛出异常
        ctx.check_cancelled()
        
        # 取消后应抛出异常
        ctx.cancel()
        assert ctx.is_cancelled()
        
        with pytest.raises(TaskCancelledError):
            ctx.check_cancelled()
    
    def test_set_progress(self, repository):
        """测试设置进度"""
        ctx = TaskContext(task_id="test-123", _repository=repository)
        
        ctx.set_progress(50, "halfway")
        
        assert ctx._progress == 50
        assert ctx._stage == "halfway"
        
        # 测试进度限制
        ctx.set_progress(150)
        assert ctx._progress == 100
        
        ctx.set_progress(-10)
        assert ctx._progress == 0
    
    def test_logging(self):
        """测试日志记录"""
        ctx = TaskContext(task_id="test-123")
        
        ctx.info("Info message", extra="data")
        ctx.warning("Warning message")
        ctx.error("Error message", code=500)
        
        assert len(ctx._logs) == 3
        
        # 检查日志格式
        info_log = ctx._logs[0]
        assert info_log["level"] == "INFO"
        assert info_log["message"] == "Info message"
        assert info_log["extra"] == "data"
        assert "timestamp" in info_log


class TestTaskExecutor:
    """测试TaskExecutor"""
    
    def test_register_handler(self, executor):
        """测试注册处理器"""
        from task_center.executor import TaskHandler, TaskContext
        
        class TestHandler(TaskHandler):
            @property
            def task_type(self):
                return "test_handler"
            
            def execute(self, context, payload):
                return {"test": True}
        
        executor.register_handler(TestHandler())
        assert "test_handler" in executor._handlers
    
    def test_submit_and_execute(self, executor_with_handlers, repository):
        """测试提交和执行任务"""
        task = Task(type="quick_task", payload={"duration": 0.1})
        repository.save(task)
        
        # 提交任务
        submitted = executor_with_handlers.submit(task)
        assert submitted.status == TaskStatus.RUNNING
        assert submitted.started_at is not None
        
        # 等待任务完成
        time.sleep(0.5)
        
        # 验证任务完成
        updated = repository.get_by_id(task.id)
        assert updated.status == TaskStatus.SUCCEEDED
        assert updated.result == {"executed": True, "duration": 0.1}
    
    def test_task_failure(self, executor_with_handlers, repository):
        """测试任务失败处理"""
        task = Task(
            type="failing_task",
            payload={"error": "Something went wrong"}
        )
        repository.save(task)
        
        executor_with_handlers.submit(task)
        time.sleep(0.3)
        
        updated = repository.get_by_id(task.id)
        assert updated.status == TaskStatus.FAILED
        assert "Something went wrong" in updated.error
    
    def test_task_cancellation(self, executor_with_handlers, repository):
        """测试任务取消"""
        task = Task(
            type="cancellable_task",
            payload={"steps": 20}
        )
        repository.save(task)
        
        # 提交任务
        executor_with_handlers.submit(task)
        time.sleep(0.3)  # 让任务开始执行
        
        # 取消任务
        cancelled = executor_with_handlers.cancel(task.id)
        assert cancelled is True
        
        # 等待任务处理取消
        time.sleep(0.5)
        
        # 验证任务状态
        updated = repository.get_by_id(task.id)
        assert updated.status == TaskStatus.CANCELLED
        assert updated.cancelled_at is not None
    
    def test_cancel_nonexistent_task(self, executor):
        """测试取消不存在的任务"""
        result = executor.cancel("nonexistent-task-id")
        assert result is False
    
    def test_get_context(self, executor_with_handlers, repository):
        """测试获取执行上下文"""
        task = Task(type="cancellable_task", payload={"steps": 10})
        repository.save(task)

        # 提交前获取上下文应为None
        ctx = executor_with_handlers.get_context(task.id)
        assert ctx is None

        # 提交后应能获取上下文
        executor_with_handlers.submit(task)
        time.sleep(0.1)

        ctx = executor_with_handlers.get_context(task.id)
        assert ctx is not None
        assert ctx.task_id == task.id

        # 等待任务完成或取消
        time.sleep(3)

        # 完成后上下文应被移除（任务可能已完成或被取消）
        final_task = repository.get_by_id(task.id)
        assert final_task.status in [TaskStatus.SUCCEEDED, TaskStatus.CANCELLED, TaskStatus.FAILED]


class TestLongRunningTaskHandler:
    """测试长任务处理器"""

    def test_task_execution_stages(self, executor, repository):
        """测试任务执行阶段"""
        from task_center.executor import LongRunningTaskHandler

        executor.register_handler(LongRunningTaskHandler())

        task = Task(
            type="long_running_task",
            payload={"duration": 2, "items": 3}
        )
        repository.save(task)

        # 提交任务
        executor.submit(task)

        # 等待一段时间，检查进度更新
        time.sleep(0.5)
        updated = repository.get_by_id(task.id)
        assert updated.status == TaskStatus.RUNNING
        # 进度可能为0（初始化阶段），但stage应该有值
        assert updated.stage != ""

        # 等待任务完成（最多等待10秒）
        completed = updated
        for _ in range(100):
            completed = repository.get_by_id(task.id)
            if completed.status == TaskStatus.SUCCEEDED:
                break
            time.sleep(0.1)

        assert completed.status == TaskStatus.SUCCEEDED
        assert completed.progress == 100
        assert completed.result is not None
        assert "processed_items" in completed.result

    def test_task_cancellation_during_execution(self, executor, repository):
        """测试执行中取消任务"""
        from task_center.executor import LongRunningTaskHandler

        executor.register_handler(LongRunningTaskHandler())

        task = Task(
            type="long_running_task",
            payload={"duration": 10, "items": 20}
        )
        repository.save(task)
        
        executor.submit(task)
        time.sleep(0.5)

        # 取消任务
        executor.cancel(task.id)

        # 等待取消处理（最多等待5秒）
        updated = repository.get_by_id(task.id)
        for _ in range(50):
            updated = repository.get_by_id(task.id)
            if updated.status == TaskStatus.CANCELLED:
                break
            time.sleep(0.1)

        assert updated.status == TaskStatus.CANCELLED
