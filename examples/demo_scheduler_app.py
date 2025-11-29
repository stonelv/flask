from flask import Flask
from flask.scheduler import Scheduler
import tasks  # Import tasks from tasks.py

# Create Flask app
app = Flask(__name__)

# Configure scheduler
app.config['SCHEDULER_ENABLED'] = True
app.config['SCHEDULER_AUTOSTART'] = True
app.config['SCHEDULER_TICK_INTERVAL'] = 1

# Initialize scheduler
scheduler = Scheduler(app)

# Discover tasks
if __name__ == '__main__':
    app.run(debug=True)
