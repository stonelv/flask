import pytest
from flask import Flask
from src.flask.auth import auth_bp
from src.flask.articles import articles_bp
from src.flask.models import db, Article

@pytest.fixture
def app():
    """创建并配置一个测试 Flask 应用"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test_secret_key'

    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(articles_bp)

    # 初始化数据库
    with app.app_context():
        db.init_app(app)
        db.create_all()

    yield app

    # 清理数据库
    with app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()

@pytest.fixture
def logged_in_client(client):
    """创建已登录的测试客户端"""
    # 登录
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'文章管理' in response.data

    return client

def test_login(client):
    """测试登录功能"""
    # 测试正确的登录凭据
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'文章管理' in response.data
    assert b'登出' in response.data

    # 测试错误的登录凭据
    response = client.post('/login', data={
        'username': 'wrong_user',
        'password': 'wrong_password'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'用户名或密码错误' in response.data

def test_unauthorized_access(client):
    """测试未登录用户访问后台管理页面"""
    # 尝试访问文章列表页面
    response = client.get('/admin/articles', follow_redirects=True)

    assert response.status_code == 200
    assert b'请先登录' in response.data
    assert b'登录' in response.data

    # 尝试访问新建文章页面
    response = client.get('/admin/articles/new', follow_redirects=True)

    assert response.status_code == 200
    assert b'请先登录' in response.data
    assert b'登录' in response.data

def test_create_and_list_article(logged_in_client):
    """测试创建文章和文章列表功能"""
    # 创建一篇文章
    response = logged_in_client.post('/admin/articles/new', data={
        'title': '测试文章',
        'content': '这是一篇测试文章的内容。' 
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'文章创建成功' in response.data
    assert b'测试文章' in response.data

    # 检查文章是否在列表中
    response = logged_in_client.get('/admin/articles')

    assert response.status_code == 200
    assert b'测试文章' in response.data
    assert b'这是一篇测试文章的内容。' in response.data

def test_search_article(logged_in_client):
    """测试文章搜索功能"""
    # 创建两篇文章
    logged_in_client.post('/admin/articles/new', data={
        'title': 'Python 教程',
        'content': '这是一篇关于 Python 编程的教程。' 
    }, follow_redirects=True)

    logged_in_client.post('/admin/articles/new', data={
        'title': 'Flask 教程',
        'content': '这是一篇关于 Flask Web 框架的教程。' 
    }, follow_redirects=True)

    # 搜索 "Python"
    response = logged_in_client.get('/admin/articles?search=Python')

    assert response.status_code == 200
    assert b'Python 教程' in response.data
    assert b'Flask 教程' not in response.data

    # 搜索 "Flask"
    response = logged_in_client.get('/admin/articles?search=Flask')

    assert response.status_code == 200
    assert b'Flask 教程' in response.data
    assert b'Python 教程' not in response.data

    # 搜索 "教程"
    response = logged_in_client.get('/admin/articles?search=教程')

    assert response.status_code == 200
    assert b'Python 教程' in response.data
    assert b'Flask 教程' in response.data

def test_toggle_publish_article(logged_in_client):
    """测试文章发布/取消发布功能"""
    # 创建一篇文章
    response = logged_in_client.post('/admin/articles/new', data={
        'title': '测试发布文章',
        'content': '这是一篇测试发布功能的文章。' 
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'文章创建成功' in response.data

    # 检查文章初始状态为草稿
    response = logged_in_client.get('/admin/articles')
    assert b'草稿' in response.data

    # 发布文章
    # 首先找到文章的 ID
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.data, 'html.parser')
    article_row = soup.find('tr', contains='测试发布文章')
    article_id = article_row.find('td').text

    # 发送发布请求
    response = logged_in_client.post(f'/admin/articles/{article_id}/toggle_publish', follow_redirects=True)

    assert response.status_code == 200
    assert b'文章已发布' in response.data

    # 检查文章状态为已发布
    response = logged_in_client.get('/admin/articles')
    assert b'已发布' in response.data

    # 取消发布文章
    response = logged_in_client.post(f'/admin/articles/{article_id}/toggle_publish', follow_redirects=True)

    assert response.status_code == 200
    assert b'文章已取消发布' in response.data

    # 检查文章状态为草稿
    response = logged_in_client.get('/admin/articles')
    assert b'草稿' in response.data

def test_delete_article(logged_in_client):
    """测试删除文章功能"""
    # 创建一篇文章
    response = logged_in_client.post('/admin/articles/new', data={
        'title': '测试删除文章',
        'content': '这是一篇测试删除功能的文章。' 
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'文章创建成功' in response.data

    # 找到文章的 ID
    from bs4 import BeautifulSoup
    response = logged_in_client.get('/admin/articles')
    soup = BeautifulSoup(response.data, 'html.parser')
    article_row = soup.find('tr', contains='测试删除文章')
    article_id = article_row.find('td').text

    # 删除文章
    response = logged_in_client.post(f'/admin/articles/{article_id}/delete', follow_redirects=True)

    assert response.status_code == 200
    assert b'文章删除成功' in response.data

    # 检查文章是否已删除
    response = logged_in_client.get('/admin/articles')
    assert b'测试删除文章' not in response.data

    # 尝试访问已删除文章的编辑页面
    response = logged_in_client.get(f'/admin/articles/{article_id}/edit', follow_redirects=True)
    assert response.status_code == 404

def test_public_article_pages(client, logged_in_client):
    """测试前台公开文章页面"""
    # 创建两篇文章，一篇发布，一篇草稿
    logged_in_client.post('/admin/articles/new', data={
        'title': '公开文章',
        'content': '这是一篇公开的文章，所有人都可以看到。' 
    }, follow_redirects=True)

    logged_in_client.post('/admin/articles/new', data={
        'title': '草稿文章',
        'content': '这是一篇草稿文章，只有管理员可以看到。' 
    }, follow_redirects=True)

    # 发布第一篇文章
    from bs4 import BeautifulSoup
    response = logged_in_client.get('/admin/articles')
    soup = BeautifulSoup(response.data, 'html.parser')
    article_rows = soup.find_all('tr')
    public_article_id = article_rows[1].find('td').text  # 第一篇文章

    logged_in_client.post(f'/admin/articles/{public_article_id}/toggle_publish', follow_redirects=True)

    # 测试前台文章列表页面
    response = client.get('/articles')

    assert response.status_code == 200
    assert b'文章列表' in response.data
    assert b'公开文章' in response.data
    assert b'草稿文章' not in response.data

    # 测试前台文章详情页面
    response = client.get(f'/articles/{public_article_id}')

    assert response.status_code == 200
    assert b'公开文章' in response.data
    assert b'这是一篇公开的文章，所有人都可以看到。' in response.data

    # 尝试访问草稿文章的详情页面
    draft_article_id = article_rows[2].find('td').text  # 第二篇文章
    response = client.get(f'/articles/{draft_article_id}', follow_redirects=True)
    assert response.status_code == 404