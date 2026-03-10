import pytest
import time
import json
from task_center import db
from task_center.models import Task, TaskStatus
from task_center.executor import executor

class TestTaskAPI:
    def test_create_task(self, client):
        response = client.post('/api/tasks', 
            json={'name': 'Test Task', 'type': 'test'},
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'task' in data
        assert data['task']['status'] == 'pending'
        assert data['task']['name'] == 'Test Task'

    def test_create_task_missing_fields(self, client):
        response = client.post('/api/tasks', 
            json={'name': 'Test Task'},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_create_task_idempotency(self, client):
        response1 = client.post('/api/tasks', 
            json={
                'name': 'Test Task', 
                'type': 'test',
                'idempotency_key': 'unique-key-123'
            },
            content_type='application/json'
        )
        assert response1.status_code == 201
        data1 = json.loads(response1.data)

        response2 = client.post('/api/tasks', 
            json={
                'name': 'Test Task', 
                'type': 'test',
                'idempotency_key': 'unique-key-123'
            },
            content_type='application/json'
        )
        assert response2.status_code == 200
        data2 = json.loads(response2.data)
        assert data1['task']['id'] == data2['task']['id']

    def test_get_task(self, client):
        response = client.post('/api/tasks', 
            json={'name': 'Test Task', 'type': 'test'},
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        task_id = data['task']['id']

        response = client.get(f'/api/tasks/{task_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['task']['id'] == task_id

    def test_get_task_not_found(self, client):
        response = client.get('/api/tasks/nonexistent-id')
        assert response.status_code == 404

    def test_list_tasks(self, client):
        for i in range(5):
            client.post('/api/tasks', 
                json={'name': f'Test Task {i}', 'type': 'test'},
                content_type='application/json'
            )

        response = client.get('/api/tasks')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['tasks']) == 5
        assert data['total'] == 5

    def test_list_tasks_pagination(self, client):
        for i in range(15):
            client.post('/api/tasks', 
                json={'name': f'Test Task {i}', 'type': 'test'},
                content_type='application/json'
            )

        response = client.get('/api/tasks?page=2&per_page=5')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['tasks']) == 5
        assert data['page'] == 2
        assert data['total'] == 15

    def test_list_tasks_filter_by_status(self, client, app):
        with app.app_context():
            task1 = Task(name='Task 1', type='test', status=TaskStatus.PENDING)
            task2 = Task(name='Task 2', type='test', status=TaskStatus.RUNNING)
            db.session.add_all([task1, task2])
            db.session.commit()

        response = client.get('/api/tasks?status=pending')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['tasks']) == 1
        assert data['tasks'][0]['status'] == 'pending'

    def test_list_tasks_filter_by_type(self, client, app):
        with app.app_context():
            task1 = Task(name='Task 1', type='import', status=TaskStatus.PENDING)
            task2 = Task(name='Task 2', type='export', status=TaskStatus.PENDING)
            db.session.add_all([task1, task2])
            db.session.commit()

        response = client.get('/api/tasks?type=import')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['tasks']) == 1
        assert data['tasks'][0]['type'] == 'import'

    def test_cancel_pending_task(self, client, app):
        with app.app_context():
            task = Task(name='Test Task', type='test', status=TaskStatus.PENDING)
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        response = client.post(f'/api/tasks/{task_id}/cancel')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['task']['status'] == 'cancelled'

    def test_cancel_running_task(self, client, app):
        response = client.post('/api/tasks', 
            json={'name': 'Long Task', 'type': 'long'},
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        task_id = data['task']['id']

        time.sleep(0.5)

        response = client.post(f'/api/tasks/{task_id}/cancel')
        assert response.status_code == 200

        time.sleep(0.5)

        response = client.get(f'/api/tasks/{task_id}')
        data = json.loads(response.data)
        assert data['task']['status'] == 'cancelled'

    def test_cancel_completed_task(self, client, app):
        with app.app_context():
            task = Task(name='Test Task', type='test', status=TaskStatus.SUCCEEDED)
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        response = client.post(f'/api/tasks/{task_id}/cancel')
        assert response.status_code == 400

    def test_cancel_nonexistent_task(self, client):
        response = client.post('/api/tasks/nonexistent-id/cancel')
        assert response.status_code == 404

    def test_task_execution(self, client, app):
        response = client.post('/api/tasks', 
            json={'name': 'Test Task', 'type': 'test'},
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        task_id = data['task']['id']

        time.sleep(1)

        response = client.get(f'/api/tasks/{task_id}')
        data = json.loads(response.data)
        assert data['task']['status'] in ['running', 'succeeded']

    def test_task_progress_updates(self, client, app):
        response = client.post('/api/tasks', 
            json={'name': 'Progress Test', 'type': 'test'},
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        task_id = data['task']['id']

        time.sleep(2)

        response = client.get(f'/api/tasks/{task_id}')
        data = json.loads(response.data)
        assert data['task']['progress'] > 0

    def test_task_payload(self, client):
        payload = {'data': 'test', 'value': 123}
        response = client.post('/api/tasks', 
            json={'name': 'Test Task', 'type': 'test', 'payload': payload},
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['task']['payload'] == payload

    def test_task_result(self, client, app):
        response = client.post('/api/tasks', 
            json={'name': 'Test Task', 'type': 'test'},
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        task_id = data['task']['id']

        time.sleep(5)

        response = client.get(f'/api/tasks/{task_id}')
        data = json.loads(response.data)
        if data['task']['status'] == 'succeeded':
            assert data['task']['result'] is not None

    def test_concurrent_task_creation(self, client):
        import threading

        def create_task():
            return client.post('/api/tasks', 
                json={'name': 'Concurrent Task', 'type': 'test', 'idempotency_key': 'concurrent-key'},
                content_type='application/json'
            )

        threads = [threading.Thread(target=create_task) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        response = client.get('/api/tasks')
        data = json.loads(response.data)
        assert data['total'] == 1
