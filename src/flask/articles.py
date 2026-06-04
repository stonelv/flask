from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from .models import Article, db
from .auth import login_required
from sqlalchemy.exc import SQLAlchemyError

# 创建蓝图
articles_bp = Blueprint('articles', __name__, template_folder='templates', static_folder='static')

# 每页显示的文章数量
PER_PAGE = 10

# 文章列表页面（后台）
@articles_bp.route('/admin/articles', methods=['GET'])
@login_required
def index():
    # 获取搜索关键词
    keyword = request.args.get('keyword', '')
    # 获取当前页码
    page = request.args.get('page', 1, type=int)
    
    # 构建查询
    if keyword:
        query = Article.query.filter(Article.title.like(f'%{keyword}%'))
    else:
        query = Article.query
    
    # 按创建时间降序排列，并分页
    articles = query.order_by(Article.created_at.desc()).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )
    
    # 获取当前主题
    theme = session.get('theme', 'light')
    
    # 渲染模板
    return render_template('articles/index.html', articles=articles, keyword=keyword, theme=theme)

# 新建文章页面
@articles_bp.route('/admin/articles/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        # 获取表单数据
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        is_published = 'is_published' in request.form
        
        # 表单验证
        errors = []
        if not title:
            errors.append('标题不能为空')
        elif len(title) > 120:
            errors.append('标题长度不能超过120个字符')
        if not content:
            errors.append('内容不能为空')
        
        if errors:
            # 验证失败，显示错误信息
            for error in errors:
                flash(error, 'danger')
            return render_template('articles/new.html', title=title, content=content, is_published=is_published)
        
        try:
            # 创建新文章
            article = Article(title=title, content=content, is_published=is_published)
            article.save()
            
            flash('文章创建成功', 'success')
            return redirect(url_for('articles.index'))
        except SQLAlchemyError as e:
            # 数据库错误
            db.session.rollback()
            flash(f'创建文章失败：{str(e)}', 'danger')
    
    # GET 请求，渲染新建文章页面
    return render_template('articles/new.html', title='', content='', is_published=False)

# 编辑文章页面
@articles_bp.route('/admin/articles/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    # 获取要编辑的文章
    article = Article.get_by_id(id)
    
    if request.method == 'POST':
        # 获取表单数据
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        is_published = 'is_published' in request.form
        
        # 表单验证
        errors = []
        if not title:
            errors.append('标题不能为空')
        elif len(title) > 120:
            errors.append('标题长度不能超过120个字符')
        if not content:
            errors.append('内容不能为空')
        
        if errors:
            # 验证失败，显示错误信息
            for error in errors:
                flash(error, 'danger')
            return render_template('articles/edit.html', article=article, title=title, content=content, is_published=is_published)
        
        try:
            # 更新文章
            article.update(title=title, content=content, is_published=is_published)
            
            flash('文章更新成功', 'success')
            return redirect(url_for('articles.index'))
        except SQLAlchemyError as e:
            # 数据库错误
            db.session.rollback()
            flash(f'更新文章失败：{str(e)}', 'danger')
    
    # GET 请求，渲染编辑文章页面
    return render_template('articles/edit.html', article=article, title=article.title, content=article.content, is_published=article.is_published)

# 删除文章
@articles_bp.route('/admin/articles/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    try:
        # 获取要删除的文章
        article = Article.get_by_id(id)
        # 删除文章
        article.delete()
        
        flash('文章删除成功', 'success')
    except SQLAlchemyError as e:
        # 数据库错误
        db.session.rollback()
        flash(f'删除文章失败：{str(e)}', 'danger')
    
    # 重定向到文章列表页面
    return redirect(url_for('articles.index'))

# 切换文章发布状态
@articles_bp.route('/admin/articles/<int:id>/toggle_publish', methods=['POST'])
@login_required
def toggle_publish(id):
    try:
        # 获取要切换状态的文章
        article = Article.get_by_id(id)
        # 切换发布状态
        article.update(is_published=not article.is_published)
        
        # 显示相应的提示信息
        if article.is_published:
            flash('文章已发布', 'success')
        else:
            flash('文章已取消发布', 'success')
    except SQLAlchemyError as e:
        # 数据库错误
        db.session.rollback()
        flash(f'切换发布状态失败：{str(e)}', 'danger')
    
    # 重定向到文章列表页面
    return redirect(url_for('articles.index'))

# 前台文章列表页面
@articles_bp.route('/articles', methods=['GET'])
def public_list():
    # 获取当前页码
    page = request.args.get('page', 1, type=int)
    
    # 获取已发布的文章，并分页
    articles = Article.query.filter_by(is_published=True).order_by(Article.created_at.desc()).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )
    
    # 渲染前台文章列表模板
    return render_template('articles/public_list.html', articles=articles)

# 前台文章详情页面
@articles_bp.route('/articles/<int:id>', methods=['GET'])
def public_detail(id):
    # 获取要查看的文章
    article = Article.get_by_id(id)
    
    # 检查文章是否存在或已发布
    if not article or not article.is_published:
        abort(404)
    
    # 渲染前台文章详情模板
    return render_template('articles/public_detail.html', article=article)

# 主题切换
@articles_bp.route('/admin/theme/toggle', methods=['POST'])
@login_required
def toggle_theme():
    # 获取当前主题
    current_theme = session.get('theme', 'light')
    # 切换主题
    new_theme = 'dark' if current_theme == 'light' else 'light'
    # 保存新主题到session
    session['theme'] = new_theme
    
    # 重定向到之前的页面
    return redirect(request.referrer or url_for('articles.index'))
