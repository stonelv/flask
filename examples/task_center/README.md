# Flask 后台任务中心

一个基于 Flask 的后台任务管理系统，提供异步任务执行、幂等性去重、进度跟踪和协作式取消功能。

## 功能特性

- **任务持久化**: 使用 SQLite 数据库存储任务状态和执行日志
- **状态管理**: 支持 PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED 五种状态
- **幂等性**: 通过 `idempotency_key` 实现请求去重，区分新建 vs 幂等命中
- **防重复执行**: 原子状态转换（claim_task）确保同一任务只执行一次
- **进度跟踪**: 支持 0-100 的进度百分比和阶段描述
- **协作式取消**: 任务可在运行中被取消
- **任务日志**: 持久化任务执行日志，支持按级别过滤和分页查询
- **结构化日志**: 使用 structlog 输出 JSON 格式日志
- **分页查询**: 支持按状态和类型过滤任务列表

## 安装

```bash
cd examples/task_center
python3 -m venv venv
source venv/bin/activate
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

**新建任务响应 (201):**
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
    },
    "is_new": true
}
```

**幂等命中响应 (200):**
```json
{
    "task": {
        "id": "existing-uuid",
        ...
    },
    "is_new": false
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

### 查询任务日志

```http
GET /api/tasks/<task_id>/logs?level=INFO&page=1&per_page=100
```

响应:
```json
{
    "task_id": "uuid-string",
    "logs": [
        {
            "id": 1,
            "task_id": "uuid-string",
            "level": "INFO",
            "message": "Task execution started",
            "extra": {"task_type": "sample_long_task"},
            "created_at": "2024-01-01T00:00:00"
        },
        {
            "id": 2,
            "task_id": "uuid-string",
            "level": "INFO",
            "message": "Progress: 20%",
            "extra": {"progress": 20, "stage": "initializing: Initializing resources"},
            "created_at": "2024-01-01T00:00:05"
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 100,
        "total": 10,
        "pages": 1
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
# 第一次请求 - 创建新任务，返回 201
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"type": "sample_long_task", "idempotency_key": "order-123"}'
# 响应: {"task": {...}, "is_new": true}

# 第二次相同请求 - 返回已存在的任务，返回 200，不会重复执行
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"type": "sample_long_task", "idempotency_key": "order-123"}'
# 响应: {"task": {...}, "is_new": false}
```

## 防重复执行机制

任务执行器通过以下机制确保同一任务只执行一次：

1. **内存级防重**: `_running_tasks` 集合跟踪正在执行的任务
2. **数据库原子 claim**: `claim_task()` 使用原子 UPDATE 确保只有一个执行器能获得执行权

```python
# claim_task 实现
def claim_task(self, task_id: str) -> bool:
    cursor = conn.execute(
        "UPDATE tasks SET status = ? WHERE id = ? AND status = ?",
        (TaskStatus.RUNNING.value, task_id, TaskStatus.PENDING.value),
    )
    return cursor.rowcount > 0  # 只有状态为 PENDING 时才返回 True
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
pip install pytest structlog
pytest tests/ -v
```

测试覆盖：
- 幂等性测试（新建 vs 命中）
- 并发幂等请求测试
- 重复 submit 防护测试
- 任务状态转换测试
- 取消任务测试
- 任务日志查询测试
- 参数校验测试

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
├── __init__.py      # 应用工厂、数据模型、TaskStore、数据库初始化
├── executor.py      # 任务执行器、取消令牌、示例任务
└── views.py         # REST API 端点

tests/
└── test_task_center.py  # 自动化测试
```

### 核心组件

- **Task**: 任务数据模型，包含状态、进度、结果等字段
- **TaskLog**: 任务日志模型，记录执行过程
- **TaskStore**: 任务持久化层，处理数据库 CRUD 操作
- **TaskExecutor**: 异步任务执行器，管理线程池和取消令牌
- **CancellationToken**: 协作式取消机制
- **CreateTaskResult**: 创建任务结果，区分新建 vs 幂等命中

### 数据库表

```sql
-- 任务表
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    progress INTEGER NOT NULL DEFAULT 0,
    stage TEXT NOT NULL DEFAULT '',
    payload TEXT,
    result TEXT,
    error TEXT,
    idempotency_key TEXT UNIQUE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- 任务日志表
CREATE TABLE task_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    extra TEXT,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
```

## 错误处理

所有错误响应都包含详细的错误信息：

```json
{
    "error": "Task not found: <task_id>"
}
```

```json
{
    "error": "Invalid status: INVALID. Valid values: PENDING, RUNNING, SUCCEEDED, FAILED, CANCELLED"
}
```
