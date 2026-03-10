import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from task_center import db, executor
from task_center.models import Task, TaskStatus

api_bp = Blueprint('api', __name__)

@api_bp.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json() or {}
    
    required_fields = ['name', 'type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    idempotency_key = data.get('idempotency_key')
    
    if idempotency_key:
        existing_task = Task.query.filter_by(idempotency_key=idempotency_key).first()
        if existing_task:
            return jsonify({
                'task': existing_task.to_dict(),
                'message': 'Task with same idempotency key already exists'
            }), 200
    
    task_id = str(uuid.uuid4())
    task = Task(
        id=task_id,
        name=data['name'],
        type=data['type'],
        status=TaskStatus.PENDING,
        progress=0,
        idempotency_key=idempotency_key,
        timeout=data.get('timeout', 300)
    )
    
    if 'payload' in data:
        task.set_payload(data['payload'])
    
    db.session.add(task)
    db.session.commit()
    
    try:
        executor.submit_task(task_id, data['type'], data.get('payload'))
    except ValueError as e:
        task.status = TaskStatus.FAILED
        task.set_error({'message': str(e)})
        db.session.commit()
        return jsonify({'error': str(e)}), 400
    
    return jsonify({
        'task': task.to_dict(),
        'message': 'Task created successfully'
    }), 201

@api_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    return jsonify({'task': task.to_dict()})

@api_bp.route('/tasks', methods=['GET'])
def list_tasks():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    task_type = request.args.get('type')
    
    query = Task.query
    
    if status:
        try:
            status_enum = TaskStatus(status.lower())
            query = query.filter_by(status=status_enum)
        except ValueError:
            return jsonify({'error': f'Invalid status: {status}. Valid statuses: {[s.value for s in TaskStatus]}'}), 400
    
    if task_type:
        query = query.filter_by(type=task_type)
    
    query = query.order_by(Task.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'tasks': [task.to_dict() for task in pagination.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })

@api_bp.route('/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    if task.status in [TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        return jsonify({
            'error': f'Cannot cancel task in {task.status.value} status',
            'task': task.to_dict()
        }), 400
    
    if executor.cancel_task(task_id):
        # Refresh task to get updated status
        db.session.refresh(task)
        return jsonify({
            'task': task.to_dict(),
            'message': 'Task cancellation requested'
        })
    else:
        task.status = TaskStatus.CANCELLED
        task.cancelled_at = datetime.utcnow()
        db.session.commit()
        return jsonify({
            'task': task.to_dict(),
            'message': 'Task marked as cancelled'
        })

@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@api_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500
