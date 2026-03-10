# Background Task Center

A reusable asynchronous task management system for Flask applications.

## Features

- **Task Persistence**: Store tasks in database with status tracking
- **Idempotency Support**: Prevent duplicate task execution using idempotency keys
- **Async Execution**: Run tasks in background using ThreadPoolExecutor
- **Progress Tracking**: Monitor task progress with stage updates
- **Cancellation**: Support cooperative task cancellation
- **REST API**: Complete API for task management
- **Structured Logging**: JSON-formatted logging for better observability
- **Automated Tests**: Comprehensive test suite

## Installation

1. Install dependencies:
```bash
pip install flask flask-sqlalchemy python-json-logger pytest
```

2. Set up the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

## Quick Start

1. Create a Flask application:

```python
from task_center import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
```

2. Run the application:
```bash
python app.py
```

## API Endpoints

### Create Task
```http
POST /api/tasks
Content-Type: application/json

{
    "name": "Data Import",
    "type": "import",
    "payload": {"file": "data.csv"},
    "idempotency_key": "unique-key-123"
}
```

**Response:**
```json
{
    "task": {
        "id": "uuid",
        "name": "Data Import",
        "type": "import",
        "status": "pending",
        "progress": 0,
        "stage": null,
        "payload": {"file": "data.csv"},
        "result": null,
        "error": null,
        "idempotency_key": "unique-key-123",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
        "started_at": null,
        "completed_at": null
    },
    "message": "Task created successfully"
}
```

### Get Task
```http
GET /api/tasks/{task_id}
```

### List Tasks
```http
GET /api/tasks?page=1&per_page=10&status=pending&type=import
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 10)
- `status`: Filter by status (pending, running, succeeded, failed, cancelled)
- `type`: Filter by task type

### Cancel Task
```http
POST /api/tasks/{task_id}/cancel
```

## Task Status

- `pending`: Task is queued and waiting to start
- `running`: Task is currently executing
- `succeeded`: Task completed successfully
- `failed`: Task failed with an error
- `cancelled`: Task was cancelled by user

## Custom Tasks

To create custom tasks, add your task function to `executor.py`:

```python
def my_custom_task(task_id, cancellation_event, *args, **kwargs):
    # Your task logic here
    # Check cancellation_event.is_set() periodically
    # Update task progress and stage
    return result
```

Then submit tasks using the executor:

```python
from task_center.executor import executor

executor.submit_task(task_id, my_custom_task, arg1, arg2)
```

## Testing

Run the test suite:

```bash
pytest task_center/tests/ -v
```

## Configuration

Edit `task_center/config.py` to customize:

- `SECRET_KEY`: Flask secret key
- `SQLALCHEMY_DATABASE_URI`: Database connection string
- `MAX_WORKERS`: Maximum number of worker threads
- `TASK_TIMEOUT`: Task timeout in seconds

## Logging

The system uses structured JSON logging. Log entries include:
- Task ID
- Stage
- Progress
- Timestamp
- Log level

Example log entry:
```json
{
    "asctime": "2024-01-01T00:00:00",
    "levelname": "INFO",
    "name": "task_center.executor",
    "message": "Task progress update",
    "task_id": "uuid",
    "stage": "Processing data",
    "progress": 50
}
```

## License

MIT
