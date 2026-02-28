from flask import Blueprint
from flask import jsonify
from flask import request

from . import TaskStatus
from . import get_task_executor
from . import get_task_store
from .executor import sample_long_task


bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json() or {}
    task_type = data.get("type")
    payload = data.get("payload")
    idempotency_key = data.get("idempotency_key")

    if not task_type:
        return jsonify({"error": "Missing required field: type"}), 400

    if not isinstance(task_type, str) or not task_type.strip():
        return jsonify({"error": "Field 'type' must be a non-empty string"}), 400

    if payload is not None and not isinstance(payload, dict):
        return jsonify({"error": "Field 'payload' must be an object"}), 400

    if idempotency_key is not None and not isinstance(idempotency_key, str):
        return jsonify({"error": "Field 'idempotency_key' must be a string"}), 400

    task_store = get_task_store()
    result = task_store.create_task(
        task_type=task_type.strip(),
        payload=payload,
        idempotency_key=idempotency_key.strip() if idempotency_key else None,
    )

    task = result.task
    is_new = result.is_new

    if is_new:
        executor = get_task_executor()
        if task.type == "sample_long_task":
            executor.register_handler("sample_long_task", sample_long_task)
        executor.submit(task.id)

        return jsonify({"task": task.to_dict(), "is_new": True}), 201
    else:
        return jsonify({"task": task.to_dict(), "is_new": False}), 200


@bp.route("/tasks/<task_id>", methods=["GET"])
def get_task(task_id: str):
    task_store = get_task_store()
    task = task_store.get_by_id(task_id)

    if not task:
        return jsonify({"error": f"Task not found: {task_id}"}), 404

    return jsonify({"task": task.to_dict()})


@bp.route("/tasks", methods=["GET"])
def list_tasks():
    task_store = get_task_store()

    status_str = request.args.get("status")
    task_type = request.args.get("type")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    if page < 1:
        return jsonify({"error": "Parameter 'page' must be >= 1"}), 400

    if per_page < 1 or per_page > 100:
        return jsonify({"error": "Parameter 'per_page' must be between 1 and 100"}), 400

    status = None
    if status_str:
        try:
            status = TaskStatus(status_str.upper())
        except ValueError:
            valid_statuses = [s.value for s in TaskStatus]
            return jsonify({
                "error": f"Invalid status: {status_str}. Valid values: {', '.join(valid_statuses)}",
            }), 400

    tasks, total = task_store.list_tasks(
        status=status,
        task_type=task_type,
        page=page,
        per_page=per_page,
    )

    return jsonify({
        "tasks": [t.to_dict() for t in tasks],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
        },
    })


@bp.route("/tasks/<task_id>/cancel", methods=["POST"])
def cancel_task(task_id: str):
    task_store = get_task_store()
    task = task_store.get_by_id(task_id)

    if not task:
        return jsonify({"error": f"Task not found: {task_id}"}), 404

    if task.status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED):
        return jsonify({
            "error": f"Cannot cancel task {task_id} with status: {task.status.value}",
            "task": task.to_dict(),
        }), 400

    executor = get_task_executor()
    executor.cancel(task_id)

    cancelled_task = task_store.cancel_task(task_id)
    if not cancelled_task:
        return jsonify({"error": f"Failed to cancel task: {task_id}"}), 500

    return jsonify({"task": cancelled_task.to_dict()})


@bp.route("/tasks/<task_id>/logs", methods=["GET"])
def get_task_logs(task_id: str):
    task_store = get_task_store()
    task = task_store.get_by_id(task_id)

    if not task:
        return jsonify({"error": f"Task not found: {task_id}"}), 404

    level = request.args.get("level")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 100, type=int)

    if page < 1:
        return jsonify({"error": "Parameter 'page' must be >= 1"}), 400

    if per_page < 1 or per_page > 500:
        return jsonify({"error": "Parameter 'per_page' must be between 1 and 500"}), 400

    logs, total = task_store.get_logs(
        task_id=task_id,
        level=level,
        page=page,
        per_page=per_page,
    )

    return jsonify({
        "task_id": task_id,
        "logs": [log.to_dict() for log in logs],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
        },
    })
