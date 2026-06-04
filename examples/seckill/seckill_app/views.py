from flask import Blueprint, jsonify, request

from seckill_app import db
from seckill_app.models import Product, Order

bp = Blueprint('seckill', __name__)


@bp.route('/seckill/<int:product_id>', methods=['POST'])
def seckill(product_id):
    user_id = request.json.get('user_id') if request.is_json else request.form.get('user_id')
    quantity = request.json.get('quantity', 1) if request.is_json else request.form.get('quantity', 1)
    
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    try:
        quantity = int(quantity)
    except (ValueError, TypeError):
        return jsonify({'error': 'quantity must be an integer'}), 400
    
    if quantity <= 0:
        return jsonify({'error': 'quantity must be greater than 0'}), 400
    
    try:
        result = db.session.execute(
            db.update(Product)
            .where(Product.id == product_id)
            .where(Product.stock >= quantity)
            .values(stock=Product.stock - quantity)
        )
        
        if result.rowcount == 0:
            product = db.session.query(Product).filter(
                Product.id == product_id
            ).first()
            
            if not product:
                return jsonify({'error': 'Product not found'}), 404
            
            return jsonify({
                'error': 'Insufficient stock',
                'available_stock': product.stock
            }), 400
        
        order = Order(
            product_id=product_id,
            user_id=user_id,
            quantity=quantity,
            status='success'
        )
        db.session.add(order)
        db.session.commit()
        
        product = db.session.query(Product).filter(
            Product.id == product_id
        ).first()
        
        return jsonify({
            'success': True,
            'message': 'Order created successfully',
            'order_id': order.id,
            'product_id': product_id,
            'user_id': user_id,
            'quantity': quantity,
            'remaining_stock': product.stock
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    return jsonify({
        'id': product.id,
        'name': product.name,
        'stock': product.stock,
        'price': product.price,
        'created_at': product.created_at.isoformat()
    }), 200


@bp.route('/product', methods=['POST'])
def create_product():
    name = request.json.get('name') if request.is_json else request.form.get('name')
    stock = request.json.get('stock', 0) if request.is_json else request.form.get('stock', 0)
    price = request.json.get('price', 0) if request.is_json else request.form.get('price', 0)
    
    if not name:
        return jsonify({'error': 'name is required'}), 400
    
    try:
        stock = int(stock)
        price = float(price)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid stock or price'}), 400
    
    product = Product(name=name, stock=stock, price=price)
    db.session.add(product)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'product_id': product.id,
        'name': product.name,
        'stock': product.stock,
        'price': product.price
    }), 201


@bp.route('/orders', methods=['GET'])
def get_orders():
    product_id = request.args.get('product_id')
    
    query = Order.query
    if product_id:
        query = query.filter(Order.product_id == product_id)
    
    orders = query.all()
    
    return jsonify({
        'orders': [
            {
                'id': order.id,
                'product_id': order.product_id,
                'user_id': order.user_id,
                'quantity': order.quantity,
                'status': order.status,
                'created_at': order.created_at.isoformat()
            }
            for order in orders
        ]
    }), 200
