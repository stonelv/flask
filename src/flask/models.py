from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, UTC

# 创建 SQLAlchemy 实例
db = SQLAlchemy()

# 定义 Article 模型
class Article(db.Model):
    # 表名
    __tablename__ = 'articles'
    
    # 字段定义
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    # 构造函数
    def __init__(self, title, content, is_published=False):
        self.title = title
        self.content = content
        self.is_published = is_published
    
    # 字符串表示
    def __repr__(self):
        return f'<Article {self.id}: {self.title}>'
    
    # 保存文章到数据库
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    # 更新文章
    def update(self, title=None, content=None, is_published=None):
        if title is not None:
            self.title = title
        if content is not None:
            self.content = content
        if is_published is not None:
            self.is_published = is_published
        db.session.commit()
    
    # 删除文章
    def delete(self):
        db.session.delete(self)
        db.session.commit()
    
    # 类方法：获取所有文章
    @classmethod
    def get_all(cls):
        return cls.query.order_by(cls.created_at.desc()).all()
    
    # 类方法：根据ID获取文章
    @classmethod
    def get_by_id(cls, id):
        article = db.session.get(cls, id)
        if article is None:
            from flask import abort
            abort(404)
        return article
    
    # 类方法：获取已发布的文章
    @classmethod
    def get_published(cls):
        return cls.query.filter_by(is_published=True).order_by(cls.created_at.desc()).all()
    
    # 类方法：搜索文章（按标题关键词）
    @classmethod
    def search(cls, keyword):
        return cls.query.filter(cls.title.like(f'%{keyword}%')).order_by(cls.created_at.desc()).all()
