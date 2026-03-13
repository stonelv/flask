import os
import logging

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///tasks.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQLite specific configuration for multi-threading support
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False},
        'pool_pre_ping': True,
        'pool_recycle': 3600,
    }
    
    # 任务执行器配置
    TASK_EXECUTOR_MAX_WORKERS = int(os.environ.get('TASK_EXECUTOR_MAX_WORKERS', 4))
    TASK_DEFAULT_TIMEOUT = int(os.environ.get('TASK_DEFAULT_TIMEOUT', 300))
    
    # 日志配置
    LOG_LEVEL = logging.INFO
    JSON_LOGGING = os.environ.get('JSON_LOGGING', 'true').lower() == 'true'
