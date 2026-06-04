"""
Flask Scheduler 使用示例
"""
from datetime import timedelta, datetime
from flask import Flask, jsonify
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)

# 配置调度器
app.config.update({
    'SCHEDULER_ENABLED': True,           # 启用调度器
    'SCHEDULER_AUTOSTART': True,        # 自动启动调度器
    'SCHEDULER_TICK_INTERVAL': 1.0,     # 检查间隔（秒）
    'SCHEDULER_MAX_WORKERS': 4,         # 最大工作线程数
    'SCHEDULER_STORAGE_PATH': 'scheduler_data.json'  # 存储路径
})

# 初始化调度器
from flask.scheduler import Scheduler
scheduler = Scheduler(app)


# 定义任务
from flask.scheduler.decorators import interval_task, delay_task, cron_task

@interval_task(interval=timedelta(seconds=10))
def my_interval_task():
    """每10秒执行一次的示例任务"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[间隔任务] 执行时间: {current_time}")
    return f"间隔任务执行成功: {current_time}"


@delay_task(delay=timedelta(seconds=5))
def my_delay_task():
    """延迟5秒后执行的示例任务"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[延迟任务] 执行时间: {current_time}")
    return f"延迟任务执行成功: {current_time}"


@cron_task("*/2 * * * *")
def my_cron_task():
    """每2分钟执行一次的cron任务"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[Cron任务] 执行时间: {current_time}")
    return f"Cron任务执行成功: {current_time}"


# 创建示例路由

@app.route('/')
def index():
    """首页"""
    return jsonify({
        'message': 'Flask Scheduler 示例应用',
        'scheduler_running': scheduler.is_running(),
        'endpoints': {
            'metrics': '/_internal/metrics',
            'tasks': '/_internal/tasks',
            'scheduler_status': '/_internal/scheduler/status',
            'health': '/_internal/health'
        }
    })


@app.route('/run-task/<task_name>', methods=['POST'])
def run_task(task_name):
    """手动运行任务"""
    success = scheduler.run_task(task_name)
    if success:
        return jsonify({'status': 'success', 'message': f'Task {task_name} started'})
    else:
        return jsonify({'status': 'error', 'message': f'Failed to start task {task_name}'}), 400


@app.route('/scheduler-info')
def scheduler_info():
    """获取调度器信息"""
    tasks = scheduler.get_all_tasks()
    metrics = scheduler.get_metrics()
    
    return jsonify({
        'scheduler_running': scheduler.is_running(),
        'total_tasks': len(tasks),
        'tasks': [task.name for task in tasks],
        'metrics': metrics
    })


# 注册管理蓝图
import sys
sys.path.insert(0, '../src')

# 调试信息
print('Python路径:', sys.path[:3])
print('当前工作目录:', __import__('os').getcwd())

# 导入函数并注册蓝图
try:
    from flask.scheduler.blueprint import create_scheduler_blueprint
    print('✓ 成功导入 create_scheduler_blueprint')
    scheduler_admin_bp = create_scheduler_blueprint(scheduler, name='scheduler_admin')
    app.register_blueprint(scheduler_admin_bp)
    print('✓ 成功注册调度器管理蓝图')
except ImportError as e:
    print('✗ 导入失败:', e)
    import traceback
    traceback.print_exc()
    # 尝试备用导入方式
    try:
        import flask.scheduler.blueprint as bp_module
        create_scheduler_blueprint = getattr(bp_module, 'create_scheduler_blueprint')
        scheduler_admin_bp = create_scheduler_blueprint(scheduler, name='scheduler_admin')
        app.register_blueprint(scheduler_admin_bp)
        print('✓ 使用备用方式成功注册蓝图')
    except Exception as e2:
        print('✗ 备用方式也失败:', e2)
        # 不注册蓝图，应用仍可运行
        print('⚠️  跳过蓝图注册，应用将继续运行')

if __name__ == '__main__':
    # 任务已经在上面定义，不需要额外导入
    logger.info("启动Flask应用和调度器...")
    app.run(debug=True, port=5000)