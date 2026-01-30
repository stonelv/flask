from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import threading

db = SQLAlchemy()


class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'stock': self.stock,
            'price': float(self.price),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    product = db.relationship('Product', backref=db.backref('orders', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


def create_app(test_config=None):
    app = Flask(__name__)
    
    if test_config:
        app.config.update(test_config)
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///seckill.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
    
    @app.route('/')
    def index():
        return jsonify({'message': 'Seckill API'}), 200
    
    @app.route('/products', methods=['GET'])
    def list_products():
        products = Product.query.all()
        return jsonify([p.to_dict() for p in products]), 200
    
    @app.route('/products/<int:product_id>', methods=['GET'])
    def get_product(product_id):
        product = Product.query.get_or_404(product_id)
        return jsonify(product.to_dict()), 200
    
    @app.route('/seckill/<int:product_id>', methods=['POST'])
    def seckill(product_id):
        try:
            updated = db.session.query(Product).filter(
                Product.id == product_id,
                Product.stock > 0
            ).update({'stock': Product.stock - 1}, synchronize_session=False)
            
            if updated == 0:
                product = db.session.get(Product, product_id)
                if not product:
                    return jsonify({'error': 'Product not found'}), 404
                return jsonify({'error': 'Out of stock'}), 400
            
            order = Order(product_id=product_id, quantity=1)
            db.session.add(order)
            db.session.commit()
            
            product = db.session.get(Product, product_id)
            
            return jsonify({
                'success': True,
                'order': order.to_dict(),
                'remaining_stock': product.stock
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/orders', methods=['GET'])
    def list_orders():
        orders = Order.query.all()
        return jsonify([o.to_dict() for o in orders]), 200
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
