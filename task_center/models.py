"""
Task Center - Database Models
"""
from __future__ import annotations

import enum
import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


class TaskStatus(str, enum.Enum):
    """任务状态枚举"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class Task:
    """任务数据模型"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "default"
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0  # 0-100
    stage: str = ""  # 当前阶段描述
    payload: dict = field(default_factory=dict)  # 任务输入参数
    result: Optional[dict] = None  # 任务执行结果
    error: Optional[str] = None  # 错误信息
    idempotency_key: Optional[str] = None  # 幂等键
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    logs: list = field(default_factory=list)  # 结构化日志
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典，用于JSON序列化"""
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status.value,
            "progress": self.progress,
            "stage": self.stage,
            "payload": self.payload,
            "result": self.result,
            "error": self.error,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "logs": self.logs,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """从字典创建Task实例"""
        task = cls()
        task.id = data.get("id", str(uuid.uuid4()))
        task.type = data.get("type", "default")
        task.status = TaskStatus(data.get("status", "PENDING"))
        task.progress = data.get("progress", 0)
        task.stage = data.get("stage", "")
        task.payload = data.get("payload", {})
        task.result = data.get("result")
        task.error = data.get("error")
        task.idempotency_key = data.get("idempotency_key")
        
        # 解析时间戳
        for field_name in ["created_at", "updated_at", "started_at", "completed_at", "cancelled_at"]:
            value = data.get(field_name)
            if value:
                setattr(task, field_name, datetime.fromisoformat(value))
        
        task.logs = data.get("logs", [])
        return task
    
    def is_terminal(self) -> bool:
        """检查任务是否处于终止状态"""
        return self.status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED)
    
    def can_cancel(self) -> bool:
        """检查任务是否可以被取消"""
        return self.status in (TaskStatus.PENDING, TaskStatus.RUNNING)


class TaskRepository:
    """任务存储仓库 - 使用SQLite持久化"""
    
    def __init__(self, db_path: str = "tasks.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """初始化数据库表"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER DEFAULT 0,
                    stage TEXT DEFAULT '',
                    payload TEXT DEFAULT '{}',
                    result TEXT,
                    error TEXT,
                    idempotency_key TEXT UNIQUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    cancelled_at TEXT,
                    logs TEXT DEFAULT '[]'
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON tasks(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_idempotency ON tasks(idempotency_key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON tasks(created_at)")
            conn.commit()
    
    def save(self, task: Task) -> Task:
        """保存或更新任务"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            # 检查任务是否已存在
            existing = conn.execute("SELECT id FROM tasks WHERE id = ?", (task.id,)).fetchone()
            
            if existing:
                # 更新现有任务
                conn.execute("""
                    UPDATE tasks SET
                        type = ?,
                        status = ?,
                        progress = ?,
                        stage = ?,
                        payload = ?,
                        result = ?,
                        error = ?,
                        updated_at = ?,
                        started_at = ?,
                        completed_at = ?,
                        cancelled_at = ?,
                        logs = ?
                    WHERE id = ?
                """, (
                    task.type,
                    task.status.value,
                    task.progress,
                    task.stage,
                    json.dumps(task.payload),
                    json.dumps(task.result) if task.result else None,
                    task.error,
                    task.updated_at.isoformat() if task.updated_at else datetime.now().isoformat(),
                    task.started_at.isoformat() if task.started_at else None,
                    task.completed_at.isoformat() if task.completed_at else None,
                    task.cancelled_at.isoformat() if task.cancelled_at else None,
                    json.dumps(task.logs),
                    task.id
                ))
            else:
                # 插入新任务
                conn.execute("""
                    INSERT INTO tasks 
                    (id, type, status, progress, stage, payload, result, error, 
                     idempotency_key, created_at, updated_at, started_at, completed_at, cancelled_at, logs)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task.id,
                    task.type,
                    task.status.value,
                    task.progress,
                    task.stage,
                    json.dumps(task.payload),
                    json.dumps(task.result) if task.result else None,
                    task.error,
                    task.idempotency_key,
                    task.created_at.isoformat() if task.created_at else datetime.now().isoformat(),
                    task.updated_at.isoformat() if task.updated_at else datetime.now().isoformat(),
                    task.started_at.isoformat() if task.started_at else None,
                    task.completed_at.isoformat() if task.completed_at else None,
                    task.cancelled_at.isoformat() if task.cancelled_at else None,
                    json.dumps(task.logs)
                ))
            conn.commit()
        return task
    
    def get_by_id(self, task_id: str) -> Optional[Task]:
        """根据ID获取任务"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_task(row)
            return None
    
    def get_by_idempotency_key(self, key: str) -> Optional[Task]:
        """根据幂等键获取任务"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tasks WHERE idempotency_key = ?", (key,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_task(row)
            return None
    
    def list_tasks(
        self, 
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[list[Task], int]:
        """分页查询任务列表"""
        import sqlite3
        
        conditions = []
        params = []
        
        if status:
            conditions.append("status = ?")
            params.append(status.value)
        
        if task_type:
            conditions.append("type = ?")
            params.append(task_type)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # 获取总数
            count_sql = f"SELECT COUNT(*) FROM tasks {where_clause}"
            cursor = conn.execute(count_sql, params)
            total = cursor.fetchone()[0]
            
            # 获取分页数据
            sql = f"SELECT * FROM tasks {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?"
            cursor = conn.execute(sql, params + [limit, offset])
            
            tasks = [self._row_to_task(row) for row in cursor.fetchall()]
            return tasks, total
    
    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """将数据库行转换为Task对象"""
        return Task(
            id=row["id"],
            type=row["type"],
            status=TaskStatus(row["status"]),
            progress=row["progress"],
            stage=row["stage"],
            payload=json.loads(row["payload"]) if row["payload"] else {},
            result=json.loads(row["result"]) if row["result"] else None,
            error=row["error"],
            idempotency_key=row["idempotency_key"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            cancelled_at=datetime.fromisoformat(row["cancelled_at"]) if row["cancelled_at"] else None,
            logs=json.loads(row["logs"]) if row["logs"] else [],
        )
    
    def delete(self, task_id: str) -> bool:
        """删除任务"""
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def cleanup_old_tasks(self, days: int = 7) -> int:
        """清理指定天数前的已完成任务"""
        import sqlite3
        from datetime import timedelta
        
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM tasks WHERE updated_at < ? AND status IN ('SUCCEEDED', 'FAILED', 'CANCELLED')",
                (cutoff,)
            )
            conn.commit()
            return cursor.rowcount
