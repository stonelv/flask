import enum
import uuid
from datetime import datetime, UTC
from typing import Optional, Dict, Any
from sqlalchemy import Enum, Text, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from . import db


def utc_now() -> datetime:
    return datetime.now(UTC)


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Task(db.Model):
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stage: Mapped[Optional[str]] = mapped_column(String(100))
    payload: Mapped[Optional[str]] = mapped_column(Text)
    result: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        db.UniqueConstraint("idempotency_key", name="uq_task_idempotency_key"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
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
        }
