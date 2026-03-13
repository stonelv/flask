import logging
import sys
from flask import Flask, jsonify, render_template
from .api import init_app as init_api
from .database import init_db, get_engine
from .executor import executor


def setup_logging():
    """Setup structured JSON logging"""
    formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Set specific log levels
    logging.getLogger("task_center").setLevel(logging.DEBUG)


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
        return jsonify({"status": "healthy", "service": "task-center"})

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.exception("Internal server error")
        return jsonify({"error": "Internal server error"}), 500

    return app
