from flask import Flask
from flask.scheduler import Scheduler, interval, delay, cron
import time

# Initialize Flask app
app = Flask(__name__)

# Configure scheduler
app.config['SCHEDULER_ENABLED'] = True
app.config['SCHEDULER_AUTOSTART'] = True
app.config['SCHEDULER_TICK_INTERVAL'] = 1

# Initialize scheduler
scheduler = Scheduler(app)


# Example 1: Task running every 10 seconds
@interval(seconds=10)
def every_10_seconds():
    print(f"Every 10 seconds task ran at: {time.ctime()}")


# Example 2: Task running once after 5 seconds delay
@delay(seconds=5)
def after_5_seconds():
    print(f"After 5 seconds task ran at: {time.ctime()}")


# Example 3: Task running every 2 minutes using cron
@cron(expr="*/2 * * * *")
def every_2_minutes():
    print(f"Every 2 minutes task ran at: {time.ctime()}")


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
