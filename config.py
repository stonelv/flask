import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///seckill.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 允许多线程访问 SQLite
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False}
    }


class TestingConfig(Config):
    TESTING = True
    # 使用文件数据库而不是内存数据库，以支持多线程测试
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_seckill.db'
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False}
    }
