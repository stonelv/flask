import subprocess
import json
import time
import os

def curl_get(url):
    env = os.environ.copy()
    env.pop('http_proxy', None)
    env.pop('https_proxy', None)
    result = subprocess.run(['curl', '-s', '--noproxy', '127.0.0.1,localhost', url], capture_output=True, text=True, env=env)
    return result.stdout

def curl_post(url, data):
    env = os.environ.copy()
    env.pop('http_proxy', None)
    env.pop('https_proxy', None)
    result = subprocess.run(['curl', '-s', '--noproxy', '127.0.0.1,localhost', '-X', 'POST', '-H', 'Content-Type: application/json', '-d', json.dumps(data), url], capture_output=True, text=True, env=env)
    return result.stdout

base_url = 'http://127.0.0.1:8888'

print("=== Testing Task Center API ===")
print()

# Test 1: Health check
print("1. Health check:")
result = curl_get(f"{base_url}/health")
print(f"   {result}")

# Test 2: Create a task
print()
print("2. Create task:")
key1 = f"test_key_{int(time.time())}_1"
task_data = {
    "type": "example_long_task",
    "idempotency_key": key1,
    "payload": {"name": "test task"}
}
result = curl_post(f"{base_url}/api/tasks", task_data)
task1 = json.loads(result)
print(f"   Task ID: {task1['id']}")
print(f"   Status: {task1['status']}")

# Test 3: Idempotency
print()
print("3. Idempotency test (same key):")
result = curl_post(f"{base_url}/api/tasks", task_data)
task2 = json.loads(result)
print(f"   Same task ID: {task1['id'] == task2['id']}")

# Test 4: Different key
print()
print("4. New task with different key:")
key2 = f"test_key_{int(time.time())}_2"
task_data3 = {
    "type": "example_long_task",
    "idempotency_key": key2,
    "payload": {"name": "another test"}
}
result = curl_post(f"{base_url}/api/tasks", task_data3)
task3 = json.loads(result)
print(f"   New task ID: {task3['id']}")

# Test 5: Get task details
print()
print("5. Get task details:")
result = curl_get(f"{base_url}/api/tasks/{task1['id']}")
task_details = json.loads(result)
print(f"   Progress: {task_details['progress']}%")
print(f"   Stage: {task_details['stage']}")
print(f"   Status: {task_details['status']}")

# Test 6: List tasks
print()
print("6. List tasks:")
result = curl_get(f"{base_url}/api/tasks")
tasks_list = json.loads(result)
print(f"   Total tasks: {tasks_list['total']}")

# Test 7: Cancel task
print()
print("7. Cancel task:")
result = curl_post(f"{base_url}/api/tasks/{task3['id']}/cancel", {})
cancel_result = json.loads(result)
print(f"   Result: {cancel_result.get('message', 'Error')}")

# Test 8: Filter by status
print()
print("8. Filter by RUNNING status:")
result = curl_get(f"{base_url}/api/tasks?status=RUNNING")
running = json.loads(result)
print(f"   Running tasks: {len(running['items'])}")

# Test 9: Filter by CANCELLED status
print()
print("9. Filter by CANCELLED status:")
result = curl_get(f"{base_url}/api/tasks?status=CANCELLED")
cancelled = json.loads(result)
print(f"   Cancelled tasks: {len(cancelled['items'])}")

# Test 10: Progress updates
print()
print("10. Checking progress updates:")
for i in range(3):
    time.sleep(1)
    result = curl_get(f"{base_url}/api/tasks/{task1['id']}")
    t = json.loads(result)
    print(f"   Progress: {t['progress']}%, Stage: {t['stage']}")

print()
print("=== All tests completed ===")
