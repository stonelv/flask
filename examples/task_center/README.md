# Task Center - 后台任务中心

提供一套可复用的异步任务能力，支持创建任务、查询任务、取消任务、幂等去重、进度上报与日志可观测。

## 功能特性

- **Task 持久化模型**：支持 PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED 五种状态，包含 progress（0-100）、stage、payload/result/error、idempotency_key
- **幂等创建**：基于 idempotency_key 的并发安全幂等去重，同 key 重复请求不会重复创建
- **原子 Claim 执行**：基于数据库 UPDATE...WHERE 的原子操作，同 task 并发下只会被一个 worker 执行
- **RESTful API**：创建、查询、列表（分页+过滤）、取消
- **异步执行器**：基于 ThreadPoolExecutor 的后台任务调度
- **持久化取消请求**：cancel_requested 字段落库，跨进程/重启后取消状态依然有效
- **协作式取消**：长任务可随时响应取消请求
- **结构化日志**：JSON 格式输出，包含任务 ID、进度等上下文

## 项目结构

```
examples/task_center/
├── src/task_center/
│   ├── __init__.py      # 工厂函数、日志配置
│   ├── models.py        # Task 模型、存储层
│   ├── executor.py      # 任务执行器、TaskContext
│   ├── routes.py        # API 路由
│   └── tasks.py         # 内置示例任务
├── tests/
│   ├── __init__.py
│   └── test_api.py      # 自动化测试
└── pyproject.toml       # 项目配置
```

## 快速开始

### 初始化数据库

首次运行前需要初始化数据库（默认使用 SQLite，文件为 `tasks.db`）：

```bash
cd examples/task_center
FLASK_APP=src/task_center flask init-db
```

如需重置数据库：

```bash
FLASK_APP=src/task_center flask drop-db
FLASK_APP=src/task_center flask init-db
```

也可以通过环境变量 `DATABASE` 指定其他数据库 URL：

```bash
DATABASE=sqlite:///custom.db FLASK_APP=src/task_center flask init-db
```

### 安装依赖

```bash
cd examples/task_center
pip install -e ".[dev]"
```

或使用 uv：

```bash
cd examples/task_center
uv sync
```

### 启动服务

```bash
cd examples/task_center
FLASK_APP=src/task_center flask run --reload --debug
```

或使用：

```bash
python -m flask --app src/task_center run -p 5000
```

## API 文档

### 1. 创建任务

```
POST /api/tasks
Content-Type: application/json

{
    "type": "long_running_task",
    "payload": {"duration": 15},
    "idempotency_key": "unique-request-key"
}
```

响应：

```json
{
    "code": 0,
    "message": "Success",
    "data": {
        "id": "uuid-xxx",
        "type": "long_running_task",
        "status": "PENDING",
        "progress": 0,
        "stage": "",
        "payload": {"duration": 15},
        "result": null,
        "error": null,
        "idempotency_key": "unique-request-key",
        "created_at": "2026-02-28T...",
        "updated_at": "2026-02-28T...",
        "started_at": null,
        "finished_at": null,
        "logs": []
    }
}
```

### 2. 查询单个任务

```
GET /api/tasks/<task_id>
```

### 3. 列出任务（分页+过滤）

```
GET /api/tasks?status=RUNNING&type=long_running_task&page=1&per_page=20
```

响应：

```json
{
    "code": 0,
    "message": "Success",
    "data": {
        "tasks": [...],
        "pagination": {
            "page": 1,
            "per_page": 20,
            "total": 42,
            "total_pages": 3
        }
    }
}
```

### 4. 取消任务

```
POST /api/tasks/<task_id>/cancel
```

## 内置任务类型

### long_running_task

10~30 秒示例长任务，分阶段更新进度：

```bash
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"type": "long_running_task", "payload": {"duration": 15}}'
```

阶段：Initializing → Processing data → Executing main logic → Validating results → Finalizing → Complete

### quick_task

快速任务用于测试：

```bash
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"type": "quick_task", "payload": {"test": 1}}'
```

## 运行测试

```bash
cd examples/task_center
pytest -v
```

测试覆盖：
- `test_create_task` - 任务创建
- `test_get_task` - 任务查询
- `test_list_tasks` - 任务列表
- `test_list_tasks_pagination` - 分页功能
- `test_list_tasks_filter_by_type` - 按类型过滤
- `test_list_tasks_filter_by_status` - 按状态过滤
- `test_idempotency_key` - 幂等去重
- `test_idempotency_concurrent` - 并发幂等安全
- `test_cancel_pending_task` - 取消任务
- `test_task_progress` - 进度上报
- `test_task_status_transitions` - 状态转换
- `test_task_result` - 任务结果
- `test_task_error` - 错误处理
- `test_database_persistence` - **数据库持久化**（服务重启后任务仍可查询）
- `test_db_unique_constraint_concurrent` - **DB唯一约束下的并发幂等**
- `test_invalid_status_param_returns_400` - **非法参数返回400**
- `test_invalid_page_param_returns_400` - **非法参数返回400**
- `test_invalid_per_page_param_returns_400` - **非法参数返回400**

## 编写自定义任务

```python
from task_center.executor import TaskContext

def register_my_tasks(executor):
    @executor.register("my_task")
    def my_handler(ctx: TaskContext):
        # 获取输入
        input_data = ctx.payload

        # 检查是否被取消
        if ctx.check_cancel():
            raise InterruptedError("Cancelled")

        # 更新进度
        ctx.update_progress(50, "Processing...")

        # 记录日志
        ctx.log("Processing step")

        return {"output": "result"}
```

## 日志输出示例

```json
{"timestamp": "2026-02-28T10:00:00Z", "level": "INFO", "message": "Task xxx submitted for execution", "logger": "task_center", "task_id": "xxx"}
```
