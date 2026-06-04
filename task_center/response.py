"""
Task Center - Unified JSON Response
统一 JSON 返回格式
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, asdict
from typing import Any, Optional

from flask import jsonify, request


@dataclass
class ApiResponse:
    """统一 API 响应格式"""
    code: int
    message: str
    data: Any = None
    request_id: str = ""
    
    def __post_init__(self):
        if not self.request_id:
            self.request_id = str(uuid.uuid4())
    
    def to_dict(self) -> dict:
        """转换为字典"""
        result = {
            "code": self.code,
            "message": self.message,
            "request_id": self.request_id,
        }
        if self.data is not None:
            result["data"] = self.data
        return result


class ResponseCode:
    """响应状态码"""
    SUCCESS = 0
    
    # 客户端错误 (4xx)
    BAD_REQUEST = 400000
    INVALID_PARAM = 400001
    MISSING_PARAM = 400002
    TASK_NOT_FOUND = 404001
    TASK_CANNOT_CANCEL = 400003
    DUPLICATE_KEY = 409001
    
    # 服务端错误 (5xx)
    INTERNAL_ERROR = 500000
    DB_ERROR = 500001


# HTTP 状态码映射
HTTP_STATUS_MAP = {
    ResponseCode.SUCCESS: 200,
    ResponseCode.BAD_REQUEST: 400,
    ResponseCode.INVALID_PARAM: 400,
    ResponseCode.MISSING_PARAM: 400,
    ResponseCode.TASK_NOT_FOUND: 404,
    ResponseCode.TASK_CANNOT_CANCEL: 400,
    ResponseCode.DUPLICATE_KEY: 200,  # 幂等返回已有任务，HTTP 200
    ResponseCode.INTERNAL_ERROR: 500,
    ResponseCode.DB_ERROR: 500,
}


def success_response(data: Any = None, message: str = "success"):
    """成功响应"""
    response = ApiResponse(
        code=ResponseCode.SUCCESS,
        message=message,
        data=data,
        request_id=getattr(request, 'request_id', str(uuid.uuid4()))
    )
    return jsonify(response.to_dict()), HTTP_STATUS_MAP[ResponseCode.SUCCESS]


def error_response(code: int, message: str, data: Any = None):
    """错误响应"""
    response = ApiResponse(
        code=code,
        message=message,
        data=data,
        request_id=getattr(request, 'request_id', str(uuid.uuid4()))
    )
    http_status = HTTP_STATUS_MAP.get(code, 500)
    return jsonify(response.to_dict()), http_status


def bad_request(message: str = "Bad request", data: Any = None):
    """400 错误"""
    return error_response(ResponseCode.BAD_REQUEST, message, data)


def not_found(message: str = "Not found", data: Any = None):
    """404 错误"""
    return error_response(ResponseCode.TASK_NOT_FOUND, message, data)


def internal_error(message: str = "Internal server error", data: Any = None):
    """500 错误"""
    return error_response(ResponseCode.INTERNAL_ERROR, message, data)
