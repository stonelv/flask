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
        task1 = response1.get_json()

        # Second request with same key
        response2 = client.post("/api/tasks", json={
            "type": "example_long_task",
            "idempotency_key": idemp_key,
            "payload": {"data": "test2"}
        })
        assert response2.status_code == 200
        task2 = response2.get_json()

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
        assert response1.get_json()["id"] != response2.get_json()["id"]

    def test_create_task_no_idempotency_key(self, client):
        """Test creating task without idempotency key"""
        response = client.post("/api/tasks", json={
            "type": "example_long_task",
        })
        assert response.status_code == 201
        task = response.get_json()
        assert task["idempotency_key"] is None


class TestTaskCRUD:
    """Test task CRUD operations"""

    def test_get_task(self, client):
        """Test getting a task by ID"""
        response = client.post("/api/tasks", json={
            "type": "example_long_task",
        })
        assert response.status_code == 201
        task = response.get_json()

        response = client.get(f"/api/tasks/{task['id']}")
        assert response.status_code == 200
        fetched = response.get_json()
        assert fetched["id"] == task["id"]

    def test_get_task_not_found(self, client):
        """Test getting non-existent task"""
        response = client.get("/api/tasks/non-existent-id")
        assert response.status_code == 404

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
        data = response.get_json()
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
        data = response.get_json()
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
        data = response.get_json()
        assert data["page"] == 2
        assert len(data["items"]) == 10


class TestTaskCancellation:
    """Test task cancellation"""

    def test_cancel_pending_task(self, client):
        """Test cancelling a pending task"""
        response = client.post("/api/tasks", json={
            "type": "example_long_task",
        })
        task = response.get_json()

        response = client.post(f"/api/tasks/{task['id']}/cancel")
        assert response.status_code == 200

        # Verify status
        response = client.get(f"/api/tasks/{task['id']}")
        assert response.get_json()["status"] == "CANCELLED"

    def test_cancel_completed_task(self, client):
        """Test cancelling a completed task fails"""
        # Create and manually mark as completed
        response = client.post("/api/tasks", json={
            "type": "example_long_task",
        })
        task = response.get_json()

        db_task = db_session.get(Task, task["id"])
        db_task.status = TaskStatus.SUCCEEDED
        db_session.commit()

        response = client.post(f"/api/tasks/{task['id']}/cancel")
        assert response.status_code == 400

    def test_cancel_nonexistent_task(self, client):
        """Test cancelling non-existent task"""
        response = client.post("/api/tasks/non-existent/cancel")
        assert response.status_code == 404


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
        task = response.get_json()
        task_id = task["id"]

        # Wait for task to complete (max 5 seconds)
        for i in range(50):
            response = client.get(f"/api/tasks/{task_id}")
            task_data = response.get_json()
            if task_data["status"] in ["SUCCEEDED", "FAILED", "CANCELLED"]:
                break
            time.sleep(0.1)

        # Verify the task completed
        response = client.get(f"/api/tasks/{task_id}")
        task_data = response.get_json()
        
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
        task = response.get_json()
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

    def test_create_task_missing_type(self, client):
        """Test creating task without type"""
        response = client.post("/api/tasks", json={
            "payload": {"test": "data"},
        })
        assert response.status_code == 400

    def test_invalid_status_filter(self, client):
        """Test filtering with invalid status"""
        response = client.get("/api/tasks?status=INVALID_STATUS")
        assert response.status_code == 400
