from flask import Flask, jsonify
from models import db, Product, Order
import os

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///seckill.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    @app.route('/seckill/<int:product_id>', methods=['POST'])
    def seckill(product_id):
        import time
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                product = db.session.query(Product).filter_by(id=product_id).with_for_update().first()
                
                if not product:
                    return jsonify({'success': False, 'message': '商品不存在'}), 404
                
                if product.stock <= 0:
                    return jsonify({'success': False, 'message': '商品已售罄'}), 400
                
                product.stock -= 1
                
                order = Order(product_id=product_id, quantity=1)
                db.session.add(order)
                
                db.session.commit()
                return jsonify({
                    'success': True, 
                    'message': '秒杀成功',
                    'order_id': order.id,
                    'remaining_stock': product.stock
                }), 200
                
            except Exception as e:
                db.session.rollback()
                retry_count += 1
                if retry_count >= max_retries:
                    return jsonify({'success': False, 'message': f'购买失败: {str(e)}'}), 500
                time.sleep(0.01)
    
    @app.route('/products', methods=['GET'])
    def get_products():
        products = Product.query.all()
        return jsonify([{
            'id': p.id,
            'name': p.name,
            'stock': p.stock,
            'price': p.price
        } for p in products])
    
    @app.route('/orders', methods=['GET'])
    def get_orders():
        orders = Order.query.all()
        return jsonify([{
            'id': o.id,
            'product_id': o.product_id,
            'quantity': o.quantity,
            'status': o.status,
            'created_at': o.created_at.isoformat()
        } for o in orders])
    
    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        
        if Product.query.count() == 0:
            product = Product(name='秒杀商品', stock=10, price=99.9)
            db.session.add(product)
            db.session.commit()
            print('初始化商品成功，库存: 10')
    
    app.run(debug=True, port=5000)
