from flask import Flask
from flask_sqlalchemy import SQLAlchemy
try:
    from pythonjsonlogger.json import JsonFormatter
except ImportError:
    from pythonjsonlogger.jsonlogger import JsonFormatter as JsonFormatter
import logging
import os

db = SQLAlchemy()


class TaskJsonFormatter(JsonFormatter):
    def add_fields(self, log_data, record, message_dict):
        super().add_fields(log_data, record, message_dict)
        log_data.setdefault("task_id", None)
        log_data.setdefault("stage", None)
        log_data.setdefault("progress", None)


def setup_logging(app: Flask) -> None:
    handler = logging.StreamHandler()
    formatter = TaskJsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s %(task_id)s %(stage)s %(progress)s"
    )
    handler.setFormatter(formatter)
    
    if not app.debug:
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
    
    task_logger = logging.getLogger("task_center")
    task_logger.addHandler(handler)
    task_logger.setLevel(logging.INFO)
    task_logger.propagate = False


def create_app(test_config=None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    
    app.config.from_mapping(
        SECRET_KEY="dev",
        SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(app.instance_path, "tasks.sqlite"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    
    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)
    
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass
    
    setup_logging(app)
    db.init_app(app)
    
    from . import models
    from . import executor
    
    with app.app_context():
        db.create_all()
    
    executor.init_app(app)
    
    from . import api
    app.register_blueprint(api.bp)
    
    return app
