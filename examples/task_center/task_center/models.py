import enum
import json
from datetime import datetime, UTC
from task_center.extensions import db

class TaskStatus(enum.Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    type = db.Column(db.String(64), nullable=False)
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    progress = db.Column(db.Integer, default=0)
    stage = db.Column(db.String(64))
    payload = db.Column(db.Text)
    result = db.Column(db.Text)
    error = db.Column(db.Text)
    idempotency_key = db.Column(db.String(64), unique=True)
    timeout = db.Column(db.Integer, default=300)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    
    __table_args__ = (
        db.Index('idx_idempotency_key', 'idempotency_key'),
        db.Index('idx_status', 'status'),
        db.Index('idx_type', 'type'),
        db.Index('idx_created_at', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'status': self.status.value if self.status else None,
            'progress': self.progress,
            'stage': self.stage,
            'payload': self._parse_json(self.payload),
            'result': self._parse_json(self.result),
            'error': self._parse_json(self.error),
            'idempotency_key': self.idempotency_key,
            'timeout': self.timeout,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
        }
    
    def set_payload(self, data):
        self.payload = json.dumps(data) if data is not None else None
    
    def set_result(self, data):
        self.result = json.dumps(data) if data is not None else None
    
    def set_error(self, data):
        self.error = json.dumps(data) if data is not None else None
    
    def _parse_json(self, text):
        if not text:
            return None
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return text
