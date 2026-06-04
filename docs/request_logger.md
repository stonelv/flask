# Flask Request Logger 扩展

Flask Request Logger 是一个轻量级扩展，提供结构化 JSON 访问日志和 Request ID 支持。

## 功能特性

- 为每个请求生成唯一的 Request ID（UUIDv4 格式）
- 在响应头中注入 Request ID
- 记录结构化 JSON 访问日志
- 支持多种配置选项

## 安装

该扩展已集成到 Flask 中，无需额外安装。

## 启用与配置

### 基本用法

```python
from flask import Flask
from flask.request_logger import RequestLogger

app = Flask(__name__)

# 初始化扩展
logger = RequestLogger(app)

@app.route('/')
def index():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run()
```

### 使用 `init_app` 初始化

```python
from flask import Flask
from flask.request_logger import RequestLogger

app = Flask(__name__)

# 配置扩展
app.config['REQUEST_LOGGER_HEADER_NAME'] = 'X-Custom-Request-ID'
app.config['REQUEST_LOGGER_LOG_JSON'] = True

# 初始化扩展
logger = RequestLogger()
logger.init_app(app)

@app.route('/')
def index():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run()
```

## 配置选项

| 配置项 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| REQUEST_LOGGER_ENABLED | bool | True | 是否启用日志记录 |
| REQUEST_LOGGER_HEADER_NAME | str | "X-Request-ID" | 响应头中 Request ID 的名称 |
| REQUEST_LOGGER_LOG_JSON | bool | True | 是否以 JSON 格式记录日志 |
| REQUEST_LOGGER_LOG_FILE | str | None | 日志文件路径（None 表示使用标准输出） |
| REQUEST_LOGGER_LOG_LEVEL | str | "INFO" | 日志级别（DEBUG、INFO、WARNING、ERROR、CRITICAL） |

## 日志字段

当使用 JSON 格式记录日志时，每条日志包含以下字段：

| 字段 | 类型 | 描述 |
|------|------|------|
| timestamp | str | 日志记录时间（ISO 8601 格式） |
| method | str | HTTP 请求方法 |
| path | str | 请求路径 |
| status | int | 响应状态码 |
| duration_ms | int | 请求处理时长（毫秒） |
| request_id | str | 请求的唯一标识符 |
| remote_addr | str | 客户端 IP 地址 |

## 示例

### 启用扩展并配置自定义 header

```python
from flask import Flask
from flask.request_logger import RequestLogger

app = Flask(__name__)

# 配置自定义 Request ID 响应头
app.config['REQUEST_LOGGER_HEADER_NAME'] = 'X-App-Request-ID'

# 初始化扩展
logger = RequestLogger(app)

@app.route('/')
def index():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run()
```

### 配置日志文件

```python
from flask import Flask
from flask.request_logger import RequestLogger

app = Flask(__name__)

# 配置日志文件路径
app.config['REQUEST_LOGGER_LOG_FILE'] = '/var/log/flask/app.log'

# 初始化扩展
logger = RequestLogger(app)

@app.route('/')
def index():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run()
```

## 测试

运行单元测试：

```bash
pytest tests/test_request_logger.py
```

## 性能

- 日志记录使用标准库 `logging`，性能高效
- 文件写入使用 `FileHandler`，不会阻塞主线程
- Request ID 生成使用 `uuid.uuid4()`，性能良好
