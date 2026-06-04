import requests
import time
import json

base_url = 'http://localhost:8888'

def run_tests():
    # Test 1: Health check
    print('1. Health check:')
    r = requests.get(f'{base_url}/health')
    print(f'   Status: {r.status_code}, Response: {r.json()}')

    # Test 2: Create a task
    print('\n2. Create task:')
    task_data = {
        'type': 'example_long_task',
        'idempotency_key': 'test_key_123_' + str(int(time.time())),
        'payload': {'name': 'test task'}
    }
    r = requests.post(f'{base_url}/api/tasks', json=task_data)
    print(f'   Status: {r.status_code}')
    task1 = r.json()
    print(f'   Task ID: {task1.get("id")}')
    print(f'   Status: {task1.get("status")}')

    # Test 3: Idempotency - same key should return same task
    print('\n3. Idempotency test (same key):')
    r = requests.post(f'{base_url}/api/tasks', json=task_data)
    print(f'   Status: {r.status_code}')
    task2 = r.json()
    print(f'   Same task ID: {task1.get("id") == task2.get("id")}')

    # Test 4: Different idempotency key - new task
    print('\n4. New task with different key:')
    task_data3 = {
        'type': 'example_long_task',
        'idempotency_key': 'test_key_456_' + str(int(time.time())),
        'payload': {'name': 'another test'}
    }
    r = requests.post(f'{base_url}/api/tasks', json=task_data3)
    print(f'   Status: {r.status_code}')
    task3 = r.json()
    print(f'   New task ID: {task3.get("id")}')

    # Test 5: Get task details
    print('\n5. Get task details:')
    r = requests.get(f'{base_url}/api/tasks/{task1.get("id")}')
    print(f'   Status: {r.status_code}')
    task_details = r.json()
    print(f'   Progress: {task_details.get("progress")}%')
    print(f'   Stage: {task_details.get("stage")}')

    # Test 6: List tasks
    print('\n6. List tasks:')
    r = requests.get(f'{base_url}/api/tasks')
    print(f'   Status: {r.status_code}')
    tasks_list = r.json()
    print(f'   Total tasks: {tasks_list.get("total")}')

    # Test 7: Cancel task 3
    print('\n7. Cancel task:')
    r = requests.post(f'{base_url}/api/tasks/{task3.get("id")}/cancel')
    print(f'   Status: {r.status_code}')
    print(f'   Response: {r.json()}')

    # Test 8: Filter by status
    print('\n8. Filter by RUNNING status:')
    r = requests.get(f'{base_url}/api/tasks?status=RUNNING')
    print(f'   Status: {r.status_code}')
    running = r.json()
    print(f'   Running tasks: {len(running.get("items", []))}')

    # Test 9: Filter by CANCELLED status
    print('\n9. Filter by CANCELLED status:')
    r = requests.get(f'{base_url}/api/tasks?status=CANCELLED')
    print(f'   Status: {r.status_code}')
    cancelled = r.json()
    print(f'   Cancelled tasks: {len(cancelled.get("items", []))}')

    # Test 10: Pagination
    print('\n10. Pagination test:')
    r = requests.get(f'{base_url}/api/tasks?page=1&per_page=5')
    print(f'   Status: {r.status_code}')
    paginated = r.json()
    print(f'   Page: {paginated.get("page")}, Per page: {paginated.get("per_page")}')

    # Wait a bit and check progress
    print('\n11. Checking progress updates:')
    for i in range(3):
        time.sleep(1)
        r = requests.get(f'{base_url}/api/tasks/{task1.get("id")}')
        t = r.json()
        print(f'   Progress: {t.get("progress")}%, Stage: {t.get("stage")}')

    print('\n=== All tests completed ===')

if __name__ == '__main__':
    run_tests()
