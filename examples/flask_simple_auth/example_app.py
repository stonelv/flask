"""
Flask Simple Auth 示例应用
"""

from flask import Flask, jsonify, request
from flask_simple_auth import SimpleAuth, require_api_key

# 创建应用
app = Flask(__name__)

# 配置静态 API keys
app.config['SIMPLE_AUTH_KEYS'] = ['api-key-1', 'api-key-2', 'api-key-3']

# 初始化扩展
auth = SimpleAuth(app)

# 公共端点
@app.route('/')
def index():
    return jsonify({
        'message': 'Flask Simple Auth 示例应用',
        'endpoints': {
            'public': '/public',
            'protected': '/protected',
            'optional': '/optional',
            'profile': '/profile'
        }
    })

# 公共端点
@app.route('/public')
def public():
    return jsonify({'message': '这是一个公共端点，不需要 API key'})

# 受保护的端点
@app.route('/protected')
@require_api_key
def protected():
    return jsonify({'message': '这是一个受保护的端点，需要有效的 API key'})

# 可选保护的端点
@app.route('/optional')
@require_api_key(optional=True)
def optional():
    api_key = auth.get_api_key_from_request()
    if api_key:
        return jsonify({
            'message': '这是一个可选保护的端点，您提供了 API key',
            'api_key': api_key
        })
    else:
        return jsonify({'message': '这是一个可选保护的端点，您没有提供 API key'})

# 用户资料端点
@app.route('/profile')
@require_api_key
def profile():
    api_key = auth.get_api_key_from_request()
    
    # 模拟根据 API key 获取用户信息
    user_profiles = {
        'api-key-1': {'name': '用户1', 'email': 'user1@example.com'},
        'api-key-2': {'name': '用户2', 'email': 'user2@example.com'},
        'api-key-3': {'name': '用户3', 'email': 'user3@example.com'},
    }
    
    profile = user_profiles.get(api_key, {'name': '未知用户', 'email': 'unknown@example.com'})
    return jsonify({
        'message': '您的用户资料',
        'profile': profile
    })

if __name__ == '__main__':
    app.run(debug=True)