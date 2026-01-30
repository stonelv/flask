from functools import wraps
from time import time
from flask import request, jsonify, Response


# 内存字典存储每个IP的访问记录
# 格式: {ip_address: {endpoint: [(timestamp1, timestamp2, ...), count]}}
_rate_limit_store = {}


def rate_limit(max_requests=10, window_seconds=60):
    """
    自定义速率限制装饰器
    
    参数:
        max_requests: 时间窗口内允许的最大请求数
        window_seconds: 时间窗口长度（秒）
    
    返回:
        装饰器函数
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取客户端IP
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            
            # 获取当前路由端点
            endpoint = request.endpoint
            
            # 获取当前时间戳
            current_time = time()
            
            # 如果是第一次访问该IP和端点，初始化记录
            if client_ip not in _rate_limit_store:
                _rate_limit_store[client_ip] = {}
            
            if endpoint not in _rate_limit_store[client_ip]:
                _rate_limit_store[client_ip][endpoint] = {
                    'timestamps': [current_time],
                    'count': 1
                }
                return f(*args, **kwargs)
            
            # 获取该IP和端点的访问记录
            ip_data = _rate_limit_store[client_ip][endpoint]
            timestamps = ip_data['timestamps']
            
            # 清理超出时间窗口的记录
            window_start = current_time - window_seconds
            valid_timestamps = [ts for ts in timestamps if ts > window_start]
            
            # 更新时间戳列表
            ip_data['timestamps'] = valid_timestamps
            
            # 检查是否超过限制
            if len(valid_timestamps) >= max_requests:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'You have exceeded the rate limit of {max_requests} requests per {window_seconds} seconds'
                }), 429
            
            # 添加当前请求的时间戳
            ip_data['timestamps'].append(current_time)
            ip_data['count'] = len(ip_data['timestamps'])
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator