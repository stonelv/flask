"""示例应用：展示自定义速率限制装饰器的实现。"""
import time
from typing import Callable

from flask import Flask, jsonify, request

# 用于存储请求计数的内存字典
# 结构: {ip_address: (count, window_start_time)}
request_counts = {}

def rate_limit(max_requests: int = 10, window_seconds: int = 60) -> Callable:
    """
    自定义速率限制装饰器。
    
    Args:
        max_requests: 时间窗口内允许的最大请求次数
        window_seconds: 时间窗口大小（秒）
    
    Returns:
        装饰后的视图函数
    """
    def decorator(f: Callable) -> Callable:
        def wrapped(*args, **kwargs):
            # 获取客户端 IP 地址
            ip_address = request.remote_addr
            current_time = time.time()
            
            # 检查 IP 是否在计数字典中
            if ip_address in request_counts:
                count, window_start = request_counts[ip_address]
                
                # 检查时间窗口是否已过期
                if current_time - window_start > window_seconds:
                    # 重置计数
                    request_counts[ip_address] = (1, current_time)
                else:
                    # 检查是否超出限制
                    if count >= max_requests:
                        return (
                            jsonify(
                                {
                                    "error": "Rate limit exceeded",
                                    "message": f"Too many requests. Please try again in {int(window_seconds - (current_time - window_start))} seconds.",
                                    "retry_after": int(window_seconds - (current_time - window_start)),
                                }
                            ),
                            429,
                        )
                    # 增加计数
                    request_counts[ip_address] = (count + 1, window_start)
            else:
                # 新 IP，初始化计数
                request_counts[ip_address] = (1, current_time)
            
            # 继续执行原视图函数
            return f(*args, **kwargs)
        
        # 保留原函数的元信息
        wrapped.__name__ = f.__name__
        wrapped.__doc__ = f.__doc__
        return wrapped
    
    return decorator


# 创建 Flask 应用
app = Flask(__name__)


@app.route("/api/limited")
@rate_limit(max_requests=10, window_seconds=60)
def limited_endpoint():
    """使用了速率限制装饰器的示例接口。"""
    return jsonify(
        {
            "message": "Success! This is a rate-limited endpoint.",
            "ip": request.remote_addr,
            "count": request_counts[request.remote_addr][0],
        }
    )


@app.route("/api/unlimited")
def unlimited_endpoint():
    """未使用速率限制的普通接口。"""
    return jsonify(
        {
            "message": "Success! This endpoint has no rate limit.",
            "ip": request.remote_addr,
        }
    )


@app.route("/api/other-limited")
@rate_limit(max_requests=5, window_seconds=30)
def other_limited_endpoint():
    """使用不同速率限制参数的示例接口。"""
    return jsonify(
        {
            "message": "Success! This is another rate-limited endpoint with different limits.",
            "ip": request.remote_addr,
            "count": request_counts[request.remote_addr][0],
        }
    )


@app.route("/")
def index():
    """首页，展示 API 文档。"""
    return jsonify(
        {
            "endpoints": {
                "/api/limited": "Rate limited: 10 requests per minute",
                "/api/unlimited": "No rate limit",
                "/api/other-limited": "Rate limited: 5 requests per 30 seconds",
            }
        }
    )
