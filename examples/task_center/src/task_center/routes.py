from flask import Blueprint
from flask import current_app
from flask import g
from flask import jsonify
from flask import request

from .models import TaskStatus

bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")


def get_storage():
    return g.task_storage


def get_executor():
    return g.task_executor


@bp.route("", methods=["POST"])
def create_task():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    task_type = data.get("type")
    if not task_type:
        return jsonify({"error": "Task 'type' is required"}), 400

    payload = data.get("payload", {})
    idempotency_key = data.get("idempotency_key")

    storage = get_storage()
    executor = get_executor()

    task = storage.create(
        task_type=task_type,
        payload=payload,
        idempotency_key=idempotency_key,
    )

    if task.status == TaskStatus.PENDING:
        executor.submit(task)

    return jsonify(task.to_dict()), 201


@bp.route("/<task_id>", methods=["GET"])
def get_task(task_id):
    storage = get_storage()
    task = storage.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task.to_dict())


@bp.route("", methods=["GET"])
def list_tasks():
    storage = get_storage()

    status_param = request.args.get("status")
    type_param = request.args.get("type")
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))

    status = TaskStatus(status_param) if status_param else None

    tasks, total = storage.list(
        status=status,
        task_type=type_param,
        page=page,
        per_page=per_page,
    )

    return jsonify({
        "tasks": [t.to_dict() for t in tasks],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        },
    })


@bp.route("/<task_id>/cancel", methods=["POST"])
def cancel_task(task_id):
    storage = get_storage()
    task = storage.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    task = storage.request_cancel(task_id)
    return jsonify(task.to_dict())
