"""
Tests for Task Models
"""
import pytest
from datetime import datetime
from task_center.models import Task, TaskRepository, TaskStatus


class TestTask:
    """测试Task模型"""
    
    def test_task_creation(self):
        """测试任务创建"""
        task = Task(
            type="test_task",
            payload={"key": "value"},
            idempotency_key="unique_key_123"
        )
        
        assert task.id is not None
        assert task.type == "test_task"
        assert task.status == TaskStatus.PENDING
        assert task.progress == 0
        assert task.payload == {"key": "value"}
        assert task.idempotency_key == "unique_key_123"
        assert task.created_at is not None
        assert task.updated_at is not None
    
    def test_task_to_dict(self):
        """测试任务序列化"""
        task = Task(
            type="test_task",
            status=TaskStatus.RUNNING,
            progress=50,
            stage="processing",
            payload={"items": [1, 2, 3]},
            result={"count": 3},
            idempotency_key="key123"
        )
        
        data = task.to_dict()
        
        assert data["id"] == task.id
        assert data["type"] == "test_task"
        assert data["status"] == "RUNNING"
        assert data["progress"] == 50
        assert data["stage"] == "processing"
        assert data["payload"] == {"items": [1, 2, 3]}
        assert data["result"] == {"count": 3}
        assert data["idempotency_key"] == "key123"
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_task_from_dict(self):
        """测试从字典创建任务"""
        data = {
            "id": "test-id-123",
            "type": "test_task",
            "status": "SUCCEEDED",
            "progress": 100,
            "stage": "done",
            "payload": {"input": "data"},
            "result": {"output": "result"},
            "error": None,
            "idempotency_key": "idem_key",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:01",
            "logs": [{"message": "test"}]
        }
        
        task = Task.from_dict(data)
        
        assert task.id == "test-id-123"
        assert task.status == TaskStatus.SUCCEEDED
        assert task.progress == 100
        assert task.created_at == datetime(2024, 1, 1, 0, 0, 0)
        assert task.updated_at == datetime(2024, 1, 1, 0, 0, 1)
    
    def test_is_terminal(self):
        """测试终止状态判断"""
        pending = Task(status=TaskStatus.PENDING)
        running = Task(status=TaskStatus.RUNNING)
        succeeded = Task(status=TaskStatus.SUCCEEDED)
        failed = Task(status=TaskStatus.FAILED)
        cancelled = Task(status=TaskStatus.CANCELLED)
        
        assert not pending.is_terminal()
        assert not running.is_terminal()
        assert succeeded.is_terminal()
        assert failed.is_terminal()
        assert cancelled.is_terminal()
    
    def test_can_cancel(self):
        """测试取消可行性判断"""
        pending = Task(status=TaskStatus.PENDING)
        running = Task(status=TaskStatus.RUNNING)
        succeeded = Task(status=TaskStatus.SUCCEEDED)
        failed = Task(status=TaskStatus.FAILED)
        cancelled = Task(status=TaskStatus.CANCELLED)
        
        assert pending.can_cancel()
        assert running.can_cancel()
        assert not succeeded.can_cancel()
        assert not failed.can_cancel()
        assert not cancelled.can_cancel()


class TestTaskRepository:
    """测试TaskRepository"""
    
    def test_save_and_get(self, repository):
        """测试保存和获取任务"""
        task = Task(
            type="test_task",
            payload={"key": "value"},
            idempotency_key="test_key"
        )
        
        saved = repository.save(task)
        assert saved.id == task.id
        
        retrieved = repository.get_by_id(task.id)
        assert retrieved is not None
        assert retrieved.id == task.id
        assert retrieved.type == "test_task"
        assert retrieved.payload == {"key": "value"}
        assert retrieved.idempotency_key == "test_key"
    
    def test_get_by_idempotency_key(self, repository):
        """测试通过幂等键获取任务"""
        task = Task(
            type="test_task",
            idempotency_key="unique_key"
        )
        repository.save(task)
        
        found = repository.get_by_idempotency_key("unique_key")
        assert found is not None
        assert found.id == task.id
        
        not_found = repository.get_by_idempotency_key("nonexistent_key")
        assert not_found is None
    
    def test_list_tasks(self, repository):
        """测试任务列表查询"""
        # 创建多个任务
        for i in range(5):
            task = Task(
                type="test_task" if i < 3 else "other_task",
                status=TaskStatus.SUCCEEDED if i < 2 else TaskStatus.PENDING
            )
            repository.save(task)
        
        # 测试分页
        tasks, total = repository.list_tasks(limit=3, offset=0)
        assert len(tasks) == 3
        assert total == 5
        
        # 测试状态过滤
        tasks, total = repository.list_tasks(status=TaskStatus.SUCCEEDED)
        assert len(tasks) == 2
        assert all(t.status == TaskStatus.SUCCEEDED for t in tasks)
        
        # 测试类型过滤
        tasks, total = repository.list_tasks(task_type="other_task")
        assert len(tasks) == 2
        assert all(t.type == "other_task" for t in tasks)
    
    def test_update_task(self, repository):
        """测试更新任务"""
        task = Task(type="test_task", status=TaskStatus.PENDING)
        repository.save(task)
        
        # 更新任务
        task.status = TaskStatus.RUNNING
        task.progress = 50
        task.stage = "halfway"
        repository.save(task)
        
        # 验证更新
        retrieved = repository.get_by_id(task.id)
        assert retrieved.status == TaskStatus.RUNNING
        assert retrieved.progress == 50
        assert retrieved.stage == "halfway"
    
    def test_delete_task(self, repository):
        """测试删除任务"""
        task = Task(type="test_task")
        repository.save(task)
        
        assert repository.delete(task.id) is True
        assert repository.get_by_id(task.id) is None
        assert repository.delete(task.id) is False
    
    def test_cleanup_old_tasks(self, repository):
        """测试清理旧任务"""
        import time
        
        # 创建旧任务（手动设置时间）
        old_task = Task(
            type="test_task",
            status=TaskStatus.SUCCEEDED
        )
        repository.save(old_task)
        
        # 创建新任务
        new_task = Task(
            type="test_task",
            status=TaskStatus.SUCCEEDED
        )
        repository.save(new_task)
        
        # 清理0天前的任务（应该清理所有已完成任务）
        count = repository.cleanup_old_tasks(days=0)
        assert count == 2
        
        assert repository.get_by_id(old_task.id) is None
        assert repository.get_by_id(new_task.id) is None
    
    def test_idempotency_key_unique(self, repository):
        """测试幂等键唯一性"""
        task1 = Task(type="test_task", idempotency_key="same_key")
        repository.save(task1)
        
        # 尝试保存相同幂等键的任务应该失败
        task2 = Task(type="test_task", idempotency_key="same_key")
        
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            repository.save(task2)
