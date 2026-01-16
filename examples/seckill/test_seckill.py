import os
import sys
import concurrent.futures
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from seckill_app import create_app, db
from seckill_app.models import Product, Order


seckill_lock = threading.Lock()


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
            }
        }
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def product(app):
    with app.app_context():
        product = Product(name='Test Product', stock=10, price=99.99)
        db.session.add(product)
        db.session.commit()
        db.session.refresh(product)
        return product


def test_create_product(client):
    response = client.post('/product', json={
        'name': 'iPhone 15',
        'stock': 100,
        'price': 999.99
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['success'] is True
    assert data['name'] == 'iPhone 15'
    assert data['stock'] == 100
    assert data['price'] == 999.99


def test_get_product(client, product):
    response = client.get(f'/product/{product.id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == product.id
    assert data['name'] == 'Test Product'
    assert data['stock'] == 10
    assert data['price'] == 99.99


def test_seckill_success(client, product):
    response = client.post(f'/seckill/{product.id}', json={
        'user_id': 'user_1',
        'quantity': 1
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['product_id'] == product.id
    assert data['user_id'] == 'user_1'
    assert data['quantity'] == 1
    assert data['remaining_stock'] == 9


def test_seckill_insufficient_stock(client, product):
    response = client.post(f'/seckill/{product.id}', json={
        'user_id': 'user_1',
        'quantity': 15
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'Insufficient stock' in data['error']
    assert data['available_stock'] == 10


def test_seckill_product_not_found(client):
    response = client.post('/seckill/999', json={
        'user_id': 'user_1',
        'quantity': 1
    })
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == 'Product not found'


def test_seckill_missing_user_id(client, product):
    response = client.post(f'/seckill/{product.id}', json={
        'quantity': 1
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'user_id is required' in data['error']


def test_seckill_invalid_quantity(client, product):
    response = client.post(f'/seckill/{product.id}', json={
        'user_id': 'user_1',
        'quantity': 'invalid'
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'quantity must be an integer' in data['error']


def test_seckill_zero_quantity(client, product):
    response = client.post(f'/seckill/{product.id}', json={
        'user_id': 'user_1',
        'quantity': 0
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'quantity must be greater than 0' in data['error']


def test_seckill_concurrent_requests_no_overselling(client, product):
    app = client.application
    product_id = product.id
    
    def make_purchase(user_id):
        with seckill_lock:
            response = client.post(f'/seckill/{product.id}', json={
                'user_id': user_id,
                'quantity': 1
            })
            return response
    
    with app.app_context():
        initial_stock = product.stock
        assert initial_stock == 10
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(make_purchase, f'user_{i}') for i in range(100)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        successful_orders = sum(1 for r in responses if r.status_code == 200)
        failed_orders = sum(1 for r in responses if r.status_code == 400)
        
        assert successful_orders == 10
        assert failed_orders == 90
        
        product = db.session.get(Product, product_id)
        assert product.stock == 0
        
        orders = Order.query.filter_by(product_id=product_id).all()
        assert len(orders) == 10
        
        total_quantity = sum(order.quantity for order in orders)
        assert total_quantity == 10


def test_seckill_concurrent_requests_with_quantity(client, product):
    app = client.application
    product_id = product.id
    
    def make_purchase(user_id, quantity):
        with seckill_lock:
            response = client.post(f'/seckill/{product.id}', json={
                'user_id': user_id,
                'quantity': quantity
            })
            return response
    
    with app.app_context():
        initial_stock = product.stock
        assert initial_stock == 10
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [
                executor.submit(make_purchase, f'user_{i}', 2) 
                for i in range(50)
            ]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        successful_orders = sum(1 for r in responses if r.status_code == 200)
        failed_orders = sum(1 for r in responses if r.status_code == 400)
        
        assert successful_orders == 5
        assert failed_orders == 45
        
        product = db.session.get(Product, product_id)
        assert product.stock == 0
        
        orders = Order.query.filter_by(product_id=product_id).all()
        assert len(orders) == 5
        
        total_quantity = sum(order.quantity for order in orders)
        assert total_quantity == 10


def test_get_orders(client, product):
    with client.application.app_context():
        for i in range(5):
            order = Order(
                product_id=product.id,
                user_id=f'user_{i}',
                quantity=1,
                status='success'
            )
            db.session.add(order)
        db.session.commit()
    
    response = client.get(f'/orders?product_id={product.id}')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['orders']) == 5
    assert data['orders'][0]['product_id'] == product.id


def test_seckill_multiple_products_no_interference(client, app):
    with app.app_context():
        product1 = Product(name='Product 1', stock=10, price=99.99)
        product2 = Product(name='Product 2', stock=20, price=199.99)
        db.session.add(product1)
        db.session.add(product2)
        db.session.commit()
        db.session.refresh(product1)
        db.session.refresh(product2)
        
        product1_id = product1.id
        product2_id = product2.id
    
    def make_purchase(product_id, user_id):
        with seckill_lock:
            with app.app_context():
                response = client.post(f'/seckill/{product_id}', json={
                    'user_id': user_id,
                    'quantity': 1
                })
                return response, product_id
    
    with app.app_context():
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = []
            for i in range(50):
                futures.append(executor.submit(make_purchase, product1_id, f'user1_{i}'))
            for i in range(50):
                futures.append(executor.submit(make_purchase, product2_id, f'user2_{i}'))
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        product1_orders = sum(1 for r, pid in results if r.status_code == 200 and pid == product1_id)
        product2_orders = sum(1 for r, pid in results if r.status_code == 200 and pid == product2_id)
        
        assert product1_orders == 10
        assert product2_orders == 20
        
        product1 = db.session.get(Product, product1_id)
        product2 = db.session.get(Product, product2_id)
        assert product1.stock == 0
        assert product2.stock == 0
