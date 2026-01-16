from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(test_config=None):
    app = Flask(__name__)
    
    if test_config is None:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///seckill.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'connect_args': {
                'check_same_thread': False,
                'isolation_level': 'EXCLUSIVE'
            }
        }
    else:
        app.config.update(test_config)
        if 'SQLALCHEMY_ENGINE_OPTIONS' not in app.config:
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'connect_args': {
                    'check_same_thread': False,
                    'isolation_level': 'EXCLUSIVE'
                }
            }
    
    db.init_app(app)
    
    from . import models, views
    
    with app.app_context():
        db.create_all()
    
    app.register_blueprint(views.bp)
    
    return app
