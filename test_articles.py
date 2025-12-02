import pytest
from app import create_app
from models import db, Article
from flask import url_for

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

@pytest.fixture
def logged_in_client(client):
    # 登录
    client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    return client

def test_login_success(client):
    """测试1: 正确账号密码登录"""
    response = client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    assert response.status_code == 302
    assert response.location.endswith(url_for('articles.list'))

def test_login_failure(client):
    """测试登录失败"""
    response = client.post('/login', data={'username': 'admin', 'password': 'wrong'})
    assert b'用户名或密码错误' in response.data

def test_unauthorized_access(client):
    """测试2: 未登录用户访问后台被重定向"""
    response = client.get('/admin/articles')
    assert response.status_code == 302
    assert response.location.endswith(url_for('auth.login'))
    
    response = client.get('/admin/articles/new')
    assert response.status_code == 302
    assert response.location.endswith(url_for('auth.login'))

def test_create_and_list_article(logged_in_client):
    """测试3: 创建文章并在列表中显示"""
    # 创建文章
    response = logged_in_client.post('/admin/articles/new', data={
        'title': '测试文章标题',
        'content': '测试文章内容'
    })
    assert response.status_code == 302
    
    # 访问文章列表
    response = logged_in_client.get('/admin/articles')
    assert response.status_code == 200
    assert b'测试文章标题' in response.data

def test_search_article(logged_in_client):
    """测试4: 搜索文章标题"""
    # 创建测试文章
    logged_in_client.post('/admin/articles/new', data={
        'title': 'Flask 入门教程',
        'content': 'Flask 学习内容'
    })
    
    # 搜索存在的标题
    response = logged_in_client.get('/admin/articles?search=Flask')
    assert b'Flask 入门教程' in response.data
    
    # 搜索不存在的标题
    response = logged_in_client.get('/admin/articles?search=Django')
    assert b'暂无文章' in response.data

def test_toggle_publish(logged_in_client):
    """测试5: 切换文章发布状态"""
    # 创建文章
    logged_in_client.post('/admin/articles/new', data={
        'title': '测试发布文章',
        'content': '发布测试内容'
    })
    
    # 获取文章ID
    response = logged_in_client.get('/admin/articles')
    data = response.data.decode('utf-8')
    article_id = data.split('/admin/articles/')[1].split('/edit')[0]
    
    # 切换发布状态
    response = logged_in_client.get(f'/admin/articles/{article_id}/toggle-publish')
    assert response.status_code == 302
    
    # 检查前台是否可见
    response = logged_in_client.get('/')
    assert b'测试发布文章' in response.data
    
    # 取消发布
    response = logged_in_client.get(f'/admin/articles/{article_id}/toggle-publish')
    response = logged_in_client.get('/')
    assert b'测试发布文章' not in response.data

def test_delete_article(logged_in_client):
    """测试6: 删除文章后无法访问"""
    # 创建文章
    logged_in_client.post('/admin/articles/new', data={
        'title': '测试删除文章',
        'content': '删除测试内容'
    })
    
    # 获取文章ID
    response = logged_in_client.get('/admin/articles')
    data = response.data.decode('utf-8')
    article_id = data.split('/admin/articles/')[1].split('/edit')[0]
    
    # 删除文章
    response = logged_in_client.get(f'/admin/articles/{article_id}/delete')
    assert response.status_code == 302
    
    # 尝试访问删除的文章编辑页
    response = logged_in_client.get(f'/admin/articles/{article_id}/edit')
    assert response.status_code == 404
    
    # 尝试访问前台详情页
    response = logged_in_client.get(f'/articles/{article_id}')
    assert response.status_code == 404

def test_form_validation(logged_in_client):
    """测试表单验证"""
    # 空标题
    response = logged_in_client.post('/admin/articles/new', data={
        'title': '',
        'content': '测试内容'
    })
    assert b'标题不能为空' in response.data
    
    # 标题过长
    long_title = 'a' * 121
    response = logged_in_client.post('/admin/articles/new', data={
        'title': long_title,
        'content': '测试内容'
    })
    assert b'标题长度不能超过120个字符' in response.data
    
    # 空内容
    response = logged_in_client.post('/admin/articles/new', data={
        'title': '测试标题',
        'content': ''
    })
    assert b'文章内容不能为空' in response.data