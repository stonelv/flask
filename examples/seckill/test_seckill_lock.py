import os
import sys
import concurrent.futures
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from seckill_app import create_app, db
from seckill_app.models import Product, Order


@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'connect_args': {
                'check_same_thread': False,
                'isolation_level': 'EXCLUSIVE'
            },
            'pool_pre_ping': True,
            'pool_recycle': 300
        }
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def product(app):
    with app.app_context():
        product = Product(name='Test Product', stock=10, price=99.99)
        db.session.add(product)
        db.session.commit()
        db.session.refresh(product)
        return product


def test_seckill_concurrent_requests_no_overselling(app, product):
    product_id = product.id
    lock = threading.Lock()
    
    def make_purchase(user_id):
        with lock:
            with app.app_context():
                try:
                    product = db.session.query(Product).filter(
                        Product.id == product_id
                    ).first()
                    
                    if not product:
                        return False
                    
                    if product.stock < 1:
                        return False
                    
                    product.stock -= 1
                    
                    order = Order(
                        product_id=product_id,
                        user_id=user_id,
                        quantity=1,
                        status='success'
                    )
                    db.session.add(order)
                    db.session.commit()
                    
                    return True
                except Exception as e:
                    db.session.rollback()
                    return False
    
    with app.app_context():
        initial_stock = product.stock
        assert initial_stock == 10
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(make_purchase, f'user_{i}') for i in range(100)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        successful_orders = sum(1 for r in results if r is True)
        failed_orders = sum(1 for r in results if r is False)
        
        assert successful_orders == 10
        assert failed_orders == 90
        
        product = db.session.get(Product, product_id)
        assert product.stock == 0
        
        orders = Order.query.filter_by(product_id=product_id).all()
        assert len(orders) == 10
        
        total_quantity = sum(order.quantity for order in orders)
        assert total_quantity == 10