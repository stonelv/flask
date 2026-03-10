from flask import Blueprint, request, jsonify
from task_center import db
from task_center.models import Task, TaskStatus
from task_center.executor import executor, sample_long_task

api_bp = Blueprint('api', __name__)

@api_bp.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    
    if not data or 'name' not in data or 'type' not in data:
        return jsonify({'error': 'Missing required fields: name and type'}), 400

    idempotency_key = data.get('idempotency_key')
    
    if idempotency_key:
        existing_task = db.session.query(Task).filter_by(idempotency_key=idempotency_key).first()
        if existing_task:
            return jsonify({
                'task': existing_task.to_dict(),
                'message': 'Task already exists (idempotency key match)'
            }), 200

    task = Task(
        name=data['name'],
        type=data['type'],
        payload=data.get('payload'),
        idempotency_key=idempotency_key
    )
    
    db.session.add(task)
    db.session.commit()

    executor.submit_task(task.id, sample_long_task)

    return jsonify({
        'task': task.to_dict(),
        'message': 'Task created successfully'
    }), 201

@api_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify({'task': task.to_dict()})

@api_bp.route('/tasks', methods=['GET'])
def list_tasks():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status = request.args.get('status')
    task_type = request.args.get('type')

    query = db.session.query(Task)

    if status:
        try:
            status_enum = TaskStatus(status.lower())
            query = query.filter_by(status=status_enum)
        except ValueError:
            return jsonify({'error': 'Invalid status value'}), 400

    if task_type:
        query = query.filter_by(type=task_type)

    query = query.order_by(Task.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'tasks': [task.to_dict() for task in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'pages': pagination.pages
    })

@api_bp.route('/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    if task.status == TaskStatus.CANCELLED:
        return jsonify({'message': 'Task is already cancelled'}), 200

    if task.status in [TaskStatus.SUCCEEDED, TaskStatus.FAILED]:
        return jsonify({'error': 'Cannot cancel a completed task'}), 400

    if executor.cancel_task(task_id):
        db.session.refresh(task)
        return jsonify({
            'task': task.to_dict(),
            'message': 'Task cancellation requested'
        })
    else:
        return jsonify({'error': 'Failed to cancel task'}), 500
