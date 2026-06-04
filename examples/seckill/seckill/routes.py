from flask import Blueprint, jsonify
from .extensions import db
from .models import Product, Order


bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    return jsonify({'message': 'Seckill API'}), 200


@bp.route('/products', methods=['GET'])
def list_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products]), 200


@bp.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    return jsonify(product.to_dict()), 200


@bp.route('/seckill/<int:product_id>', methods=['POST'])
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


@bp.route('/orders', methods=['GET'])
def list_orders():
    orders = Order.query.all()
    return jsonify([o.to_dict() for o in orders]), 200
