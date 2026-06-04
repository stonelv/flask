# 文章管理迷你系统

## 功能介绍

这是一个基于 Flask 框架开发的文章管理迷你系统，具有以下功能：

### 1. 用户认证
- 固定用户登录/登出：admin / admin123
- 未登录访问后台需跳转到登录页面
- 登录状态使用 session 管理

### 2. 文章管理
- **文章模型**：id, title, content, is_published(bool), created_at, updated_at
- **后台功能**：
  - 文章列表（分页，每页10条）
  - 按标题关键词搜索文章
  - 新建文章
  - 编辑文章
  - 删除文章
  - 发布/取消发布文章切换
- **前台功能**：
  - 列出已发布文章
  - 查看文章详情

### 3. 主题切换
- 后台页面提供 Light/Dark 主题切换按钮
- 使用 session 保存主题选择
- 页面根元素添加对应 class 实现主题切换

### 4. 表单验证
- 标题必填且长度 1–120 字符
- 内容必填
- 实时表单验证反馈

### 5. 操作反馈
- 使用 flash 显示操作结果（创建成功、更新成功、删除成功、登录失败等）

## 代码结构

```
flask/
├── src/
│   └── flask/
│       ├── auth.py              # 认证功能模块
│       ├── articles.py          # 文章管理功能模块
│       ├── models.py            # 数据模型定义
│       ├── templates/           # 模板文件目录
│       │   ├── base.html        # 基础模板
│       │   ├── auth/            # 认证相关模板
│       │   │   └── login.html   # 登录页面模板
│       │   └── articles/        # 文章相关模板
│       │       ├── index.html       # 文章管理列表模板
│       │       ├── new.html         # 新建文章模板
│       │       ├── edit.html        # 编辑文章模板
│       │       ├── public_list.html # 前台文章列表模板
│       │       └── public_detail.html # 前台文章详情模板
│       └── static/              # 静态文件目录
│           ├── css/              # CSS 样式文件
│           │   └── style.css     # 主样式文件（包含主题切换）
│           └── js/               # JavaScript 文件
│               └── main.js        # 主 JavaScript 文件（表单验证、动画等）
└── tests/
    └── test_article_management.py # 文章管理系统测试文件
```

## 启动方法

### 1. 安装依赖

```bash
# 使用 pip 安装依赖
pip install -e .

# 或者使用 uv 安装依赖
uv sync
```

### 2. 创建数据库表

```bash
# 启动 Python 交互式环境
python

# 在 Python 环境中执行以下代码
from flask import Flask
from src.flask.models import db, Article
from src.flask.auth import auth_bp
from src.flask.articles import articles_bp

# 创建 Flask 应用
app = Flask(__name__)

# 配置数据库
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///articles.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'

# 注册蓝图
app.register_blueprint(auth_bp)
app.register_blueprint(articles_bp)

# 初始化数据库
with app.app_context():
    db.create_all()
    print("数据库表创建成功！")

# 退出 Python 环境
exit()
```

### 3. 启动开发服务器

```bash
# 设置 FLASK_APP 环境变量
set FLASK_APP=src.flask

# 启动开发服务器
flask run
```

### 4. 访问系统

- 前台首页：http://localhost:5000/articles
- 后台登录：http://localhost:5000/login
- 后台文章管理：http://localhost:5000/admin/articles

## 运行测试

### 1. 安装测试依赖

```bash
# 使用 pip 安装测试依赖
pip install -e .[test]

# 或者使用 uv 安装测试依赖
uv sync
```

### 2. 运行测试

```bash
# 运行所有测试
pytest tests/test_article_management.py

# 运行特定测试函数
pytest tests/test_article_management.py::test_login

# 运行测试并显示详细输出
pytest tests/test_article_management.py -v

# 运行测试并生成覆盖率报告
pytest tests/test_article_management.py --cov=src.flask --cov-report=html
```

### 3. 测试用例说明

测试文件包含以下测试用例：

1. `test_login` - 测试登录功能
2. `test_unauthorized_access` - 测试未登录访问限制
3. `test_article_create_and_list` - 测试文章创建与列表功能
4. `test_article_search` - 测试文章搜索功能
5. `test_article_toggle_publish` - 测试文章发布状态切换功能
6. `test_article_delete` - 测试文章删除功能
7. `test_public_articles` - 测试前台文章列表和详情功能
8. `test_theme_toggle` - 测试主题切换功能

## 使用说明

### 1. 登录系统

1. 访问 http://localhost:5000/login
2. 输入用户名：admin
3. 输入密码：admin123
4. 点击登录按钮

### 2. 管理文章

#### 新建文章
1. 登录后点击导航栏中的"新建文章"
2. 输入文章标题（1-120字符）
3. 输入文章内容
4. 选择是否立即发布
5. 点击"创建文章"按钮

#### 编辑文章
1. 在文章管理列表中找到要编辑的文章
2. 点击文章右侧的"编辑"按钮
3. 修改文章标题或内容
4. 调整发布状态
5. 点击"更新文章"按钮

#### 删除文章
1. 在文章管理列表中找到要删除的文章
2. 点击文章右侧的"删除"按钮
3. 确认删除操作

#### 发布/取消发布文章
1. 在文章管理列表中找到要操作的文章
2. 点击文章右侧的"发布"或"取消发布"按钮

#### 搜索文章
1. 在文章管理列表页面的搜索框中输入关键词
2. 点击"搜索"按钮
3. 系统将显示包含关键词的文章列表
4. 点击"清除"按钮可返回完整文章列表

### 3. 主题切换

1. 登录后在文章管理页面
2. 点击右上角的"切换到深色主题"或"切换到浅色主题"按钮
3. 页面将立即切换到相应的主题
4. 主题选择将保存在 session 中，下次登录时会自动应用

### 4. 前台访问

#### 查看文章列表
1. 访问 http://localhost:5000/articles
2. 系统将显示所有已发布的文章列表
3. 点击文章标题可查看文章详情

#### 查看文章详情
1. 在文章列表中点击要查看的文章标题
2. 系统将显示文章的详细内容，包括标题、发布时间、最后更新时间和文章正文
3. 点击"返回文章列表"按钮可返回文章列表页面

## 技术栈

- **后端框架**：Flask 2.x
- **数据库**：SQLite
- **ORM**：SQLAlchemy
- **前端技术**：HTML5, CSS3, JavaScript (ES6+)
- **测试框架**：pytest
- **其他工具**：Werkzeug, Jinja2

## 开发环境要求

- Python 3.8+ 
- pip 或 uv 包管理器
- 现代浏览器（支持 ES6+ 和 CSS Grid）

## 部署建议

### 1. 生产环境配置

```python
# 生产环境配置示例
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///path/to/articles.db'
app.config['SECRET_KEY'] = 'your_secure_secret_key_here'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEBUG'] = False
app.config['TESTING'] = False
```

### 2. 数据库迁移

对于生产环境，建议使用 Flask-Migrate 进行数据库迁移：

```bash
# 安装 Flask-Migrate
pip install flask-migrate

# 初始化迁移环境
flask db init

# 创建迁移脚本
flask db migrate -m "Initial migration"

# 应用迁移
flask db upgrade
```

### 3. 性能优化

- 使用生产级 WSGI 服务器（如 Gunicorn）
- 启用 Flask 缓存
- 优化数据库查询
- 使用 CDN 加速静态文件

### 4. 安全建议

- 使用 HTTPS 协议
- 定期更新依赖包
- 实施 SQL 注入防护
- 实施 XSS 防护
- 配置安全的 CORS 策略
- 定期备份数据库
