import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock
from task_center.database import Task, TaskStatus, db_session
from task_center.executor import executor, example_long_task, register_task_type, get_task_func


# Fast test task for integration tests
async def fast_test_task(payload, progress_callback, cancel_event):
    """A fast task for testing"""
    await progress_callback(50, "working")
    await asyncio.sleep(0.1)
    return {"status": "done"}


register_task_type("fast_test", fast_test_task)


class TestIdempotency:
    """Test idempotent task creation"""

    def test_create_task_with_idempotency_key(self, client):
        """Test that tasks with same idempotency_key return same task"""
        idemp_key = "test-idemp-key-123"

        # First request
        response1 = client.post("/api/tasks", json={
            "type": "example_long_task",
            "idempotency_key": idemp_key,
            "payload": {"data": "test1"}
        })
        assert response1.status_code == 201
        result1 = response1.get_json()
        assert result1["error"] is None
        task1 = result1["data"]

        # Second request with same key
        response2 = client.post("/api/tasks", json={
            "type": "example_long_task",
            "idempotency_key": idemp_key,
            "payload": {"data": "test2"}
        })
        assert response2.status_code == 200
        result2 = response2.get_json()
        assert result2["error"] is None
        task2 = result2["data"]

        # Should return same task
        assert task1["id"] == task2["id"]
        assert task1["payload"]["data"] == "test1"

    def test_create_task_different_keys(self, client):
        """Test that different idempotency keys create different tasks"""
        response1 = client.post("/api/tasks", json={
            "type": "example_long_task",
            "idempotency_key": "key-1",
        })
        response2 = client.post("/api/tasks", json={
            "type": "example_long_task",
            "idempotency_key": "key-2",
        })

        assert response1.status_code == 201
        assert response2.status_code == 201
        result1 = response1.get_json()
        result2 = response2.get_json()
        assert result1["error"] is None
        assert result2["error"] is None
        assert result1["data"]["id"] != result2["data"]["id"]

    def test_create_task_no_idempotency_key(self, client):
        """Test creating task without idempotency key"""
        response = client.post("/api/tasks", json={
            "type": "example_long_task",
        })
        assert response.status_code == 201
        result = response.get_json()
        assert result["error"] is None
        task = result["data"]
        assert task["idempotency_key"] is None


class TestTaskCRUD:
    """Test task CRUD operations"""

    def test_get_task(self, client):
        """Test getting a task by ID"""
        response = client.post("/api/tasks", json={
            "type": "example_long_task",
        })
        assert response.status_code == 201
        result = response.get_json()
        assert result["error"] is None
        task = result["data"]

        response = client.get(f"/api/tasks/{task['id']}")
        assert response.status_code == 200
        result = response.get_json()
        assert result["error"] is None
        fetched = result["data"]
        assert fetched["id"] == task["id"]

    def test_get_task_not_found(self, client):
        """Test getting non-existent task"""
        response = client.get("/api/tasks/non-existent-id")
        assert response.status_code == 404
        result = response.get_json()
        assert result["error"] == "Task not found"

    def test_list_tasks(self, client):
        """Test listing tasks"""
        # Create some tasks
        for i in range(5):
            client.post("/api/tasks", json={
                "type": "example_long_task",
                "idempotency_key": f"list-test-{i}",
            })

        response = client.get("/api/tasks")
        assert response.status_code == 200
        result = response.get_json()
        assert result["error"] is None
        data = result["data"]
        assert data["total"] >= 5
        assert len(data["items"]) == min(5, data["per_page"])

    def test_list_tasks_filter_by_type(self, client):
        """Test filtering tasks by type"""
        client.post("/api/tasks", json={
            "type": "example_long_task",
            "idempotency_key": "filter-type-1",
        })

        response = client.get("/api/tasks?type=example_long_task")
        assert response.status_code == 200
        result = response.get_json()
        assert result["error"] is None
        data = result["data"]
        for task in data["items"]:
            assert task["type"] == "example_long_task"

    def test_list_tasks_pagination(self, client):
        """Test task pagination"""
        for i in range(25):
            client.post("/api/tasks", json={
                "type": "example_long_task",
                "idempotency_key": f"paginate-{i}",
            })

        response = client.get("/api/tasks?page=2&per_page=10")
        assert response.status_code == 200
        result = response.get_json()
        assert result["error"] is None
        data = result["data"]
        assert data["page"] == 2
        assert len(data["items"]) == 10


class TestTaskCancellation:
    """Test task cancellation"""

    def test_cancel_pending_task(self, client):
        """Test cancelling a pending task"""
        response = client.post("/api/tasks", json={
            "type": "example_long_task",
        })
        assert response.status_code == 201
        result = response.get_json()
        assert result["error"] is None
        task = result["data"]

        response = client.post(f"/api/tasks/{task['id']}/cancel")
        assert response.status_code == 200
        result = response.get_json()
        assert result["error"] is None

        # Verify status
        response = client.get(f"/api/tasks/{task['id']}")
        result = response.get_json()
        assert result["data"]["status"] == "CANCELLED"

    def test_cancel_completed_task(self, client):
        """Test cancelling a completed task fails"""
        # Create and manually mark as completed
        response = client.post("/api/tasks", json={
            "type": "example_long_task",
        })
        assert response.status_code == 201
        result = response.get_json()
        assert result["error"] is None
        task = result["data"]

        db_task = db_session.get(Task, task["id"])
        db_task.status = TaskStatus.SUCCEEDED
        db_session.commit()

        response = client.post(f"/api/tasks/{task['id']}/cancel")
        assert response.status_code == 400
        result = response.get_json()
        assert result["error"] is not None

    def test_cancel_nonexistent_task(self, client):
        """Test cancelling non-existent task"""
        response = client.post("/api/tasks/non-existent/cancel")
        assert response.status_code == 404
        result = response.get_json()
        assert result["error"] == "Task not found"


class TestTaskStatus:
    """Test task status transitions"""

    @pytest.mark.asyncio
    async def test_task_progress_updates(self):
        """Test that task progress is updated during execution"""
        # Create a mock task that reports progress
        progress_updates = []

        async def mock_progress(progress, stage):
            progress_updates.append((progress, stage))

        cancel_event = asyncio.Event()

        # Run a quick version of the task
        with patch('random.randint', return_value=1):
            try:
                await example_long_task({}, mock_progress, cancel_event)
            except:
                pass

        # Should have some progress updates
        assert len(progress_updates) > 0

    def test_task_executes_and_completes(self, client):
        """Test that a task actually executes and completes"""
        import time
        
        # Create a fast test task
        response = client.post("/api/tasks", json={
            "type": "fast_test",
            "idempotency_key": "execute-test-1",
        })
        assert response.status_code == 201
        result = response.get_json()
        assert result["error"] is None
        task = result["data"]
        task_id = task["id"]

        # Wait for task to complete (max 5 seconds)
        task_data = None
        for i in range(50):
            response = client.get(f"/api/tasks/{task_id}")
            result = response.get_json()
            task_data = result["data"]
            if task_data["status"] in ["SUCCEEDED", "FAILED", "CANCELLED"]:
                break
            time.sleep(0.1)

        # Verify the task completed
        response = client.get(f"/api/tasks/{task_id}")
        result = response.get_json()
        task_data = result["data"]
        
        # Check that the task succeeded
        assert task_data["status"] == "SUCCEEDED", f"Task failed with status: {task_data['status']}, error: {task_data['error']}"
        
        # Check that progress was updated
        assert task_data["progress"] == 100
        assert task_data["result"] == {"status": "done"}

    def test_task_initial_status(self, client):
        """Test task starts with PENDING status"""
        response = client.post("/api/tasks", json={
            "type": "example_long_task",
        })
        assert response.status_code == 201
        result = response.get_json()
        assert result["error"] is None
        task = result["data"]
        assert task["status"] == "PENDING"
        assert task["progress"] == 0


class TestTaskValidation:
    """Test task validation"""

    def test_create_task_invalid_type(self, client):
        """Test creating task with invalid type"""
        response = client.post("/api/tasks", json={
            "type": "non_existent_type",
        })
        assert response.status_code == 400
        result = response.get_json()
        assert result["message"] is not None  # Error in message field

    def test_create_task_missing_type(self, client):
        """Test creating task without type"""
        response = client.post("/api/tasks", json={
            "payload": {"test": "data"},
        })
        assert response.status_code == 400
        result = response.get_json()
        assert result["message"] is not None

    def test_invalid_status_filter(self, client):
        """Test filtering with invalid status"""
        response = client.get("/api/tasks?status=INVALID_STATUS")
        assert response.status_code == 400
        result = response.get_json()
        assert result["error"] is not None


# Test counter for idempotency test
_execution_counter = {}


class TestConcurrentIdempotency:
    """Test concurrent idempotent task creation - database atomic guarantee"""

    def test_concurrent_requests_same_idempotency_key(self, app):
        """Test that concurrent POST requests with same idempotency_key only create one task
        
        This tests the database-level atomic guarantee: insert first, then handle unique conflict.
        Uses an execution counter to prove the task only executes once.
        """
        import threading
        import time
        from task_center.executor import register_task_type, _task_registry
        
        global _execution_counter
        test_key = "concurrent-idempotency-test-key"
        _execution_counter[test_key] = 0
        
        # Create a tracking task that increments a counter when executed
        async def tracked_task(payload, progress_callback, cancel_event):
            global _execution_counter
            _execution_counter[test_key] += 1
            await asyncio.sleep(0.2)  # Simulate work
            return {"counter": _execution_counter[test_key]}
        
        # Register the test task type
        register_task_type("tracked_test", tracked_task)
        
        # Number of concurrent threads
        NUM_THREADS = 20
        results = []
        errors = []
        
        def make_request():
            try:
                with app.test_client() as client:
                    response = client.post("/api/tasks", json={
                        "type": "tracked_test",
                        "idempotency_key": test_key,
                        "payload": {"thread": threading.get_ident()}
                    })
                    results.append((response.status_code, response.get_json()))
            except Exception as e:
                errors.append(str(e))
        
        # Start all threads at roughly the same time
        threads = [threading.Thread(target=make_request) for _ in range(NUM_THREADS)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Collect all task IDs returned
        task_ids = []
        for status, data in results:
            assert status in [200, 201], f"Unexpected status {status}: {data}"
            assert data["error"] is None
            task_ids.append(data["data"]["id"])
        
        # All requests should return the SAME task ID
        unique_task_ids = set(task_ids)
        assert len(unique_task_ids) == 1, \
            f"Expected 1 unique task ID, got {len(unique_task_ids)}: {unique_task_ids}"
        
        # Verify only one task in database with this idempotency_key
        from task_center.database import Task, db_session
        tasks = db_session.query(Task).filter_by(idempotency_key=test_key).all()
        assert len(tasks) == 1, f"Expected 1 task in DB, got {len(tasks)}"
        
        # Wait for task to execute and verify it only ran ONCE
        time.sleep(1.0)  # Give time for task to complete
        assert _execution_counter[test_key] == 1, \
            f"Task should execute exactly once, but executed {_execution_counter[test_key]} times"
        
        # Cleanup
        del _execution_counter[test_key]
        if "tracked_test" in _task_registry:
            del _task_registry["tracked_test"]


class TestCancelStateConsistency:
    """Test that CANCELLED state is preserved and not overwritten"""

    def test_cancelled_task_stays_cancelled(self, client):
        """Test that once cancelled, a task cannot be changed to SUCCEEDED/FAILED"""
        import time
        
        # Create a task
        response = client.post("/api/tasks", json={
            "type": "example_long_task",
        })
        assert response.status_code == 201
        result = response.get_json()
        task_id = result["data"]["id"]
        
        # Give it a moment to start
        time.sleep(0.1)
        
        # Cancel the task
        response = client.post(f"/api/tasks/{task_id}/cancel")
        assert response.status_code == 200
        
        # Verify cancelled state
        response = client.get(f"/api/tasks/{task_id}")
        result = response.get_json()
        assert result["data"]["status"] == "CANCELLED"
        assert result["data"]["cancelled_at"] is not None
        
        # Wait and verify status remains CANCELLED
        time.sleep(2.0)
        response = client.get(f"/api/tasks/{task_id}")
        result = response.get_json()
        
        # The task must stay CANCELLED - this is the key assertion
        assert result["data"]["status"] == "CANCELLED", \
            f"Task status changed from CANCELLED to {result['data']['status']}"
        assert result["data"]["cancelled_at"] is not None
        
        # Verify result/error are not set (or error indicates cancellation)
        if result["data"]["error"]:
            assert "cancelled" in result["data"]["error"].lower()

    def test_cancel_before_execution_preserves_state(self, client):
        """Test cancelling a task before it starts preserves CANCELLED state"""
        import time
        from task_center.executor import register_task_type, _task_registry
        
        # Create a task that signals when it starts
        started_event = []
        
        async def signal_task(payload, progress_callback, cancel_event):
            started_event.append(True)
            await asyncio.sleep(1.0)
            return {"done": True}
        
        register_task_type("signal_test", signal_task)
        
        # Create and immediately cancel
        response = client.post("/api/tasks", json={
            "type": "signal_test",
        })
        assert response.status_code == 201
        result = response.get_json()
        assert result["error"] is None
        task_id = result["data"]["id"]
        
        # Cancel immediately (before execution starts)
        response = client.post(f"/api/tasks/{task_id}/cancel")
        assert response.status_code == 200
        result = response.get_json()
        assert result["error"] is None
        
        # Wait and check
        time.sleep(0.5)
        response = client.get(f"/api/tasks/{task_id}")
        result = response.get_json()
        
        # Task should remain CANCELLED
        assert result["data"]["status"] == "CANCELLED"
        assert result["data"]["cancelled_at"] is not None
        
        # Cleanup
        if "signal_test" in _task_registry:
            del _task_registry["signal_test"]
