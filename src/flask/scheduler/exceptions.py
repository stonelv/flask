class SchedulerError(Exception):
    """Base exception for scheduler errors."""
    pass


class TaskNotFoundError(SchedulerError):
    """Raised when a task is not found."""
    pass


class CronFormatError(SchedulerError):
    """Raised when a cron expression is invalid."""
    pass


class TaskExecutionError(SchedulerError):
    """Raised when a task execution fails."""
    pass
