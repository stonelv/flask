import pytest
import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from task_center.models import Task, TaskStatus

class TestTaskCreation:
    def test_create_task_basic(self, client):
        response = client.post('/api/tasks', json={
            'name': 'Test Task',
            'type': 'long_running_task'
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['error'] is None
        assert 'task' in data['data']
        assert data['data']['task']['name'] == 'Test Task'
        assert data['data']['task']['status'] == 'pending'
        assert data['data']['task']['progress'] == 0

    def test_create_task_with_payload(self, client):
        payload = {'duration': 5, 'data': 'test'}
        response = client.post('/api/tasks', json={
            'name': 'Test Task with Payload',
            'type': 'long_running_task',
            'payload': payload
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['error'] is None
        assert data['data']['task']['payload'] == payload

    def test_create_task_with_timeout(self, client):
        response = client.post('/api/tasks', json={
            'name': 'Test Task with Timeout',
            'type': 'long_running_task',
            'timeout': 60
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['error'] is None
        assert data['data']['task']['timeout'] == 60

    def test_create_task_missing_required_fields(self, client):
        response = client.post('/api/tasks', json={
            'name': 'Test Task'
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] is not None

    def test_create_task_invalid_type(self, client):
        response = client.post('/api/tasks', json={
            'name': 'Test Task',
            'type': 'invalid_type'
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] is not None

class TestIdempotency:
    def test_create_task_idempotency_same_key(self, client):
        idempotency_key = str(uuid.uuid4())
        response1 = client.post('/api/tasks', json={
            'name': 'Test Task',
            'type': 'long_running_task',
            'idempotency_key': idempotency_key
        })
        assert response1.status_code == 201
        data1 = response1.get_json()
        assert data1['error'] is None
        task1 = data1['data']['task']

        response2 = client.post('/api/tasks', json={
            'name': 'Test Task 2',
            'type': 'long_running_task',
            'idempotency_key': idempotency_key
        })
        assert response2.status_code == 200
        data2 = response2.get_json()
        assert data2['error'] is None
        task2 = data2['data']['task']
        assert task1['id'] == task2['id']
        assert 'already exists' in data2['message']

    def test_create_task_idempotency_different_keys(self, client):
        response1 = client.post('/api/tasks', json={
            'name': 'Test Task 1',
            'type': 'long_running_task',
            'idempotency_key': str(uuid.uuid4())
        })
        assert response1.status_code == 201
        data1 = response1.get_json()
        assert data1['error'] is None

        response2 = client.post('/api/tasks', json={
            'name': 'Test Task 2',
            'type': 'long_running_task',
            'idempotency_key': str(uuid.uuid4())
        })
        assert response2.status_code == 201
        data2 = response2.get_json()
        assert data2['error'] is None
        assert data1['data']['task']['id'] != data2['data']['task']['id']

    def test_concurrent_idempotent_requests(self, client, app):
        """Test that concurrent requests with same idempotency key only create one task"""
        idempotency_key = str(uuid.uuid4())
        results = []
        task_ids = set()

        def make_request():
            with app.test_client() as c:
                response = c.post('/api/tasks', json={
                    'name': 'Concurrent Test Task',
                    'type': 'long_running_task',
                    'idempotency_key': idempotency_key
                })
                return response

        # Use ThreadPoolExecutor to simulate concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            for future in as_completed(futures):
                response = future.result()
                data = response.get_json()
                assert data['error'] is None, f"Request failed: {data['error']}"
                task_id = data['data']['task']['id']
                task_ids.add(task_id)
                results.append(response.status_code)

        # All requests should succeed (either 201 or 200)
        for status_code in results:
            assert status_code in [201, 200], f"Unexpected status code: {status_code}"

        # Only one unique task should be created
        assert len(task_ids) == 1, f"Expected 1 unique task, got {len(task_ids)}: {task_ids}"

class TestTaskQuery:
    def test_get_task(self, client):
        create_response = client.post('/api/tasks', json={
            'name': 'Test Task',
            'type': 'long_running_task'
        })
        assert create_response.status_code == 201
        task_id = create_response.get_json()['data']['task']['id']

        get_response = client.get(f'/api/tasks/{task_id}')
        assert get_response.status_code == 200
        data = get_response.get_json()
        assert data['error'] is None
        assert data['data']['task']['id'] == task_id

    def test_get_task_not_found(self, client):
        response = client.get('/api/tasks/nonexistent')
        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] is not None

    def test_list_tasks(self, client):
        for i in range(5):
            client.post('/api/tasks', json={
                'name': f'Test Task {i}',
                'type': 'long_running_task'
            })

        response = client.get('/api/tasks')
        assert response.status_code == 200
        data = response.get_json()
        assert data['error'] is None
        assert len(data['data']['tasks']) == 5
        assert 'pagination' in data['data']

    def test_list_tasks_pagination(self, client):
        for i in range(15):
            client.post('/api/tasks', json={
                'name': f'Test Task {i}',
                'type': 'long_running_task'
            })

        response = client.get('/api/tasks?page=2&per_page=10')
        assert response.status_code == 200
        data = response.get_json()
        assert data['error'] is None
        assert len(data['data']['tasks']) == 5
        assert data['data']['pagination']['page'] == 2
        assert data['data']['pagination']['total'] == 15

    def test_list_tasks_filter_by_type(self, client):
        client.post('/api/tasks', json={
            'name': 'Task 1',
            'type': 'type1'
        })
        client.post('/api/tasks', json={
            'name': 'Task 2',
            'type': 'type2'
        })

        response = client.get('/api/tasks?type=type1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['error'] is None
        assert len(data['data']['tasks']) == 1
        assert data['data']['tasks'][0]['type'] == 'type1'

    def test_list_tasks_filter_by_status(self, client, app):
        with app.app_context():
            task1 = Task(
                id=str(uuid.uuid4()),
                name='Task 1',
                type='test',
                status=TaskStatus.SUCCEEDED
            )
            task2 = Task(
                id=str(uuid.uuid4()),
                name='Task 2',
                type='test',
                status=TaskStatus.FAILED
            )
            from task_center import db
            db.session.add(task1)
            db.session.add(task2)
            db.session.commit()

        response = client.get('/api/tasks?status=succeeded')
        assert response.status_code == 200
        data = response.get_json()
        assert data['error'] is None
        assert len(data['data']['tasks']) == 1
        assert data['data']['tasks'][0]['status'] == 'succeeded'

    def test_list_tasks_invalid_status(self, client):
        response = client.get('/api/tasks?status=invalid')
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] is not None

class TestTaskCancellation:
    def test_cancel_pending_task(self, client, app):
        create_response = client.post('/api/tasks', json={
            'name': 'Test Task',
            'type': 'long_running_task'
        })
        assert create_response.status_code == 201
        task_id = create_response.get_json()['data']['task']['id']

        cancel_response = client.post(f'/api/tasks/{task_id}/cancel')
        assert cancel_response.status_code == 200
        data = cancel_response.get_json()
        assert data['error'] is None

        get_response = client.get(f'/api/tasks/{task_id}')
        assert get_response.get_json()['data']['task']['status'] == 'cancelled'

    def test_cancel_running_task(self, client):
        create_response = client.post('/api/tasks', json={
            'name': 'Long Task',
            'type': 'long_running_task',
            'payload': {'duration': 10}
        })
        assert create_response.status_code == 201
        task_id = create_response.get_json()['data']['task']['id']

        time.sleep(0.5)

        cancel_response = client.post(f'/api/tasks/{task_id}/cancel')
        assert cancel_response.status_code == 200
        data = cancel_response.get_json()
        assert data['error'] is None

        time.sleep(0.5)

        get_response = client.get(f'/api/tasks/{task_id}')
        assert get_response.get_json()['data']['task']['status'] == 'cancelled'

    def test_cancel_completed_task(self, client, app):
        with app.app_context():
            task = Task(
                id=str(uuid.uuid4()),
                name='Completed Task',
                type='test',
                status=TaskStatus.SUCCEEDED
            )
            from task_center import db
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        cancel_response = client.post(f'/api/tasks/{task_id}/cancel')
        assert cancel_response.status_code == 400
        data = cancel_response.get_json()
        assert data['error'] is not None

    def test_cancel_nonexistent_task(self, client):
        response = client.post('/api/tasks/nonexistent/cancel')
        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] is not None

class TestTaskExecution:
    def test_task_execution_completes(self, client):
        create_response = client.post('/api/tasks', json={
            'name': 'Test Task',
            'type': 'long_running_task',
            'payload': {'duration': 2}
        })
        assert create_response.status_code == 201
        task_id = create_response.get_json()['data']['task']['id']

        time.sleep(3)

        get_response = client.get(f'/api/tasks/{task_id}')
        task = get_response.get_json()['data']['task']
        assert task['status'] in ['succeeded', 'failed']
        if task['status'] == 'succeeded':
            assert task['progress'] == 100

    def test_task_progress_updates(self, client):
        create_response = client.post('/api/tasks', json={
            'name': 'Test Task',
            'type': 'long_running_task',
            'payload': {'duration': 3}
        })
        assert create_response.status_code == 201
        task_id = create_response.get_json()['data']['task']['id']

        time.sleep(1)

        get_response = client.get(f'/api/tasks/{task_id}')
        task = get_response.get_json()['data']['task']
        if task['status'] == 'running':
            assert 0 < task['progress'] < 100
            assert task['stage'] is not None
