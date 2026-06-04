from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index

db = SQLAlchemy()


def utc_now():
    return datetime.now(timezone.utc)


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    orders = db.relationship('Order', backref='product', lazy=True)

    __table_args__ = (
        Index('idx_product_stock', 'stock'),
    )

    def __repr__(self):
        return f'<Product {self.name} stock={self.stock}>'


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_id = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), default='success')
    created_at = db.Column(db.DateTime, default=utc_now)

    __table_args__ = (
        Index('idx_order_product_id', 'product_id'),
        Index('idx_order_user_id', 'user_id'),
    )

    def __repr__(self):
        return f'<Order product_id={self.product_id} user_id={self.user_id}>'
