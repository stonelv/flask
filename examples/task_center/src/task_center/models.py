import enum
import json
import uuid
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type

from sqlalchemy import Boolean
from sqlalchemy import create_engine
from sqlalchemy import Index
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Session
from sqlalchemy.types import DateTime
from sqlalchemy.types import Integer
from sqlalchemy.types import String
from sqlalchemy.types import Text
from sqlalchemy.types import TypeDecorator


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JSONType(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value: Optional[str], dialect: Any) -> Any:
        if value is None:
            return None
        return json.loads(value)


class ListType(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value: Optional[str], dialect: Any) -> List[Any]:
        if value is None:
            return []
        result = json.loads(value)
        return result if isinstance(result, list) else []


class Base(DeclarativeBase):
    pass


class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    type: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    stage: Mapped[str] = mapped_column(String(200), default="")
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    logs: Mapped[List[str]] = mapped_column(ListType, default=list)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_tasks_idempotency_key", "idempotency_key", unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "payload": self.payload,
            "result": self.result,
            "error": self.error,
            "progress": self.progress,
            "stage": self.stage,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "logs": self.logs,
            "cancel_requested": self.cancel_requested,
        }

    def is_cancelled(self) -> bool:
        return self.cancel_requested or self.status == TaskStatus.CANCELLED


class Task:
    def __init__(self, model: TaskModel):
        self._model = model

    @property
    def id(self) -> str:
        return self._model.id

    @property
    def type(self) -> str:
        return self._model.type

    @property
    def status(self) -> TaskStatus:
        return TaskStatus(self._model.status)

    @status.setter
    def status(self, value: TaskStatus):
        self._model.status = value.value

    @property
    def payload(self) -> Dict[str, Any]:
        return self._model.payload

    @property
    def result(self) -> Optional[Dict[str, Any]]:
        return self._model.result

    @result.setter
    def result(self, value: Optional[Dict[str, Any]]):
        self._model.result = value

    @property
    def error(self) -> Optional[str]:
        return self._model.error

    @error.setter
    def error(self, value: Optional[str]):
        self._model.error = value

    @property
    def progress(self) -> int:
        return self._model.progress

    @progress.setter
    def progress(self, value: int):
        self._model.progress = value

    @property
    def stage(self) -> str:
        return self._model.stage

    @stage.setter
    def stage(self, value: str):
        self._model.stage = value

    @property
    def idempotency_key(self) -> Optional[str]:
        return self._model.idempotency_key

    @property
    def created_at(self) -> datetime:
        return self._model.created_at

    @property
    def updated_at(self) -> datetime:
        return self._model.updated_at

    @property
    def started_at(self) -> Optional[datetime]:
        return self._model.started_at

    @started_at.setter
    def started_at(self, value: Optional[datetime]):
        self._model.started_at = value

    @property
    def finished_at(self) -> Optional[datetime]:
        return self._model.finished_at

    @finished_at.setter
    def finished_at(self, value: Optional[datetime]):
        self._model.finished_at = value

    @property
    def logs(self) -> List[str]:
        return self._model.logs

    @property
    def cancel_requested(self) -> bool:
        return self._model.cancel_requested

    @cancel_requested.setter
    def cancel_requested(self, value: bool):
        self._model.cancel_requested = value

    def to_dict(self) -> Dict[str, Any]:
        return self._model.to_dict()

    def is_cancelled(self) -> bool:
        return self._model.is_cancelled()


class TaskStorage:
    def __init__(self, db_url: str = "sqlite:///tasks.db"):
        self._db_url = db_url
        self._engine = create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})

    def init_db(self) -> None:
        Base.metadata.create_all(self._engine)

    def drop_db(self) -> None:
        Base.metadata.drop_all(self._engine)

    def _session(self) -> Session:
        return Session(self._engine)

    def create(
        self,
        task_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Optional[Task]:
        session = self._session()
        try:
            if idempotency_key:
                existing = session.query(TaskModel).filter(
                    TaskModel.idempotency_key == idempotency_key
                ).first()
                if existing:
                    return Task(existing)

            task_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            model = TaskModel(
                id=task_id,
                type=task_type,
                status=TaskStatus.PENDING.value,
                payload=payload,
                idempotency_key=idempotency_key,
                created_at=now,
                updated_at=now,
            )
            session.add(model)
            session.commit()
            session.refresh(model)
            return Task(model)
        except IntegrityError:
            session.rollback()
            if idempotency_key:
                existing = session.query(TaskModel).filter(
                    TaskModel.idempotency_key == idempotency_key
                ).first()
                if existing:
                    return Task(existing)
            return None
        finally:
            session.close()

    def claim_for_execution(self, task_id: str) -> Optional[Task]:
        session = self._session()
        try:
            stmt = (
                update(TaskModel)
                .where(TaskModel.id == task_id)
                .where(TaskModel.status == TaskStatus.PENDING.value)
                .where(TaskModel.cancel_requested == False)
                .values(
                    status=TaskStatus.RUNNING.value,
                    started_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                .execution_options(synchronize_session="fetch")
            )
            result = session.execute(stmt)
            session.commit()
            if result.rowcount == 0:
                return None
            model = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            return Task(model) if model else None
        finally:
            session.close()

    def get(self, task_id: str) -> Optional[Task]:
        session = self._session()
        try:
            model = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            return Task(model) if model else None
        finally:
            session.close()

    def list(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[Task], int]:
        session = self._session()
        try:
            query = session.query(TaskModel)
            if status:
                query = query.filter(TaskModel.status == status.value)
            if task_type:
                query = query.filter(TaskModel.type == task_type)

            query = query.order_by(TaskModel.created_at.desc())
            total = query.count()
            start = (page - 1) * per_page
            models = query.offset(start).limit(per_page).all()
            tasks = [Task(m) for m in models]
            return tasks, total
        finally:
            session.close()

    def update(self, task_id: str, **kwargs) -> Optional[Task]:
        session = self._session()
        try:
            model = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            if not model:
                return None

            for key, value in kwargs.items():
                if key == "status" and isinstance(value, TaskStatus):
                    model.status = value.value
                elif hasattr(model, key):
                    setattr(model, key, value)

            model.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(model)
            return Task(model)
        finally:
            session.close()

    def add_log(self, task_id: str, message: str) -> None:
        session = self._session()
        try:
            model = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            if model:
                timestamp = datetime.now(timezone.utc).isoformat()
                new_logs = list(model.logs) if model.logs else []
                new_logs.append(f"[{timestamp}] {message}")
                model.logs = new_logs
                model.updated_at = datetime.now(timezone.utc)
                session.commit()
        finally:
            session.close()

    def request_cancel(self, task_id: str) -> Optional[Task]:
        session = self._session()
        try:
            model = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            if not model:
                return None

            if model.status in (
                TaskStatus.SUCCEEDED.value,
                TaskStatus.FAILED.value,
                TaskStatus.CANCELLED.value,
            ):
                return Task(model)

            if model.status == TaskStatus.PENDING.value:
                model.status = TaskStatus.CANCELLED.value
                model.cancel_requested = True
                model.finished_at = datetime.now(timezone.utc)
                model.updated_at = datetime.now(timezone.utc)
                session.commit()
                session.refresh(model)
                return Task(model)

            model.cancel_requested = True
            model.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(model)
            return Task(model)
        finally:
            session.close()
