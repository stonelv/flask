import uuid
import logging
from datetime import datetime, UTC
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from .database import db_session, Task, TaskStatus
from .executor import executor, get_task_func


logger = logging.getLogger(__name__)
bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/tasks", methods=["POST"])
def create_task():
    """Create a new task with idempotency support - atomic insert first"""
    data = request.get_json()

    if not data or "type" not in data:
        return jsonify({"error": None, "data": None, "message": "Task type is required"}), 400

    task_type = data["type"]
    idempotency_key = data.get("idempotency_key")
    payload = data.get("payload", {})

    # Validate task type exists first
    task_func = get_task_func(task_type)
    if not task_func:
        return jsonify({"error": None, "data": None, "message": f"Unknown task type: {task_type}"}), 400

    # Create new task
    task_id = str(uuid.uuid4())
    task = Task(
        id=task_id,
        type=task_type,
        status=TaskStatus.PENDING,
        progress=0,
        stage="init",
        payload=payload,
        idempotency_key=idempotency_key,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    try:
        db_session.add(task)
        db_session.commit()
        
        # Get the task dict before submitting for execution
        task_response = task.to_dict()
        
        # Submit task for execution
        executor.submit_task(task_id, task_func)
        
        logger.info(f"Created task {task_id} of type {task_type}", 
                   extra={"task_id": task_id, "stage": "init", "progress": 0})
        return jsonify({"error": None, "data": task_response, "message": "Task created successfully"}), 201
        
    except IntegrityError:
        db_session.rollback()
        # Unique constraint violation - find existing task
        if idempotency_key:
            existing_task = db_session.query(Task).filter_by(idempotency_key=idempotency_key).first()
            if existing_task:
                logger.info(f"Returning existing task for idempotency_key: {idempotency_key}",
                           extra={"task_id": existing_task.id, "stage": existing_task.stage, "progress": existing_task.progress})
                return jsonify({"error": None, "data": existing_task.to_dict(), "message": "Task already exists"}), 200
        # If no idempotency_key or not found, re-raise
        raise


@bp.route("/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    """Get task by ID"""
    task = db_session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found", "data": None, "message": None}), 404
    return jsonify({"error": None, "data": task.to_dict(), "message": None})


@bp.route("/tasks", methods=["GET"])
def list_tasks():
    """List tasks with filtering and pagination"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status = request.args.get("status")
    task_type = request.args.get("type")

    query = db_session.query(Task)

    if status:
        try:
            status_enum = TaskStatus[status.upper()]
            query = query.filter_by(status=status_enum)
        except KeyError:
            return jsonify({"error": f"Invalid status: {status}", "data": None, "message": None}), 400

    if task_type:
        query = query.filter_by(type=task_type)

    # Sort by created time descending
    query = query.order_by(Task.created_at.desc())

    # Pagination
    total = query.count()
    tasks = query.offset((page - 1) * per_page).limit(per_page).all()

    result = {
        "items": [task.to_dict() for task in tasks],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }
    return jsonify({"error": None, "data": result, "message": None})


@bp.route("/tasks/<task_id>/cancel", methods=["POST"])
def cancel_task(task_id):
    """Cancel a running task"""
    task = db_session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found", "data": None, "message": None}), 404

    if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
        return jsonify({"error": f"Cannot cancel task with status {task.status}", "data": None, "message": None}), 400

    success = executor.cancel_task(task_id)
    if not success:
        return jsonify({"error": "Failed to cancel task", "data": None, "message": None}), 500

    # Refresh task from database
    db_session.refresh(task)
    
    logger.info(f"Cancelled task {task_id}", 
               extra={"task_id": task_id, "stage": task.stage, "progress": task.progress})
    return jsonify({
        "error": None, 
        "data": task.to_dict(), 
        "message": "Task cancelled successfully"
    })


@bp.teardown_request
def shutdown_session(exception=None):
    db_session.remove()


def init_app(app):
    """Initialize the task center app"""
    app.register_blueprint(bp)
