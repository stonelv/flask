from flask import Flask, jsonify
from rate_limit import rate_limit

app = Flask(__name__)

# 普通路由，没有速率限制
@app.route('/')
def index():
    return jsonify({
        'message': 'Welcome to the Flask Rate Limit Demo!',
        'endpoints': [
            '/api/data - Limited to 10 requests per minute',
            '/api/public - No rate limit'
        ]
    })

# 带有速率限制的API路由
@app.route('/api/data')
@rate_limit(max_requests=10, window_seconds=60)
def get_data():
    return jsonify({
        'data': 'This is a rate-limited API endpoint',
        'message': 'You can access this endpoint up to 10 times per minute'
    })

# 公开API，没有速率限制
@app.route('/api/public')
def public_api():
    return jsonify({
        'data': 'This is a public API endpoint with no rate limit'
    })

# 自定义速率限制的示例 - 5次请求每30秒
@app.route('/api/strict')
@rate_limit(max_requests=5, window_seconds=30)
def strict_api():
    return jsonify({
        'data': 'This is a strictly rate-limited API endpoint',
        'message': 'You can access this endpoint up to 5 times per 30 seconds'
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)