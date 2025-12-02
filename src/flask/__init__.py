from . import json as json
from .app import Flask as Flask
from .blueprints import Blueprint as Blueprint
from .config import Config as Config
from .ctx import after_this_request as after_this_request
from .ctx import copy_current_request_context as copy_current_request_context
from .ctx import has_app_context as has_app_context
from .ctx import has_request_context as has_request_context
from .globals import current_app as current_app
from .globals import g as g
from .globals import request as request
from .globals import session as session
from .helpers import abort as abort
from .helpers import flash as flash
from .helpers import get_flashed_messages as get_flashed_messages
from .helpers import get_template_attribute as get_template_attribute
from .helpers import make_response as make_response
from .helpers import redirect as redirect
from .helpers import send_file as send_file
from .helpers import send_from_directory as send_from_directory
from .helpers import stream_with_context as stream_with_context
from .helpers import url_for as url_for
from .json import jsonify as jsonify
from .signals import appcontext_popped as appcontext_popped
from .signals import appcontext_pushed as appcontext_pushed
from .signals import appcontext_tearing_down as appcontext_tearing_down
from .signals import before_render_template as before_render_template
from .signals import got_request_exception as got_request_exception
from .signals import message_flashed as message_flashed
from .signals import request_finished as request_finished
from .signals import request_started as request_started
from .signals import request_tearing_down as request_tearing_down
from .signals import template_rendered as template_rendered
from .templating import render_template as render_template
from .templating import render_template_string as render_template_string
from .templating import stream_template as stream_template
from .templating import stream_template_string as stream_template_string
from .wrappers import Request as Request
from .wrappers import Response as Response

# 导入文章管理系统模块
from .auth import auth_bp
from .articles import articles_bp
from .models import db, Article


def init_article_management(app):
    """初始化文章管理系统
    
    Args:
        app: Flask 应用实例
    """
    # 配置数据库
    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///articles.db'
    
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
    
    # 初始化数据库
    db.init_app(app)
    
    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(articles_bp)
    
    # 创建数据库表（如果不存在）
    with app.app_context():
        db.create_all()


# 导出文章管理系统模块
__all__ = [
    'Flask', 'Blueprint', 'Config',
    'after_this_request', 'copy_current_request_context',
    'has_app_context', 'has_request_context',
    'current_app', 'g', 'request', 'session',
    'abort', 'flash', 'get_flashed_messages', 'get_template_attribute',
    'make_response', 'redirect', 'send_file', 'send_from_directory',
    'stream_with_context', 'url_for',
    'jsonify',
    'appcontext_popped', 'appcontext_pushed', 'appcontext_tearing_down',
    'before_render_template', 'got_request_exception', 'message_flashed',
    'request_finished', 'request_started', 'request_tearing_down',
    'template_rendered',
    'render_template', 'render_template_string', 'stream_template',
    'stream_template_string',
    'Request', 'Response',
    'auth_bp', 'articles_bp', 'db', 'Article', 'init_article_management'
]
