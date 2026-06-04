import time
from functools import wraps
from flask import request, jsonify

# 存储访问记录的内存字典
# 格式: {ip_address: [timestamps_list]}
_access_records = {}


def rate_limit(limit=10, window_seconds=60):
    """
    自定义速率限制装饰器
    
    Args:
        limit: 时间窗口内允许的最大请求次数
        window_seconds: 时间窗口大小（秒）
        
    Returns:
        装饰器函数
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取客户端IP地址
            client_ip = request.remote_addr
            
            # 获取当前时间戳
            current_time = time.time()
            
            # 初始化该IP的访问记录（如果不存在）
            if client_ip not in _access_records:
                _access_records[client_ip] = []
            
            # 清理时间窗口外的旧记录
            # 只保留当前时间窗口内的记录
            _access_records[client_ip] = [
                timestamp for timestamp in _access_records[client_ip]
                if timestamp > current_time - window_seconds
            ]
            
            # 检查是否超出限制
            if len(_access_records[client_ip]) >= limit:
                return jsonify({
                    "error": "Too Many Requests",
                    "message": f"Rate limit exceeded. Please try again after {window_seconds} seconds.",
                    "limit": limit,
                    "window_seconds": window_seconds
                }), 429
            
            # 记录本次请求时间
            _access_records[client_ip].append(current_time)
            
            # 执行原始函数
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator