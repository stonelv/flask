# Flask 后台任务中心

一个基于 Flask 的后台任务管理系统，提供异步任务执行、幂等性去重、进度跟踪和协作式取消功能。

## 功能特性

- **任务持久化**: 使用 SQLite 数据库存储任务状态
- **状态管理**: 支持 PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED 五种状态
- **幂等性**: 通过 idempotency_key 实现请求去重
- **进度跟踪**: 支持 0-100 的进度百分比和阶段描述
- **协作式取消**: 任务可在运行中被取消
- **结构化日志**: 使用 structlog 输出 JSON 格式日志
- **分页查询**: 支持按状态和类型过滤任务列表

## 安装

```bash
cd examples/task_center
pip install -e .
```

## 运行

```bash
# 初始化数据库
flask --app task_center init-db

# 启动开发服务器
flask --app task_center run --debug
```

## API 接口

### 创建任务

```http
POST /api/tasks
Content-Type: application/json

{
    "type": "sample_long_task",
    "payload": {"key": "value"},
    "idempotency_key": "unique-request-id"
}
```

响应:
```json
{
    "task": {
        "id": "uuid-string",
        "type": "sample_long_task",
        "status": "PENDING",
        "progress": 0,
        "stage": "initialized",
        "payload": {"key": "value"},
        "result": null,
        "error": null,
        "idempotency_key": "unique-request-id",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
    }
}
```

### 查询任务

```http
GET /api/tasks/<task_id>
```

响应:
```json
{
    "task": {
        "id": "uuid-string",
        "type": "sample_long_task",
        "status": "RUNNING",
        "progress": 45,
        "stage": "processing: Processing data",
        "payload": {"key": "value"},
        "result": null,
        "error": null,
        "idempotency_key": "unique-request-id",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:30"
    }
}
```

### 列表任务

```http
GET /api/tasks?status=PENDING&type=sample_long_task&page=1&per_page=20
```

响应:
```json
{
    "tasks": [...],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 100,
        "pages": 5
    }
}
```

### 取消任务

```http
POST /api/tasks/<task_id>/cancel
```

响应:
```json
{
    "task": {
        "id": "uuid-string",
        "status": "CANCELLED",
        ...
    }
}
```

## 任务状态

| 状态 | 说明 |
|------|------|
| PENDING | 任务已创建，等待执行 |
| RUNNING | 任务正在执行中 |
| SUCCEEDED | 任务执行成功 |
| FAILED | 任务执行失败 |
| CANCELLED | 任务已被取消 |

## 幂等性

使用 `idempotency_key` 确保相同请求不会重复执行：

```bash
# 第一次请求 - 创建新任务
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"type": "sample_long_task", "idempotency_key": "order-123"}'

# 第二次相同请求 - 返回已存在的任务
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"type": "sample_long_task", "idempotency_key": "order-123"}'
```

## 示例长任务

内置的 `sample_long_task` 会执行 10-30 秒，分阶段更新进度：

1. **initializing** (0-20%): 初始化资源
2. **processing** (20-40%): 处理数据
3. **validating** (40-60%): 验证结果
4. **finalizing** (60-80%): 完成输出
5. **cleanup** (80-100%): 清理资源

## 自定义任务处理器

```python
from task_center import create_app, get_task_executor
from task_center.executor import TaskExecutor

def my_task_handler(payload, progress_callback, cancellation_token):
    for i in range(100):
        if cancellation_token.is_cancelled:
            raise TaskCancelledError("my_task")
        
        progress_callback(i + 1, f"Processing item {i + 1}")
        time.sleep(0.1)
    
    return {"processed": 100}

app = create_app()
executor = app.extensions["task_executor"]
executor.register_handler("my_task", my_task_handler)
```

## 运行测试

```bash
cd examples/task_center
pip install pytest
pytest tests/ -v
```

## 日志格式

日志以 JSON 格式输出，便于日志聚合和分析：

```json
{
    "event": "task_started",
    "task_id": "uuid-string",
    "task_type": "sample_long_task",
    "level": "info",
    "timestamp": "2024-01-01T00:00:00.000000Z"
}
```

## 架构说明

```
task_center/
├── __init__.py      # 应用工厂、数据模型、TaskStore
├── executor.py      # 任务执行器、取消令牌、示例任务
└── views.py         # REST API 端点

tests/
└── test_task_center.py  # 自动化测试
```

### 核心组件

- **Task**: 任务数据模型，包含状态、进度、结果等字段
- **TaskStore**: 任务持久化层，处理数据库 CRUD 操作
- **TaskExecutor**: 异步任务执行器，管理线程池和取消令牌
- **CancellationToken**: 协作式取消机制
