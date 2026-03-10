import pytest
import time
import uuid
from task_center.models import Task, TaskStatus

class TestTaskCreation:
    def test_create_task_basic(self, client):
        response = client.post('/api/tasks', json={
            'name': 'Test Task',
            'type': 'long_running_task'
        })
        assert response.status_code == 201
        data = response.get_json()
        assert 'task' in data
        assert data['task']['name'] == 'Test Task'
        assert data['task']['status'] == 'pending'
        assert data['task']['progress'] == 0

    def test_create_task_with_payload(self, client):
        payload = {'duration': 5, 'data': 'test'}
        response = client.post('/api/tasks', json={
            'name': 'Test Task with Payload',
            'type': 'long_running_task',
            'payload': payload
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['task']['payload'] == payload

    def test_create_task_missing_required_fields(self, client):
        response = client.post('/api/tasks', json={
            'name': 'Test Task'
        })
        assert response.status_code == 400
        assert 'error' in response.get_json()

    def test_create_task_invalid_type(self, client):
        response = client.post('/api/tasks', json={
            'name': 'Test Task',
            'type': 'invalid_type'
        })
        assert response.status_code == 400

class TestIdempotency:
    def test_create_task_idempotency_same_key(self, client):
        idempotency_key = str(uuid.uuid4())
        response1 = client.post('/api/tasks', json={
            'name': 'Test Task',
            'type': 'long_running_task',
            'idempotency_key': idempotency_key
        })
        assert response1.status_code == 201
        task1 = response1.get_json()['task']

        response2 = client.post('/api/tasks', json={
            'name': 'Test Task 2',
            'type': 'long_running_task',
            'idempotency_key': idempotency_key
        })
        assert response2.status_code == 200
        task2 = response2.get_json()['task']
        assert task1['id'] == task2['id']
        assert 'already exists' in response2.get_json()['message']

    def test_create_task_idempotency_different_keys(self, client):
        response1 = client.post('/api/tasks', json={
            'name': 'Test Task 1',
            'type': 'long_running_task',
            'idempotency_key': str(uuid.uuid4())
        })
        assert response1.status_code == 201

        response2 = client.post('/api/tasks', json={
            'name': 'Test Task 2',
            'type': 'long_running_task',
            'idempotency_key': str(uuid.uuid4())
        })
        assert response2.status_code == 201
        assert response1.get_json()['task']['id'] != response2.get_json()['task']['id']

class TestTaskQuery:
    def test_get_task(self, client):
        create_response = client.post('/api/tasks', json={
            'name': 'Test Task',
            'type': 'long_running_task'
        })
        task_id = create_response.get_json()['task']['id']

        get_response = client.get(f'/api/tasks/{task_id}')
        assert get_response.status_code == 200
        assert get_response.get_json()['task']['id'] == task_id

    def test_get_task_not_found(self, client):
        response = client.get('/api/tasks/nonexistent')
        assert response.status_code == 404

    def test_list_tasks(self, client):
        for i in range(5):
            client.post('/api/tasks', json={
                'name': f'Test Task {i}',
                'type': 'long_running_task'
            })

        response = client.get('/api/tasks')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['tasks']) == 5
        assert 'pagination' in data

    def test_list_tasks_pagination(self, client):
        for i in range(15):
            client.post('/api/tasks', json={
                'name': f'Test Task {i}',
                'type': 'long_running_task'
            })

        response = client.get('/api/tasks?page=2&per_page=10')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['tasks']) == 5
        assert data['pagination']['page'] == 2
        assert data['pagination']['total'] == 15

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
        assert len(response.get_json()['tasks']) == 1
        assert response.get_json()['tasks'][0]['type'] == 'type1'

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
        assert len(response.get_json()['tasks']) == 1
        assert response.get_json()['tasks'][0]['status'] == 'succeeded'

    def test_list_tasks_invalid_status(self, client):
        response = client.get('/api/tasks?status=invalid')
        assert response.status_code == 400

class TestTaskCancellation:
    def test_cancel_pending_task(self, client, app):
        create_response = client.post('/api/tasks', json={
            'name': 'Test Task',
            'type': 'long_running_task'
        })
        task_id = create_response.get_json()['task']['id']

        cancel_response = client.post(f'/api/tasks/{task_id}/cancel')
        assert cancel_response.status_code == 200

        get_response = client.get(f'/api/tasks/{task_id}')
        assert get_response.get_json()['task']['status'] == 'cancelled'

    def test_cancel_running_task(self, client):
        create_response = client.post('/api/tasks', json={
            'name': 'Long Task',
            'type': 'long_running_task',
            'payload': {'duration': 10}
        })
        task_id = create_response.get_json()['task']['id']

        time.sleep(0.5)

        cancel_response = client.post(f'/api/tasks/{task_id}/cancel')
        assert cancel_response.status_code == 200

        time.sleep(0.5)

        get_response = client.get(f'/api/tasks/{task_id}')
        assert get_response.get_json()['task']['status'] == 'cancelled'

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

    def test_cancel_nonexistent_task(self, client):
        response = client.post('/api/tasks/nonexistent/cancel')
        assert response.status_code == 404

class TestTaskExecution:
    def test_task_execution_completes(self, client):
        create_response = client.post('/api/tasks', json={
            'name': 'Test Task',
            'type': 'long_running_task',
            'payload': {'duration': 2}
        })
        task_id = create_response.get_json()['task']['id']

        time.sleep(3)

        get_response = client.get(f'/api/tasks/{task_id}')
        task = get_response.get_json()['task']
        assert task['status'] in ['succeeded', 'failed']
        if task['status'] == 'succeeded':
            assert task['progress'] == 100

    def test_task_progress_updates(self, client):
        create_response = client.post('/api/tasks', json={
            'name': 'Test Task',
            'type': 'long_running_task',
            'payload': {'duration': 3}
        })
        task_id = create_response.get_json()['task']['id']

        time.sleep(1)

        get_response = client.get(f'/api/tasks/{task_id}')
        task = get_response.get_json()['task']
        if task['status'] == 'running':
            assert 0 < task['progress'] < 100
            assert task['stage'] is not None
