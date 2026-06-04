# Flask 后台任务中心

一个可复用的 Flask 异步任务中心实现，支持任务创建、查询、取消、幂等性去重、进度上报与结构化日志。

## 功能特性

- ✅ **任务持久化** - 任务状态落库 SQLite/PostgreSQL/MySQL
- ✅ **完整状态机** - PENDING / RUNNING / SUCCEEDED / FAILED / CANCELLED
- ✅ **幂等性保证** - 按 idempotency_key 去重，并发安全
- ✅ **进度追踪** - 0-100% 进度 + stage 阶段标识
- ✅ **协作式取消** - 支持取消正在运行的任务
- ✅ **异步执行器** - 独立线程运行 asyncio 事件循环，不阻塞 Flask
- ✅ **结构化日志** - JSON 格式日志，包含 task_id、stage、progress 上下文
- ✅ **RESTful API** - 标准的 HTTP 接口

## 快速开始

### 安装依赖

```bash
cd examples/task_center
pip install -e .
```

或使用 uv:

```bash
uv pip install -e .
```

### 运行服务

```bash
python app.py
```

服务将在 `http://localhost:5000` 启动

### 运行测试

```bash
python -m pytest tests/ -v
```

## API 接口

### 创建任务 (幂等)

```bash
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "type": "example_long_task",
    "idempotency_key": "my_unique_key_123",
    "payload": {
      "min_duration": 10,
      "max_duration": 30
    }
  }'
```

**响应**:
- `201 Created` - 新任务创建成功
- `200 OK` - 相同幂等键的任务已存在
- `400 Bad Request` - 参数错误

### 查询单个任务

```bash
curl http://localhost:5000/api/tasks/{task_id}
```

### 查询任务列表 (分页过滤)

```bash
# 分页
curl "http://localhost:5000/api/tasks?page=1&per_page=20"

# 按状态过滤
curl "http://localhost:5000/api/tasks?status=RUNNING"

# 按类型过滤
curl "http://localhost:5000/api/tasks?type=example_long_task"

# 组合过滤
curl "http://localhost:5000/api/tasks?status=PENDING&type=example_long_task"
```

### 取消任务

```bash
curl -X POST http://localhost:5000/api/tasks/{task_id}/cancel
```

## 任务模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | UUID |
| type | string | 任务类型 |
| status | enum | PENDING / RUNNING / SUCCEEDED / FAILED / CANCELLED |
| progress | int | 0-100 |
| stage | string | 当前阶段标识 |
| payload | json | 任务输入参数 |
| result | json | 任务执行结果 |
| error | json | 错误信息 (包含 traceback) |
| idempotency_key | string | 幂等键 (唯一约束) |
| created_at | datetime | 创建时间 |
| started_at | datetime | 开始执行时间 |
| completed_at | datetime | 完成时间 |

## 自定义任务处理器

```python
from task_center.executor import get_executor, TaskContext

async def my_task_handler(context: TaskContext, payload: dict):
    # 更新进度
    context.update_progress(0, "initializing")
    context.log("Starting my task")
    
    # 检查是否被取消
    if context.is_cancelled():
        return
    
    # 执行任务逻辑
    context.update_progress(50, "processing")
    
    # 支持协作式取消
    for item in work_items:
        if context.is_cancelled():
            break
        await process_item(item)
    
    context.update_progress(100, "completed")
    return {"result": "success"}

# 注册处理器
executor = get_executor()
executor.register_task_handler("my_task_type", my_task_handler)
```

## 架构设计

### 执行器模型

```
┌─────────────────────────────────────────────────────────┐
│                    Flask Main Thread                    │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐        │
│  │ API      │────▶│ Task     │────▶│ Command  │        │
│  │ Handlers │     │ Model    │     │ Queue    │        │
│  └──────────┘     └──────────┘     └────┬─────┘        │
└─────────────────────────────────────────┼──────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────┐
│                  Worker Thread (asyncio)               │
│  ┌─────────────────────────────────────────────────┐  │
│  │              Event Loop                         │  │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐    │  │
│  │  │ Task     │──▶│ Task     │──▶│ Task     │    │  │
│  │  │ Context  │   │ Handler  │   │ State    │    │  │
│  │  └──────────┘   └──────────┘   └──────────┘    │  │
│  └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 幂等性实现

1. **数据库唯一约束**: `idempotency_key` 字段有唯一索引
2. **行级锁**: 查询时使用 `SELECT ... FOR UPDATE`
3. **冲突重试**: `IntegrityError` 捕获后重试查询

## 日志示例

```json
{
  "asctime": "2024-01-15T10:30:00.123Z",
  "name": "task_center",
  "levelname": "INFO",
  "message": "Task progress updated",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "stage": "processing",
  "progress": 50
}
```

## 项目结构

```
task_center/
├── task_center/
│   ├── __init__.py      # 应用工厂 + 日志配置
│   ├── models.py        # Task 数据库模型
│   ├── executor.py      # 异步任务执行器
│   └── api.py           # REST API
├── tests/
│   ├── conftest.py      # pytest 配置
│   └── test_tasks.py    # 测试用例
├── app.py               # 入口文件
├── pyproject.toml       # 项目配置
└── README.md            # 本文档
```

## 并发安全

1. **SQLite**: 使用文件数据库 (避免内存数据库连接隔离)
2. **行级锁**: 所有状态变更使用 `SELECT ... FOR UPDATE`
3. **命令队列**: 线程间通信使用线程安全的 `Queue`
4. **任务取消**: 同时设置 `cancellation_requests` 和 `TaskContext._cancelled`

## 故障恢复

- 服务重启后，PENDING/RUNNING 状态的任务不会自动恢复
- 可通过扫描数据库实现任务恢复逻辑 (扩展功能)
- 建议使用数据库触发器或外部调度器处理故障恢复

## License

BSD-3-Clause
