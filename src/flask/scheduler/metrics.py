import os
import time
from datetime import datetime, timezone
from typing import Optional

class Metrics:
    """Metrics collection for the scheduler."""
    
    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.rate_limited_count = 0
    
    def get_rss(self) -> Optional[int]:
        """Get RSS memory usage in bytes."""
        try:
            if os.name == 'nt':
                # Windows implementation
                import psutil
                process = psutil.Process(os.getpid())
                return process.memory_info().rss
            else:
                # Unix implementation
                import resource
                return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024  # Convert to bytes
        except ImportError:
            return None
    
    def get_uptime(self) -> float:
        """Get uptime in seconds."""
        now = datetime.now(timezone.utc)
        return (now - self.start_time).total_seconds()
