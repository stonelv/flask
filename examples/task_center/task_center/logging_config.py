import logging
import json
from datetime import datetime, UTC

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.now(UTC).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'task_id': getattr(record, 'task_id', None),
            'stage': getattr(record, 'stage', None),
            'progress': getattr(record, 'progress', None),
        }
        
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging(app):
    if app.config.get('JSON_LOGGING', False):
        formatter = JsonFormatter()
        for handler in app.logger.handlers:
            handler.setFormatter(formatter)
    
    app.logger.setLevel(app.config.get('LOG_LEVEL', 'INFO'))
