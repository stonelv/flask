# 后台任务中心 (Task Center)

一套可复用的异步任务管理系统，提供任务创建、查询、取消、幂等去重、进度上报与日志可观测等能力。

## 功能特性

- **任务生命周期管理**: PENDING → RUNNING → SUCCEEDED/FAILED/CANCELLED
- **幂等性控制**: 通过 `idempotency_key` 防止重复执行，支持多进程并发安全
- **进度追踪**: 实时进度上报 (0-100) 和阶段描述
- **协作式取消**: 支持安全地取消运行中任务
- **结构化日志**: 完整的任务执行日志记录，包含固定字段（task_id, type, status, progress, stage, elapsed_ms）
- **统一 API 响应**: 所有接口返回统一格式 `{code, message, data, request_id}`
- **RESTful API**: 简洁的 HTTP 接口

## 项目结构

```
task_center/
├── __init__.py          # 包入口
├── models.py            # 数据模型和数据库操作
├── executor.py          # 异步任务执行器
├── service.py           # 业务逻辑层（幂等控制）
├── app.py               # Flask API 应用
├── tests/               # 测试目录
│   ├── __init__.py
│   ├── conftest.py      # 测试配置和fixtures
│   ├── test_models.py   # 模型测试
│   ├── test_executor.py # 执行器测试
│   ├── test_service.py  # 服务层测试
│   └── test_api.py      # API测试
└── README.md            # 本文档
```

## 快速开始

### 1. 安装依赖

```bash
# 确保已安装 Flask
pip install flask

# 或使用项目依赖
pip install -e .
```

### 2. 启动服务

```bash
# 方式1: 直接运行
python -m task_center.app

# 方式2: 使用 Flask CLI
export FLASK_APP=task_center.app
flask run --port 5000
```

服务将在 `http://localhost:5000` 启动。

### 3. 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `TASK_CENTER_DB` | SQLite 数据库路径 | `tasks.db` |
| `TASK_CENTER_MAX_WORKERS` | 最大并发工作线程数 | `5` |

## API 文档

### 统一响应格式

所有 API 响应都采用统一的 JSON 格式：

```json
{
  "code": 0,              // 业务状态码，0 表示成功
  "message": "success",   // 状态描述
  "data": { ... },        // 业务数据（可选）
  "request_id": "uuid"    // 请求追踪 ID
}
```

### 错误码说明

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| 0 | 200 | 成功 |
| 400000 | 400 | 请求参数错误 |
| 400001 | 400 | 参数验证失败 |
| 400002 | 400 | 缺少必需参数 |
| 400003 | 400 | 任务无法取消 |
| 404001 | 404 | 任务不存在 |
| 409001 | 409 | 幂等键冲突（返回已存在任务） |
| 500000 | 500 | 服务器内部错误 |
| 500001 | 500 | 数据库错误 |

### 健康检查

```http
GET /health
```

**响应示例:**
```json
{
  "code": 0,
  "message": "healthy",
  "data": {
    "timestamp": "2024-01-01T12:00:00"
  },
  "request_id": "uuid-string"
}
```

### 创建任务

```http
POST /api/tasks
Content-Type: application/json

{
  "type": "long_running_task",
  "payload": {
    "duration": 20,
    "items": 10
  },
  "idempotency_key": "unique_key_123"  // 可选，用于幂等控制
}
```

**响应示例:**
```json
{
  "code": 0,
  "message": "Task created successfully",
  "data": {
    "task": {
      "id": "uuid-string",
      "type": "long_running_task",
      "status": "RUNNING",
      "progress": 0,
      "stage": "初始化中...",
      "payload": {"duration": 20, "items": 10},
      "result": null,
      "error": null,
      "idempotency_key": "unique_key_123",
      "created_at": "2024-01-01T12:00:00",
      "updated_at": "2024-01-01T12:00:00",
      "started_at": "2024-01-01T12:00:00",
      "completed_at": null,
      "cancelled_at": null
    },
    "is_new": true
  },
  "request_id": "uuid-string"
}
```

**状态码:**
- `201 Created`: 新任务创建成功
- `200 OK`: 返回已存在的任务（幂等）

**幂等性保证:**
- 使用 `idempotency_key` 确保同一业务操作不会重复执行
- 多进程并发场景下也能保证幂等（使用数据库唯一约束）
- 重复请求返回已存在的任务，不会再次触发执行

### 获取任务列表

```http
GET /api/tasks?status=RUNNING&type=long_running_task&limit=20&offset=0
```

**查询参数:**
- `status`: 按状态过滤 (PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED)
- `type`: 按类型过滤
- `limit`: 每页数量 (1-100, 默认20)
- `offset`: 偏移量 (默认0)

**响应示例:**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "tasks": [...],
    "pagination": {
      "total": 100,
      "limit": 20,
      "offset": 0,
      "has_more": true
    }
  },
  "request_id": "uuid-string"
}
```

### 获取任务详情

```http
GET /api/tasks/{task_id}
```

**响应示例:**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task": {
      "id": "uuid-string",
      "status": "SUCCEEDED",
      "progress": 100,
      "stage": "任务完成",
      "result": {
        "processed_items": 10,
        "duration": 20,
        "summary": "Successfully processed 10 items in 20 seconds"
      }
    }
  },
  "request_id": "uuid-string"
}
```

### 取消任务

```http
POST /api/tasks/{task_id}/cancel
```

**响应示例:**
```json
{
  "code": 0,
  "message": "Task cancelled successfully",
  "data": {
    "task": {
      "id": "uuid-string",
      "status": "CANCELLED",
      ...
    }
  },
  "request_id": "uuid-string"
}
```

### 获取任务结构化日志

```http
GET /api/tasks/{task_id}/logs
```

**响应示例:**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "uuid-string",
    "type": "long_running_task",
    "status": "SUCCEEDED",
    "progress": 100,
    "stage": "任务完成",
    "elapsed_ms": 20500,
    "logs": [
      {
        "timestamp": "2024-01-01T12:00:01",
        "level": "INFO",
        "message": "Task started"
      },
      {
        "timestamp": "2024-01-01T12:00:05",
        "level": "INFO",
        "message": "Processing...",
        "progress": 50
      },
      {
        "timestamp": "2024-01-01T12:00:20",
        "level": "INFO",
        "message": "Task completed",
        "progress": 100
      }
    ]
  },
  "request_id": "uuid-string"
}
```

**结构化日志字段说明:**
- `task_id`: 任务唯一标识
- `type`: 任务类型
- `status`: 当前任务状态
- `progress`: 当前进度 (0-100)
- `stage`: 当前阶段描述
- `elapsed_ms`: 执行耗时（毫秒）
- `logs`: 日志条目列表，每条包含 `timestamp`, `level`, `message` 等字段

## 内置任务类型

### long_running_task

示例长任务，执行时间 10-30 秒，分5个阶段：

1. **初始化** (0-10%): 系统资源初始化
2. **数据准备** (10-30%): 加载和验证数据
3. **数据处理** (30-70%): 主要处理逻辑
4. **结果汇总** (70-90%): 生成报告
5. **清理** (90-100%): 资源释放

**参数:**
- `duration`: 执行时长（秒），范围 10-30
- `items`: 处理的数据项数量

## 扩展自定义任务

```python
from task_center.executor import TaskHandler, TaskContext

class MyTaskHandler(TaskHandler):
    @property
    def task_type(self) -> str:
        return "my_custom_task"
    
    def execute(self, context: TaskContext, payload: dict) -> dict:
        # 检查取消状态
        context.check_cancelled()
        
        # 更新进度
        context.set_progress(50, "处理中...")
        
        # 记录日志
        context.info("开始处理", data=payload)
        
        # 执行业务逻辑
        result = process_data(payload)
        
        # 完成
        context.set_progress(100, "完成")
        return {"result": result}

# 注册处理器
executor.register_handler(MyTaskHandler())
```

## 运行测试

```bash
# 运行所有测试
pytest task_center/tests/ -v

# 运行特定测试文件
pytest task_center/tests/test_api.py -v

# 运行特定测试
pytest task_center/tests/test_api.py::TestCreateTaskEndpoint -v

# 生成覆盖率报告
pytest task_center/tests/ --cov=task_center --cov-report=html
```

## 使用示例

### 创建并监控任务

```bash
# 1. 创建任务
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "type": "long_running_task",
    "payload": {"duration": 20, "items": 10},
    "idempotency_key": "my-operation-123"
  }'

# 2. 查询任务状态
curl http://localhost:5000/api/tasks/{task_id}

# 3. 获取任务结构化日志
curl http://localhost:5000/api/tasks/{task_id}/logs

# 4. 取消任务
curl -X POST http://localhost:5000/api/tasks/{task_id}/cancel
```

### Python 客户端示例

```python
import requests
import time

# 创建任务
response = requests.post("http://localhost:5000/api/tasks", json={
    "type": "long_running_task",
    "payload": {"duration": 20, "items": 10},
    "idempotency_key": "operation-123"
})
data = response.json()
if data["code"] != 0:
    print(f"Error: {data['message']}")
    exit(1)

task = data["data"]["task"]
print(f"Task created: {task['id']}, is_new: {data['data']['is_new']}")

# 轮询任务状态
while task["status"] in ["PENDING", "RUNNING"]:
    time.sleep(1)
    response = requests.get(f"http://localhost:5000/api/tasks/{task['id']}")
    result = response.json()
    if result["code"] == 0:
        task = result["data"]["task"]
        print(f"Progress: {task['progress']}%, Stage: {task['stage']}")

print(f"Final status: {task['status']}")
if task.get("result"):
    print(f"Result: {task['result']}")

# 获取结构化日志
response = requests.get(f"http://localhost:5000/api/tasks/{task['id']}/logs")
log_data = response.json()
if log_data["code"] == 0:
    print(f"Execution time: {log_data['data']['elapsed_ms']}ms")
    for log in log_data["data"]["logs"]:
        print(f"[{log['level']}] {log['timestamp']}: {log['message']}")
```

## 幂等性说明

任务中心通过 `idempotency_key` 实现幂等性控制：

1. **首次请求**: 创建新任务并返回 `is_new: true`
2. **重复请求**: 返回已存在的任务并返回 `is_new: false`
3. **并发安全**: 使用数据库唯一约束确保多进程/多线程场景下同 key 不会创建重复任务
4. **不重复执行**: 重复请求不会再次触发任务执行，保证业务安全

**实现机制:**
- 数据库层：使用 SQLite 唯一索引约束 `idempotency_key`
- 原子操作：使用 `INSERT` 尝试插入，冲突时回读已有任务
- 进程安全：不依赖进程内锁，支持多进程部署

**最佳实践:**
- 为每个业务操作生成唯一的幂等键（如 `order_123_payment`）
- 幂等键应包含业务标识，便于追踪
- 已完成的任务也会返回，可用于查询历史状态
- 幂等键建议包含时间戳或版本号，避免长期冲突

## 架构说明

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  Flask API  │────▶│   Service   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
                       ┌────────────────────────┘
                       ▼
              ┌─────────────────┐
              │  Idempotency    │
              │    Control      │
              └────────┬────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐
    │ SQLite  │   │ Thread  │   │  Task   │
    │   DB    │   │  Pool   │   │ Handler │
    └─────────┘   └─────────┘   └─────────┘
```

## 许可证

MIT License
