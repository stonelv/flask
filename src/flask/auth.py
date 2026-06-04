from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps

# 创建蓝图
auth_bp = Blueprint('auth', __name__, template_folder='templates', static_folder='static')

# 固定的用户名和密码
USERNAME = 'admin'
PASSWORD = 'admin123'

# 登录装饰器，用于保护需要登录的路由
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查用户是否已登录
        if 'logged_in' not in session or not session['logged_in']:
            # 保存用户尝试访问的页面，登录后重定向回去
            session['next_url'] = request.url
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# 登录路由
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # 获取表单数据
        username = request.form['username']
        password = request.form['password']
        
        # 验证用户名和密码
        if username == USERNAME and password == PASSWORD:
            # 登录成功，设置session
            session['logged_in'] = True
            session['username'] = username
            
            # 检查是否有保存的重定向URL
            next_url = session.pop('next_url', None)
            if next_url:
                return redirect(next_url)
            
            # 重定向到文章列表页面
            flash('登录成功', 'success')
            return redirect(url_for('articles.index'))
        else:
            # 登录失败，显示错误信息
            flash('用户名或密码错误', 'danger')
    
    # 如果是GET请求，显示登录页面
    return render_template('auth/login.html')

# 登出路由
@auth_bp.route('/logout')
def logout():
    # 清除session中的登录信息
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('已退出登录', 'info')
    # 重定向到登录页面
    return redirect(url_for('auth.login'))
