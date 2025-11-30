# Flask Simple Auth

一个简单的 Flask 扩展，用于 API key 验证。

## 特性

- 支持从 HTTP header 或查询参数中获取 API key
- 支持静态 API keys 列表验证
- 支持自定义 key_loader 函数进行动态验证
- 提供 `@require_api_key` 装饰器保护路由
- 支持可选验证（optional=True）
- 可配置的错误消息和 realm

## 安装

```bash
pip install flask_simple_auth
```

## 快速开始

### 基本使用

```python
from flask import Flask, jsonify
from flask_simple_auth import SimpleAuth, require_api_key

app = Flask(__name__)

# 配置静态 API keys
app.config['SIMPLE_AUTH_KEYS'] = ['key1', 'key2', 'key3']

# 初始化扩展
auth = SimpleAuth(app)

@app.route('/protected')
@require_api_key
def protected():
    return jsonify({'message': '这是一个受保护的端点'})

@app.route('/public')
def public():
    return jsonify({'message': '这是一个公共端点'})

if __name__ == '__main__':
    app.run(debug=True)
```

### 使用应用工厂模式

```python
from flask import Flask, jsonify
from flask_simple_auth import SimpleAuth, require_api_key

def create_app():
    app = Flask(__name__)
    
    # 配置
    app.config['SIMPLE_AUTH_KEYS'] = ['key1', 'key2', 'key3']
    
    # 初始化扩展
    auth = SimpleAuth()
    auth.init_app(app)
    
    @app.route('/protected')
    @require_api_key
    def protected():
        return jsonify({'message': '这是一个受保护的端点'})
    
    return app
```

## 配置选项

| 配置项 | 默认值 | 描述 |
|--------|--------|------|
| `SIMPLE_AUTH_HEADER_NAME` | `X-API-Key` | 包含 API key 的 HTTP header 名称 |
| `SIMPLE_AUTH_KEYS` | `[]` | 静态 API keys 列表 |
| `SIMPLE_AUTH_REALM` | `Protected Area` | HTTP WWW-Authenticate realm |
| `SIMPLE_AUTH_ERROR_MESSAGE` | `Invalid or missing API key` | 认证失败时的错误消息 |
| `SIMPLE_AUTH_KEY_LOADER` | `None` | 自定义 key_loader 函数 |

## 使用方法

### 1. 使用静态 API keys

```python
app = Flask(__name__)
app.config['SIMPLE_AUTH_KEYS'] = ['key1', 'key2', 'key3']
auth = SimpleAuth(app)
```

### 2. 使用自定义 key_loader

```python
app = Flask(__name__)

def key_loader(api_key):
    # 这里可以实现从数据库或其他存储中验证 API key
    # 返回 True 表示有效，False 表示无效
    return api_key.startswith('valid_')

app.config['SIMPLE_AUTH_KEY_LOADER'] = key_loader
auth = SimpleAuth(app)
```

### 3. 自定义 header 名称

```python
app = Flask(__name__)
app.config['SIMPLE_AUTH_HEADER_NAME'] = 'Authorization'
app.config['SIMPLE_AUTH_KEYS'] = ['key1', 'key2', 'key3']
auth = SimpleAuth(app)
```

### 4. 可选验证

```python
@app.route('/optional')
@require_api_key(optional=True)
def optional():
    # 无论是否有 API key 都会执行此函数
    return jsonify({'message': '这是一个可选保护的端点'})
```

## API 使用示例

### 使用 header 传递 API key

```bash
curl -H "X-API-Key: key1" http://localhost:5000/protected
```

### 使用查询参数传递 API key

```bash
curl "http://localhost:5000/protected?api_key=key1"
```

### 使用自定义 header

```bash
curl -H "Authorization: key1" http://localhost:5000/protected
```

## 测试

运行测试：

```bash
pytest
```

## 许可证

MIT License