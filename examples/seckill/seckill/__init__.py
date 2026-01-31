from flask import Flask
from .extensions import db
from .routes import bp
from .config import config


def create_app(config_name=None):
    if config_name is None:
        config_name = 'default'
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    db.init_app(app)
    
    with app.app_context():
        from . import models
        db.create_all()
    
    app.register_blueprint(bp)
    
    return app


__all__ = ['create_app', 'db', 'models']
