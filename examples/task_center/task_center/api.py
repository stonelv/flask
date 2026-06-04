import json
import logging
from datetime import datetime, UTC
from typing import Any, Dict

from flask import Blueprint, abort, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload

from . import db
from .models import Task, TaskStatus
from .executor import get_executor

bp = Blueprint("api", __name__, url_prefix="/api/tasks")
logger = logging.getLogger("task_center")


@bp.post("")
def create_task():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    task_type = data.get("type")
    if not task_type:
        return jsonify({"error": "Task type is required"}), 400

    idempotency_key = data.get("idempotency_key")
    payload = data.get("payload", {})

    try:
        if idempotency_key:
            existing_task = db.session.execute(
                select(Task).where(Task.idempotency_key == idempotency_key).with_for_update()
            ).scalar_one_or_none()
            
            if existing_task:
                logger.info(
                    f"Task with idempotency_key {idempotency_key} already exists",
                    extra={
                        "task_id": existing_task.id,
                        "stage": None,
                        "progress": 0,
                    },
                )
                return jsonify(existing_task.to_dict()), 200

        task = Task(
            type=task_type,
            status=TaskStatus.PENDING,
            progress=0,
            stage=None,
            payload=json.dumps(payload) if payload else None,
            idempotency_key=idempotency_key,
        )
        db.session.add(task)
        db.session.commit()

        logger.info(
            f"Task created",
            extra={
                "task_id": task.id,
                "stage": "created",
                "progress": 0,
            },
        )

        executor = get_executor()
        executor.submit_task(task.id)

        return jsonify(task.to_dict()), 201

    except IntegrityError as e:
        db.session.rollback()
        if "idempotency_key" in str(e):
            existing_task = db.session.execute(
                select(Task).where(Task.idempotency_key == idempotency_key)
            ).scalar_one_or_none()
            if existing_task:
                return jsonify(existing_task.to_dict()), 200
        logger.error(
            f"Integrity error creating task: {e}",
            extra={"task_id": None, "stage": None, "progress": 0},
        )
        return jsonify({"error": "Failed to create task due to concurrency"}), 409
    except Exception as e:
        db.session.rollback()
        logger.error(
            f"Error creating task: {e}",
            extra={"task_id": None, "stage": None, "progress": 0},
        )
        return jsonify({"error": str(e)}), 500


@bp.get("/<task_id>")
def get_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task.to_dict())


@bp.get("")
def list_tasks():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status = request.args.get("status")
    task_type = request.args.get("type")

    query = select(Task).order_by(Task.created_at.desc())

    if status:
        try:
            status_enum = TaskStatus(status.upper())
            query = query.where(Task.status == status_enum)
        except ValueError:
            return jsonify({"error": f"Invalid status: {status}"}), 400

    if task_type:
        query = query.where(Task.type == task_type)

    result = db.paginate(query, page=page, per_page=per_page)

    return jsonify({
        "items": [task.to_dict() for task in result.items],
        "total": result.total,
        "page": result.page,
        "per_page": result.per_page,
        "pages": result.pages,
    })


@bp.post("/<task_id>/cancel")
def cancel_task(task_id):
    try:
        stmt = select(Task).where(Task.id == task_id).with_for_update()
        task = db.session.execute(stmt).scalar_one_or_none()

        if not task:
            return jsonify({"error": "Task not found"}), 404

        if task.status == TaskStatus.CANCELLED:
            return jsonify(task.to_dict())

        if task.status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED):
            return jsonify({"error": f"Cannot cancel task in {task.status} state"}), 400

        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now(UTC)
            db.session.commit()
            logger.info(
                "Pending task cancelled",
                extra={"task_id": task_id, "stage": "cancelled", "progress": task.progress},
            )
        else:
            executor = get_executor()
            executor.request_cancel(task_id)
            logger.info(
                "Cancellation requested for running task",
                extra={"task_id": task_id, "stage": "cancelling", "progress": task.progress},
            )

        return jsonify(task.to_dict())

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(
            f"Database error cancelling task: {e}",
            extra={"task_id": task_id, "stage": None, "progress": 0},
        )
        return jsonify({"error": "Database error"}), 500
