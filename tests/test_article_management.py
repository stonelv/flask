import pytest
import warnings
from flask import Flask
from src.flask.auth import auth_bp
from src.flask.articles import articles_bp
from src.flask.models import db, Article
import os

# 禁用资源警告
warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.filterwarnings("ignore", category=pytest.PytestUnraisableExceptionWarning)

# 修改pytest配置以禁用资源警告
def pytest_configure(config):
    config.addinivalue_line(
        "filterwarnings", "ignore::ResourceWarning"
    )
    config.addinivalue_line(
        "filterwarnings", "ignore::pytest.PytestUnraisableExceptionWarning"
    )

# 创建测试应用
@pytest.fixture
def app():
    # 创建Flask应用
    app = Flask(__name__)
    
    # 配置测试环境
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SECRET_KEY'] = 'test_secret_key'
    
    # 配置SQLite数据库（内存中）
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 初始化数据库
    db.init_app(app)
    
    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(articles_bp)
    
    # 初始化数据库表
    with app.app_context():
        db.create_all()
        
        # 添加一些测试数据
        test_article1 = Article(title='测试文章1', content='这是第一篇测试文章的内容', is_published=True)
        test_article2 = Article(title='测试文章2', content='这是第二篇测试文章的内容', is_published=False)
        test_article3 = Article(title='Flask教程', content='这是一篇关于Flask的教程文章', is_published=True)
        
        db.session.add_all([test_article1, test_article2, test_article3])
        db.session.commit()
    
    yield app
    
    # 清理测试数据
    with app.app_context():
        db.drop_all()
        # 关闭数据库连接
        db.session.remove()
        db.engine.dispose()

# 创建测试客户端
@pytest.fixture
def client(app):
    return app.test_client()

# 创建数据库会话
@pytest.fixture
def db_session(app):
    """创建数据库会话fixture，用于测试数据库操作"""
    with app.app_context():
        # 开始事务
        db.session.begin()
        
        # 提供会话给测试用例
        yield db.session
        
        # 回滚事务
        db.session.rollback()
        
        # 关闭数据库连接
        db.session.remove()
        db.engine.dispose()

# 测试结束后清理数据库连接
@pytest.fixture(scope='session', autouse=True)
def cleanup_database():
    """测试会话结束后清理数据库连接的fixture（不访问db.engine）"""
    yield
    
    # 不尝试访问 db.engine，因为 app 已经被销毁了
    pass

# 测试登录功能
def test_login(client, db_session):
    try:
        # 测试正确的用户名和密码
        response = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        assert response.status_code == 200
        assert '文章管理' in response.get_data(as_text=True)
        assert '新建文章' in response.get_data(as_text=True)

        # 测试错误的用户名和密码
        response = client.post('/login', data={'username': 'wrong', 'password': 'wrong'}, follow_redirects=True)
        assert response.status_code == 200
        assert '用户名或密码错误' in response.get_data(as_text=True)
    finally:
        # 关闭数据库连接
        db.session.remove()
        db.engine.dispose()

# 测试未登录访问限制
def test_unauthorized_access(client):
    # 尝试访问文章管理页面
    response = client.get('/admin/articles', follow_redirects=True)
    assert response.status_code == 200
    assert '请先登录' in response.get_data(as_text=True)
    
    # 尝试访问新建文章页面
    response = client.get('/admin/articles/new', follow_redirects=True)
    assert response.status_code == 200
    assert '请先登录' in response.get_data(as_text=True)

# 测试文章创建与列表功能
def test_article_create_and_list(client):
    # 登录
    client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    
    # 测试创建新文章
    response = client.post('/admin/articles/new', data={
        'title': '新创建的文章',
        'content': '这是新创建的文章的内容',
        'is_published': 'on'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert '文章创建成功' in response.get_data(as_text=True)
    assert '新创建的文章' in response.get_data(as_text=True)
    
    # 测试文章列表
    response = client.get('/admin/articles')
    assert response.status_code == 200
    assert '测试文章1' in response.get_data(as_text=True)
    assert '测试文章2' in response.get_data(as_text=True)
    assert 'Flask教程' in response.get_data(as_text=True)
    assert '新创建的文章' in response.get_data(as_text=True)

# 测试文章搜索功能
def test_article_search(client):
    # 登录
    client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    
    # 测试搜索"测试"关键词
    response = client.get('/admin/articles?keyword=测试')
    assert response.status_code == 200
    assert '测试文章1' in response.get_data(as_text=True)
    assert '测试文章2' in response.get_data(as_text=True)
    assert 'Flask教程' not in response.get_data(as_text=True)
    
    # 测试搜索"Flask"关键词
    response = client.get('/admin/articles?keyword=Flask')
    assert response.status_code == 200
    assert 'Flask教程' in response.get_data(as_text=True)
    assert '测试文章1' not in response.get_data(as_text=True)
    assert '测试文章2' not in response.get_data(as_text=True)
    
    # 测试搜索不存在的关键词
    response = client.get('/admin/articles?keyword=不存在的关键词')
    assert response.status_code == 200
    assert '没有找到与' in response.get_data(as_text=True)

# 测试文章发布状态切换功能
def test_article_toggle_publish(client):
    # 登录
    client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    
    # 测试将草稿文章发布
    response = client.post('/admin/articles/2/toggle_publish', follow_redirects=True)
    assert response.status_code == 200
    assert '文章已发布' in response.get_data(as_text=True)
    
    # 验证文章状态已更新
    with client.application.app_context():
        from src.flask.models import db
        article = db.session.get(Article, 2)
        assert article.is_published == True
    
    # 测试将已发布文章设为草稿
    response = client.post('/admin/articles/2/toggle_publish', follow_redirects=True)
    assert response.status_code == 200
    assert '文章已取消发布' in response.get_data(as_text=True)
    
    # 验证文章状态已更新
    with client.application.app_context():
        from src.flask.models import db
        article = db.session.get(Article, 2)
        assert article.is_published == False

# 测试文章删除功能
def test_article_delete(client):
    # 登录
    client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    
    # 测试删除文章
    response = client.post('/admin/articles/1/delete', follow_redirects=True)
    assert response.status_code == 200
    assert '文章删除成功' in response.get_data(as_text=True)
    
    # 验证文章已删除
    with client.application.app_context():
        from src.flask.models import db
        article = db.session.get(Article, 1)
        assert article is None
    
    # 测试删除不存在的文章
    response = client.post('/admin/articles/999/delete', follow_redirects=True)
    assert response.status_code == 404

# 测试前台文章列表和详情功能
def test_public_articles(client):
    # 测试前台文章列表
    response = client.get('/articles')
    assert response.status_code == 200
    assert '文章列表' in response.get_data(as_text=True)
    assert '测试文章1' in response.get_data(as_text=True)
    assert 'Flask教程' in response.get_data(as_text=True)
    assert '测试文章2' not in response.get_data(as_text=True)  # 草稿文章不应显示在前台
    
    # 测试文章详情页面
    response = client.get('/articles/1')
    assert response.status_code == 200
    assert '测试文章1' in response.get_data(as_text=True)
    assert '这是第一篇测试文章的内容' in response.get_data(as_text=True)
    
    # 测试访问草稿文章的详情页面
    response = client.get('/articles/2')
    assert response.status_code == 404
    
    # 测试访问不存在的文章
    response = client.get('/articles/999')
    assert response.status_code == 404

# 测试主题切换功能
def test_theme_toggle(client):
    # 登录
    client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    
    # 测试切换到深色主题
    response = client.post('/admin/theme/toggle', follow_redirects=True)
    assert response.status_code == 200
    
    # 验证主题已切换（通过检查session）
    with client.session_transaction() as sess:
        assert sess.get('theme') == 'dark'
    
    # 测试切换回浅色主题
    response = client.post('/admin/theme/toggle', follow_redirects=True)
    assert response.status_code == 200
    
    # 验证主题已切换
    with client.session_transaction() as sess:
        assert sess.get('theme') == 'light'
