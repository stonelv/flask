"""
Task Center Demo - 演示脚本
展示后台任务中心的各种功能
"""
import json
import time
import sys
import requests


BASE_URL = "http://localhost:5000"


def print_section(title):
    """打印章节标题"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")


def print_json(data):
    """美化打印JSON"""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def wait_for_server():
    """等待服务器启动"""
    print("等待服务器启动...")
    for i in range(30):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=1)
            if response.status_code == 200:
                print("✓ 服务器已就绪\n")
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(0.5)
        print(".", end="", flush=True)
    
    print("\n✗ 服务器未启动，请先运行: python -m task_center.app")
    return False


def demo_create_task():
    """演示创建任务"""
    print_section("1. 创建任务")
    
    response = requests.post(
        f"{BASE_URL}/api/tasks",
        json={
            "type": "long_running_task",
            "payload": {
                "duration": 15,
                "items": 5
            }
        }
    )
    
    print(f"状态码: {response.status_code}")
    data = response.json()
    print_json(data)
    
    return data["task"]["id"]


def demo_idempotency():
    """演示幂等性"""
    print_section("2. 幂等性测试（重复请求）")
    
    idempotency_key = f"demo_operation_{int(time.time())}"
    
    print(f"幂等键: {idempotency_key}\n")
    
    # 第一次请求
    print("第一次请求:")
    response1 = requests.post(
        f"{BASE_URL}/api/tasks",
        json={
            "type": "long_running_task",
            "payload": {"duration": 20},
            "idempotency_key": idempotency_key
        }
    )
    data1 = response1.json()
    print(f"  状态码: {response1.status_code}")
    print(f"  is_new: {data1['is_new']}")
    print(f"  task_id: {data1['task']['id']}")
    
    # 第二次请求（相同幂等键）
    print("\n第二次请求（相同幂等键）:")
    response2 = requests.post(
        f"{BASE_URL}/api/tasks",
        json={
            "type": "long_running_task",
            "payload": {"duration": 30},  # 不同参数
            "idempotency_key": idempotency_key
        }
    )
    data2 = response2.json()
    print(f"  状态码: {response2.status_code}")
    print(f"  is_new: {data2['is_new']}")
    print(f"  task_id: {data2['task']['id']}")
    
    # 验证是同一个任务
    if data1['task']['id'] == data2['task']['id']:
        print("\n✓ 幂等性验证成功：两次请求返回同一任务")
    else:
        print("\n✗ 幂等性验证失败")
    
    return data1['task']['id']


def demo_monitor_task(task_id):
    """演示监控任务进度"""
    print_section(f"3. 监控任务进度 (ID: {task_id})")
    
    print("轮询任务状态（按 Ctrl+C 跳过）...\n")
    
    try:
        for i in range(60):  # 最多轮询60次
            response = requests.get(f"{BASE_URL}/api/tasks/{task_id}")
            task = response.json()["task"]
            
            status = task["status"]
            progress = task["progress"]
            stage = task["stage"]
            
            # 打印进度条
            bar_length = 30
            filled = int(bar_length * progress / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            print(f"\r[{bar}] {progress:3d}% | {status:12s} | {stage}", end="", flush=True)
            
            if status in ["SUCCEEDED", "FAILED", "CANCELLED"]:
                print()  # 换行
                print(f"\n任务结束: {status}")
                if task.get("result"):
                    print("结果:")
                    print_json(task["result"])
                if task.get("error"):
                    print(f"错误: {task['error']}")
                return
            
            time.sleep(0.5)
        
        print("\n\n轮询超时")
        
    except KeyboardInterrupt:
        print("\n\n用户中断轮询")


def demo_cancel_task():
    """演示取消任务"""
    print_section("4. 取消任务演示")
    
    # 创建任务
    print("创建长任务...")
    response = requests.post(
        f"{BASE_URL}/api/tasks",
        json={
            "type": "long_running_task",
            "payload": {
                "duration": 30,  # 30秒任务
                "items": 20
            }
        }
    )
    task_id = response.json()["task"]["id"]
    print(f"任务ID: {task_id}")
    
    # 等待任务开始运行
    print("等待任务开始运行...")
    time.sleep(1)
    
    # 取消任务
    print("发送取消请求...")
    cancel_response = requests.post(f"{BASE_URL}/api/tasks/{task_id}/cancel")
    cancel_data = cancel_response.json()
    
    print(f"\n取消响应:")
    print_json(cancel_data)
    
    # 等待取消生效
    print("\n等待取消生效...")
    time.sleep(1)
    
    # 查询最终状态
    response = requests.get(f"{BASE_URL}/api/tasks/{task_id}")
    task = response.json()["task"]
    print(f"\n最终状态: {task['status']}")


def demo_list_tasks():
    """演示任务列表"""
    print_section("5. 任务列表查询")
    
    # 创建几个任务
    print("创建示例任务...")
    for i in range(3):
        requests.post(
            f"{BASE_URL}/api/tasks",
            json={
                "type": "long_running_task",
                "payload": {"duration": 15}
            }
        )
    
    time.sleep(0.5)
    
    # 查询所有任务
    print("\n所有任务:")
    response = requests.get(f"{BASE_URL}/api/tasks?limit=5")
    data = response.json()
    print(f"总数: {data['pagination']['total']}")
    for task in data['tasks']:
        print(f"  - {task['id'][:8]}... | {task['type'][:20]:20s} | {task['status']:12s} | {task['progress']:3d}%")
    
    # 按状态过滤
    print("\n运行中任务:")
    response = requests.get(f"{BASE_URL}/api/tasks?status=RUNNING")
    data = response.json()
    print(f"数量: {len(data['tasks'])}")
    
    # 按类型过滤
    print("\nlong_running_task 类型:")
    response = requests.get(f"{BASE_URL}/api/tasks?type=long_running_task")
    data = response.json()
    print(f"数量: {len(data['tasks'])}")


def demo_logs():
    """演示日志查看"""
    print_section("6. 任务日志查看")
    
    # 创建一个任务并等待完成
    print("创建任务...")
    response = requests.post(
        f"{BASE_URL}/api/tasks",
        json={
            "type": "long_running_task",
            "payload": {"duration": 12, "items": 3}
        }
    )
    task_id = response.json()["task"]["id"]
    
    print("等待任务完成...")
    while True:
        response = requests.get(f"{BASE_URL}/api/tasks/{task_id}")
        task = response.json()["task"]
        if task["status"] in ["SUCCEEDED", "FAILED", "CANCELLED"]:
            break
        time.sleep(0.5)
    
    print(f"\n任务日志 ({len(task['logs'])} 条):")
    for log in task['logs']:
        timestamp = log['timestamp'].split('T')[1].split('.')[0]
        level = log['level']
        message = log['message']
        print(f"  [{timestamp}] {level:7s} | {message}")


def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║              Task Center 功能演示                        ║
║                                                          ║
║  本演示将展示后台任务中心的各项功能：                    ║
║  1. 创建任务                                             ║
║  2. 幂等性测试                                           ║
║  3. 进度监控                                             ║
║  4. 任务取消                                             ║
║  5. 列表查询                                             ║
║  6. 日志查看                                             ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # 检查服务器
    if not wait_for_server():
        sys.exit(1)
    
    try:
        # 运行演示
        demo_create_task()
        demo_idempotency()
        
        # 创建一个任务用于监控
        response = requests.post(
            f"{BASE_URL}/api/tasks",
            json={
                "type": "long_running_task",
                "payload": {"duration": 12, "items": 5}
            }
        )
        task_id = response.json()["task"]["id"]
        demo_monitor_task(task_id)
        
        demo_cancel_task()
        demo_list_tasks()
        demo_logs()
        
        print_section("演示完成")
        print("感谢使用 Task Center!")
        
    except KeyboardInterrupt:
        print("\n\n演示被用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
