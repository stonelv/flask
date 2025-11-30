# Flask Simple Auth Extension

一个简单的 Flask 扩展，用于 API Key 验证。

## 功能特性

- 支持配置静态 API Keys
- 支持自定义 API Key 验证函数
- 支持配置 API Key 所在的请求头
- 提供 `@require_api_key` 装饰器保护路由

## 安装

将扩展文件 `simple_auth.py` 放置在 Flask 项目的 `src/flask` 目录下。

## 配置

### 静态 API Keys

在 Flask 应用配置中设置静态 API Keys：

```python
app.config["SIMPLE_AUTH_API_KEYS"] = ["api_key_1", "api_key_2"]
```

### API Key 头

配置 API Key 所在的请求头（默认：`X-API-Key`）：

```python
app.config["SIMPLE_AUTH_API_KEY_HEADER"] = "Custom-API-Key"
```

## 使用方法

### 初始化扩展

#### 方法一：在创建应用时初始化

```python
from flask import Flask
from flask.simple_auth import SimpleAuth

app = Flask(__name__)
app.config["SIMPLE_AUTH_API_KEYS"] = ["valid_key"]

auth = SimpleAuth(app)
```

#### 方法二：使用 `init_app` 方法初始化

```python
from flask import Flask
from flask.simple_auth import SimpleAuth

app = Flask(__name__)
app.config["SIMPLE_AUTH_API_KEYS"] = ["valid_key"]

auth = SimpleAuth()
auth.init_app(app)
```

### 保护路由

使用 `@require_api_key` 装饰器保护需要 API Key 验证的路由：

```python
from flask import jsonify

@app.route("/protected")
@auth.require_api_key
 def protected_route():
    return jsonify({"message": "Access granted"})
```

### 自定义 API Key 验证

使用 `@key_loader_callback` 装饰器注册自定义 API Key 验证函数：

```python
@auth.key_loader_callback
 def custom_key_loader(api_key):
    # 在这里实现自定义的 API Key 验证逻辑
    # 例如：从数据库中查询 API Key 是否有效
    return api_key == "custom_valid_key"
```

## 测试

运行单元测试：

```bash
pytest tests/test_simple_auth.py
```

## 错误处理

- 当 API Key 缺失时，返回 401 状态码和 "API key is missing" 错误信息
- 当 API Key 无效时，返回 403 状态码和 "Invalid API key" 错误信息

## 示例

### 完整示例

```python
from flask import Flask, jsonify
from flask.simple_auth import SimpleAuth

app = Flask(__name__)

# 配置静态 API Keys
app.config["SIMPLE_AUTH_API_KEYS"] = ["static_key_1", "static_key_2"]
# 配置 API Key 头
app.config["SIMPLE_AUTH_API_KEY_HEADER"] = "X-API-Key"

# 初始化扩展
auth = SimpleAuth(app)

# 注册自定义 API Key 验证函数
@auth.key_loader_callback
 def custom_key_loader(api_key):
    return api_key == "custom_key"

# 受保护的路由（使用静态 API Keys 验证）
@app.route("/protected_static")
@auth.require_api_key
 def protected_static():
    return jsonify({"message": "Access granted using static API key"})

# 受保护的路由（使用自定义验证函数）
@app.route("/protected_custom")
@auth.require_api_key
 def protected_custom():
    return jsonify({"message": "Access granted using custom API key"})

if __name__ == "__main__":
    app.run()
```

### 测试示例

使用 curl 测试受保护的路由：

1. 使用有效的静态 API Key：

```bash
curl -H "X-API-Key: static_key_1" http://localhost:5000/protected_static
```

响应：
```json
{"message": "Access granted using static API key"}
```

2. 使用有效的自定义 API Key：

```bash
curl -H "X-API-Key: custom_key" http://localhost:5000/protected_custom
```

响应：
```json
{"message": "Access granted using custom API key"}
```

3. 使用无效的 API Key：

```bash
curl -H "X-API-Key: invalid_key" http://localhost:5000/protected_static
```

响应：
```
{"error": "Invalid API key"}
```

4. 不提供 API Key：

```bash
curl http://localhost:5000/protected_static
```

响应：
```
{"error": "API key is missing"}
```