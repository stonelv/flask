# Flask Simple Auth

一个简单的 Flask 扩展，用于 API Key 验证。

## 功能特点

- 支持配置自定义请求头名称
- 支持静态 API Key 列表
- 支持自定义 Key Loader 函数（动态验证）
- 提供 `@require_api_key` 装饰器，轻松保护路由

## 安装

```bash
pip install flask-simple-auth
```

## 使用方法

### 1. 初始化扩展

```python
from flask import Flask
from flask_simple_auth import simple_auth

app = Flask(__name__)

# 配置 API Key
app.config['SIMPLE_AUTH_API_KEYS'] = ['your_api_key_here']

# 初始化扩展
simple_auth.init_app(app)
```

或者使用工厂模式：

```python
from flask import Flask
from flask_simple_auth import FlaskSimpleAuth

auth = FlaskSimpleAuth()

def create_app():
    app = Flask(__name__)
    app.config['SIMPLE_AUTH_API_KEYS'] = ['your_api_key_here']
    auth.init_app(app)
    return app
```

### 2. 保护路由

使用 `@require_api_key` 装饰器保护需要验证的路由：

```python
from flask import jsonify
from flask_simple_auth import simple_auth

@app.route('/protected')
@simple_auth.require_api_key
def protected_route():
    return jsonify({'message': 'Access granted'}), 200
```

### 3. 配置选项

#### 静态 API Key 列表

配置静态 API Key 列表，客户端需要提供其中一个 Key 才能访问受保护的路由：

```python
app.config['SIMPLE_AUTH_API_KEYS'] = ['key1', 'key2', 'key3']
```

#### 自定义请求头

默认使用 `X-API-Key` 作为请求头名称，你可以配置自定义名称：

```python
app.config['SIMPLE_AUTH_API_KEY_HEADER'] = 'Authorization'
```

#### 自定义 Key Loader

如果你需要动态验证 API Key（例如从数据库中查询），可以配置 Key Loader 函数：

```python
def api_key_loader(api_key):
    # 这里可以实现从数据库或其他地方验证 API Key
    # 例如：return User.query.filter_by(api_key=api_key).first() is not None
    return api_key == 'dynamic_key'

app.config['SIMPLE_AUTH_API_KEY_LOADER'] = api_key_loader
```

Key Loader 函数接收 API Key 作为参数，并返回布尔值表示验证是否通过。

### 4. 客户端请求

客户端需要在请求头中提供 API Key 才能访问受保护的路由：

```bash
curl -H "X-API-Key: your_api_key_here" http://localhost:5000/protected
```

如果使用自定义请求头：

```bash
curl -H "Authorization: your_api_key_here" http://localhost:5000/protected
```

## 错误响应

- **401 Missing API Key**：请求头中缺少 API Key
- **403 Invalid API Key**：提供的 API Key 无效
- **500 Internal Server Error**：Key Loader 函数执行出错

## 测试

运行单元测试：

```bash
pytest tests/test_flask_simple_auth.py
```
