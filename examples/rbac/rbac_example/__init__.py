from functools import wraps

from flask import Flask, request, jsonify, g

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key"


ROLES = {
    "admin": {"read", "write", "delete", "manage"},
    "editor": {"read", "write"},
    "viewer": {"read"},
}

USERS = {
    "admin_user": {"password": "admin123", "role": "admin"},
    "editor_user": {"password": "editor123", "role": "editor"},
    "viewer_user": {"password": "viewer123", "role": "viewer"},
}


class PermissionError(Exception):
    pass


def check_permission(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, "user") or not g.user:
                return jsonify({"error": "Forbidden: You do not have permission to access this resource."}), 403
            
            user_role = g.user.get("role")
            if not user_role or user_role not in ROLES:
                return jsonify({"error": "Forbidden: You do not have permission to access this resource."}), 403
            
            role_permissions = ROLES.get(user_role, set())
            if permission not in role_permissions:
                return jsonify({"error": "Forbidden: You do not have permission to access this resource."}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.authorization
        if not auth:
            return jsonify({"error": "Forbidden: You do not have permission to access this resource."}), 403
        
        username = auth.username
        password = auth.password
        
        user = USERS.get(username)
        if not user or user.get("password") != password:
            return jsonify({"error": "Forbidden: You do not have permission to access this resource."}), 403
        
        g.user = {"username": username, "role": user.get("role")}
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def index():
    return "RBAC Example API"


@app.route("/login", methods=["POST"])
def login():
    auth = request.authorization
    if not auth:
        return jsonify({"error": "Forbidden: You do not have permission to access this resource."}), 403
    
    username = auth.username
    password = auth.password
    
    user = USERS.get(username)
    if not user or user.get("password") != password:
        return jsonify({"error": "Forbidden: You do not have permission to access this resource."}), 403
    
    return jsonify({
        "message": "Login successful",
        "username": username,
        "role": user.get("role")
    })


@app.route("/api/manage", methods=["GET"])
@login_required
@check_permission("manage")
def manage_users():
    return jsonify({
        "message": "Admin management access granted",
        "users": list(USERS.keys())
    })


@app.route("/api/content", methods=["GET"])
@login_required
@check_permission("read")
def get_content():
    return jsonify({
        "message": "Content read access granted",
        "content": "Sample content"
    })


@app.route("/api/content", methods=["POST"])
@login_required
@check_permission("write")
def create_content():
    return jsonify({
        "message": "Content created",
        "user": g.user.get("username")
    })


@app.route("/api/content", methods=["PUT"])
@login_required
@check_permission("write")
def update_content():
    return jsonify({
        "message": "Content updated",
        "user": g.user.get("username")
    })


@app.route("/api/content", methods=["DELETE"])
@login_required
@check_permission("write")
def delete_content():
    return jsonify({
        "message": "Content deleted",
        "user": g.user.get("username")
    })
