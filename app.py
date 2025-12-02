from flask import Flask
from models import db
from auth import auth_bp
from articles import articles_bp
import os

def create_app():
    app = Flask(__name__)
    
    # 配置
    app.config['SECRET_KEY'] = 'dev-secret-key-12345'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///articles.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600
    
    # 初始化数据库
    db.init_app(app)
    
    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(articles_bp)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)