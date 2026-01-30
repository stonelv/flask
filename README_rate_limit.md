# 自定义速率限制装饰器 @rate_limit

本项目实现了一个自定义的Flask路由装饰器 `@rate_limit`，用于API接口的速率限制。

## 功能特点

- 限制同一IP地址在指定时间窗口内的访问次数
- 默认限制：1分钟内最多10次访问
- 超出限制时返回HTTP 429状态码和JSON提示信息
- 使用内存字典手动实现计数和时间窗口逻辑，不依赖第三方扩展
- 按路由端点分别计数，不同端点互不影响

## 文件说明

### rate_limit.py
包含自定义速率限制装饰器的实现，主要特点：
- 使用内存字典存储每个IP的访问记录
- 按IP和路由端点分别计数
- 自动清理超出时间窗口的记录
- 支持自定义最大请求数和时间窗口

### app_example.py
示例Flask应用，展示了如何使用@rate_limit装饰器：
- `/api/data` - 默认限制（10次/分钟）
- `/api/strict` - 严格限制（5次/30秒）
- `/api/public` - 无限制的公开端点

### test_rate_limit_simple.py
测试脚本，用于验证速率限制功能：
- 测试无限制端点
- 测试默认限制端点
- 测试严格限制端点
- 验证超出限制时的响应

## 使用方法

1. 导入装饰器：
```python
from rate_limit import rate_limit
```

2. 应用到路由：
```python
@app.route('/api/data')
@rate_limit(max_requests=10, window_seconds=60)
def get_data():
    return jsonify({'data': 'This is a rate-limited endpoint'})
```

## 测试结果

测试显示装饰器工作正常：
- 无限制端点可以无限访问
- 默认限制端点在10次请求后返回429状态码
- 严格限制端点在5次请求后返回429状态码
- 超出限制时返回正确的JSON错误信息

## 注意事项

- 速率限制数据存储在内存中，服务器重启后会重置
- 生产环境中可能需要考虑使用Redis等外部存储
- 装饰器按IP和路由端点分别计数，不同端点互不影响