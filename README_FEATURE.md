# 文章管理迷你系统

这是一个基于 Flask 框架开发的文章管理迷你系统，提供了文章的创建、编辑、删除、发布/取消发布等功能，同时支持前台公开文章展示和后台管理功能。

## 功能特性

### 1. 用户认证
- 固定用户登录：admin / admin123
- 未登录用户访问后台管理页面将自动跳转到登录页面
- 支持用户登出功能

### 2. 文章管理
- **文章模型**：包含 id、title、content、is_published、created_at、updated_at 字段
- **后台功能**：
  - 文章列表（支持分页，每页 10 条）
  - 文章搜索（支持按标题和内容关键词搜索）
  - 新建文章
  - 编辑文章
  - 删除文章
  - 发布/取消发布文章切换
- **前台功能**：
  - 已发布文章列表（支持分页）
  - 文章详情页

### 3. 主题切换
- 后台页面提供 Light/Dark 主题切换按钮
- 使用 session 保存用户的主题选择
- 页面根元素会添加对应的 class（dark-theme）

### 4. 表单验证
- 标题：必填，长度 1–120 个字符
- 内容：必填

### 5. 操作反馈
- 使用 flash 消息显示操作结果（创建成功、更新成功、删除成功、登录失败等）

## 代码结构

```
flask/
├── src/
│   └── flask/
│       ├── __init__.py      # 应用初始化
│       ├── app.py            # 应用核心
│       ├── auth.py           # 用户认证模块
│       ├── articles.py       # 文章管理模块
│       ├── models.py         # 数据模型
│       └── ...
├── templates/
│   ├── auth/
│   │   └── login.html        # 登录页面模板
│   └── articles/
│       ├── index.html         # 后台文章列表模板
│       ├── new.html           # 新建文章模板
│       ├── edit.html          # 编辑文章模板
│       ├── public_index.html  # 前台文章列表模板
│       └── public_show.html   # 前台文章详情模板
├── static/
│   ├── css/
│   │   └── style.css          # 样式文件
│   └── js/
│       └── script.js           # JavaScript 文件
├── tests/
│   └── test_article_management.py  # 文章管理系统测试
└── README_FEATURE.md           # 功能说明文档
```

## 启动方法

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
export FLASK_APP=src.flask
export FLASK_ENV=development
export SECRET_KEY=your_secret_key
export SQLALCHEMY_DATABASE_URI=sqlite:///articles.db
```

### 3. 初始化数据库

```bash
flask shell
>>> from src.flask.models import db
>>> db.create_all()
>>> exit()
```

### 4. 启动应用

```bash
flask run
```

应用将在 `http://localhost:5000` 启动。

## 运行测试

### 1. 安装测试依赖

```bash
pip install pytest pytest-flask beautifulsoup4
```

### 2. 运行测试

```bash
pytest tests/test_article_management.py -v
```

测试将覆盖以下功能：
- 登录功能
- 未登录访问限制
- 创建与列表文章
- 文章搜索
- 发布/取消发布切换
- 删除文章
- 前台公开页面

## 访问方式

### 1. 前台页面

- 文章列表：`http://localhost:5000/articles`
- 文章详情：`http://localhost:5000/articles/<id>`

### 2. 后台管理

- 登录页面：`http://localhost:5000/login`
- 文章管理：`http://localhost:5000/admin/articles`
- 新建文章：`http://localhost:5000/admin/articles/new`
- 编辑文章：`http://localhost:5000/admin/articles/<id>/edit`

## 主题切换

在后台管理页面右上角，点击"切换到暗色主题"或"切换到亮色主题"按钮即可切换主题。主题选择将保存在用户的 session 中，下次访问时会自动应用。

## 技术栈

- **后端**：Flask、SQLAlchemy
- **前端**：HTML、CSS、JavaScript
- **数据库**：SQLite
- **测试**：Pytest、Flask-Testing、BeautifulSoup4

## 开发说明

- 所有代码遵循 Flask 最佳实践
- 模板使用 Jinja2 引擎
- 样式文件支持响应式设计
- JavaScript 实现了交互功能和表单验证
- 测试覆盖了主要功能和边界情况