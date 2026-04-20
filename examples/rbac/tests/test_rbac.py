import pytest
from base64 import b64encode


FORBIDDEN_MESSAGE = "Forbidden: You do not have permission to access this resource."


def get_auth_header(username, password):
    return {
        "Authorization": "Basic " + b64encode(f"{username}:{password}".encode()).decode()
    }


class TestLogin:
    def test_successful_login_admin(self, client):
        response = client.post(
            "/login",
            headers=get_auth_header("admin_user", "admin123")
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == "admin_user"
        assert data["role"] == "admin"

    def test_successful_login_editor(self, client):
        response = client.post(
            "/login",
            headers=get_auth_header("editor_user", "editor123")
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == "editor_user"
        assert data["role"] == "editor"

    def test_successful_login_viewer(self, client):
        response = client.post(
            "/login",
            headers=get_auth_header("viewer_user", "viewer123")
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == "viewer_user"
        assert data["role"] == "viewer"

    def test_failed_login_invalid_credentials(self, client):
        response = client.post(
            "/login",
            headers=get_auth_header("invalid_user", "wrongpassword")
        )
        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == FORBIDDEN_MESSAGE

    def test_failed_login_no_auth(self, client):
        response = client.post("/login")
        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == FORBIDDEN_MESSAGE


class TestManageUsersEndpoint:
    def test_admin_can_access_manage(self, client):
        response = client.get(
            "/api/manage",
            headers=get_auth_header("admin_user", "admin123")
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Admin management access granted"

    def test_editor_cannot_access_manage(self, client):
        response = client.get(
            "/api/manage",
            headers=get_auth_header("editor_user", "editor123")
        )
        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == FORBIDDEN_MESSAGE

    def test_viewer_cannot_access_manage(self, client):
        response = client.get(
            "/api/manage",
            headers=get_auth_header("viewer_user", "viewer123")
        )
        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == FORBIDDEN_MESSAGE

    def test_no_auth_cannot_access_manage(self, client):
        response = client.get("/api/manage")
        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == FORBIDDEN_MESSAGE


class TestContentReadEndpoint:
    def test_admin_can_read_content(self, client):
        response = client.get(
            "/api/content",
            headers=get_auth_header("admin_user", "admin123")
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Content read access granted"

    def test_editor_can_read_content(self, client):
        response = client.get(
            "/api/content",
            headers=get_auth_header("editor_user", "editor123")
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Content read access granted"

    def test_viewer_can_read_content(self, client):
        response = client.get(
            "/api/content",
            headers=get_auth_header("viewer_user", "viewer123")
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Content read access granted"

    def test_no_auth_cannot_read_content(self, client):
        response = client.get("/api/content")
        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == FORBIDDEN_MESSAGE


class TestContentWriteEndpoint:
    def test_admin_can_create_content(self, client):
        response = client.post(
            "/api/content",
            headers=get_auth_header("admin_user", "admin123")
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Content created"

    def test_admin_can_update_content(self, client):
        response = client.put(
            "/api/content",
            headers=get_auth_header("admin_user", "admin123")
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Content updated"

    def test_admin_can_delete_content(self, client):
        response = client.delete(
            "/api/content",
            headers=get_auth_header("admin_user", "admin123")
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Content deleted"

    def test_editor_can_create_content(self, client):
        response = client.post(
            "/api/content",
            headers=get_auth_header("editor_user", "editor123")
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Content created"

    def test_editor_can_update_content(self, client):
        response = client.put(
            "/api/content",
            headers=get_auth_header("editor_user", "editor123")
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Content updated"

    def test_editor_can_delete_content(self, client):
        response = client.delete(
            "/api/content",
            headers=get_auth_header("editor_user", "editor123")
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Content deleted"

    def test_viewer_cannot_create_content(self, client):
        response = client.post(
            "/api/content",
            headers=get_auth_header("viewer_user", "viewer123")
        )
        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == FORBIDDEN_MESSAGE

    def test_viewer_cannot_update_content(self, client):
        response = client.put(
            "/api/content",
            headers=get_auth_header("viewer_user", "viewer123")
        )
        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == FORBIDDEN_MESSAGE

    def test_viewer_cannot_delete_content(self, client):
        response = client.delete(
            "/api/content",
            headers=get_auth_header("viewer_user", "viewer123")
        )
        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == FORBIDDEN_MESSAGE

    def test_no_auth_cannot_create_content(self, client):
        response = client.post("/api/content")
        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == FORBIDDEN_MESSAGE

    def test_no_auth_cannot_update_content(self, client):
        response = client.put("/api/content")
        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == FORBIDDEN_MESSAGE

    def test_no_auth_cannot_delete_content(self, client):
        response = client.delete("/api/content")
        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == FORBIDDEN_MESSAGE


class TestForbiddenMessageConsistency:
    def test_all_forbidden_responses_have_same_message(self, client):
        endpoints = [
            ("/api/manage", "GET"),
            ("/api/content", "GET"),
            ("/api/content", "POST"),
            ("/api/content", "PUT"),
            ("/api/content", "DELETE"),
            ("/login", "POST"),
        ]
        
        messages = set()
        for endpoint, method in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint)
            elif method == "PUT":
                response = client.put(endpoint)
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            assert response.status_code == 403
            data = response.get_json()
            messages.add(data["error"])
        
        assert len(messages) == 1
        assert list(messages)[0] == FORBIDDEN_MESSAGE
