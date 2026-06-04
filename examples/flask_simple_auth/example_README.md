# Flask Simple Auth

一个简单的Flask API key认证扩展。

## 快速开始

```bash
# 安装扩展
cd examples/flask_simple_auth
pip install -e .

# 运行示例应用
python example_app.py

# 在另一个终端测试
curl http://localhost:5000/
curl -H "X-API-Key: demo-key-123" http://localhost:5000/user-info
```

## 主要特性

- ✅ 简单的API key认证
- ✅ 可配置的header名称
- ✅ 支持静态key列表
- ✅ 支持自定义key验证函数
- ✅ 提供`@require_api_key`装饰器
- ✅ 完整的测试覆盖
- ✅ 易于集成

## 项目结构

```
flask_simple_auth/
├── flask_simple_auth/          # 扩展包
│   ├── __init__.py           # 包初始化
│   ├── extension.py           # 核心扩展类
│   └── decorators.py          # 装饰器
├── tests/                     # 测试文件
│   ├── conftest.py           # 测试配置
│   ├── test_extension.py     # 扩展测试
│   ├── test_decorators.py    # 装饰器测试
│   └── test_integration.py   # 集成测试
├── pyproject.toml            # 项目配置
├── README.md                 # 使用文档
├── LICENSE.txt               # 许可证
└── example_app.py            # 示例应用
```

## 运行测试

```bash
# 运行所有测试
pytest -v

# 运行特定测试文件
pytest tests/test_extension.py -v

# 运行测试并显示覆盖率
pytest --cov=flask_simple_auth --cov-report=html
```

## 使用示例

```python
from flask import Flask, jsonify
from flask_simple_auth import SimpleAuth, require_api_key

app = Flask(__name__)
app.config["SIMPLE_AUTH_STATIC_KEYS"] = {"secret-key"}
auth = SimpleAuth(app)

@app.route("/protected")
@require_api_key()
def protected():
    return jsonify({"message": "This is protected"})

if __name__ == "__main__":
    app.run()
```