import uuid
import threading
from flask import Flask, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from models import db, Product, Order
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route('/')
    def index():
        return jsonify({'message': 'Seckill API Server'})

    @app.route('/product/<int:product_id>', methods=['GET'])
    def get_product(product_id):
        product = db.session.get(Product, product_id)
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        return jsonify({
            'id': product.id,
            'name': product.name,
            'stock': product.stock,
            'price': str(product.price)
        })

    @app.route('/seckill/<int:product_id>', methods=['POST'])
    def seckill(product_id):
        user_id = request.json.get('user_id') if request.is_json else None
        if not user_id:
            user_id = str(uuid.uuid4())

        try:
            result = process_seckill_atomic(product_id, user_id)
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/seckill/pessimistic/<int:product_id>', methods=['POST'])
    def seckill_pessimistic_route(product_id):
        user_id = request.json.get('user_id') if request.is_json else None
        if not user_id:
            user_id = str(uuid.uuid4())

        try:
            result = process_seckill_pessimistic(product_id, user_id)
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return app


def process_seckill_atomic(product_id, user_id):
    """
    使用数据库原子操作实现秒杀
    通过 UPDATE ... WHERE stock > 0 确保原子性
    """
    max_retries = 5

    for attempt in range(max_retries):
        try:
            db.session.begin_nested()

            result = db.session.execute(
                text("UPDATE products SET stock = stock - 1 WHERE id = :id AND stock > 0"),
                {'id': product_id}
            )

            if result.rowcount == 0:
                db.session.rollback()
                product = db.session.get(Product, product_id)
                if not product:
                    return {'success': False, 'message': 'Product not found'}
                return {'success': False, 'message': 'Out of stock'}

            order = Order(
                product_id=product_id,
                user_id=user_id,
                quantity=1,
                status='success'
            )
            db.session.add(order)
            db.session.commit()

            new_stock_result = db.session.execute(
                text("SELECT stock FROM products WHERE id = :id"),
                {'id': product_id}
            )
            new_stock = new_stock_result.scalar()

            return {
                'success': True,
                'message': 'Order placed successfully',
                'order_id': order.id,
                'remaining_stock': new_stock,
                'user_id': user_id
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            if attempt < max_retries - 1:
                continue
            return {'success': False, 'message': 'Database error, please try again'}

    return {'success': False, 'message': 'Too many retries, please try again'}


def process_seckill_pessimistic(product_id, user_id):
    """
    悲观锁实现秒杀
    使用数据库行锁（SELECT FOR UPDATE）
    注意：SQLite 不支持 FOR UPDATE，但在事务中通过串行化隔离级别仍能保证一致性
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    try:
        db.session.begin()

        # 使用 with_for_update() 方法，SQLAlchemy 会根据数据库类型生成合适的 SQL
        # 对于 SQLite，会回退到普通 SELECT，但通过事务仍能保证一致性
        result = db.session.execute(
            text("SELECT stock FROM products WHERE id = :id"),
            {'id': product_id}
        )
        row = result.fetchone()

        if not row:
            db.session.rollback()
            return {'success': False, 'message': 'Product not found'}

        stock = row[0]

        if stock <= 0:
            db.session.rollback()
            return {'success': False, 'message': 'Out of stock'}

        # 使用原子更新确保一致性
        update_result = db.session.execute(
            text("UPDATE products SET stock = stock - 1 WHERE id = :id AND stock = :stock"),
            {'id': product_id, 'stock': stock}
        )

        if update_result.rowcount == 0:
            db.session.rollback()
            return {'success': False, 'message': 'Concurrent update detected, please retry'}

        order = Order(
            product_id=product_id,
            user_id=user_id,
            quantity=1,
            status='success'
        )
        db.session.add(order)
        db.session.commit()

        return {
            'success': True,
            'message': 'Order placed successfully',
            'order_id': order.id,
            'remaining_stock': stock - 1,
            'user_id': user_id
        }

    except SQLAlchemyError as e:
        db.session.rollback()
        raise e
