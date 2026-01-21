from flask import Blueprint, Flask
from typing import Any

class ExceptionA(Exception):
    pass

class ExceptionB(Exception):
    pass

class ExceptionC(ExceptionA):
    pass

blueprint = Blueprint('test', __name__)

# 测试1: 基本链式装饰器
@blueprint.errorhandler(ExceptionB)
@blueprint.errorhandler(ExceptionA)
def handle_both(e: Exception) -> str:
    return "error"

# 测试2: 更具体的类型注解
@blueprint.errorhandler(ExceptionB)
@blueprint.errorhandler(ExceptionA)
def handle_specific(e: Any) -> str:
    return "error"

# 测试3: 单独的装饰器
@blueprint.errorhandler(ExceptionC)
def handle_c(e: ExceptionC) -> str:
    return "error c"

# 测试4: 实际使用
app = Flask(__name__)
app.register_blueprint(blueprint)

# 测试触发异常
try:
    raise ExceptionA("Test A")
except Exception:
    pass

try:
    raise ExceptionB("Test B")
except Exception:
    pass

try:
    raise ExceptionC("Test C")
except Exception:
    pass

print("All tests completed")
