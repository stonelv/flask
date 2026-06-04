from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, current_app
from flask.scheduler.exceptions import TaskNotFoundError

# Create blueprint
scheduler_blueprint = Blueprint('scheduler', __name__)

@scheduler_blueprint.route('/metrics', methods=['GET'])
def get_metrics():
    """Get scheduler metrics."""
    scheduler = current_app.extensions.get('scheduler')
    if not scheduler:
        return jsonify({'error': 'Scheduler not initialized'}), 500
    
    # Get tasks info
    tasks_info = []
    for task in scheduler.storage.get_all_tasks():
        tasks_info.append({
            'name': task.name,
            'status': task.status,
            'next_run': task.next_run.isoformat() if task.next_run else None,
            'last_run': task.last_run.isoformat() if task.last_run else None,
            'run_count': task.run_count,
            'last_duration_ms': task.last_duration_ms,
            'last_error': task.last_error
        })
    
    # Prepare response
    response = {
        'rss': scheduler.metrics.get_rss(),
        'uptime_seconds': scheduler.metrics.get_uptime(),
        'tasks': tasks_info
    }
    
    # Add rate limited count if available
    if hasattr(scheduler.metrics, 'rate_limited_count'):
        response['rate_limited_count'] = scheduler.metrics.rate_limited_count
    
    return jsonify(response)

@scheduler_blueprint.route('/tasks/<name>/run', methods=['POST'])
def run_task(name):
    """Run a task immediately."""
    scheduler = current_app.extensions.get('scheduler')
    if not scheduler:
        return jsonify({'error': 'Scheduler not initialized'}), 500
    
    task = scheduler.storage.get_task(name)
    if not task:
        raise TaskNotFoundError(f'Task {name} not found')
    
    # Update next_run to now + interval/cron/delay
    now = datetime.now(timezone.utc)
    if task.task_type == 'interval':
        task.next_run = now
    elif task.task_type == 'cron':
        task.next_run = now
    elif task.task_type == 'delay':
        task.next_run = now
    
    return jsonify({'message': f'Task {name} scheduled to run immediately'})

@scheduler_blueprint.route('/tasks/reload', methods=['POST'])
def reload_tasks():
    """Reload all tasks."""
    scheduler = current_app.extensions.get('scheduler')
    if not scheduler:
        return jsonify({'error': 'Scheduler not initialized'}), 500
    
    scheduler.reload()
    return jsonify({'message': 'Tasks reloaded successfully'})
