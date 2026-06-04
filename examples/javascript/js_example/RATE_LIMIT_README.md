# Flask 速率限制装饰器示例

这是一个自定义的 Flask 路由装饰器 `@rate_limit`，用于实现 API 接口的速率限制功能。

## 功能特性

- 基于 IP 地址的速率限制
- 可配置的最大请求数和时间窗口
- 超出限制时返回 HTTP 429 状态码和 JSON 错误信息
- 使用内存字典手动实现计数和时间窗口逻辑
- 不依赖 Flask-Limiter 等第三方扩展

## 使用方法

### 基本用法

```python
from flask import Flask, jsonify
from rate_limit_example import rate_limit

app = Flask(__name__)

@app.route("/api/test", methods=["GET"])
@rate_limit(max_calls=10, period=60)
def test_api():
    return jsonify({"message": "Hello, World!", "status": "success"})
```

### 参数说明

- `max_calls`: 时间窗口内允许的最大请求数（默认：10）
- `period`: 时间窗口长度，单位为秒（默认：60）

### 示例

运行示例应用：

```bash
python rate_limit_example.py
```

运行测试脚本：

```bash
python test_rate_limit.py
```

## API 端点

### `/api/test` (GET)
- 受速率限制保护
- 1分钟内最多访问10次
- 返回：`{"message": "Hello, World!", "status": "success"}`

### `/api/data` (GET, POST)
- 受速率限制保护
- 1分钟内最多访问10次
- GET 返回：`{"data": [1, 2, 3, 4, 5], "status": "success"}`
- POST 接收 JSON 数据并返回

### `/api/info` (GET)
- 不受速率限制保护
- 返回使用说明

## 速率限制响应

当超出速率限制时，返回：

```json
{
  "error": "Too many requests",
  "message": "Rate limit exceeded. Maximum 10 requests per 60 seconds."
}
```

HTTP 状态码：429

## 实现原理

装饰器使用内存字典 `rate_limit_data` 来跟踪每个 IP 的请求计数：

```python
rate_limit_data = {
    "192.168.1.1": {
        "count": 5,
        "start_time": 1704067200.0
    }
}
```

每次请求时：
1. 获取客户端 IP 地址
2. 检查是否在时间窗口内
3. 更新计数器或重置时间窗口
4. 如果超出限制，返回 429 错误

## 注意事项

- 使用内存存储，重启应用后计数会重置
- 适用于单进程应用，多进程环境需要使用共享存储
- 在生产环境中，建议使用 Redis 等分布式缓存替代内存字典
