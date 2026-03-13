import logging
import sys
from flask import Flask, jsonify, render_template
from .api import init_app as init_api
from .database import init_db, get_engine
from .executor import executor


class TaskJSONFormatter(logging.Formatter):
    """JSON formatter that includes task-related extra fields"""
    def format(self, record):
        import json
        log_record = {
            "timestamp": self.formatTime(record, "%Y-%m-%d %H:%M:%S,%f")[:-3],
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Add extra fields if present
        if hasattr(record, 'task_id'):
            log_record['task_id'] = record.task_id
        if hasattr(record, 'stage'):
            log_record['stage'] = record.stage
        if hasattr(record, 'progress'):
            log_record['progress'] = record.progress
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_record, ensure_ascii=False)


def setup_logging():
    """Setup structured JSON logging"""
    formatter = TaskJSONFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    # Remove default handlers to avoid duplicate logs
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Set specific log levels
    logging.getLogger("task_center").setLevel(logging.DEBUG)
    logging.getLogger("werkzeug").setLevel(logging.INFO)


def create_app(test_config=None) -> Flask:
    app = Flask(__name__)

    setup_logging()

    app.config.from_mapping(
        SECRET_KEY="dev-key-change-in-production",
        DATABASE="sqlite:////tmp/task_center.db",
    )

    if test_config is None:
        app.config.from_prefixed_env()
    else:
        app.config.from_mapping(test_config)

    # Initialize database
    init_db(app)

    # Set database engine for executor
    executor.set_engine(get_engine())

    # Initialize API
    init_api(app)

    # Home page
    @app.route("/")
    def index():
        return render_template("index.html")

    # Simple health check
    @app.route("/health")
    def health_check():
        return jsonify({
            "error": None, 
            "data": {"status": "healthy", "service": "task-center"}, 
            "message": None
        })

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found", "data": None, "message": None}), 404

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.exception("Internal server error")
        return jsonify({"error": "Internal server error", "data": None, "message": None}), 500

    return app
