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
    """Create a new task with idempotency support"""
    data = request.get_json()

    if not data or "type" not in data:
        return jsonify({"error": "Task type is required"}), 400

    task_type = data["type"]
    idempotency_key = data.get("idempotency_key")
    payload = data.get("payload", {})

    # Check if idempotency key exists
    if idempotency_key:
        existing_task = db_session.query(Task).filter_by(idempotency_key=idempotency_key).first()
        if existing_task:
            logger.info(f"Returning existing task for idempotency_key: {idempotency_key}")
            return jsonify(existing_task.to_dict()), 200

    # Validate task type exists
    if not get_task_func(task_type):
        return jsonify({"error": f"Unknown task type: {task_type}"}), 400

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
    except IntegrityError:
        db_session.rollback()
        # Race condition: another request with same idempotency_key was processed
        existing_task = db_session.query(Task).filter_by(idempotency_key=idempotency_key).first()
        if existing_task:
            return jsonify(existing_task.to_dict()), 200
        raise

    # Get the task dict before submitting for execution (to capture initial state)
    task_response = task.to_dict()

    # Submit task for execution
    task_func = get_task_func(task_type)
    if task_func:
        executor.submit_task(task_id, task_func)

    logger.info(f"Created task {task_id} of type {task_type}")
    return jsonify(task_response), 201


@bp.route("/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    """Get task by ID"""
    task = db_session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task.to_dict())


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
            return jsonify({"error": f"Invalid status: {status}"}), 400

    if task_type:
        query = query.filter_by(type=task_type)

    # Sort by created time descending
    query = query.order_by(Task.created_at.desc())

    # Pagination
    total = query.count()
    tasks = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "items": [task.to_dict() for task in tasks],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    })


@bp.route("/tasks/<task_id>/cancel", methods=["POST"])
def cancel_task(task_id):
    """Cancel a running task"""
    task = db_session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
        return jsonify({"error": f"Cannot cancel task with status {task.status}"}), 400

    success = executor.cancel_task(task_id)
    if not success:
        return jsonify({"error": "Failed to cancel task"}), 500

    # Refresh task from database
    db_session.refresh(task)
    return jsonify({"message": "Task cancelled successfully", "task": task.to_dict()})


@bp.teardown_request
def shutdown_session(exception=None):
    db_session.remove()


def init_app(app):
    """Initialize the task center app"""
    app.register_blueprint(bp)
