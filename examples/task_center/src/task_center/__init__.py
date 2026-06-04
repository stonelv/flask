import json
import logging
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from typing import Optional

import click
import structlog
from flask import current_app
from flask import Flask
from flask import g


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class Task:
    id: str
    type: str
    status: TaskStatus
    progress: int
    stage: str
    payload: Optional[dict[str, Any]]
    result: Optional[dict[str, Any]]
    error: Optional[str]
    idempotency_key: Optional[str]
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
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
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class TaskLog:
    id: int
    task_id: str
    level: str
    message: str
    extra: Optional[dict[str, Any]]
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "level": self.level,
            "message": self.message,
            "extra": self.extra,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class CreateTaskResult:
    task: Task
    is_new: bool


def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            progress INTEGER NOT NULL DEFAULT 0,
            stage TEXT NOT NULL DEFAULT '',
            payload TEXT,
            result TEXT,
            error TEXT,
            idempotency_key TEXT UNIQUE,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        );
        CREATE TABLE IF NOT EXISTS task_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            extra TEXT,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type);
        CREATE INDEX IF NOT EXISTS idx_tasks_idempotency_key ON tasks(idempotency_key);
        CREATE INDEX IF NOT EXISTS idx_task_logs_task_id ON task_logs(task_id);
        CREATE INDEX IF NOT EXISTS idx_task_logs_created_at ON task_logs(created_at);
    """)
    db.commit()


@click.command("init-db")
def init_db_command():
    init_db()
    click.echo("Initialized the database.")


sqlite3.register_converter("timestamp", lambda v: datetime.fromisoformat(v.decode()))


class TaskStore:
    def __init__(self, app: Flask):
        self.app = app
        self._lock = threading.Lock()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(
            self.app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_task(
        self,
        task_type: str,
        payload: Optional[dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> CreateTaskResult:
        if idempotency_key:
            existing = self.get_by_idempotency_key(idempotency_key)
            if existing:
                return CreateTaskResult(task=existing, is_new=False)

        now = datetime.utcnow()
        task = Task(
            id=str(uuid.uuid4()),
            type=task_type,
            status=TaskStatus.PENDING,
            progress=0,
            stage="initialized",
            payload=payload,
            result=None,
            error=None,
            idempotency_key=idempotency_key,
            created_at=now,
            updated_at=now,
        )

        with self._lock, self.get_connection() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO tasks (id, type, status, progress, stage, payload, result, error, idempotency_key, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.id,
                        task.type,
                        task.status.value,
                        task.progress,
                        task.stage,
                        json.dumps(task.payload) if task.payload else None,
                        json.dumps(task.result) if task.result else None,
                        task.error,
                        task.idempotency_key,
                        task.created_at,
                        task.updated_at,
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                if idempotency_key:
                    existing = self.get_by_idempotency_key(idempotency_key)
                    if existing:
                        return CreateTaskResult(task=existing, is_new=False)
                raise

        return CreateTaskResult(task=task, is_new=True)

    def claim_task(self, task_id: str) -> bool:
        with self._lock, self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ? AND status = ?",
                (TaskStatus.RUNNING.value, datetime.utcnow(), task_id, TaskStatus.PENDING.value),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_by_id(self, task_id: str) -> Optional[Task]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            return self._row_to_task(row) if row else None

    def get_by_idempotency_key(self, key: str) -> Optional[Task]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE idempotency_key = ?", (key,)
            ).fetchone()
            return self._row_to_task(row) if row else None

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Task], int]:
        offset = (page - 1) * per_page
        conditions: list[str] = []
        params: list[Any] = []

        if status:
            conditions.append("status = ?")
            params.append(status.value)
        if task_type:
            conditions.append("type = ?")
            params.append(task_type)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with self.get_connection() as conn:
            count_row = conn.execute(
                f"SELECT COUNT(*) as count FROM tasks WHERE {where_clause}", params
            ).fetchone()
            total = count_row["count"] if count_row else 0

            rows = conn.execute(
                f"SELECT * FROM tasks WHERE {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                params + [per_page, offset],
            ).fetchall()

            return [self._row_to_task(row) for row in rows], total

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        stage: Optional[str] = None,
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[Task]:
        with self._lock, self.get_connection() as conn:
            task = self.get_by_id(task_id)
            if not task:
                return None

            if task.status == TaskStatus.CANCELLED:
                return task

            updates: list[str] = ["updated_at = ?"]
            values: list[Any] = [datetime.utcnow()]

            if status is not None:
                updates.append("status = ?")
                values.append(status.value)
            if progress is not None:
                updates.append("progress = ?")
                values.append(max(0, min(100, progress)))
            if stage is not None:
                updates.append("stage = ?")
                values.append(stage)
            if result is not None:
                updates.append("result = ?")
                values.append(json.dumps(result))
            if error is not None:
                updates.append("error = ?")
                values.append(error)

            values.append(task_id)
            conn.execute(
                f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", values
            )
            conn.commit()

            return self.get_by_id(task_id)

    def cancel_task(self, task_id: str) -> Optional[Task]:
        with self._lock, self.get_connection() as conn:
            task = self.get_by_id(task_id)
            if not task:
                return None

            if task.status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return task

            conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                (TaskStatus.CANCELLED.value, datetime.utcnow(), task_id),
            )
            conn.commit()

            return self.get_by_id(task_id)

    def add_log(
        self,
        task_id: str,
        level: str,
        message: str,
        extra: Optional[dict[str, Any]] = None,
    ) -> TaskLog:
        now = datetime.utcnow()
        with self._lock, self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO task_logs (task_id, level, message, extra, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (task_id, level, message, json.dumps(extra) if extra else None, now),
            )
            conn.commit()
            return TaskLog(
                id=cursor.lastrowid,
                task_id=task_id,
                level=level,
                message=message,
                extra=extra,
                created_at=now,
            )

    def get_logs(
        self,
        task_id: str,
        level: Optional[str] = None,
        page: int = 1,
        per_page: int = 100,
    ) -> tuple[list[TaskLog], int]:
        offset = (page - 1) * per_page
        conditions: list[str] = ["task_id = ?"]
        params: list[Any] = [task_id]

        if level:
            conditions.append("level = ?")
            params.append(level.upper())

        where_clause = " AND ".join(conditions)

        with self.get_connection() as conn:
            count_row = conn.execute(
                f"SELECT COUNT(*) as count FROM task_logs WHERE {where_clause}", params
            ).fetchone()
            total = count_row["count"] if count_row else 0

            rows = conn.execute(
                f"SELECT * FROM task_logs WHERE {where_clause} ORDER BY created_at ASC LIMIT ? OFFSET ?",
                params + [per_page, offset],
            ).fetchall()

            return [self._row_to_task_log(row) for row in rows], total

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            type=row["type"],
            status=TaskStatus(row["status"]),
            progress=row["progress"],
            stage=row["stage"],
            payload=json.loads(row["payload"]) if row["payload"] else None,
            result=json.loads(row["result"]) if row["result"] else None,
            error=row["error"],
            idempotency_key=row["idempotency_key"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _row_to_task_log(self, row: sqlite3.Row) -> TaskLog:
        return TaskLog(
            id=row["id"],
            task_id=row["task_id"],
            level=row["level"],
            message=row["message"],
            extra=json.loads(row["extra"]) if row["extra"] else None,
            created_at=row["created_at"],
        )


def create_app() -> Flask:
    configure_logging()

    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE="/tmp/task_center.db",
    )
    app.config.from_prefixed_env()

    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

    from .executor import TaskExecutor
    from .views import bp

    app.register_blueprint(bp)

    task_store = TaskStore(app)
    app.extensions["task_store"] = task_store
    app.extensions["task_executor"] = TaskExecutor(app, task_store)

    return app


def get_task_store() -> TaskStore:
    return current_app.extensions["task_store"]


def get_task_executor() -> "TaskExecutor":
    return current_app.extensions["task_executor"]
