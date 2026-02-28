import threading
import time

import pytest

from task_center import create_app
from task_center.models import TaskStatus


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "TASK_WORKERS": 2})
    yield app
    executor = app.extensions["task_executor"]
    executor.stop(wait=True)


@pytest.fixture
def client(app):
    return app.test_client()


def test_create_task(client):
    resp = client.post(
        "/api/tasks",
        json={"type": "quick_task", "payload": {"key": "value"}},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert "id" in data
    assert data["type"] == "quick_task"
    assert data["status"] in ("PENDING", "RUNNING")
    assert data["payload"] == {"key": "value"}


def test_create_task_missing_type(client):
    resp = client.post("/api/tasks", json={"payload": {}})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_get_task(client):
    resp = client.post(
        "/api/tasks",
        json={"type": "quick_task", "payload": {}},
    )
    task_id = resp.get_json()["id"]

    resp = client.get(f"/api/tasks/{task_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == task_id


def test_get_task_not_found(client):
    resp = client.get("/api/tasks/nonexistent")
    assert resp.status_code == 404


def test_list_tasks(client):
    for i in range(5):
        client.post(
            "/api/tasks",
            json={"type": "quick_task", "payload": {"index": i}},
        )

    resp = client.get("/api/tasks")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "tasks" in data
    assert "pagination" in data
    assert len(data["tasks"]) >= 5
    assert data["pagination"]["total"] >= 5


def test_list_tasks_pagination(client):
    for i in range(10):
        client.post(
            "/api/tasks",
            json={"type": "quick_task", "payload": {"index": i}},
        )

    resp = client.get("/api/tasks?per_page=3&page=2")
    data = resp.get_json()
    assert len(data["tasks"]) == 3
    assert data["pagination"]["page"] == 2
    assert data["pagination"]["per_page"] == 3


def test_list_tasks_filter_by_type(client):
    client.post("/api/tasks", json={"type": "quick_task", "payload": {}})
    client.post("/api/tasks", json={"type": "long_running_task", "payload": {"duration": 1}})

    resp = client.get("/api/tasks?type=quick_task")
    data = resp.get_json()
    for task in data["tasks"]:
        assert task["type"] == "quick_task"


def test_idempotency_key(client):
    idempotency_key = "test-key-12345"

    resp1 = client.post(
        "/api/tasks",
        json={
            "type": "quick_task",
            "payload": {"first": True},
            "idempotency_key": idempotency_key,
        },
    )
    data1 = resp1.get_json()

    resp2 = client.post(
        "/api/tasks",
        json={
            "type": "quick_task",
            "payload": {"first": False},
            "idempotency_key": idempotency_key,
        },
    )
    data2 = resp2.get_json()

    assert data1["id"] == data2["id"]
    assert data1["payload"] == data2["payload"]


def test_idempotency_concurrent(app, client):
    results = []
    errors = []
    idempotency_key = "concurrent-test-key"

    def create_task():
        try:
            with app.test_client() as c:
                resp = c.post(
                    "/api/tasks",
                    json={
                        "type": "quick_task",
                        "payload": {},
                        "idempotency_key": idempotency_key,
                    },
                )
                results.append(resp.get_json())
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=create_task) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(results) == 10
    task_ids = [r["id"] for r in results]
    assert len(set(task_ids)) == 1


def test_cancel_pending_task(client):
    storage = client.application.extensions["task_storage"]
    executor = client.application.extensions["task_executor"]
    executor._handlers.pop("delayed_test", None)

    @executor.register("delayed_test")
    def delayed_handler(ctx):
        for i in range(10):
            if ctx.check_cancel():
                raise InterruptedError("Cancelled")
            ctx.update_progress(i * 10, f"Step {i}")
            time.sleep(0.5)
        return {"done": True}

    resp = client.post("/api/tasks", json={"type": "delayed_test", "payload": {}})
    task_id = resp.get_json()["id"]

    time.sleep(0.1)

    cancel_resp = client.post(f"/api/tasks/{task_id}/cancel")
    assert cancel_resp.status_code == 200

    time.sleep(0.1)

    task_resp = client.get(f"/api/tasks/{task_id}")
    task_data = task_resp.get_json()
    assert task_data["status"] in ("CANCELLED", "RUNNING")

    if task_data["status"] == "RUNNING":
        time.sleep(1)
        task_resp = client.get(f"/api/tasks/{task_id}")
        task_data = task_resp.get_json()

    assert task_data["status"] == "CANCELLED"


def test_task_progress(app, client):
    executor = app.extensions["task_executor"]

    @executor.register("progress_test")
    def progress_handler(ctx):
        stages = [25, 50, 75, 100]
        for p in stages:
            ctx.update_progress(p, f"Stage {p}%")
            if ctx.check_cancel():
                break
            time.sleep(0.1)
        return {"done": True}

    resp = client.post("/api/tasks", json={"type": "progress_test", "payload": {}})
    task_id = resp.get_json()["id"]

    progresses = []
    for _ in range(10):
        time.sleep(0.08)
        task_resp = client.get(f"/api/tasks/{task_id}")
        data = task_resp.get_json()
        progresses.append(data["progress"])
        if data["status"] == "SUCCEEDED":
            break

    assert 100 in progresses
    final_resp = client.get(f"/api/tasks/{task_id}")
    assert final_resp.get_json()["status"] == "SUCCEEDED"


def test_task_status_transitions(app, client):
    executor = app.extensions["task_executor"]

    @executor.register("status_test")
    def status_handler(ctx):
        time.sleep(0.2)
        return {"result": "ok"}

    resp = client.post("/api/tasks", json={"type": "status_test", "payload": {}})
    task_id = resp.get_json()["id"]
    initial_status = resp.get_json()["status"]

    assert initial_status in ("PENDING", "RUNNING")

    time.sleep(0.05)
    running_resp = client.get(f"/api/tasks/{task_id}")
    running_status = running_resp.get_json()["status"]
    assert running_status in ("PENDING", "RUNNING", "SUCCEEDED")

    time.sleep(0.4)
    final_resp = client.get(f"/api/tasks/{task_id}")
    assert final_resp.get_json()["status"] == "SUCCEEDED"


def test_task_result(client):
    resp = client.post(
        "/api/tasks",
        json={"type": "quick_task", "payload": {"test": 123}},
    )
    task_id = resp.get_json()["id"]

    time.sleep(1.5)

    final_resp = client.get(f"/api/tasks/{task_id}")
    data = final_resp.get_json()
    assert data["status"] == "SUCCEEDED"
    assert data["result"] is not None


def test_task_error(app, client):
    executor = app.extensions["task_executor"]

    @executor.register("error_test")
    def error_handler(ctx):
        raise ValueError("Intentional error for testing")

    resp = client.post("/api/tasks", json={"type": "error_test", "payload": {}})
    task_id = resp.get_json()["id"]

    time.sleep(0.5)

    final_resp = client.get(f"/api/tasks/{task_id}")
    data = final_resp.get_json()
    assert data["status"] == "FAILED"
    assert data["error"] is not None
    assert "ValueError" in data["error"]
