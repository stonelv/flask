"""
Flask 自定义速率限制装饰器示例
功能：限制同一 IP 地址在 1 分钟内最多只能访问 10 次该接口
"""

import time
from functools import wraps
from threading import Lock
from flask import Flask, request, jsonify

app = Flask(__name__)

# 内存存储：{ip: [(timestamp1, count), (timestamp2, count), ...]}
# 使用列表存储时间窗口内的请求记录
_request_records = {}
_records_lock = Lock()


def rate_limit(max_requests=10, window_seconds=60):
    """
    速率限制装饰器
    
    Args:
        max_requests: 时间窗口内允许的最大请求数（默认10次）
        window_seconds: 时间窗口大小，单位秒（默认60秒）
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取客户端 IP 地址
            ip = request.remote_addr
            
            # 如果通过代理，尝试获取真实 IP
            forwarded_for = request.headers.get('X-Forwarded-For')
            if forwarded_for:
                ip = forwarded_for.split(',')[0].strip()
            
            current_time = time.time()
            
            with _records_lock:
                # 初始化该 IP 的记录
                if ip not in _request_records:
                    _request_records[ip] = []
                
                # 清理过期的记录（超出时间窗口的请求）
                _request_records[ip] = [
                    req_time for req_time in _request_records[ip]
                    if current_time - req_time < window_seconds
                ]
                
                # 检查是否超出限制
                if len(_request_records[ip]) >= max_requests:
                    # 计算重置时间
                    oldest_request = min(_request_records[ip])
                    reset_time = int(oldest_request + window_seconds - current_time) + 1
                    
                    response = jsonify({
                        "error": "Too Many Requests",
                        "message": f"Rate limit exceeded. Try again in {reset_time} seconds.",
                        "limit": max_requests,
                        "window": window_seconds,
                        "remaining": 0
                    })
                    response.status_code = 429
                    
                    # 添加标准速率限制响应头
                    response.headers['X-RateLimit-Limit'] = str(max_requests)
                    response.headers['X-RateLimit-Remaining'] = '0'
                    response.headers['X-RateLimit-Reset'] = str(int(oldest_request + window_seconds))
                    response.headers['Retry-After'] = str(reset_time)
                    
                    return response
                
                # 记录当前请求
                _request_records[ip].append(current_time)
                
                # 计算剩余请求次数
                remaining = max_requests - len(_request_records[ip])
            
            # 执行被装饰的函数
            response = f(*args, **kwargs)
            
            # 如果是 Response 对象，添加速率限制头
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(max_requests)
                response.headers['X-RateLimit-Remaining'] = str(remaining)
            
            return response
        
        return decorated_function
    return decorator


# ============ 示例路由 ============

@app.route('/')
def index():
    """首页 - 无速率限制"""
    return jsonify({
        "message": "Welcome to Flask Rate Limit Example",
        "endpoints": {
            "/api/data": "GET - 速率限制：10次/分钟",
            "/api/login": "POST - 速率限制：5次/分钟"
        }
    })


@app.route('/api/data', methods=['GET'])
@rate_limit(max_requests=10, window_seconds=60)
def get_data():
    """
    获取数据接口 - 限制：1分钟内最多10次请求
    """
    return jsonify({
        "status": "success",
        "data": {
            "items": ["item1", "item2", "item3"],
            "timestamp": time.time()
        }
    })


@app.route('/api/login', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=60)
def login():
    """
    登录接口 - 限制：1分钟内最多5次请求（更严格的限制）
    """
    return jsonify({
        "status": "success",
        "message": "Login endpoint (simulated)"
    })


@app.route('/api/public', methods=['GET'])
@rate_limit(max_requests=100, window_seconds=60)
def public_data():
    """
    公开数据接口 - 限制：1分钟内最多100次请求（较宽松的限制）
    """
    return jsonify({
        "status": "success",
        "data": "This is public data with higher rate limit"
    })


# 错误处理器
@app.errorhandler(429)
def ratelimit_handler(e):
    """处理 429 错误"""
    return jsonify({
        "error": "Too Many Requests",
        "message": "Rate limit exceeded. Please try again later."
    }), 429


if __name__ == '__main__':
    print("=" * 60)
    print("Flask Rate Limit Example Server")
    print("=" * 60)
    print("\n可用端点：")
    print("  GET  /           - 首页（无限制）")
    print("  GET  /api/data   - 数据接口（10次/分钟）")
    print("  POST /api/login  - 登录接口（5次/分钟）")
    print("  GET  /api/public - 公开数据（100次/分钟）")
    print("\n测试命令示例：")
    print('  for i in {1..12}; do curl -s http://127.0.0.1:5001/api/data | jq; done')
    print("\n" + "=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5001)
