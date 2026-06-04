# Flask-Simple-Auth Example Application

from flask import Flask, jsonify, g
from flask_simple_auth import SimpleAuth, require_api_key

# 创建Flask应用
app = Flask(__name__)

# 配置API key认证
app.config.update(
    SIMPLE_AUTH_HEADER_NAME="X-API-Key",  # API key的header名称
    SIMPLE_AUTH_STATIC_KEYS={
        "demo-key-123",
        "admin-key-456",
        "user-key-789"
    },
    SIMPLE_AUTH_ERROR_MESSAGE="访问被拒绝：无效的API密钥",
    SIMPLE_AUTH_ERROR_STATUS_CODE=401
)

# 初始化SimpleAuth扩展
auth = SimpleAuth(app)

# 公共端点 - 无需认证
@app.route("/")
def index():
    """首页 - 公开访问"""
    return jsonify({
        "message": "欢迎使用Flask Simple Auth示例",
        "endpoints": {
            "public": "/",
            "status": "/status",
            "user_info": "/user-info",
            "admin_panel": "/admin"
        },
        "usage": {
            "header": app.config["SIMPLE_AUTH_HEADER_NAME"],
            "valid_keys": list(app.config["SIMPLE_AUTH_STATIC_KEYS"])
        }
    })

# 状态端点 - 公开访问
@app.route("/status")
def status():
    """系统状态 - 公开访问"""
    return jsonify({
        "status": "运行正常",
        "auth_enabled": True,
        "header_name": app.config["SIMPLE_AUTH_HEADER_NAME"]
    })

# 用户信息端点 - 需要认证
@app.route("/user-info")
@require_api_key()
def user_info():
    """用户信息 - 需要API key认证"""
    return jsonify({
        "message": "用户信息获取成功",
        "authenticated": g.api_key_authenticated,
        "api_key": g.api_key,
        "access_level": "user"
    })

# 管理面板端点 - 需要认证
@app.route("/admin")
@require_api_key()
def admin_panel():
    """管理面板 - 需要API key认证"""
    return jsonify({
        "message": "管理面板访问成功",
        "authenticated": g.api_key_authenticated,
        "api_key": g.api_key,
        "access_level": "admin",
        "features": ["用户管理", "系统配置", "日志查看"]
    })

# 自定义key验证函数示例
@app.route("/custom-auth")
def custom_auth_example():
    """演示自定义key验证函数"""
    def custom_key_loader(api_key):
        """自定义key验证：验证key格式"""
        return api_key.startswith("custom-") and len(api_key) > 10
    
    # 临时设置自定义key loader
    original_loader = app.config.get("SIMPLE_AUTH_KEY_LOADER")
    app.config["SIMPLE_AUTH_KEY_LOADER"] = custom_key_loader
    
    # 创建临时路由来演示
    @app.route("/custom-endpoint")
    @require_api_key()
    def custom_endpoint():
        return jsonify({
            "message": "自定义认证成功",
            "api_key": g.api_key
        })
    
    # 恢复原始配置
    app.config["SIMPLE_AUTH_KEY_LOADER"] = original_loader
    
    return jsonify({
        "message": "自定义认证示例",
        "usage": "访问 /custom-endpoint 并使用格式为 'custom-xxx' 的key",
        "example": "curl -H 'X-API-Key: custom-valid-key' http://localhost:5000/custom-endpoint"
    })

# 错误处理
@app.errorhandler(401)
def unauthorized(error):
    """处理401未授权错误"""
    return jsonify({
        "error": "未授权访问",
        "message": str(error),
        "hint": f"请在请求头中添加: {app.config['SIMPLE_AUTH_HEADER_NAME']}: your-api-key"
    }), 401

@app.errorhandler(404)
def not_found(error):
    """处理404未找到错误"""
    return jsonify({
        "error": "页面未找到",
        "message": "请求的端点不存在"
    }), 404

if __name__ == "__main__":
    print("Flask Simple Auth 示例应用启动!")
    print("可用的API key:")
    for key in app.config["SIMPLE_AUTH_STATIC_KEYS"]:
        print(f"  - {key}")
    print(f"Header名称: {app.config['SIMPLE_AUTH_HEADER_NAME']}")
    print("\n测试命令:")
    print('curl http://localhost:5000/')
    print('curl -H "X-API-Key: demo-key-123" http://localhost:5000/user-info')
    print('curl -H "X-API-Key: admin-key-456" http://localhost:5000/admin')
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5000)