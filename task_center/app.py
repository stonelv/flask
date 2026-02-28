"""
Task Center - Flask API Application
"""
from __future__ import annotations

import logging
import os
from datetime import datetime

from flask import Flask, jsonify, request

from .models import TaskRepository, TaskStatus
from .executor import TaskExecutor
from .service import TaskService


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
    
    # 注册关闭钩子
    @app.teardown_appcontext
    def shutdown_executor(exception=None):
        """应用关闭时清理资源"""
        pass  # 在应用关闭时统一处理
    
    @app.before_request
    def log_request():
        """记录请求日志"""
        logger = logging.getLogger("task_center.api")
        logger.info(
            f"{request.method} {request.path}",
            extra={
                "method": request.method,
                "path": request.path,
                "remote_addr": request.remote_addr,
            }
        )
    
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
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        })
    
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
        """
        data = request.get_json(silent=True)
        
        if data is None:
            return jsonify({"error": "Request body is required"}), 400
        
        task_type = data.get("type")
        if not task_type:
            return jsonify({"error": "type is required"}), 400
        
        payload = data.get("payload", {})
        idempotency_key = data.get("idempotency_key")
        
        try:
            task, is_new = app.task_service.create_task(
                task_type=task_type,
                payload=payload,
                idempotency_key=idempotency_key
            )
            
            response = {
                "task": task.to_dict(),
                "is_new": is_new
            }
            
            status_code = 201 if is_new else 200
            return jsonify(response), status_code
            
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logging.getLogger("task_center.api").exception("Failed to create task")
            return jsonify({"error": "Internal server error"}), 500
    
    @app.route("/api/tasks", methods=["GET"])
    def list_tasks():
        """
        获取任务列表
        
        Query Parameters:
            status: 按状态过滤 (PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED)
            type: 按类型过滤
            limit: 每页数量，默认20
            offset: 偏移量，默认0
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
                return jsonify({
                    "error": f"Invalid status: {status_filter}. Valid values: {[s.value for s in TaskStatus]}"
                }), 400
        
        try:
            tasks, total = app.task_service.list_tasks(
                status=status,
                task_type=type_filter,
                limit=limit,
                offset=offset
            )
            
            return jsonify({
                "tasks": [task.to_dict() for task in tasks],
                "pagination": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(tasks) < total
                }
            })
            
        except Exception as e:
            logging.getLogger("task_center.api").exception("Failed to list tasks")
            return jsonify({"error": "Internal server error"}), 500
    
    @app.route("/api/tasks/<task_id>", methods=["GET"])
    def get_task(task_id: str):
        """
        获取任务详情
        
        Path Parameters:
            task_id: 任务ID
        """
        task = app.task_service.get_task(task_id)
        
        if not task:
            return jsonify({"error": "Task not found"}), 404
        
        return jsonify({"task": task.to_dict()})
    
    @app.route("/api/tasks/<task_id>/cancel", methods=["POST"])
    def cancel_task(task_id: str):
        """
        取消任务
        
        Path Parameters:
            task_id: 任务ID
        """
        success, message = app.task_service.cancel_task(task_id)
        
        if not success:
            return jsonify({"error": message}), 400
        
        # 获取更新后的任务
        task = app.task_service.get_task(task_id)
        
        return jsonify({
            "message": message,
            "task": task.to_dict() if task else None
        })


def register_error_handlers(app: Flask):
    """注册错误处理器"""
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed"}), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500


# 创建应用实例
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
