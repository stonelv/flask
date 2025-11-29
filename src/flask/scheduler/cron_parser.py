import re
from datetime import datetime, timedelta
from typing import List, Optional, Tuple


class CronParser:
    """Cron expression parser"""
    
    @staticmethod
    def parse(cron_expr: str) -> List[str]:
        """Parse a cron expression into its components"""
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            raise ValueError("Cron expression must have 5 parts: minute hour day month weekday")
        return parts

    @staticmethod
    def get_next_run(cron_expr: str, now: Optional[datetime] = None) -> datetime:
        """Calculate the next run time for a cron expression"""
        if now is None:
            now = datetime.utcnow()
        
        parts = CronParser.parse(cron_expr)
        minute, hour, day, month, weekday = parts
        
        # Start checking from next minute
        next_run = now + timedelta(minutes=1)
        
        # Infinite loop until we find a matching time
        while True:
            # Check all parts of the cron expression
            if not CronParser._matches_part(next_run.minute, minute):
                next_run += timedelta(minutes=1)
                continue
            
            if not CronParser._matches_part(next_run.hour, hour):
                next_run = next_run.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                continue
            
            if not CronParser._matches_part(next_run.day, day):
                next_run = next_run.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                continue
            
            if not CronParser._matches_part(next_run.month, month):
                next_run = next_run.replace(day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32)
                next_run = next_run.replace(day=1)
                continue
            
            if not CronParser._matches_part(next_run.weekday(), weekday):
                next_run += timedelta(days=1)
                continue
            
            return next_run

    @staticmethod
    def _matches_part(value: int, part: str) -> bool:
        """Check if a value matches a cron part"""
        if part == '*':
            return True
        
        # Check for range
        if '-' in part:
            start, end = part.split('-')
            return int(start) <= value <= int(end)
        
        # Check for step
        if '/' in part:
            base, step = part.split('/')
            if base == '*':
                base = '0' if part == '*/' else base
            return value % int(step) == int(base)
        
        # Check for list
        if ',' in part:
            return str(value) in part.split(',')
        
        # Exact match
        return str(value) == part
