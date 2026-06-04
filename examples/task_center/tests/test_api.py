import threading
import time

import pytest

from task_center import create_app
from task_center.models import TaskStatus


@pytest.fixture
def app():
    import tempfile
    import os
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db_url = f"sqlite:///{db_path}"
        app = create_app({"TESTING": True, "TASK_WORKERS": 2, "DATABASE": db_url})
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
    resp_data = resp.get_json()
    assert resp_data["code"] == 0
    data = resp_data["data"]
    assert "id" in data
    assert data["type"] == "quick_task"
    assert data["status"] in ("PENDING", "RUNNING")
    assert data["payload"] == {"key": "value"}


def test_create_task_missing_type(client):
    resp = client.post("/api/tasks", json={"payload": {}})
    assert resp.status_code == 400
    resp_data = resp.get_json()
    assert resp_data["code"] != 0
    assert "message" in resp_data


def test_get_task(client):
    resp = client.post(
        "/api/tasks",
        json={"type": "quick_task", "payload": {}},
    )
    task_id = resp.get_json()["data"]["id"]

    resp = client.get(f"/api/tasks/{task_id}")
    assert resp.status_code == 200
    resp_data = resp.get_json()
    assert resp_data["code"] == 0
    data = resp_data["data"]
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
    resp_data = resp.get_json()
    assert resp_data["code"] == 0
    data = resp_data["data"]
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
    resp_data = resp.get_json()
    assert resp_data["code"] == 0
    data = resp_data["data"]
    assert len(data["tasks"]) == 3
    assert data["pagination"]["page"] == 2
    assert data["pagination"]["per_page"] == 3


def test_list_tasks_filter_by_type(client):
    client.post("/api/tasks", json={"type": "quick_task", "payload": {}})
    client.post("/api/tasks", json={"type": "long_running_task", "payload": {"duration": 1}})

    resp = client.get("/api/tasks?type=quick_task")
    resp_data = resp.get_json()
    assert resp_data["code"] == 0
    data = resp_data["data"]
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
    data1 = resp1.get_json()["data"]

    resp2 = client.post(
        "/api/tasks",
        json={
            "type": "quick_task",
            "payload": {"first": False},
            "idempotency_key": idempotency_key,
        },
    )
    data2 = resp2.get_json()["data"]

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
    task_ids = [r["data"]["id"] for r in results]
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
    task_id = resp.get_json()["data"]["id"]

    time.sleep(0.1)

    cancel_resp = client.post(f"/api/tasks/{task_id}/cancel")
    assert cancel_resp.status_code == 200

    time.sleep(0.1)

    task_resp = client.get(f"/api/tasks/{task_id}")
    task_data = task_resp.get_json()["data"]
    assert task_data["status"] in ("CANCELLED", "RUNNING")

    if task_data["status"] == "RUNNING":
        time.sleep(1)
        task_resp = client.get(f"/api/tasks/{task_id}")
        task_data = task_resp.get_json()["data"]

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
    task_id = resp.get_json()["data"]["id"]

    progresses = []
    for _ in range(10):
        time.sleep(0.08)
        task_resp = client.get(f"/api/tasks/{task_id}")
        data = task_resp.get_json()["data"]
        progresses.append(data["progress"])
        if data["status"] == "SUCCEEDED":
            break

    assert 100 in progresses
    final_resp = client.get(f"/api/tasks/{task_id}")
    assert final_resp.get_json()["data"]["status"] == "SUCCEEDED"


def test_task_status_transitions(app, client):
    executor = app.extensions["task_executor"]

    @executor.register("status_test")
    def status_handler(ctx):
        time.sleep(0.2)
        return {"result": "ok"}

    resp = client.post("/api/tasks", json={"type": "status_test", "payload": {}})
    task_id = resp.get_json()["data"]["id"]
    initial_status = resp.get_json()["data"]["status"]

    assert initial_status in ("PENDING", "RUNNING")

    time.sleep(0.05)
    running_resp = client.get(f"/api/tasks/{task_id}")
    running_status = running_resp.get_json()["data"]["status"]
    assert running_status in ("PENDING", "RUNNING", "SUCCEEDED")

    time.sleep(0.4)
    final_resp = client.get(f"/api/tasks/{task_id}")
    assert final_resp.get_json()["data"]["status"] == "SUCCEEDED"


def test_task_result(client):
    resp = client.post(
        "/api/tasks",
        json={"type": "quick_task", "payload": {"test": 123}},
    )
    task_id = resp.get_json()["data"]["id"]

    time.sleep(1.5)

    final_resp = client.get(f"/api/tasks/{task_id}")
    data = final_resp.get_json()["data"]
    assert data["status"] == "SUCCEEDED"
    assert data["result"] is not None


def test_task_error(app, client):
    executor = app.extensions["task_executor"]

    @executor.register("error_test")
    def error_handler(ctx):
        raise ValueError("Intentional error for testing")

    resp = client.post("/api/tasks", json={"type": "error_test", "payload": {}})
    task_id = resp.get_json()["data"]["id"]

    time.sleep(0.5)

    final_resp = client.get(f"/api/tasks/{task_id}")
    data = final_resp.get_json()["data"]
    assert data["status"] == "FAILED"
    assert data["error"] is not None
    assert "ValueError" in data["error"]


def test_database_persistence(app):
    import os
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_tasks.db")
        db_url = f"sqlite:///{db_path}"
        
        app1 = create_app({"TESTING": True, "TASK_WORKERS": 2, "DATABASE": db_url})
        client1 = app1.test_client()
        
        resp = client1.post(
            "/api/tasks",
            json={"type": "quick_task", "payload": {"persistence": "test"}},
        )
        assert resp.status_code == 201
        task_id = resp.get_json()["data"]["id"]
        
        time.sleep(0.5)
        
        app1.extensions["task_executor"].stop(wait=True)
        del app1
        
        app2 = create_app({"TESTING": True, "TASK_WORKERS": 2, "DATABASE": db_url})
        client2 = app2.test_client()
        
        resp2 = client2.get(f"/api/tasks/{task_id}")
        assert resp2.status_code == 200
        data = resp2.get_json()["data"]
        assert data["id"] == task_id
        assert data["payload"] == {"persistence": "test"}
        assert data["status"] == "SUCCEEDED"
        
        resp3 = client2.get("/api/tasks")
        assert resp3.status_code == 200
        tasks = resp3.get_json()["data"]["tasks"]
        assert len(tasks) >= 1
        
        app2.extensions["task_executor"].stop(wait=True)


def test_db_unique_constraint_concurrent(app):
    results = []
    errors = []
    idempotency_key = "db-concurrent-unique-test"
    
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
                results.append({
                    "status_code": resp.status_code,
                    "json": resp.get_json(),
                })
        except Exception as e:
            errors.append(str(e))
    
    threads = [threading.Thread(target=create_task) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    assert len(errors) == 0, f"Errors: {errors}"
    assert len(results) == 20
    
    for r in results:
        assert r["status_code"] in (201,), f"Unexpected status: {r}"
        assert r["json"]["code"] == 0, f"Unexpected response: {r['json']}"
    
    task_ids = [r["json"]["data"]["id"] for r in results]
    unique_ids = set(task_ids)
    assert len(unique_ids) == 1, f"Expected 1 unique task, got {len(unique_ids)}: {unique_ids}"


def test_invalid_status_param_returns_400(client):
    resp = client.get("/api/tasks?status=INVALID_STATUS")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] != 0
    assert "Invalid 'status'" in data["message"]


def test_invalid_page_param_returns_400(client):
    resp = client.get("/api/tasks?page=not_a_number")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] != 0
    assert "Invalid 'page'" in data["message"]


def test_invalid_per_page_param_returns_400(client):
    resp = client.get("/api/tasks?per_page=invalid")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] != 0
    assert "Invalid 'per_page'" in data["message"]


def test_atomic_claim_no_double_execution(app):
    import os
    import tempfile
    from concurrent.futures import ThreadPoolExecutor as TPE
    from concurrent.futures import wait
    from task_center.models import TaskStorage, TaskStatus

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "claim_test.db")
        db_url = f"sqlite:///{db_path}"

        storage = TaskStorage(db_url)
        storage.init_db()

        execution_count = [0]
        execution_lock = threading.Lock()

        def claim_and_execute(task_id):
            task = storage.claim_for_execution(task_id)
            if task:
                with execution_lock:
                    execution_count[0] += 1
                time.sleep(0.2)
                storage.update(task_id, status=TaskStatus.SUCCEEDED)
                return True
            return False

        task = storage.create("test_type", {"test": "value"})
        assert task is not None
        task_id = task.id

        futures = []
        with TPE(max_workers=10) as executor:
            for _ in range(10):
                fut = executor.submit(claim_and_execute, task_id)
                futures.append(fut)
            wait(futures)

        results = [f.result() for f in futures]
        true_count = sum(1 for r in results if r)

        assert true_count == 1, f"Expected exactly 1 successful claim, got {true_count}"
        assert execution_count[0] == 1, f"Expected execution exactly once, got {execution_count[0]}"

        final_task = storage.get(task_id)
        assert final_task.status == TaskStatus.SUCCEEDED


def test_cancel_persistence_across_restart(app):
    import os
    import tempfile
    from task_center import create_app

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "cancel_test.db")
        db_url = f"sqlite:///{db_path}"

        app1 = create_app({"TESTING": True, "TASK_WORKERS": 1, "DATABASE": db_url})
        client1 = app1.test_client()
        executor1 = app1.extensions["task_executor"]

        @executor1.register("slow_restart_test")
        def slow_handler1(ctx):
            for i in range(20):
                if ctx.check_cancel():
                    raise InterruptedError("Cancelled")
                ctx.update_progress(i * 5, f"Step {i}")
                time.sleep(0.3)
            return {"done": True}

        resp = client1.post("/api/tasks", json={"type": "slow_restart_test", "payload": {}})
        task_id = resp.get_json()["data"]["id"]

        time.sleep(0.2)

        task_before = client1.get(f"/api/tasks/{task_id}").get_json()["data"]
        assert task_before["status"] in ("PENDING", "RUNNING")

        cancel_resp = client1.post(f"/api/tasks/{task_id}/cancel")
        assert cancel_resp.status_code == 200
        cancel_data = cancel_resp.get_json()["data"]
        assert cancel_data["cancel_requested"] == True or cancel_data["status"] == "CANCELLED"

        app1.extensions["task_executor"].stop(wait=False)
        del app1

        app2 = create_app({"TESTING": True, "TASK_WORKERS": 1, "DATABASE": db_url})
        client2 = app2.test_client()
        executor2 = app2.extensions["task_executor"]

        @executor2.register("slow_restart_test")
        def slow_handler2(ctx):
            for i in range(20):
                if ctx.check_cancel():
                    raise InterruptedError("Cancelled")
                ctx.update_progress(i * 5, f"Step {i}")
                time.sleep(0.3)
            return {"done": True}

        task_after = client2.get(f"/api/tasks/{task_id}").get_json()["data"]
        assert task_after["cancel_requested"] == True or task_after["status"] == "CANCELLED"

        if task_after["status"] == "RUNNING":
            time.sleep(1)
            task_final = client2.get(f"/api/tasks/{task_id}").get_json()["data"]
            assert task_final["status"] == "CANCELLED"

        app2.extensions["task_executor"].stop(wait=True)
