from datetime import datetime, timezone

from seckill_app import db


class Product(db.Model):
    __tablename__ = 'product'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<Product {self.name} - Stock: {self.stock}>'


class Order(db.Model):
    __tablename__ = 'order'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    user_id = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), default='success')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    product = db.relationship('Product', backref=db.backref('orders', lazy=True))
    
    def __repr__(self):
        return f'<Order {self.id} - User: {self.user_id} - Product: {self.product_id}>'
