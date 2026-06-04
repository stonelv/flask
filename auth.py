from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, request, flash, session

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('请先登录后台管理系统', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == 'admin' and password == 'admin123':
            session['user'] = username
            flash('登录成功！', 'success')
            return redirect(url_for('articles.list'))
        else:
            flash('用户名或密码错误，请重试', 'danger')
            return redirect(url_for('auth.login'))
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    flash('已成功登出', 'info')
    return redirect(url_for('auth.login'))