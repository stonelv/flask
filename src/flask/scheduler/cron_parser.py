from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple


class CronParser:
    """Parser for cron expressions (supports minute, hour, day_of_month fields)."""
    
    @staticmethod
    def parse(cron_expr: str) -> Tuple[List[int], List[int], List[int]]:
        """Parse a cron expression into minute, hour, day_of_month lists."""
        parts = cron_expr.strip().split()
        if len(parts) != 3:
            raise ValueError(f"Invalid cron expression: {cron_expr}. Expected 3 fields: minute hour day_of_month")
        
        minute_part, hour_part, day_part = parts
        
        return (
            CronParser._parse_field(minute_part, 0, 59),
            CronParser._parse_field(hour_part, 0, 23),
            CronParser._parse_field(day_part, 1, 31)
        )
    
    @staticmethod
    def _parse_field(field: str, min_val: int, max_val: int) -> List[int]:
        """Parse a single cron field into a list of values."""
        values = []
        
        if field == '*':
            return list(range(min_val, max_val + 1))
        
        for part in field.split(','):
            if '-' in part:
                # Range
                start, end = part.split('-')
                start = int(start)
                end = int(end)
                if start < min_val or end > max_val:
                    raise ValueError(f"Range {part} out of bounds [{min_val}-{max_val}]")
                values.extend(range(start, end + 1))
            elif '/' in part:
                # Step
                base, step = part.split('/')
                step = int(step)
                if base == '*':
                    base_values = list(range(min_val, max_val + 1))
                else:
                    base_values = [int(base)]
                values.extend(v for v in base_values if v % step == 0)
            else:
                # Single value
                val = int(part)
                if val < min_val or val > max_val:
                    raise ValueError(f"Value {val} out of bounds [{min_val}-{max_val}]")
                values.append(val)
        
        return sorted(list(set(values)))

    @staticmethod
    def get_next_run(cron_expr: str, now: Optional[datetime] = None) -> datetime:
        """Calculate the next run time for a cron expression."""
        if now is None:
            now = datetime.now(timezone.utc)
        
        minute, hour, day = CronParser.parse(cron_expr)
        
        # Make sure now is timezone-aware
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        
        # Start checking from the next minute
        next_run = now + timedelta(minutes=1)
        
        while True:
            if (next_run.minute in minute and 
                next_run.hour in hour and 
                next_run.day in day):
                return next_run.replace(second=0, microsecond=0)
            
            # Move to next minute
            next_run += timedelta(minutes=1)
            
            # Prevent infinite loop (check up to 1 year ahead)
            if next_run > now + timedelta(days=365):
                raise ValueError(f"No valid next run time found for cron expression {cron_expr}")


