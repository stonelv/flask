"""
Task Center - Service Layer
提供幂等性控制和业务逻辑
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Optional

from .models import Task, TaskRepository, TaskStatus
from .executor import TaskExecutor

logger = logging.getLogger("task_center")


class TaskService:
    """任务服务 - 提供幂等性控制和业务逻辑"""
    
    def __init__(self, repository: TaskRepository, executor: TaskExecutor):
        self.repository = repository
        self.executor = executor
        # 用于幂等性控制的锁，确保同key的并发请求安全
        self._idempotency_locks: dict[str, threading.Lock] = {}
        self._main_lock = threading.Lock()
    
    def _get_idempotency_lock(self, key: str) -> threading.Lock:
        """获取幂等键对应的锁"""
        with self._main_lock:
            if key not in self._idempotency_locks:
                self._idempotency_locks[key] = threading.Lock()
            return self._idempotency_locks[key]
    
    def create_task(
        self,
        task_type: str,
        payload: dict,
        idempotency_key: Optional[str] = None
    ) -> tuple[Task, bool]:
        """
        创建任务（幂等）
        
        Args:
            task_type: 任务类型
            payload: 任务参数
            idempotency_key: 幂等键，用于去重
            
        Returns:
            (task, is_new): 任务对象和是否为新创建
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
            return task, True
        
        # 使用幂等键锁确保并发安全
        lock = self._get_idempotency_lock(idempotency_key)
        
        with lock:
            # 检查是否已存在相同幂等键的任务
            existing_task = self.repository.get_by_idempotency_key(idempotency_key)
            
            if existing_task:
                logger.info(
                    f"Idempotent request detected, returning existing task: {existing_task.id} "
                    f"(key={idempotency_key}, status={existing_task.status.value})"
                )
                return existing_task, False
            
            # 创建新任务
            task = Task(
                type=task_type,
                payload=payload,
                idempotency_key=idempotency_key,
                status=TaskStatus.PENDING
            )
            self.repository.save(task)
            self.executor.submit(task)
            
            logger.info(
                f"Created new task with idempotency key: {task.id} (key={idempotency_key})"
            )
            return task, True
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务详情"""
        return self.repository.get_by_id(task_id)
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[list[Task], int]:
        """分页查询任务列表"""
        return self.repository.list_tasks(
            status=status,
            task_type=task_type,
            limit=limit,
            offset=offset
        )
    
    def cancel_task(self, task_id: str) -> tuple[bool, str]:
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
