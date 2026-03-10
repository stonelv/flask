# 后台任务中心

一个基于 Flask 的可复用异步任务中心，提供任务创建、查询、取消、幂等去重、进度上报和日志可观测能力。

## 功能特性

- ✅ **任务持久化** - 任务状态落库存储，支持 PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED 状态
- ✅ **幂等性保证** - 基于 idempotency_key 的并发安全去重
- ✅ **异步执行** - 基于 ThreadPoolExecutor 的异步任务执行器
- ✅ **进度上报** - 任务执行阶段进度和状态更新
- ✅ **协作式取消** - 支持运行中任务的优雅取消
- ✅ **结构化日志** - JSON 格式日志，便于日志收集和分析
- ✅ **RESTful API** - 标准 HTTP 接口，支持分页和过滤
- ✅ **自动化测试** - 覆盖幂等性、取消、状态查询、列表过滤等场景

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

### 运行应用

```bash
python app.py
```

应用将在 `http://localhost:5000` 启动。

## API 接口

### 创建任务

```bash
POST /api/tasks
Content-Type: application/json

{
    "name": "我的长任务",
    "type": "long_running_task",
    "payload": {
        "duration": 15,
        "data": "自定义数据"
    },
    "idempotency_key": "unique-key-12345",
    "timeout": 300
}
```

**响应:**
```json
{
    "task": {
        "id": "uuid-string",
        "name": "我的长任务",
        "type": "long_running_task",
        "status": "pending",
        "progress": 0,
        "stage": null,
        "payload": {
            "duration": 15,
            "data": "自定义数据"
        },
        "result": null,
        "error": null,
        "idempotency_key": "unique-key-12345",
        "timeout": 300,
        "created_at": "2024-01-01T00:00:00",
        "started_at": null,
        "completed_at": null,
        "cancelled_at": null
    },
    "message": "Task created successfully"
}
```

### 查询单个任务

```bash
GET /api/tasks/{task_id}
```

### 查询任务列表

```bash
GET /api/tasks?page=1&per_page=20&status=running&type=long_running_task
```

**查询参数:**
- `page`: 页码 (默认: 1)
- `per_page`: 每页数量 (默认: 20)
- `status`: 按状态过滤 (pending/running/succeeded/failed/cancelled)
- `type`: 按任务类型过滤

### 取消任务

```bash
POST /api/tasks/{task_id}/cancel
```

## 任务状态流转

```
PENDING → RUNNING → SUCCEEDED
                    → FAILED
                    → CANCELLED
          → CANCELLED
```

## 扩展自定义任务

```python
from task_center import executor

def my_custom_task_handler(context, payload):
    context.update_progress(0, "开始初始化")
    
    # 检查是否被取消
    if context.is_cancelled():
        return {'cancelled': True}
    
    context.update_progress(50, "处理中")
    context.log("正在处理数据")
    
    # 执行你的业务逻辑
    result = do_some_work(payload)
    
    context.update_progress(100, "完成")
    return {'result': result}

# 注册自定义任务类型
executor.register_task_handler('my_custom_task', my_custom_task_handler)
```

## 运行测试

```bash
pytest tests/ -v
```

或使用 uv:

```bash
uv run pytest tests/ -v
```

## 日志配置

日志文件位于 `logs/task_center.log`，采用 JSON 格式：

```json
{
    "timestamp": "2024-01-01 00:00:00,000",
    "level": "INFO",
    "module": "executor",
    "message": "[Task uuid] Starting long running task"
}
```

## 配置项

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| SECRET_KEY | SECRET_KEY | dev-secret-key | 应用密钥 |
| SQLALCHEMY_DATABASE_URI | DATABASE_URL | sqlite:///tasks.db | 数据库连接 |
| TASK_EXECUTOR_MAX_WORKERS | TASK_EXECUTOR_MAX_WORKERS | 4 | 最大工作线程数 |
| TASK_DEFAULT_TIMEOUT | TASK_DEFAULT_TIMEOUT | 300 | 默认超时时间(秒) |

## 项目结构

```
task_center/
├── task_center/
│   ├── __init__.py      # 应用工厂
│   ├── config.py        # 配置类
│   ├── models.py        # 数据模型
│   ├── executor.py      # 任务执行器
│   └── api.py           # API 端点
├── tests/
│   ├── conftest.py      # pytest 配置
│   └── test_tasks.py    # 测试用例
├── app.py               # 应用入口
├── pyproject.toml       # 项目配置
└── README.md            # 本文档
```

## License

BSD-3-Clause
