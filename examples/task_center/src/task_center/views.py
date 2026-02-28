from flask import Blueprint
from flask import current_app
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

    task_store = get_task_store()
    task = task_store.create_task(
        task_type=task_type,
        payload=payload,
        idempotency_key=idempotency_key,
    )

    executor = get_task_executor()
    if task.type == "sample_long_task":
        executor.register_handler("sample_long_task", sample_long_task)

    executor.submit(task.id)

    return jsonify({"task": task.to_dict()}), 201


@bp.route("/tasks/<task_id>", methods=["GET"])
def get_task(task_id: str):
    task_store = get_task_store()
    task = task_store.get_by_id(task_id)

    if not task:
        return jsonify({"error": "Task not found"}), 404

    return jsonify({"task": task.to_dict()})


@bp.route("/tasks", methods=["GET"])
def list_tasks():
    task_store = get_task_store()

    status_str = request.args.get("status")
    task_type = request.args.get("type")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    status = None
    if status_str:
        try:
            status = TaskStatus(status_str.upper())
        except ValueError:
            return jsonify({"error": f"Invalid status: {status_str}"}), 400

    tasks, total = task_store.list_tasks(
        status=status,
        task_type=task_type,
        page=max(1, page),
        per_page=min(100, max(1, per_page)),
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
        return jsonify({"error": "Task not found"}), 404

    if task.status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED):
        return jsonify({
            "error": f"Cannot cancel task with status: {task.status.value}",
            "task": task.to_dict(),
        }), 400

    executor = get_task_executor()
    executor.cancel(task_id)

    cancelled_task = task_store.cancel_task(task_id)
    if not cancelled_task:
        return jsonify({"error": "Failed to cancel task"}), 500

    return jsonify({"task": cancelled_task.to_dict()})
