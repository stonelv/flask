from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__)

# 固定用户信息
FIXED_USER = {'username': 'admin', 'password': 'admin123'}

# 登录装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# 登录页面
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == FIXED_USER['username'] and password == FIXED_USER['password']:
            session['username'] = username
            flash('登录成功', 'success')
            return redirect(url_for('articles.index'))
        else:
            flash('用户名或密码错误', 'danger')

    return render_template('auth/login.html')

# 登出
@auth_bp.route('/logout')
def logout():
    session.pop('username', None)
    flash('已登出', 'info')
    return redirect(url_for('auth.login'))