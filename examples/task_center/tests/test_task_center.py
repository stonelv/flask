import os
import tempfile
import time

import pytest
from task_center import create_app
from task_center import init_db
from task_center import TaskStatus
from task_center.executor import TaskExecutor


def quick_test_task(payload, progress_callback, token):
    for i in range(5):
        if token.is_cancelled:
            return {"status": "cancelled", "completed_steps": i}
        progress_callback((i + 1) * 20, f"Step {i + 1}")
        time.sleep(0.1)
    return {"status": "completed", "steps": 5}


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()

    app = create_app()
    app.config["DATABASE"] = db_path

    with app.app_context():
        init_db()

    executor = app.extensions["task_executor"]
    executor.register_handler("quick_test", quick_test_task)

    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


class TestCreateTask:
    def test_create_task_success(self, client):
        response = client.post(
            "/api/tasks",
            json={"type": "quick_test", "payload": {"key": "value"}},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert "task" in data
        task = data["task"]
        assert task["type"] == "quick_test"
        assert task["status"] == TaskStatus.PENDING.value
        assert task["payload"] == {"key": "value"}
        assert task["progress"] == 0
        assert "id" in task

    def test_create_task_missing_type(self, client):
        response = client.post("/api/tasks", json={"payload": {}})
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_task_idempotency(self, client):
        idempotency_key = "test-idempotency-key-123"

        response1 = client.post(
            "/api/tasks",
            json={
                "type": "quick_test",
                "payload": {"test": 1},
                "idempotency_key": idempotency_key,
            },
        )
        assert response1.status_code == 201
        task1 = response1.get_json()["task"]

        response2 = client.post(
            "/api/tasks",
            json={
                "type": "quick_test",
                "payload": {"test": 2},
                "idempotency_key": idempotency_key,
            },
        )
        assert response2.status_code == 201
        task2 = response2.get_json()["task"]

        assert task1["id"] == task2["id"]
        assert task1["payload"] == task2["payload"]

    def test_create_task_different_idempotency_keys(self, client):
        response1 = client.post(
            "/api/tasks",
            json={
                "type": "quick_test",
                "idempotency_key": "key-1",
            },
        )
        response2 = client.post(
            "/api/tasks",
            json={
                "type": "quick_test",
                "idempotency_key": "key-2",
            },
        )

        task1 = response1.get_json()["task"]
        task2 = response2.get_json()["task"]

        assert task1["id"] != task2["id"]


class TestGetTask:
    def test_get_task_success(self, client):
        create_response = client.post(
            "/api/tasks", json={"type": "quick_test"}
        )
        task_id = create_response.get_json()["task"]["id"]

        response = client.get(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["task"]["id"] == task_id

    def test_get_task_not_found(self, client):
        response = client.get("/api/tasks/non-existent-id")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data


class TestListTasks:
    def test_list_tasks_empty(self, client):
        response = client.get("/api/tasks")
        assert response.status_code == 200
        data = response.get_json()
        assert data["tasks"] == []
        assert data["pagination"]["total"] == 0

    def test_list_tasks_with_data(self, client):
        for i in range(5):
            client.post(
                "/api/tasks",
                json={"type": "quick_test", "payload": {"index": i}},
            )

        response = client.get("/api/tasks")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["tasks"]) == 5
        assert data["pagination"]["total"] == 5

    def test_list_tasks_pagination(self, client):
        for i in range(25):
            client.post(
                "/api/tasks",
                json={"type": "quick_test"},
            )

        response = client.get("/api/tasks?page=2&per_page=10")
        data = response.get_json()
        assert len(data["tasks"]) == 10
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["per_page"] == 10
        assert data["pagination"]["total"] == 25
        assert data["pagination"]["pages"] == 3

    def test_list_tasks_filter_by_status(self, client):
        client.post("/api/tasks", json={"type": "quick_test"})

        response = client.get("/api/tasks?status=PENDING")
        assert response.status_code == 200
        data = response.get_json()
        for task in data["tasks"]:
            assert task["status"] == TaskStatus.PENDING.value

    def test_list_tasks_filter_by_type(self, client):
        client.post("/api/tasks", json={"type": "quick_test"})

        response = client.get("/api/tasks?type=quick_test")
        assert response.status_code == 200
        data = response.get_json()
        for task in data["tasks"]:
            assert task["type"] == "quick_test"

    def test_list_tasks_invalid_status(self, client):
        response = client.get("/api/tasks?status=INVALID")
        assert response.status_code == 400


class TestCancelTask:
    def test_cancel_pending_task(self, client):
        create_response = client.post(
            "/api/tasks",
            json={"type": "quick_test"},
        )
        task_id = create_response.get_json()["task"]["id"]

        response = client.post(f"/api/tasks/{task_id}/cancel")
        assert response.status_code == 200
        data = response.get_json()
        assert data["task"]["status"] == TaskStatus.CANCELLED.value

    def test_cancel_non_existent_task(self, client):
        response = client.post("/api/tasks/non-existent-id/cancel")
        assert response.status_code == 404

    def test_cancel_running_task(self, client):
        create_response = client.post(
            "/api/tasks",
            json={"type": "quick_test"},
        )
        task_id = create_response.get_json()["task"]["id"]

        time.sleep(0.2)

        cancel_response = client.post(f"/api/tasks/{task_id}/cancel")
        assert cancel_response.status_code == 200

        time.sleep(0.5)

        get_response = client.get(f"/api/tasks/{task_id}")
        task = get_response.get_json()["task"]
        assert task["status"] in [TaskStatus.CANCELLED.value, TaskStatus.SUCCEEDED.value]


class TestTaskStatus:
    def test_task_status_transitions(self, client):
        response = client.post(
            "/api/tasks",
            json={"type": "quick_test"},
        )
        task_id = response.get_json()["task"]["id"]

        time.sleep(0.3)

        get_response = client.get(f"/api/tasks/{task_id}")
        task = get_response.get_json()["task"]
        assert task["status"] in [
            TaskStatus.PENDING.value,
            TaskStatus.RUNNING.value,
            TaskStatus.SUCCEEDED.value,
        ]

    def test_task_progress_updates(self, client):
        response = client.post(
            "/api/tasks",
            json={"type": "quick_test"},
        )
        task_id = response.get_json()["task"]["id"]

        time.sleep(0.3)

        get_response = client.get(f"/api/tasks/{task_id}")
        task = get_response.get_json()["task"]
        if task["status"] == TaskStatus.RUNNING.value:
            assert task["progress"] >= 0
            assert task["progress"] <= 100
            assert task["stage"] != ""

    def test_task_completes_successfully(self, client):
        response = client.post(
            "/api/tasks",
            json={"type": "quick_test"},
        )
        task_id = response.get_json()["task"]["id"]

        time.sleep(1)

        get_response = client.get(f"/api/tasks/{task_id}")
        task = get_response.get_json()["task"]
        assert task["status"] == TaskStatus.SUCCEEDED.value
        assert task["progress"] == 100
        assert task["result"]["status"] == "completed"


class TestTaskStore:
    def test_create_and_retrieve_task(self, app):
        from task_center import get_task_store

        with app.app_context():
            store = get_task_store()
            task = store.create_task("test_type", {"key": "value"})

            retrieved = store.get_by_id(task.id)
            assert retrieved is not None
            assert retrieved.id == task.id
            assert retrieved.type == "test_type"
            assert retrieved.payload == {"key": "value"}

    def test_update_task(self, app):
        from task_center import get_task_store

        with app.app_context():
            store = get_task_store()
            task = store.create_task("test_type")

            updated = store.update_task(
                task.id,
                status=TaskStatus.RUNNING,
                progress=50,
                stage="processing",
            )

            assert updated is not None
            assert updated.status == TaskStatus.RUNNING
            assert updated.progress == 50
            assert updated.stage == "processing"

    def test_cancel_task(self, app):
        from task_center import get_task_store

        with app.app_context():
            store = get_task_store()
            task = store.create_task("test_type")

            cancelled = store.cancel_task(task.id)

            assert cancelled is not None
            assert cancelled.status == TaskStatus.CANCELLED

    def test_idempotency_key_uniqueness(self, app):
        from task_center import get_task_store

        with app.app_context():
            store = get_task_store()

            task1 = store.create_task("test_type", idempotency_key="unique-key")
            task2 = store.create_task("test_type", idempotency_key="unique-key")

            assert task1.id == task2.id

    def test_list_tasks_with_filters(self, app):
        from task_center import get_task_store

        with app.app_context():
            store = get_task_store()

            store.create_task("type_a", idempotency_key="a1")
            store.create_task("type_b", idempotency_key="b1")
            store.create_task("type_a", idempotency_key="a2")

            tasks_a, total_a = store.list_tasks(task_type="type_a")
            assert total_a == 2

            tasks_b, total_b = store.list_tasks(task_type="type_b")
            assert total_b == 1

    def test_progress_bounds(self, app):
        from task_center import get_task_store

        with app.app_context():
            store = get_task_store()
            task = store.create_task("test_type")

            updated = store.update_task(task.id, progress=150)
            assert updated.progress == 100

            updated = store.update_task(task.id, progress=-10)
            assert updated.progress == 0
