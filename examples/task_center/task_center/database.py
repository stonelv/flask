import enum
import threading
from datetime import datetime, UTC
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, Enum, JSON
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


engine = None
# Use thread-local scoped sessions
db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False),
    scopefunc=threading.get_ident
)
Base = declarative_base()


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True)
    type = Column(String(100), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    progress = Column(Integer, default=0)
    stage = Column(String(100), default="init")
    payload = Column(JSON)
    result = Column(JSON)
    error = Column(Text)
    idempotency_key = Column(String(100), unique=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    cancelled_at = Column(DateTime)

    def to_dict(self):
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
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
        }


def init_db(app):
    """Initialize database with app configuration"""
    global engine
    database_url = app.config.get("DATABASE", "sqlite:////tmp/task_center.db")
    
    # Add SQLite specific settings for multi-threading
    connect_args = {}
    if database_url.startswith('sqlite:'):
        connect_args['check_same_thread'] = False
    
    # Configure pool settings for multi-threading
    engine = create_engine(
        database_url, 
        connect_args=connect_args,
        pool_size=20,
        max_overflow=40,
        pool_timeout=60,
        pool_recycle=3600,
    )
    db_session.configure(bind=engine)
    Base.metadata.create_all(bind=engine)


def get_engine():
    """Get the current engine - for testing"""
    return engine


def create_thread_session():
    """Create a new session for background threads"""
    return sessionmaker(bind=engine)()
