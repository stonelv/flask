from flask.scheduler import interval_seconds, delay_seconds, cron

# Global counter for interval task
counter = 0

@interval_seconds(seconds=10)
def interval_task():
    """Task that runs every 10 seconds."""
    global counter
    counter += 1
    print(f"Interval task ran. Counter: {counter}")

@delay_seconds(seconds=5)
def delay_task():
    """Task that runs once after 5 seconds."""
    print("Delay task ran.")

@cron(cron_expr="*/2 * *")  # Every 2 minutes
def cron_task():
    """Task that runs on cron schedule."""
    from datetime import datetime
    print(f"Cron task ran. Current time: {datetime.now()}")
