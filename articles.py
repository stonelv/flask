from flask import Blueprint, render_template, redirect, url_for, request, flash, session, abort
from models import db, Article
from auth import login_required

articles_bp = Blueprint('articles', __name__)

# 后台文章列表
@articles_bp.route('/admin/articles')
@login_required
def list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    
    query = Article.query
    if search:
        query = query.filter(Article.title.contains(search))
    
    pagination = query.order_by(Article.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('admin/articles/list.html', 
                           pagination=pagination, search=search)

# 新建文章
@articles_bp.route('/admin/articles/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        
        # 表单验证
        if not title:
            flash('标题不能为空', 'danger')
            return redirect(url_for('articles.new'))
        if len(title) > 120:
            flash('标题长度不能超过120个字符', 'danger')
            return redirect(url_for('articles.new'))
        if not content:
            flash('文章内容不能为空', 'danger')
            return redirect(url_for('articles.new'))
        
        article = Article(title=title, content=content)
        db.session.add(article)
        db.session.commit()
        
        flash('文章创建成功', 'success')
        return redirect(url_for('articles.list'))
    
    return render_template('admin/articles/form.html')

# 编辑文章
@articles_bp.route('/admin/articles/<int:article_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(article_id):
    article = db.session.get(Article, article_id)
    if not article:
        abort(404)
    
    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        
        # 表单验证
        if not title:
            flash('标题不能为空', 'danger')
            return redirect(url_for('articles.edit', article_id=article_id))
        if len(title) > 120:
            flash('标题长度不能超过120个字符', 'danger')
            return redirect(url_for('articles.edit', article_id=article_id))
        if not content:
            flash('文章内容不能为空', 'danger')
            return redirect(url_for('articles.edit', article_id=article_id))
        
        article.title = title
        article.content = content
        db.session.commit()
        
        flash('文章更新成功', 'success')
        return redirect(url_for('articles.list'))
    
    return render_template('admin/articles/form.html', article=article)

# 删除文章
@articles_bp.route('/admin/articles/<int:article_id>/delete')
@login_required
def delete(article_id):
    article = db.session.get(Article, article_id)
    if not article:
        abort(404)
    db.session.delete(article)
    db.session.commit()
    
    flash('文章已删除', 'success')
    return redirect(url_for('articles.list'))

# 切换发布状态
@articles_bp.route('/admin/articles/<int:article_id>/toggle-publish')
@login_required
def toggle_publish(article_id):
    article = db.session.get(Article, article_id)
    if not article:
        abort(404)
    article.is_published = not article.is_published
    db.session.commit()
    
    status = '发布' if article.is_published else '取消发布'
    flash(f'文章已{status}', 'success')
    return redirect(url_for('articles.list'))

# 前台文章列表
@articles_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    
    pagination = (Article.query.filter_by(is_published=True)
        .order_by(Article.created_at.desc())
        .paginate(page=page, per_page=10, error_out=False))
    
    return render_template('front/index.html', pagination=pagination)

# 前台文章详情
@articles_bp.route('/articles/<int:article_id>')
def detail(article_id):
    article = db.session.get(Article, article_id)
    if not article or not article.is_published:
        abort(404)
    return render_template('front/detail.html', article=article)

# 主题切换
@articles_bp.route('/toggle-theme')
def toggle_theme():
    current_theme = session.get('theme', 'light')
    session['theme'] = 'dark' if current_theme == 'light' else 'light'
    return redirect(request.referrer or url_for('articles.index'))