"""
Task Center - Flask API Application
统一 JSON 返回格式
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime

from flask import Flask, jsonify, request, g

from .models import TaskRepository, TaskStatus
from .executor import TaskExecutor
from .service import TaskService
from .response import (
    success_response, error_response, bad_request, not_found, internal_error,
    ResponseCode
)


def create_app(test_config: dict = None) -> Flask:
    """创建Flask应用"""
    app = Flask(__name__)

    # 配置
    app.config.from_mapping(
        DATABASE=os.environ.get("TASK_CENTER_DB", "tasks.db"),
        MAX_WORKERS=int(os.environ.get("TASK_CENTER_MAX_WORKERS", "5")),
        JSON_SORT_KEYS=False,
    )

    if test_config:
        app.config.update(test_config)

    # 配置结构化日志
    setup_logging()

    # 初始化组件
    repository = TaskRepository(app.config["DATABASE"])
    executor = TaskExecutor(repository, max_workers=app.config["MAX_WORKERS"])
    service = TaskService(repository, executor)

    # 存储在应用上下文中
    app.repository = repository
    app.executor = executor
    app.task_service = service

    # 注册路由
    register_routes(app)

    # 注册错误处理
    register_error_handlers(app)

    # 请求前生成 request_id
    @app.before_request
    def before_request():
        g.request_id = str(uuid.uuid4())
        logger = logging.getLogger("task_center.api")
        logger.info(
            f"{request.method} {request.path}",
            extra={
                "method": request.method,
                "path": request.path,
                "remote_addr": request.remote_addr,
                "request_id": g.request_id,
            }
        )

    # 注册关闭钩子
    @app.teardown_appcontext
    def shutdown_executor(exception=None):
        """应用关闭时清理资源"""
        pass

    return app


def setup_logging():
    """配置结构化日志"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 设置第三方库日志级别
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def register_routes(app: Flask):
    """注册API路由"""

    @app.route("/health", methods=["GET"])
    def health_check():
        """健康检查"""
        return success_response(
            data={"status": "healthy", "timestamp": datetime.utcnow().isoformat()},
            message="Service is healthy"
        )

    @app.route("/api/tasks", methods=["POST"])
    def create_task():
        """
        创建任务

        Request Body:
            {
                "type": "long_running_task",  # 任务类型
                "payload": {...},              # 任务参数
                "idempotency_key": "..."       # 可选，幂等键
            }

        Response:
            {
                "code": 0,
                "message": "success",
                "data": {
                    "task": {...},
                    "is_new": true
                },
                "request_id": "..."
            }
        """
        data = request.get_json(silent=True)

        if data is None:
            return bad_request("Request body is required")

        task_type = data.get("type")
        if not task_type:
            return error_response(
                ResponseCode.MISSING_PARAM,
                "type is required",
                {"field": "type"}
            )

        payload = data.get("payload", {})
        idempotency_key = data.get("idempotency_key")

        try:
            task, is_new, error = app.task_service.create_task(
                task_type=task_type,
                payload=payload,
                idempotency_key=idempotency_key
            )

            if error:
                return internal_error(error)

            response_data = {
                "task": task.to_dict(),
                "is_new": is_new
            }

            if is_new:
                return success_response(data=response_data, message="Task created successfully")
            else:
                # 幂等返回已有任务
                return success_response(
                    data=response_data,
                    message="Task already exists (idempotent request)"
                )

        except ValueError as e:
            return error_response(ResponseCode.INVALID_PARAM, str(e))
        except Exception as e:
            logging.getLogger("task_center.api").exception("Failed to create task")
            return internal_error("Internal server error")

    @app.route("/api/tasks", methods=["GET"])
    def list_tasks():
        """
        获取任务列表

        Query Parameters:
            status: 按状态过滤 (PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED)
            type: 按类型过滤
            limit: 每页数量，默认20
            offset: 偏移量，默认0

        Response:
            {
                "code": 0,
                "message": "success",
                "data": {
                    "tasks": [...],
                    "pagination": {...}
                },
                "request_id": "..."
            }
        """
        # 解析查询参数
        status_filter = request.args.get("status")
        type_filter = request.args.get("type")
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)

        # 限制分页参数
        limit = max(1, min(100, limit))
        offset = max(0, offset)

        # 解析状态
        status = None
        if status_filter:
            try:
                status = TaskStatus(status_filter.upper())
            except ValueError:
                return error_response(
                    ResponseCode.INVALID_PARAM,
                    f"Invalid status: {status_filter}",
                    {"valid_values": [s.value for s in TaskStatus]}
                )

        try:
            tasks, total = app.task_service.list_tasks(
                status=status,
                task_type=type_filter,
                limit=limit,
                offset=offset
            )

            response_data = {
                "tasks": [task.to_dict() for task in tasks],
                "pagination": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(tasks) < total
                }
            }

            return success_response(data=response_data)

        except Exception as e:
            logging.getLogger("task_center.api").exception("Failed to list tasks")
            return internal_error("Internal server error")

    @app.route("/api/tasks/<task_id>", methods=["GET"])
    def get_task(task_id: str):
        """
        获取任务详情

        Path Parameters:
            task_id: 任务ID

        Response:
            {
                "code": 0,
                "message": "success",
                "data": {"task": {...}},
                "request_id": "..."
            }
        """
        task = app.task_service.get_task(task_id)

        if not task:
            return not_found("Task not found")

        return success_response(data={"task": task.to_dict()})

    @app.route("/api/tasks/<task_id>/logs", methods=["GET"])
    def get_task_logs(task_id: str):
        """
        获取任务结构化日志

        Path Parameters:
            task_id: 任务ID

        Response:
            {
                "code": 0,
                "message": "success",
                "data": {
                    "task_id": "...",
                    "logs": [...]
                },
                "request_id": "..."
            }
        """
        task = app.task_service.get_task(task_id)

        if not task:
            return not_found("Task not found")

        # 计算执行时间
        elapsed_ms = None
        if task.started_at:
            end_time = task.completed_at or task.cancelled_at or datetime.utcnow()
            elapsed_ms = int((end_time - task.started_at).total_seconds() * 1000)

        response_data = {
            "task_id": task.id,
            "type": task.type,
            "status": task.status.value,
            "progress": task.progress,
            "stage": task.stage,
            "elapsed_ms": elapsed_ms,
            "logs": task.logs
        }

        return success_response(data=response_data)

    @app.route("/api/tasks/<task_id>/cancel", methods=["POST"])
    def cancel_task(task_id: str):
        """
        取消任务

        Path Parameters:
            task_id: 任务ID

        Response:
            {
                "code": 0,
                "message": "Task cancelled",
                "data": {"task": {...}},
                "request_id": "..."
            }
        """
        success, message = app.task_service.cancel_task(task_id)

        if not success:
            if "not found" in message.lower():
                return not_found(message)
            else:
                return error_response(ResponseCode.TASK_CANNOT_CANCEL, message)

        # 获取更新后的任务
        task = app.task_service.get_task(task_id)

        return success_response(
            data={"task": task.to_dict() if task else None},
            message=message
        )


def register_error_handlers(app: Flask):
    """注册错误处理器"""

    @app.errorhandler(404)
    def not_found_handler(error):
        return not_found("Resource not found")

    @app.errorhandler(405)
    def method_not_allowed_handler(error):
        return error_response(ResponseCode.BAD_REQUEST, "Method not allowed")

    @app.errorhandler(500)
    def internal_error_handler(error):
        return internal_error("Internal server error")


# 创建应用实例
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
