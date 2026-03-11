import asyncio
import json
import pytest
import time
from task_center import db
from task_center.models import Task, TaskStatus
from task_center.executor import TaskContext, get_executor


class TestTaskModel:
    def test_task_creation(self, app):
        with app.app_context():
            task = Task(
                type="test_task",
                status=TaskStatus.PENDING,
                progress=0,
                payload=json.dumps({"key": "value"}),
                idempotency_key="test_key_123",
            )
            db.session.add(task)
            db.session.commit()

            assert task.id is not None
            assert task.type == "test_task"
            assert task.status == TaskStatus.PENDING
            assert task.progress == 0
            assert task.idempotency_key == "test_key_123"
            assert task.created_at is not None
            assert task.updated_at is not None

    def test_task_to_dict(self, app):
        with app.app_context():
            task = Task(
                type="test_task",
                status=TaskStatus.RUNNING,
                progress=50,
                stage="processing",
                idempotency_key="test_key",
            )
            db.session.add(task)
            db.session.commit()

            task_dict = task.to_dict()
            assert task_dict["id"] == task.id
            assert task_dict["type"] == "test_task"
            assert task_dict["status"] == "RUNNING"
            assert task_dict["progress"] == 50
            assert task_dict["stage"] == "processing"
            assert task_dict["idempotency_key"] == "test_key"


class TestTaskAPI:
    def test_create_task(self, client):
        response = client.post(
            "/api/tasks",
            json={"type": "example_long_task", "payload": {"min_duration": 1, "max_duration": 2}},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["type"] == "example_long_task"
        assert data["status"] == "PENDING"
        assert data["progress"] == 0

    def test_create_task_with_idempotency_key(self, client):
        idemp_key = "test_idempotency_key_12345"
        
        response1 = client.post(
            "/api/tasks",
            json={
                "type": "example_long_task",
                "idempotency_key": idemp_key,
                "payload": {"data": "first"},
            },
        )
        assert response1.status_code == 201
        data1 = response1.get_json()

        response2 = client.post(
            "/api/tasks",
            json={
                "type": "example_long_task",
                "idempotency_key": idemp_key,
                "payload": {"data": "second"},
            },
        )
        assert response2.status_code == 200
        data2 = response2.get_json()

        assert data1["id"] == data2["id"]
        assert data1["created_at"] == data2["created_at"]

    def test_get_task(self, client, app):
        with app.app_context():
            task = Task(type="test_task", status=TaskStatus.PENDING)
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        response = client.get(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == task_id
        assert data["type"] == "test_task"

    def test_get_task_not_found(self, client):
        response = client.get("/api/tasks/nonexistent_id")
        assert response.status_code == 404

    def test_list_tasks(self, client, app):
        with app.app_context():
            for i in range(5):
                task = Task(type=f"task_{i}", status=TaskStatus.PENDING)
                db.session.add(task)
            db.session.commit()

        response = client.get("/api/tasks?per_page=10")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] >= 5
        assert len(data["items"]) >= 5

    def test_list_tasks_filter_by_status(self, client, app):
        with app.app_context():
            task1 = Task(type="task1", status=TaskStatus.PENDING)
            task2 = Task(type="task2", status=TaskStatus.RUNNING)
            task3 = Task(type="task3", status=TaskStatus.SUCCEEDED)
            db.session.add_all([task1, task2, task3])
            db.session.commit()

        response = client.get("/api/tasks?status=RUNNING")
        assert response.status_code == 200
        data = response.get_json()
        for item in data["items"]:
            assert item["status"] == "RUNNING"

    def test_list_tasks_filter_by_type(self, client, app):
        with app.app_context():
            task1 = Task(type="type_a", status=TaskStatus.PENDING)
            task2 = Task(type="type_b", status=TaskStatus.PENDING)
            db.session.add_all([task1, task2])
            db.session.commit()

        response = client.get("/api/tasks?type=type_a")
        assert response.status_code == 200
        data = response.get_json()
        for item in data["items"]:
            assert item["type"] == "type_a"

    def test_cancel_pending_task(self, client, app):
        with app.app_context():
            task = Task(type="test_task", status=TaskStatus.PENDING)
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        response = client.post(f"/api/tasks/{task_id}/cancel")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "CANCELLED"

    def test_cancel_completed_task(self, client, app):
        with app.app_context():
            task = Task(type="test_task", status=TaskStatus.SUCCEEDED)
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        response = client.post(f"/api/tasks/{task_id}/cancel")
        assert response.status_code == 400


class TestIdempotency:
    def test_concurrent_idempotent_requests(self, client, app):
        import threading

        idemp_key = "concurrent_test_key"
        results = []

        def make_request():
            response = client.post(
                "/api/tasks",
                json={
                    "type": "example_long_task",
                    "idempotency_key": idemp_key,
                },
            )
            results.append((response.status_code, response.get_json()))

        threads = [threading.Thread(target=make_request) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        task_ids = set()
        for status, data in results:
            assert status in (200, 201), f"Unexpected status {status}: {data}"
            task_ids.add(data["id"])

        assert len(task_ids) == 1


class TestTaskExecutor:
    @pytest.mark.asyncio
    async def test_task_context_update_progress(self, app):
        with app.app_context():
            task = Task(type="test_task", status=TaskStatus.PENDING)
            db.session.add(task)
            db.session.commit()
            task_id = task.id

            context = TaskContext(task_id, app)
            context.update_progress(50, "processing")

            db.session.refresh(task)
            assert task.progress == 50
            assert task.stage == "processing"

    @pytest.mark.asyncio
    async def test_task_context_cancel(self, app):
        context = TaskContext("test_id", app)
        assert not context.is_cancelled()
        context.cancel()
        assert context.is_cancelled()

    @pytest.mark.asyncio
    async def test_example_long_task(self, app, executor):
        # Wait for executor to be ready
        await asyncio.sleep(0.1)
        
        with app.app_context():
            task = Task(
                type="example_long_task",
                status=TaskStatus.PENDING,
                payload=json.dumps({"min_duration": 0.5, "max_duration": 1}),
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        executor.submit_task(task_id)
        
        # Wait for task to complete
        for _ in range(30):
            await asyncio.sleep(0.1)
            with app.app_context():
                task = db.session.get(Task, task_id)
                if task and task.status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED):
                    break
        
        with app.app_context():
            task = db.session.get(Task, task_id)
            assert task.status == TaskStatus.SUCCEEDED
            assert task.progress == 100

    @pytest.mark.asyncio
    async def test_task_cancellation(self, app, executor):
        # Wait for executor to be ready
        await asyncio.sleep(0.1)
        
        with app.app_context():
            task = Task(
                type="example_long_task",
                status=TaskStatus.PENDING,
                payload=json.dumps({"min_duration": 5, "max_duration": 10}),
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        executor.submit_task(task_id)
        
        # Wait for task to start running
        for _ in range(20):
            await asyncio.sleep(0.05)
            with app.app_context():
                task = db.session.get(Task, task_id)
                if task and task.status == TaskStatus.RUNNING:
                    break
        
        executor.request_cancel(task_id)
        
        # Wait for cancellation to take effect
        for _ in range(30):
            await asyncio.sleep(0.1)
            with app.app_context():
                task = db.session.get(Task, task_id)
                if task and task.status == TaskStatus.CANCELLED:
                    break
        
        with app.app_context():
            task = db.session.get(Task, task_id)
            assert task.status == TaskStatus.CANCELLED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
