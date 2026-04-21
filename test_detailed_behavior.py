"""详细验证当前代码的行为"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flask import Flask, Blueprint, request


def test_detailed_behavior():
    """详细测试当前代码的行为"""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 100

    parent = Blueprint("parent", __name__)
    parent.max_content_length = 150  # 外层

    child = Blueprint("child", __name__)
    child.max_content_length = 200  # 中间层

    grandchild = Blueprint("grandchild", __name__)
    grandchild.max_content_length = 250  # 最内层

    print("=" * 80)
    print("测试设置")
    print("=" * 80)
    print(f"全局 MAX_CONTENT_LENGTH: {app.config['MAX_CONTENT_LENGTH']}")
    print(f"parent.max_content_length: {parent.max_content_length}")
    print(f"child.max_content_length: {child.max_content_length}")
    print(f"grandchild.max_content_length: {grandchild.max_content_length}")
    print()
    print("蓝图嵌套关系:")
    print("  parent (最外层)")
    print("    └── child (中间层)")
    print("         └── grandchild (最内层)")

    @grandchild.post("/test")
    def gc_test():
        print(f"  [视图中] request.endpoint = {request.endpoint}")
        print(f"  [视图中] request.blueprint = {request.blueprint}")
        print(f"  [视图中] request.blueprints = {request.blueprints}")
        print(f"  [视图中] request.max_content_length = {request.max_content_length}")
        return f"max={request.max_content_length}"

    child.register_blueprint(grandchild, url_prefix="/gc")
    parent.register_blueprint(child, url_prefix="/c")
    app.register_blueprint(parent, url_prefix="/p")

    print("\n" + "=" * 80)
    print("app.blueprints 中的内容")
    print("=" * 80)
    for name, bp in app.blueprints.items():
        print(f"  {name}: max_content_length = {bp.max_content_length}")

    client = app.test_client()

    print("\n" + "=" * 80)
    print("发送请求到 /p/c/gc/test")
    print("=" * 80)

    response = client.post("/p/c/gc/test", data="x" * 10)
    result = response.data.decode()
    print(f"响应: {result}")

    print("\n" + "=" * 80)
    print("分析")
    print("=" * 80)
    
    print("""
request.blueprints = ['parent.child.grandchild', 'parent.child', 'parent']

遍历顺序 (for bp_name in req.blueprints):
  1. 'parent.child.grandchild' (最内层)
  2. 'parent.child' (中间层)
  3. 'parent' (最外层)

检查逻辑:
  for bp_name in req.blueprints:
      if bp_name in self.blueprints:
          bp = self.blueprints[bp_name]
          if bp.max_content_length is not None:
              req.max_content_length = bp.max_content_length
              break

所以:
  1. 检查 'parent.child.grandchild'
     - 存在于 app.blueprints 中
     - bp.max_content_length = 250 (不是 None)
     - 设置 req.max_content_length = 250
     - break

结果: 使用了最内层 grandchild 的 250，符合"最内层优先"的预期！
""")

    print("-" * 80)
    print("如果使用 reversed() 会怎样？")
    print("-" * 80)
    print("""
reversed(request.blueprints) = ['parent', 'parent.child', 'parent.child.grandchild']

遍历顺序 (for bp_name in reversed(req.blueprints)):
  1. 'parent' (最外层)
  2. 'parent.child' (中间层)
  3. 'parent.child.grandchild' (最内层)

检查逻辑:
  for bp_name in reversed(req.blueprints):
      if bp_name in self.blueprints:
          bp = self.blueprints[bp_name]
          if bp.max_content_length is not None:
              req.max_content_length = bp.max_content_length
              break

所以:
  1. 检查 'parent'
     - 存在于 app.blueprints 中
     - bp.max_content_length = 150 (不是 None)
     - 设置 req.max_content_length = 150
     - break

结果: 使用了最外层 parent 的 150，与"最内层优先"的预期相反！
""")

    print("=" * 80)
    print("结论")
    print("=" * 80)
    actual_max = int(result.split('=')[1])
    print(f"实际使用的 max_content_length: {actual_max}")
    print(f"期望（最内层优先）: 250")
    print(f"匹配: {actual_max == 250}")
    
    if actual_max == 250:
        print("\n✓ 当前代码实现是正确的！最内层蓝图优先。")
    else:
        print(f"\n✗ 当前代码实现有问题！期望 250，实际 {actual_max}")


if __name__ == '__main__':
    test_detailed_behavior()
