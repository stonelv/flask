import logging
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from pythonjsonlogger import jsonlogger

def setup_logging(app):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    json_handler = logging.StreamHandler()
    json_formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s %(task_id)s %(stage)s %(progress)s'
    )
    json_handler.setFormatter(json_formatter)

    logger.addHandler(json_handler)

    class TaskFilter(logging.Filter):
        def filter(self, record):
            record.task_id = getattr(record, 'task_id', 'N/A')
            record.stage = getattr(record, 'stage', 'N/A')
            record.progress = getattr(record, 'progress', 'N/A')
            return True

    logger.addFilter(TaskFilter())

    app.logger = logger
