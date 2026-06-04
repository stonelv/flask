"""
Tests for Task Service - 多进程幂等并发安全
"""
import time
import threading
import pytest
from task_center.models import Task, TaskStatus


class TestTaskService:
    """测试TaskService"""

    def test_create_task_without_idempotency(self, service):
        """测试无幂等键创建任务"""
        task, is_new, error = service.create_task(
            task_type="long_running_task",
            payload={"duration": 15}
        )

        assert error is None
        assert is_new is True
        assert task.id is not None
        assert task.type == "long_running_task"
        assert task.status == TaskStatus.RUNNING
        assert task.idempotency_key is None

    def test_create_task_with_idempotency(self, service):
        """测试有幂等键创建任务"""
        idempotency_key = "unique_operation_123"

        # 第一次创建
        task1, is_new1, error1 = service.create_task(
            task_type="long_running_task",
            payload={"duration": 15},
            idempotency_key=idempotency_key
        )

        assert error1 is None
        assert is_new1 is True
        assert task1.idempotency_key == idempotency_key

        # 第二次使用相同幂等键
        task2, is_new2, error2 = service.create_task(
            task_type="long_running_task",
            payload={"duration": 20},  # 不同参数
            idempotency_key=idempotency_key
        )

        assert error2 is None
        assert is_new2 is False
        assert task2.id == task1.id  # 返回相同任务

    def test_idempotency_concurrent_safety(self, service):
        """测试幂等性并发安全 - 确保同 key 不会重复执行"""
        idempotency_key = "concurrent_test_key"
        results = []

        def create_task():
            task, is_new, error = service.create_task(
                task_type="long_running_task",
                payload={"duration": 15},
                idempotency_key=idempotency_key
            )
            if task:
                results.append((task.id, is_new))

        # 并发创建
        threads = [threading.Thread(target=create_task) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有结果应该是同一个任务
        task_ids = set(r[0] for r in results)
        assert len(task_ids) == 1, f"Expected 1 unique task, got {len(task_ids)}"

        # 只有一个应该是新创建的
        new_count = sum(1 for _, is_new in results if is_new)
        assert new_count == 1, f"Expected 1 new task, got {new_count}"

    def test_get_task(self, service):
        """测试获取任务"""
        # 创建任务
        task, _, _ = service.create_task(
            task_type="long_running_task",
            payload={"duration": 15}
        )

        # 获取任务
        found = service.get_task(task.id)
        assert found is not None
        assert found.id == task.id

        # 获取不存在的任务
        not_found = service.get_task("nonexistent-id")
        assert not_found is None

    def test_list_tasks(self, service):
        """测试任务列表"""
        # 创建多个任务
        for i in range(3):
            service.create_task(
                task_type="long_running_task",
                payload={"duration": 15}
            )

        # 等待任务完成
        time.sleep(0.5)

        # 查询所有任务
        tasks, total = service.list_tasks(limit=10, offset=0)
        assert total >= 3
        assert len(tasks) >= 3

        # 按状态过滤
        running_tasks, _ = service.list_tasks(status=TaskStatus.RUNNING)
        succeeded_tasks, _ = service.list_tasks(status=TaskStatus.SUCCEEDED)

        # 按类型过滤
        lr_tasks, _ = service.list_tasks(task_type="long_running_task")
        assert len(lr_tasks) >= 3

    def test_cancel_pending_task(self, service):
        """测试取消待处理任务"""
        # 创建一个任务
        task, _, _ = service.create_task(
            task_type="long_running_task",
            payload={"duration": 15}
        )

        # 立即取消
        success, message = service.cancel_task(task.id)

        assert success is True
        # 消息可能是 "Task cancelled" 或 "Task cancellation requested"
        assert "cancel" in message.lower()

        # 验证状态（可能需要等待状态更新）
        for _ in range(20):
            updated = service.get_task(task.id)
            if updated.status == TaskStatus.CANCELLED:
                break
            time.sleep(0.1)
        assert updated.status == TaskStatus.CANCELLED

    def test_cancel_running_task(self, service):
        """测试取消运行中任务"""
        # 创建并启动任务
        task, _, _ = service.create_task(
            task_type="long_running_task",
            payload={"duration": 20}
        )

        # 等待任务开始运行
        time.sleep(0.3)

        # 取消任务
        success, message = service.cancel_task(task.id)

        assert success is True

        # 等待取消生效
        time.sleep(0.5)

        # 验证状态
        updated = service.get_task(task.id)
        assert updated.status == TaskStatus.CANCELLED

    def test_cancel_completed_task(self, service, executor_with_handlers):
        """测试取消已完成任务"""
        # 使用带handler的executor
        service.executor = executor_with_handlers

        # 创建一个快速完成的任务
        task, _, _ = service.create_task(
            task_type="quick_task",
            payload={"duration": 0.1}
        )

        # 等待完成
        time.sleep(0.5)

        # 尝试取消
        success, message = service.cancel_task(task.id)

        assert success is False
        assert "cannot be cancelled" in message.lower()

    def test_cancel_nonexistent_task(self, service):
        """测试取消不存在的任务"""
        success, message = service.cancel_task("nonexistent-id")

        assert success is False
        assert "not found" in message.lower()

    def test_cleanup_old_tasks(self, service, executor_with_handlers):
        """测试清理旧任务"""
        # 使用带handler的executor
        service.executor = executor_with_handlers

        # 创建任务
        task, _, _ = service.create_task(
            task_type="quick_task",
            payload={"duration": 0.1}
        )

        # 等待完成
        time.sleep(0.5)

        # 清理0天前的任务
        count = service.cleanup_old_tasks(days=0)
        assert count >= 1

        # 验证任务已删除
        assert service.get_task(task.id) is None


class TestIdempotencyNoDuplicateExecution:
    """测试幂等性确保不重复执行"""

    def test_same_key_not_re_execute(self, service):
        """
        关键测试：同 key 重复请求不能再次 submit/execute
        验证方式：检查任务状态，重复请求后任务状态不应重置为 PENDING
        """
        idempotency_key = "test_no_reexecute_key"

        # 第一次创建
        task1, is_new1, _ = service.create_task(
            task_type="long_running_task",
            payload={"duration": 15},
            idempotency_key=idempotency_key
        )

        assert is_new1 is True
        first_status = task1.status

        # 等待任务开始运行
        time.sleep(0.2)

        # 获取更新后的状态
        task1_updated = service.get_task(task1.id)
        status_before = task1_updated.status

        # 第二次使用相同幂等键
        task2, is_new2, _ = service.create_task(
            task_type="long_running_task",
            payload={"duration": 20},
            idempotency_key=idempotency_key
        )

        assert is_new2 is False
        assert task2.id == task1.id

        # 关键验证：任务状态不应被重置
        # 如果重复执行，状态可能会变回 PENDING
        task2_check = service.get_task(task2.id)
        assert task2_check.status == status_before, \
            f"Task status should remain {status_before}, but got {task2_check.status}"
