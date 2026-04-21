"""测试嵌套蓝图的 max_content_length 优先级

这个测试文件用于验证：
1. 路由级 max_content_length 最高优先级
2. 最内层（最具体）蓝图优先
3. 未设置时回退到最近祖先
4. 最终回退到全局配置

修复前：测试应该失败（如果外层优先）
修复后：测试应该通过（最内层优先）
"""
from flask import Blueprint, Flask, request


class TestNestedBlueprintMaxContentLength:
    """测试嵌套蓝图的 max_content_length 优先级"""

    def test_innermost_blueprint_priority(self, app: Flask, client):
        """测试最内层蓝图优先

        设置：
        - 全局: 100
        - parent (最外层): 150
        - child (中间层): 200
        - grandchild (最内层): 250

        期望：
        - grandchild_only 使用 250（最内层优先）
        - child_only 使用 200（最内层优先）
        - parent_only 使用 150

        验证方法：
        - 发送 240 字节（介于 200 和 250 之间）
          - 如果使用 250: 240 < 250，成功（200）
          - 如果使用 150 或 200: 240 > 150/200，失败（413）
        """
        app.config["MAX_CONTENT_LENGTH"] = 100

        parent = Blueprint("parent", __name__)
        parent.max_content_length = 150

        child = Blueprint("child", __name__)
        child.max_content_length = 200

        grandchild = Blueprint("grandchild", __name__)
        grandchild.max_content_length = 250

        @parent.post("/parent_only")
        def parent_only():
            return str(len(request.get_data()))

        @child.post("/child_only")
        def child_only():
            return str(len(request.get_data()))

        @grandchild.post("/grandchild_only")
        def grandchild_only():
            return str(len(request.get_data()))

        child.register_blueprint(grandchild, url_prefix="/gc")
        parent.register_blueprint(child, url_prefix="/c")
        app.register_blueprint(parent, url_prefix="/p")

        @app.errorhandler(413)
        def handle_too_large(e):
            return "Too large", 413

        # 测试 parent_only: 应该使用 parent 的 150
        response = client.post("/p/parent_only", data="x" * 140)
        assert response.status_code == 200, (
            "parent_only 应该使用 parent 的 150，140 < 150 应该成功"
        )
        response = client.post("/p/parent_only", data="x" * 160)
        assert response.status_code == 413, (
            "parent_only 应该使用 parent 的 150，160 > 150 应该失败"
        )

        # 测试 child_only: 应该使用 child 的 200（不是 parent 的 150）
        # 发送 180 字节（介于 150 和 200 之间）
        # - 如果使用 200: 180 < 200，成功
        # - 如果使用 150: 180 > 150，失败
        response = client.post("/p/c/child_only", data="x" * 180)
        assert response.status_code == 200, (
            "child_only 应该使用 child 的 200，不是 parent 的 150。"
            "如果这个断言失败，说明实现优先使用了外层蓝图。"
        )
        response = client.post("/p/c/child_only", data="x" * 220)
        assert response.status_code == 413, (
            "child_only 应该使用 child 的 200，220 > 200 应该失败"
        )

        # 测试 grandchild_only: 应该使用 grandchild 的 250
        # 发送 240 字节（介于 200 和 250 之间）
        # - 如果使用 250: 240 < 250，成功
        # - 如果使用 150 或 200: 240 > 150/200，失败
        response = client.post("/p/c/gc/grandchild_only", data="x" * 240)
        assert response.status_code == 200, (
            "grandchild_only 应该使用 grandchild 的 250，不是 child 或 parent 的。"
            "如果这个断言失败，说明实现优先使用了外层蓝图。"
        )
        response = client.post("/p/c/gc/grandchild_only", data="x" * 260)
        assert response.status_code == 413, (
            "grandchild_only 应该使用 grandchild 的 250，260 > 250 应该失败"
        )

    def test_skip_none_values(self, app: Flask, client):
        """测试跳过 None 值，使用最近已设置的祖先

        设置：
        - 全局: 100
        - parent: 150（设置了）
        - child: None（未设置）
        - grandchild: None（未设置）

        期望：
        - grandchild_only 使用 parent 的 150（最近的已设置祖先）
        """
        app.config["MAX_CONTENT_LENGTH"] = 100

        parent = Blueprint("parent", __name__)
        parent.max_content_length = 150

        child = Blueprint("child", __name__)
        # 不设置 child.max_content_length（None）

        grandchild = Blueprint("grandchild", __name__)
        # 不设置 grandchild.max_content_length（None）

        @grandchild.post("/test")
        def gc_test():
            return str(len(request.get_data()))

        child.register_blueprint(grandchild, url_prefix="/gc")
        parent.register_blueprint(child, url_prefix="/c")
        app.register_blueprint(parent, url_prefix="/p")

        @app.errorhandler(413)
        def handle_too_large(e):
            return "Too large", 413

        # 发送 140 字节（介于 100 和 150 之间）
        # - 如果使用 150: 140 < 150，成功
        # - 如果使用 100: 140 > 100，失败
        response = client.post("/p/c/gc/test", data="x" * 140)
        assert response.status_code == 200, (
            "应该使用 parent 的 150，因为 child 和 grandchild 都未设置。"
            "如果这个断言失败，说明实现没有正确跳过 None 值。"
        )
        response = client.post("/p/c/gc/test", data="x" * 160)
        assert response.status_code == 413, (
            "应该使用 parent 的 150，160 > 150 应该失败"
        )

    def test_route_level_highest_priority(self, app: Flask, client):
        """测试路由级 max_content_length 最高优先级

        设置：
        - 全局: 100
        - parent: 150
        - child: 200
        - grandchild: 250
        - 路由级别: 300

        期望：
        - custom_route 使用 300（路由级别最高）
        """
        app.config["MAX_CONTENT_LENGTH"] = 100

        parent = Blueprint("parent", __name__)
        parent.max_content_length = 150

        child = Blueprint("child", __name__)
        child.max_content_length = 200

        grandchild = Blueprint("grandchild", __name__)
        grandchild.max_content_length = 250

        @grandchild.post("/custom", max_content_length=300)
        def custom_route():
            return str(len(request.get_data()))

        child.register_blueprint(grandchild, url_prefix="/gc")
        parent.register_blueprint(child, url_prefix="/c")
        app.register_blueprint(parent, url_prefix="/p")

        @app.errorhandler(413)
        def handle_too_large(e):
            return "Too large", 413

        # 发送 290 字节（介于 250 和 300 之间）
        # - 如果使用 300: 290 < 300，成功
        # - 如果使用 250 或更低: 290 > 250，失败
        response = client.post("/p/c/gc/custom", data="x" * 290)
        assert response.status_code == 200, (
            "应该使用路由级别的 300，不是蓝图级别的。"
            "如果这个断言失败，说明路由级别优先级没有正确实现。"
        )
        response = client.post("/p/c/gc/custom", data="x" * 310)
        assert response.status_code == 413, (
            "应该使用路由级别的 300，310 > 300 应该失败"
        )

    def test_fallback_to_global(self, app: Flask, client):
        """测试所有蓝图都未设置时回退到全局配置

        设置：
        - 全局: 100
        - parent: None
        - child: None
        - grandchild: None

        期望：
        - 使用全局的 100
        """
        app.config["MAX_CONTENT_LENGTH"] = 100

        parent = Blueprint("parent", __name__)
        # 不设置 parent.max_content_length

        child = Blueprint("child", __name__)
        # 不设置 child.max_content_length

        grandchild = Blueprint("grandchild", __name__)
        # 不设置 grandchild.max_content_length

        @grandchild.post("/test")
        def gc_test():
            return str(len(request.get_data()))

        child.register_blueprint(grandchild, url_prefix="/gc")
        parent.register_blueprint(child, url_prefix="/c")
        app.register_blueprint(parent, url_prefix="/p")

        @app.errorhandler(413)
        def handle_too_large(e):
            return "Too large", 413

        response = client.post("/p/c/gc/test", data="x" * 90)
        assert response.status_code == 200, (
            "应该使用全局的 100，90 < 100 应该成功"
        )
        response = client.post("/p/c/gc/test", data="x" * 110)
        assert response.status_code == 413, (
            "应该使用全局的 100，110 > 100 应该失败"
        )
