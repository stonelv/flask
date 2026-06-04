from flask import Blueprint
from flask import current_app
from flask import g
from flask import jsonify
from flask import request

from .models import TaskStatus

bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")


class ApiResponse:
    @staticmethod
    def success(data=None, message: str = "Success"):
        return jsonify({
            "code": 0,
            "message": message,
            "data": data
        })

    @staticmethod
    def error(code: int, message: str, details=None, status_code: int = 400):
        response = jsonify({
            "code": code,
            "message": message,
            "details": details
        })
        response.status_code = status_code
        return response


class ErrorCodes:
    BAD_REQUEST = 40000
    VALIDATION_ERROR = 40001
    INVALID_PARAMETER = 40002
    NOT_FOUND = 40400
    INTERNAL_ERROR = 50000


def get_storage():
    return g.task_storage


def get_executor():
    return g.task_executor


@bp.route("", methods=["POST"])
def create_task():
    data = request.get_json()
    if not data:
        return ApiResponse.error(
            ErrorCodes.VALIDATION_ERROR,
            "Request body is required",
            {"field": "body"}
        )

    task_type = data.get("type")
    if not task_type:
        return ApiResponse.error(
            ErrorCodes.VALIDATION_ERROR,
            "Task 'type' is required",
            {"field": "type"}
        )

    payload = data.get("payload", {})
    idempotency_key = data.get("idempotency_key")

    storage = get_storage()
    executor = get_executor()

    task = storage.create(
        task_type=task_type,
        payload=payload,
        idempotency_key=idempotency_key,
    )

    if task is None:
        return ApiResponse.error(
            ErrorCodes.INTERNAL_ERROR,
            "Failed to create task due to database constraint",
            status_code=500
        )

    if task.status == TaskStatus.PENDING:
        executor.submit(task)

    return ApiResponse.success(task.to_dict(), "Task created"), 201


@bp.route("/<task_id>", methods=["GET"])
def get_task(task_id):
    storage = get_storage()
    task = storage.get(task_id)
    if not task:
        return ApiResponse.error(
            ErrorCodes.NOT_FOUND,
            "Task not found",
            {"task_id": task_id},
            404
        )
    return ApiResponse.success(task.to_dict())


@bp.route("", methods=["GET"])
def list_tasks():
    storage = get_storage()

    status_param = request.args.get("status")
    type_param = request.args.get("type")

    page_str = request.args.get("page")
    if page_str is not None:
        try:
            page = max(1, int(page_str))
        except (TypeError, ValueError):
            return ApiResponse.error(
                ErrorCodes.INVALID_PARAMETER,
                "Invalid 'page' parameter",
                {"field": "page", "expected": "positive integer"}
            )
    else:
        page = 1

    per_page_str = request.args.get("per_page")
    if per_page_str is not None:
        try:
            per_page = min(100, max(1, int(per_page_str)))
        except (TypeError, ValueError):
            return ApiResponse.error(
                ErrorCodes.INVALID_PARAMETER,
                "Invalid 'per_page' parameter",
                {"field": "per_page", "expected": "integer between 1 and 100"}
            )
    else:
        per_page = 20

    status = None
    if status_param:
        try:
            status = TaskStatus(status_param.upper())
        except ValueError:
            valid_statuses = [s.value for s in TaskStatus]
            return ApiResponse.error(
                ErrorCodes.INVALID_PARAMETER,
                f"Invalid 'status' parameter",
                {"field": "status", "expected": valid_statuses}
            )

    tasks, total = storage.list(
        status=status,
        task_type=type_param,
        page=page,
        per_page=per_page,
    )

    return ApiResponse.success({
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
        return ApiResponse.error(
            ErrorCodes.NOT_FOUND,
            "Task not found",
            {"task_id": task_id},
            404
        )

    task = storage.request_cancel(task_id)
    return ApiResponse.success(task.to_dict(), "Cancel requested")
