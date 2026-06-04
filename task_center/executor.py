"""
Task Center - Async Task Executor
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from .models import Task, TaskRepository, TaskStatus

# 配置结构化日志
logger = logging.getLogger("task_center")


class TaskCancelledError(Exception):
    """任务被取消异常"""
    pass


@dataclass
class TaskContext:
    """任务执行上下文"""
    task_id: str
    _cancelled: bool = False
    _progress: int = 0
    _stage: str = ""
    _logs: list = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _repository: Optional[TaskRepository] = None
    
    def is_cancelled(self) -> bool:
        """检查任务是否被取消"""
        return self._cancelled
    
    def check_cancelled(self) -> None:
        """检查取消状态，如果被取消则抛出异常"""
        if self._cancelled:
            raise TaskCancelledError("Task has been cancelled")
    
    def set_progress(self, progress: int, stage: str = "") -> None:
        """更新进度和阶段"""
        with self._lock:
            self._progress = max(0, min(100, progress))
            if stage:
                self._stage = stage
            self._persist_update()
    
    def log(self, level: str, message: str, **kwargs) -> None:
        """添加结构化日志"""
        with self._lock:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": level,
                "message": message,
                **kwargs
            }
            self._logs.append(log_entry)
            
            # 同时输出到标准日志
            log_func = getattr(logger, level.lower(), logger.info)
            log_func(f"[{self.task_id}] {message}", extra=kwargs)
            
            self._persist_update()
    
    def info(self, message: str, **kwargs) -> None:
        """记录info级别日志"""
        self.log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """记录warning级别日志"""
        self.log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """记录error级别日志"""
        self.log("ERROR", message, **kwargs)
    
    def _persist_update(self) -> None:
        """持久化更新到数据库"""
        if self._repository:
            try:
                task = self._repository.get_by_id(self.task_id)
                if task:
                    task.progress = self._progress
                    task.stage = self._stage
                    task.logs = self._logs.copy()
                    task.updated_at = datetime.utcnow()
                    self._repository.save(task)
            except Exception as e:
                logger.error(f"Failed to persist task update: {e}")
    
    def cancel(self) -> None:
        """标记任务为取消状态"""
        with self._lock:
            self._cancelled = True


class TaskHandler(ABC):
    """任务处理器基类"""
    
    @property
    @abstractmethod
    def task_type(self) -> str:
        """返回任务类型"""
        pass
    
    @abstractmethod
    def execute(self, context: TaskContext, payload: dict) -> dict:
        """
        执行任务
        
        Args:
            context: 任务执行上下文
            payload: 任务输入参数
            
        Returns:
            任务执行结果
        """
        pass


class LongRunningTaskHandler(TaskHandler):
    """示例长任务处理器 - 10~30秒的模拟任务"""
    
    @property
    def task_type(self) -> str:
        return "long_running_task"
    
    def execute(self, context: TaskContext, payload: dict) -> dict:
        """
        执行示例长任务
        
        阶段：
        1. 初始化 (0-10%)
        2. 数据准备 (10-30%)
        3. 数据处理 (30-70%)
        4. 结果汇总 (70-90%)
        5. 清理 (90-100%)
        """
        # 获取配置参数
        duration = payload.get("duration", 20)  # 默认20秒
        duration = max(10, min(30, duration))  # 限制在10-30秒
        
        context.info("Task started", duration=duration, payload=payload)
        
        # 阶段1: 初始化 (0-10%)
        context.set_progress(0, "初始化中...")
        self._simulate_work(context, duration * 0.1, "初始化系统资源")
        context.set_progress(10, "初始化完成")
        context.info("Initialization completed")
        
        # 阶段2: 数据准备 (10-30%)
        context.set_progress(10, "准备数据中...")
        self._simulate_work(context, duration * 0.2, "加载和验证数据")
        context.set_progress(30, "数据准备完成")
        context.info("Data preparation completed")
        
        # 阶段3: 数据处理 (30-70%) - 主要工作阶段
        context.set_progress(30, "处理数据中...")
        items = payload.get("items", 10)
        for i in range(items):
            context.check_cancelled()
            progress = 30 + (i + 1) * 40 // items
            context.set_progress(progress, f"处理数据项 {i+1}/{items}")
            time.sleep(duration * 0.4 / items)
            context.info(f"Processed item {i+1}/{items}")
        context.set_progress(70, "数据处理完成")
        
        # 阶段4: 结果汇总 (70-90%)
        context.set_progress(70, "汇总结果中...")
        self._simulate_work(context, duration * 0.2, "生成报告")
        context.set_progress(90, "结果汇总完成")
        context.info("Result aggregation completed")
        
        # 阶段5: 清理 (90-100%)
        context.set_progress(90, "清理资源中...")
        self._simulate_work(context, duration * 0.1, "释放资源")
        context.set_progress(100, "任务完成")
        context.info("Cleanup completed")
        
        return {
            "processed_items": items,
            "duration": duration,
            "summary": f"Successfully processed {items} items in {duration} seconds"
        }
    
    def _simulate_work(self, context: TaskContext, duration: float, description: str) -> None:
        """模拟工作，支持取消检查"""
        steps = max(1, int(duration * 2))  # 每0.5秒检查一次
        sleep_time = duration / steps
        
        for i in range(steps):
            context.check_cancelled()
            time.sleep(sleep_time)


class TaskExecutor:
    """任务执行器 - 管理异步任务执行"""
    
    def __init__(self, repository: TaskRepository, max_workers: int = 5):
        self.repository = repository
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running_tasks: dict[str, TaskContext] = {}
        self._handlers: dict[str, TaskHandler] = {}
        self._lock = threading.Lock()
        
        # 注册内置处理器
        self.register_handler(LongRunningTaskHandler())
    
    def register_handler(self, handler: TaskHandler) -> None:
        """注册任务处理器"""
        self._handlers[handler.task_type] = handler
        logger.info(f"Registered task handler: {handler.task_type}")
    
    def submit(self, task: Task) -> Task:
        """提交任务执行"""
        handler = self._handlers.get(task.type)
        if not handler:
            raise ValueError(f"No handler registered for task type: {task.type}")
        
        # 更新任务状态
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        self.repository.save(task)
        
        # 创建执行上下文
        context = TaskContext(
            task_id=task.id,
            _repository=self.repository
        )
        
        with self._lock:
            self._running_tasks[task.id] = context
        
        # 提交到线程池执行
        future = self._executor.submit(self._execute_task, task, handler, context)
        
        # 添加回调处理结果
        future.add_done_callback(lambda f: self._on_task_complete(task.id, f))
        
        return task
    
    def _execute_task(self, task: Task, handler: TaskHandler, context: TaskContext) -> None:
        """在后台线程中执行任务"""
        try:
            context.info("Task execution started", task_type=task.type)
            
            # 执行处理器
            result = handler.execute(context, task.payload)
            
            # 检查是否被取消
            context.check_cancelled()
            
            # 更新任务为成功
            task.status = TaskStatus.SUCCEEDED
            task.result = result
            task.progress = 100
            task.completed_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()
            task.stage = "任务完成"
            
            context.info("Task completed successfully")
            
        except TaskCancelledError:
            task.status = TaskStatus.CANCELLED
            task.error = "Task was cancelled by user"
            task.cancelled_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()
            context.info("Task was cancelled")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()
            context.error("Task failed", error=str(e), error_type=type(e).__name__)
            logger.exception(f"Task {task.id} failed")
        
        finally:
            # 更新日志
            task.logs = context._logs.copy()
            self.repository.save(task)
            
            with self._lock:
                self._running_tasks.pop(task.id, None)
    
    def _on_task_complete(self, task_id: str, future) -> None:
        """任务完成回调"""
        try:
            future.result()  # 检查是否有未捕获的异常
        except Exception as e:
            logger.error(f"Unexpected error in task {task_id}: {e}")
    
    def cancel(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            context = self._running_tasks.get(task_id)
            if context:
                context.cancel()
                return True
            return False
    
    def get_context(self, task_id: str) -> Optional[TaskContext]:
        """获取任务执行上下文"""
        with self._lock:
            return self._running_tasks.get(task_id)
    
    def shutdown(self, wait: bool = True) -> None:
        """关闭执行器"""
        # 取消所有运行中的任务
        with self._lock:
            for context in self._running_tasks.values():
                context.cancel()
        
        self._executor.shutdown(wait=wait)
        logger.info("Task executor shut down")
