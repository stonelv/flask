# Task Center - 后台任务中心

一个可复用的 Flask 异步任务中心，支持任务创建、查询、取消、幂等去重、进度上报和日志可观测。

## 功能特性

- ✅ **任务持久化** - SQLite 数据库存储，支持 PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED 状态
- ✅ **幂等性保证** - 按 `idempotency_key` 去重，并发安全
- ✅ **RESTful API** - 完整的 CRUD 操作接口
- ✅ **异步执行器** - 基于 asyncio 的任务执行器
- ✅ **协作式取消** - 支持取消正在运行的任务
- ✅ **进度上报** - 分阶段进度更新（0-100%）
- ✅ **结构化日志** - JSON 格式的日志输出
- ✅ **Web 界面** - 简单易用的任务管理界面
- ✅ **自动化测试** - 覆盖幂等性、取消、状态转换、列表过滤等

## 快速开始

### 安装依赖

```bash
cd examples/task_center
uv pip install -e ".[dev]"
```

### 启动应用

```bash
# 开发模式
flask --app task_center run --debug

# 或使用 ASGI 服务器（支持异步）
uv pip install uvicorn
uvicorn --factory task_center:create_app --reload
```

访问 http://localhost:5000 查看 Web 界面

## API 文档

### 创建任务

```bash
POST /api/tasks
Content-Type: application/json

{
    "type": "example_long_task",
    "idempotency_key": "unique-key-123",  # 可选，用于幂等去重
    "payload": {                          # 可选，任务参数
        "input": "data"
    }
}
```

**响应：**
- `201 Created` - 新任务创建成功
- `200 OK` - 幂等键已存在，返回已有任务
- `400 Bad Request` - 请求参数错误

### 查询单个任务

```bash
GET /api/tasks/<task_id>
```

### 查询任务列表

```bash
GET /api/tasks?page=1&per_page=20&status=RUNNING&type=example_long_task
```

**查询参数：**
- `page` - 页码（默认：1）
- `per_page` - 每页数量（默认：20）
- `status` - 按状态过滤（PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED）
- `type` - 按任务类型过滤

### 取消任务

```bash
POST /api/tasks/<task_id>/cancel
```

## 任务模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | 任务 UUID |
| type | String(100) | 任务类型 |
| status | Enum | 任务状态 |
| progress | Integer | 进度 0-100 |
| stage | String(100) | 当前阶段 |
| payload | JSON | 任务输入参数 |
| result | JSON | 任务结果 |
| error | Text | 错误信息 |
| idempotency_key | String(100) | 幂等键（唯一） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |
| started_at | DateTime | 开始时间 |
| completed_at | DateTime | 完成时间 |

## 运行测试

```bash
cd examples/task_center
pytest tests/ -v
```

## 注册自定义任务

```python
from task_center.executor import register_task_type

async def my_custom_task(payload, progress_callback, cancel_event):
    # 任务逻辑
    await progress_callback(50, "processing")
    
    if cancel_event.is_set():
        raise TaskCancelledError()
    
    return {"result": "success"}

register_task_type("my_custom_task", my_custom_task)
```

## 项目结构

```
task_center/
├── task_center/
│   ├── __init__.py      # 应用工厂
│   ├── api.py           # API 路由
│   ├── database.py      # 数据库模型
│   ├── executor.py      # 任务执行器
│   └── templates/
│       └── index.html   # Web 界面
├── tests/
│   ├── conftest.py      # pytest 配置
│   └── test_tasks.py    # 测试用例
├── pyproject.toml       # 项目配置
└── README.md            # 本文档
```

## 日志格式

应用输出结构化 JSON 日志：

```json
{
    "timestamp": "2024-01-01 12:00:00,000",
    "level": "INFO",
    "logger": "task_center.executor",
    "message": "Starting task abc123"
}
```

## 注意事项

1. **生产环境**：请使用 PostgreSQL/MySQL 替代 SQLite，并配置合适的连接池
2. **分布式部署**：当前实现使用内存中的 asyncio 任务，分布式场景请考虑使用 Celery/RQ
3. **任务持久化**：重启后待执行任务需要重新调度
4. **并发控制**：建议根据服务器资源限制并发任务数
