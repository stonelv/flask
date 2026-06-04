from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from .models import db, Article
from .auth import login_required
from sqlalchemy import or_

# 创建文章蓝图
articles_bp = Blueprint('articles', __name__)

# 后台文章列表
@articles_bp.route('/admin/articles')
@login_required
def index():
    # 获取搜索关键词
    search = request.args.get('search', '')
    # 获取当前页码
    page = request.args.get('page', 1, type=int)
    # 每页显示数量
    per_page = 10

    # 构建查询
    if search:
        query = db.select(Article).filter(or_(Article.title.contains(search), Article.content.contains(search))).order_by(Article.updated_at.desc())
    else:
        query = db.select(Article).order_by(Article.updated_at.desc())

    # 分页查询
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    articles = pagination.items

    return render_template('articles/index.html', articles=articles, pagination=pagination, search=search)

# 新建文章
@articles_bp.route('/admin/articles/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()

        # 表单验证
        errors = []
        if not title:
            errors.append('标题不能为空')
        elif len(title) > 120:
            errors.append('标题长度不能超过 120 个字符')
        if not content:
            errors.append('内容不能为空')

        if errors:
            for error in errors:
                flash(error, 'danger')
        else:
            # 创建文章
            article = Article(title=title, content=content)
            db.session.add(article)
            db.session.commit()

            flash('文章创建成功', 'success')
            return redirect(url_for('articles.index'))

    return render_template('articles/new.html')

# 编辑文章
@articles_bp.route('/admin/articles/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    article = db.session.get(Article, id)
    if not article:
        abort(404)

    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()

        # 表单验证
        errors = []
        if not title:
            errors.append('标题不能为空')
        elif len(title) > 120:
            errors.append('标题长度不能超过 120 个字符')
        if not content:
            errors.append('内容不能为空')

        if errors:
            for error in errors:
                flash(error, 'danger')
        else:
            # 更新文章
            article.title = title
            article.content = content
            db.session.commit()

            flash('文章更新成功', 'success')
            return redirect(url_for('articles.index'))

    return render_template('articles/edit.html', article=article)

# 删除文章
@articles_bp.route('/admin/articles/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    article = db.session.get(Article, id)
    if not article:
        abort(404)
    db.session.delete(article)
    db.session.commit()

    flash('文章删除成功', 'success')
    return redirect(url_for('articles.index'))

# 切换文章发布状态
@articles_bp.route('/admin/articles/<int:id>/toggle_publish', methods=['POST'])
@login_required
def toggle_publish(id):
    article = db.session.get(Article, id)
    if not article:
        abort(404)
    article.is_published = not article.is_published
    db.session.commit()

    status = '发布' if article.is_published else '取消发布'
    flash(f'文章已{status}', 'success')
    return redirect(url_for('articles.index'))

# 前台文章列表
@articles_bp.route('/articles')
def public_index():
    # 获取当前页码
    page = request.args.get('page', 1, type=int)
    # 每页显示数量
    per_page = 10

    # 分页查询已发布的文章
    query = db.select(Article).filter_by(is_published=True).order_by(Article.updated_at.desc())
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    articles = pagination.items

    return render_template('articles/public_index.html', articles=articles, pagination=pagination)

# 前台文章详情
@articles_bp.route('/articles/<int:id>')
def public_show(id):
    article = db.session.execute(db.select(Article).filter_by(id=id, is_published=True)).scalar_one_or_none()
    if not article:
        abort(404)
    return render_template('articles/public_show.html', article=article)

# 主题切换
@articles_bp.route('/toggle_theme')
def toggle_theme():
    current_theme = session.get('theme', 'light')
    new_theme = 'dark' if current_theme == 'light' else 'light'
    session['theme'] = new_theme

    # 重定向到之前的页面
    return redirect(request.referrer or url_for('articles.public_index'))