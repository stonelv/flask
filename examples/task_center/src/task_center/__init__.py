import atexit
import json
import logging
import sys
from typing import Any
from typing import Dict

from flask import Flask
from flask import g

from .executor import TaskExecutor
from .models import TaskStorage
from .tasks import register_handlers


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "task_id"):
            log_record["task_id"] = record.task_id
        if hasattr(record, "progress"):
            log_record["progress"] = record.progress
        if hasattr(record, "stage"):
            log_record["stage"] = record.stage
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def configure_logging(app: Flask):
    level = logging.DEBUG if app.debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter(datefmt="%Y-%m-%dT%H:%M:%SZ")
    handler.setFormatter(formatter)
    handler.setLevel(level)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    task_logger = logging.getLogger("task_center")
    task_logger.setLevel(level)
    task_logger.addHandler(handler)


def create_app(test_config: Dict[str, Any] = None) -> Flask:
    app = Flask(__name__)

    config = {
        "TASK_WORKERS": 4,
        "USE_RELOADER": False,
    }
    if test_config:
        config.update(test_config)

    app.config.from_mapping(config)
    app.config.from_prefixed_env()

    configure_logging(app)

    storage = TaskStorage()
    executor = TaskExecutor(storage, max_workers=app.config["TASK_WORKERS"])
    register_handlers(executor)

    executor.start()

    @app.before_request
    def before_request():
        g.task_storage = storage
        g.task_executor = executor

    @atexit.register
    def shutdown():
        executor.stop()

    app.extensions["task_storage"] = storage
    app.extensions["task_executor"] = executor

    from . import routes

    app.register_blueprint(routes.bp)

    @app.route("/")
    def index():
        return {
            "name": "Task Center API",
            "endpoints": {
                "create": "POST /api/tasks",
                "get": "GET /api/tasks/<id>",
                "list": "GET /api/tasks",
                "cancel": "POST /api/tasks/<id>/cancel",
            },
            "task_types": list(executor._handlers.keys()),
        }

    return app
