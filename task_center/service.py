"""
Task Center - Service Layer
提供幂等性控制和业务逻辑 - 支持多进程并发安全
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Optional, Tuple

from .models import Task, TaskRepository, TaskStatus
from .executor import TaskExecutor

logger = logging.getLogger("task_center")


class TaskService:
    """任务服务 - 提供幂等性控制和业务逻辑（支持多进程并发安全）"""

    def __init__(self, repository: TaskRepository, executor: TaskExecutor):
        self.repository = repository
        self.executor = executor
        # 进程内锁，用于减少同一进程内的 DB 冲突
        self._idempotency_locks: dict[str, threading.Lock] = {}
        self._main_lock = threading.Lock()

    def _get_idempotency_lock(self, key: str) -> threading.Lock:
        """获取幂等键对应的进程内锁"""
        with self._main_lock:
            if key not in self._idempotency_locks:
                self._idempotency_locks[key] = threading.Lock()
            return self._idempotency_locks[key]

    def create_task(
        self,
        task_type: str,
        payload: dict,
        idempotency_key: Optional[str] = None
    ) -> Tuple[Task, bool, Optional[str]]:
        """
        创建任务（幂等，支持多进程并发安全）

        实现策略：
        1. 先尝试原子插入（INSERT），捕获唯一键冲突
        2. 冲突时回读已有任务
        3. 仅当插入成功时才提交执行

        Args:
            task_type: 任务类型
            payload: 任务参数
            idempotency_key: 幂等键，用于去重

        Returns:
            (task, is_new, error): 任务对象、是否为新创建、错误信息
        """
        # 如果没有幂等键，直接创建新任务
        if not idempotency_key:
            task = Task(
                type=task_type,
                payload=payload,
                status=TaskStatus.PENDING
            )
            self.repository.save(task)
            self.executor.submit(task)
            logger.info(f"Created new task without idempotency key: {task.id}")
            return task, True, None

        # 使用进程内锁减少同进程内的 DB 冲突
        lock = self._get_idempotency_lock(idempotency_key)

        with lock:
            # 策略：先尝试原子插入，利用 DB 唯一键约束
            task = Task(
                type=task_type,
                payload=payload,
                idempotency_key=idempotency_key,
                status=TaskStatus.PENDING
            )

            # 尝试原子插入
            inserted = self.repository.insert_or_none(task)

            if inserted:
                # 插入成功，提交执行
                self.executor.submit(task)
                logger.info(
                    f"Created new task with idempotency key: {task.id} (key={idempotency_key})"
                )
                return task, True, None
            else:
                # 插入失败（唯一键冲突），回读已有任务
                existing_task = self.repository.get_by_idempotency_key(idempotency_key)

                if existing_task:
                    logger.info(
                        f"Idempotent request detected, returning existing task: {existing_task.id} "
                        f"(key={idempotency_key}, status={existing_task.status.value})"
                    )
                    return existing_task, False, None
                else:
                    # 极端情况：插入失败但查不到（理论上不应发生）
                    error_msg = "Failed to create or retrieve task"
                    logger.error(error_msg)
                    return None, False, error_msg

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务详情"""
        return self.repository.get_by_id(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[list[Task], int]:
        """分页查询任务列表"""
        return self.repository.list_tasks(
            status=status,
            task_type=task_type,
            limit=limit,
            offset=offset
        )

    def cancel_task(self, task_id: str) -> Tuple[bool, str]:
        """
        取消任务

        Returns:
            (success, message): 是否成功和消息
        """
        task = self.repository.get_by_id(task_id)

        if not task:
            return False, "Task not found"

        if not task.can_cancel():
            return False, f"Task cannot be cancelled, current status: {task.status.value}"

        # 尝试取消执行器中的任务
        cancelled = self.executor.cancel(task_id)

        if cancelled:
            # 任务正在执行，已标记取消
            logger.info(f"Cancelled running task: {task_id}")
            return True, "Task cancellation requested"
        else:
            # 任务可能还未开始执行，直接更新状态
            task.status = TaskStatus.CANCELLED
            task.cancelled_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()
            self.repository.save(task)
            logger.info(f"Cancelled pending task: {task_id}")
            return True, "Task cancelled"

    def cleanup_old_tasks(self, days: int = 7) -> int:
        """清理旧任务"""
        count = self.repository.cleanup_old_tasks(days)
        logger.info(f"Cleaned up {count} old tasks")
        return count
