from flask import Flask
from task_center.config import Config
from task_center.executor import TaskExecutor
from task_center.extensions import db

executor = TaskExecutor()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    executor.init_app(app)
    
    from task_center.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    with app.app_context():
        db.create_all()
    
    return app
