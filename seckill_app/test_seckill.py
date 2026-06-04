import pytest
import os
from app import create_app
from models import db, Product, Order
from concurrent.futures import ThreadPoolExecutor
import threading

@pytest.fixture
def app():
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    app = create_app()
    app.config['TESTING'] = True
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def init_product_id(app):
    with app.app_context():
        product = Product(name='测试商品', stock=10, price=99.9)
        db.session.add(product)
        db.session.commit()
        product_id = product.id
        db.session.remove()
        return product_id

def test_single_seckill_success(client, init_product_id):
    response = client.post(f'/seckill/{init_product_id}')
    data = response.get_json()
    
    assert response.status_code == 200
    assert data['success'] is True
    assert data['remaining_stock'] == 9
    
    with client.application.app_context():
        product = db.session.get(Product, init_product_id)
        orders = Order.query.filter_by(product_id=init_product_id).all()
        assert product.stock == 9
        assert len(orders) == 1

def test_seckill_out_of_stock(client, init_product_id):
    with client.application.app_context():
        product = db.session.get(Product, init_product_id)
        product.stock = 0
        db.session.commit()
    
    response = client.post(f'/seckill/{init_product_id}')
    data = response.get_json()
    
    assert response.status_code == 400
    assert data['success'] is False
    assert '已售罄' in data['message']

def test_seckill_nonexistent_product(client):
    response = client.post('/seckill/999')
    data = response.get_json()
    
    assert response.status_code == 404
    assert data['success'] is False
    assert '不存在' in data['message']

def test_concurrent_seckill(client, init_product_id):
    num_requests = 100
    success_count = 0
    failure_count = 0
    lock = threading.Lock()
    
    def make_request():
        nonlocal success_count, failure_count
        response = client.post(f'/seckill/{init_product_id}')
        data = response.get_json()
        
        with lock:
            if data['success']:
                success_count += 1
            else:
                failure_count += 1
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(make_request) for _ in range(num_requests)]
        for future in futures:
            future.result()
    
    with client.application.app_context():
        product = db.session.get(Product, init_product_id)
        orders = Order.query.filter_by(product_id=init_product_id).all()
        
        assert product.stock == 0
        assert len(orders) == 10
        assert success_count == 10
        assert failure_count == 90
        assert product.stock >= 0

if __name__ == '__main__':
    pytest.main(['-v', 'test_seckill.py'])
