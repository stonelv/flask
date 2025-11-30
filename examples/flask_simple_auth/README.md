# Flask-Simple-Auth

一个简单易用的Flask API key认证扩展。

## 功能特性

- 🔑 简单的API key认证
- 🔧 可配置的header名称
- 📋 支持静态key列表
- ⚙️ 支持自定义key验证函数
- 🎯 提供`@require_api_key`装饰器
- 🧪 完整的测试覆盖
- 📚 易于使用的API

## 安装

```bash
pip install flask-simple-auth
```

或者从源码安装：

```bash
cd examples/flask_simple_auth
pip install -e .
```

## 快速开始

### 基本使用

```python
from flask import Flask, jsonify
from flask_simple_auth import SimpleAuth, require_api_key

app = Flask(__name__)

# 配置静态API keys
app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"your-secret-key-1", "your-secret-key-2"}

# 初始化扩展
auth = SimpleAuth(app)

@app.route("/public")
def public():
    return jsonify({"message": "This is a public endpoint"})

@app.route("/protected")
@require_api_key()
def protected():
    return jsonify({"message": "This is a protected endpoint"})

if __name__ == "__main__":
    app.run(debug=True)
```

### 测试API

```bash
# 公共端点（无需认证）
curl http://localhost:5000/public

# 保护端点（需要API key）
curl -H "X-API-Key: your-secret-key-1" http://localhost:5000/protected

# 无效key会返回401错误
curl -H "X-API-Key: wrong-key" http://localhost:5000/protected
```

## 配置选项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `SIMPLE_AUTH_HEADER_NAME` | `"X-API-Key"` | API key的HTTP header名称 |
| `SIMPLE_AUTH_STATIC_KEYS` | `set()` | 静态API key集合 |
| `SIMPLE_AUTH_KEY_LOADER` | `None` | 自定义key验证函数 |
| `SIMPLE_AUTH_ERROR_MESSAGE` | `"Invalid or missing API key"` | 认证失败时的错误消息 |
| `SIMPLE_AUTH_ERROR_STATUS_CODE` | `401` | 认证失败时的HTTP状态码 |

## 高级用法

### 自定义Header名称

```python
app.config["SIMPLE_AUTH_HEADER_NAME"] = "Authorization"
app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"secret-key"}

# 现在需要使用自定义的header名称
curl -H "Authorization: secret-key" http://localhost:5000/protected
```

### 使用自定义Key验证函数

```python
def custom_key_loader(api_key):
    """自定义key验证逻辑"""
    # 检查key是否以特定前缀开头
    if api_key.startswith("user-") and api_key.endswith("-2024"):
        return True
    return False

app.config["SIMPLE_AUTH_KEY_LOADER"] = custom_key_loader

# 使用符合格式的key
curl -H "X-API-Key: user-alice-2024" http://localhost:5000/protected
```

### 自定义错误处理

```python
app.config["SIMPLE_AUTH_ERROR_MESSAGE"] = "访问被拒绝：无效的API密钥"
app.config["SIMPLE_AUTH_ERROR_STATUS_CODE"] = 403
```

### 在g对象中访问认证信息

```python
@app.route("/user-info")
@require_api_key()
def user_info():
    return jsonify({
        "authenticated": g.api_key_authenticated,
        "api_key": g.api_key
    })
```

## 完整示例

```python
from flask import Flask, jsonify, g
from flask_simple_auth import SimpleAuth, require_api_key

app = Flask(__name__)

# 配置认证
app.config.update(
    SIMPLE_AUTH_HEADER_NAME="X-API-Key",
    SIMPLE_AUTH_STATIC_KEYS={"admin-key", "user-key"},
    SIMPLE_AUTH_ERROR_MESSAGE="Access denied: Invalid API key",
    SIMPLE_AUTH_ERROR_STATUS_CODE=403
)

# 初始化扩展
auth = SimpleAuth(app)

# 公共端点
@app.route("/")
def index():
    return jsonify({
        "message": "Welcome to Flask Simple Auth API",
        "endpoints": {
            "public": "/",
            "admin": "/admin",
            "user": "/user"
        }
    })

# 管理端点
@app.route("/admin")
@require_api_key()
def admin():
    return jsonify({
        "message": "Admin area",
        "level": "admin",
        "authenticated_key": g.api_key
    })

# 用户端点
@app.route("/user")
@require_api_key()
def user():
    return jsonify({
        "message": "User area",
        "level": "user",
        "authenticated": g.api_key_authenticated
    })

if __name__ == "__main__":
    app.run(debug=True)
```

## API参考

### SimpleAuth类

```python
SimpleAuth(app=None)
```

Flask-Simple-Auth扩展类。

**参数：**
- `app` - Flask应用实例（可选，可以后续通过`init_app()`初始化）

**方法：**
- `init_app(app)` - 初始化扩展
- `get_api_key()` - 从当前请求中获取API key
- `validate_api_key(api_key)` - 验证API key
- `authenticate_request()` - 验证当前请求

### require_api_key装饰器

```python
@require_api_key(auth=None)
```

要求API key认证的装饰器。

**参数：**
- `auth` - SimpleAuth实例（可选，如果不提供则从当前应用获取）

## 测试

扩展包含完整的测试套件：

```bash
cd examples/flask_simple_auth
pytest -v
```

运行测试覆盖率：

```bash
pytest --cov=flask_simple_auth --cov-report=html
```

## 贡献

欢迎提交Issue和Pull Request来改进这个扩展。

## 许可证

MIT License - 详见LICENSE文件。