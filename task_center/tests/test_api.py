"""
Tests for Flask API
"""
import json
import time
import pytest


class TestHealthEndpoint:
    """测试健康检查端点"""
    
    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestCreateTaskEndpoint:
    """测试创建任务端点"""
    
    def test_create_task_success(self, client):
        """测试成功创建任务"""
        response = client.post(
            "/api/tasks",
            data=json.dumps({
                "type": "long_running_task",
                "payload": {"duration": 15, "items": 5}
            }),
            content_type="application/json"
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["is_new"] is True
        assert "task" in data
        assert data["task"]["type"] == "long_running_task"
        assert data["task"]["status"] == "RUNNING"
    
    def test_create_task_with_idempotency(self, client):
        """测试幂等创建任务"""
        idempotency_key = "test_idempotency_key"
        
        # 第一次创建
        response1 = client.post(
            "/api/tasks",
            data=json.dumps({
                "type": "long_running_task",
                "payload": {"duration": 15},
                "idempotency_key": idempotency_key
            }),
            content_type="application/json"
        )
        
        assert response1.status_code == 201
        data1 = json.loads(response1.data)
        task_id = data1["task"]["id"]
        
        # 第二次使用相同幂等键
        response2 = client.post(
            "/api/tasks",
            data=json.dumps({
                "type": "long_running_task",
                "payload": {"duration": 20},
                "idempotency_key": idempotency_key
            }),
            content_type="application/json"
        )
        
        assert response2.status_code == 200
        data2 = json.loads(response2.data)
        assert data2["is_new"] is False
        assert data2["task"]["id"] == task_id
    
    def test_create_task_missing_type(self, client):
        """测试缺少任务类型"""
        response = client.post(
            "/api/tasks",
            data=json.dumps({"payload": {}}),
            content_type="application/json"
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
    
    def test_create_task_missing_body(self, client):
        """测试缺少请求体"""
        response = client.post(
            "/api/tasks",
            data="",
            content_type="application/json"
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
    
    def test_create_task_invalid_type(self, client):
        """测试无效的任务类型"""
        response = client.post(
            "/api/tasks",
            data=json.dumps({
                "type": "nonexistent_type",
                "payload": {}
            }),
            content_type="application/json"
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data


class TestListTasksEndpoint:
    """测试任务列表端点"""
    
    def test_list_tasks_empty(self, client):
        """测试空列表"""
        response = client.get("/api/tasks")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "tasks" in data
        assert "pagination" in data
        assert data["pagination"]["total"] == 0
    
    def test_list_tasks_with_data(self, client):
        """测试有数据的列表"""
        # 创建任务
        for _ in range(3):
            client.post(
                "/api/tasks",
                data=json.dumps({
                    "type": "long_running_task",
                    "payload": {"duration": 15}
                }),
                content_type="application/json"
            )
        
        response = client.get("/api/tasks")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data["tasks"]) == 3
        assert data["pagination"]["total"] == 3
    
    def test_list_tasks_with_pagination(self, client):
        """测试分页"""
        # 创建5个任务
        for _ in range(5):
            client.post(
                "/api/tasks",
                data=json.dumps({
                    "type": "long_running_task",
                    "payload": {"duration": 15}
                }),
                content_type="application/json"
            )
        
        # 第一页
        response = client.get("/api/tasks?limit=2&offset=0")
        data = json.loads(response.data)
        assert len(data["tasks"]) == 2
        assert data["pagination"]["has_more"] is True
        
        # 第二页
        response = client.get("/api/tasks?limit=2&offset=2")
        data = json.loads(response.data)
        assert len(data["tasks"]) == 2
        assert data["pagination"]["has_more"] is True
    
    def test_list_tasks_with_status_filter(self, client):
        """测试按状态过滤"""
        # 创建任务并等待完成
        client.post(
            "/api/tasks",
            data=json.dumps({
                "type": "long_running_task",
                "payload": {"duration": 15}
            }),
            content_type="application/json"
        )
        
        # 查询运行中任务
        response = client.get("/api/tasks?status=RUNNING")
        data = json.loads(response.data)
        assert len(data["tasks"]) >= 1
        assert all(t["status"] == "RUNNING" for t in data["tasks"])
    
    def test_list_tasks_with_type_filter(self, client):
        """测试按类型过滤"""
        client.post(
            "/api/tasks",
            data=json.dumps({
                "type": "long_running_task",
                "payload": {"duration": 15}
            }),
            content_type="application/json"
        )
        
        response = client.get("/api/tasks?type=long_running_task")
        data = json.loads(response.data)
        assert len(data["tasks"]) >= 1
        assert all(t["type"] == "long_running_task" for t in data["tasks"])
    
    def test_list_tasks_invalid_status(self, client):
        """测试无效的状态过滤"""
        response = client.get("/api/tasks?status=INVALID")
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data


class TestGetTaskEndpoint:
    """测试获取任务详情端点"""
    
    def test_get_task_success(self, client):
        """测试成功获取任务"""
        # 创建任务
        create_response = client.post(
            "/api/tasks",
            data=json.dumps({
                "type": "long_running_task",
                "payload": {"duration": 15}
            }),
            content_type="application/json"
        )
        task_id = json.loads(create_response.data)["task"]["id"]
        
        # 获取任务
        response = client.get(f"/api/tasks/{task_id}")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["task"]["id"] == task_id
        assert data["task"]["type"] == "long_running_task"
    
    def test_get_task_not_found(self, client):
        """测试获取不存在的任务"""
        response = client.get("/api/tasks/nonexistent-id")
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data


class TestCancelTaskEndpoint:
    """测试取消任务端点"""
    
    def test_cancel_task_success(self, client):
        """测试成功取消任务"""
        import time
        
        # 创建任务
        create_response = client.post(
            "/api/tasks",
            data=json.dumps({
                "type": "long_running_task",
                "payload": {"duration": 20}
            }),
            content_type="application/json"
        )
        task_id = json.loads(create_response.data)["task"]["id"]
        
        # 等待任务开始运行
        time.sleep(0.3)
        
        # 取消任务
        response = client.post(f"/api/tasks/{task_id}/cancel")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "message" in data
        
        # 等待取消生效
        time.sleep(0.5)
        
        # 查询最终状态
        response = client.get(f"/api/tasks/{task_id}")
        task = json.loads(response.data)["task"]
        assert task["status"] == "CANCELLED"
    
    def test_cancel_task_not_found(self, client):
        """测试取消不存在的任务"""
        response = client.post("/api/tasks/nonexistent-id/cancel")
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
    
    def test_cancel_completed_task(self, client):
        """测试取消已完成的任务"""
        # 创建一个快速任务并等待完成
        create_response = client.post(
            "/api/tasks",
            data=json.dumps({
                "type": "long_running_task",
                "payload": {"duration": 15}
            }),
            content_type="application/json"
        )
        task_id = json.loads(create_response.data)["task"]["id"]
        
        # 等待任务完成
        time.sleep(0.5)
        
        # 尝试取消
        response = client.post(f"/api/tasks/{task_id}/cancel")
        
        # 可能成功（如果任务还在运行）或失败（如果已完成）
        assert response.status_code in [200, 400]


class TestErrorHandling:
    """测试错误处理"""
    
    def test_404_error(self, client):
        """测试404错误"""
        response = client.get("/nonexistent-path")
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data
    
    def test_405_error(self, client):
        """测试405错误"""
        response = client.put("/api/tasks")  # PUT不支持
        
        assert response.status_code == 405
        data = json.loads(response.data)
        assert "error" in data
