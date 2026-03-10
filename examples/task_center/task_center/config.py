import os
import logging
from logging.handlers import RotatingFileHandler

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///tasks.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 任务执行器配置
    TASK_EXECUTOR_MAX_WORKERS = int(os.environ.get('TASK_EXECUTOR_MAX_WORKERS', 4))
    TASK_DEFAULT_TIMEOUT = int(os.environ.get('TASK_DEFAULT_TIMEOUT', 300))
    
    # 日志配置
    LOG_LEVEL = logging.INFO
    LOG_FILE = 'task_center.log'
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

def setup_logging(app):
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            f'logs/{Config.LOG_FILE}',
            maxBytes=Config.LOG_MAX_SIZE,
            backupCount=Config.LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}'
        ))
        file_handler.setLevel(Config.LOG_LEVEL)
        app.logger.addHandler(file_handler)
    
    app.logger.setLevel(Config.LOG_LEVEL)
