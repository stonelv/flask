# Request Logger 扩展

Request Logger 是一个轻量级的 Flask 扩展，提供结构化 JSON 访问日志记录和 Request ID 支持，帮助开发者更好地跟踪和调试请求。

## 功能特性

- 为每个请求生成唯一的 Request ID（UUIDv4）
- 将 Request ID 注入到响应头中，便于请求追踪
- 记录结构化的 JSON 格式访问日志
- 支持多种配置选项
- 兼容 Flask 的应用工厂模式

## 安装

Request Logger 已包含在 Flask 核心中，无需额外安装。

## 基本使用

### 直接初始化

```python
from flask import Flask
from flask.request_logger import RequestLogger

app = Flask(__name__)
logger = RequestLogger(app)

@app.route('/')
def index():
    return 'Hello, World!'
```

### 应用工厂模式

```python
from flask import Flask
from flask.request_logger import RequestLogger

logger = RequestLogger()

def create_app():
    app = Flask(__name__)
    logger.init_app(app)
    
    @app.route('/')
    def index():
        return 'Hello, World!'
    
    return app
```

## 配置选项

可以通过 `app.config` 或在调用 `init_app` 时传递配置字典来配置 Request Logger：

| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| REQUEST_LOGGER_ENABLED | True | 是否启用日志记录 |
| REQUEST_LOGGER_HEADER_NAME | X-Request-ID | 响应头中 Request ID 的名称 |
| REQUEST_LOGGER_LOG_JSON | True | 是否以 JSON 格式记录日志 |
| REQUEST_LOGGER_LOG_FILE | None | 日志文件路径，None 表示使用标准输出 |
| REQUEST_LOGGER_LOG_LEVEL | INFO | 日志级别（DEBUG, INFO, WARNING, ERROR） |

### 配置示例

```python
app.config.update(
    REQUEST_LOGGER_ENABLED=True,
    REQUEST_LOGGER_HEADER_NAME='Custom-Request-ID',
    REQUEST_LOGGER_LOG_JSON=True,
    REQUEST_LOGGER_LOG_FILE='/var/log/flask/access.log',
    REQUEST_LOGGER_LOG_LEVEL='DEBUG'
)

# 或者在 init_app 中传递配置
logger.init_app(app, {
    'REQUEST_LOGGER_HEADER_NAME': 'Custom-Request-ID',
    'REQUEST_LOGGER_LOG_FILE': '/var/log/flask/access.log'
})
```

## 访问当前请求的 Request ID

Request Logger 提供了一个全局代理对象，可以在请求处理过程中访问当前请求的 Request ID：

```python
from flask.request_logger import request_id

@app.route('/')
def index():
    # 在日志中使用 request_id
    app.logger.info(f'Processing request with ID: {request_id}')
    return f'Request ID: {request_id}'
```

## 日志格式

### JSON 格式

当日志格式设置为 JSON 时，每个请求的日志包含以下字段：

```json
{
  "timestamp": "2023-01-01T12:00:00Z",
  "method": "GET",
  "path": "/",
  "status": 200,
  "duration_ms": 15,
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "remote_addr": "127.0.0.1"
}
```

### 文本格式

当日志格式设置为文本时，日志格式为：

```
GET / 200 15ms 123e4567-e89b-12d3-a456-426614174000 127.0.0.1
```

## 使用场景

### 1. 请求追踪

通过 Request ID，可以在分布式系统中追踪请求的完整生命周期，特别是在微服务架构中非常有用。

### 2. 性能监控

通过记录的 `duration_ms` 字段，可以分析请求的响应时间，识别性能瓶颈。

### 3. 访问分析

结构化的访问日志便于导入到日志分析工具中，进行访问模式分析和异常检测。

## 示例：并发请求测试

以下是一个简单的示例，展示如何测试并发请求并观察 Request ID：

```python
from flask import Flask, jsonify
from flask.request_logger import RequestLogger
import requests
import threading
import time

app = Flask(__name__)
logger = RequestLogger(app)

@app.route('/api/test')
def test():
    # 模拟一些处理时间
    time.sleep(0.1)
    return jsonify({
        'status': 'success',
        'message': 'Request processed'
    })

# 测试并发请求
def send_requests():
    def make_request():
        response = requests.get('http://localhost:5000/api/test')
        print(f"Status: {response.status_code}, Request ID: {response.headers.get('X-Request-ID')}")
    
    threads = []
    for _ in range(5):
        t = threading.Thread(target=make_request)
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()

if __name__ == '__main__':
    # 在实际测试中，先启动Flask服务器，然后在另一个进程中运行send_requests
    app.run(debug=True)
```

## 注意事项

- 当日志文件路径指定后，请确保应用程序有写入该路径的权限
- 在生产环境中，建议配置适当的日志轮转机制，避免日志文件过大
- Request Logger 依赖于 Flask 的请求上下文，因此只能在请求处理过程中使用
