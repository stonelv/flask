import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from app import create_app, db, Product, Order


@pytest.fixture
def app():
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///test_seckill.db?check_same_thread=False',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'pool_pre_ping': True,
            'pool_recycle': 3600
        }
    }
    app = create_app(test_config)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    assert 'Seckill API' in response.json['message']


def test_create_product(app):
    with app.app_context():
        product = Product(name='Test Product', stock=100, price=99.99)
        db.session.add(product)
        db.session.commit()
        
        assert product.id is not None
        assert product.name == 'Test Product'
        assert product.stock == 100


def test_seckill_success(client, app):
    with app.app_context():
        product = Product(name='iPhone', stock=10, price=6999.00)
        db.session.add(product)
        db.session.commit()
        product_id = product.id
    
    response = client.post(f'/seckill/{product_id}')
    assert response.status_code == 200
    assert response.json['success'] is True
    assert response.json['remaining_stock'] == 9
    
    with app.app_context():
        order = Order.query.filter_by(product_id=product_id).first()
        assert order is not None
        assert order.quantity == 1


def test_seckill_out_of_stock(client, app):
    with app.app_context():
        product = Product(name='Limited Product', stock=0, price=100.00)
        db.session.add(product)
        db.session.commit()
        product_id = product.id
    
    response = client.post(f'/seckill/{product_id}')
    assert response.status_code == 400
    assert response.json['error'] == 'Out of stock'


def test_seckill_product_not_found(client):
    response = client.post('/seckill/99999')
    assert response.status_code == 404
    assert response.json['error'] == 'Product not found'


def test_concurrent_seckill_no_negative_stock(app):
    with app.app_context():
        product = Product(name='Seckill Product', stock=10, price=100.00)
        db.session.add(product)
        db.session.commit()
        product_id = product.id
    
    success_count = 0
    fail_count = 0
    lock = threading.Lock()
    
    def seckill_request():
        nonlocal success_count, fail_count
        with app.test_client() as client:
            response = client.post(f'/seckill/{product_id}')
            with lock:
                if response.status_code == 200:
                    success_count += 1
                else:
                    fail_count += 1
    
    threads = []
    for _ in range(100):
        t = threading.Thread(target=seckill_request)
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    with app.app_context():
        product = db.session.get(Product, product_id)
        order_count = Order.query.filter_by(product_id=product_id).count()
        
        assert product.stock == 0, f'Expected stock 0, got {product.stock}'
        assert product.stock >= 0, f'Stock became negative: {product.stock}'
        assert success_count == 10, f'Expected 10 successful orders, got {success_count}'
        assert fail_count == 90, f'Expected 90 failed requests, got {fail_count}'
        assert order_count == 10, f'Expected 10 orders, got {order_count}'


def test_concurrent_seckill_with_thread_pool(app):
    with app.app_context():
        product = Product(name='Pool Test Product', stock=10, price=100.00)
        db.session.add(product)
        db.session.commit()
        product_id = product.id
    
    results = []
    
    def seckill_request():
        with app.test_client() as client:
            response = client.post(f'/seckill/{product_id}')
            return response.status_code == 200
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(seckill_request) for _ in range(100)]
        for future in as_completed(futures):
            results.append(future.result())
    
    success_count = sum(results)
    fail_count = len(results) - success_count
    
    with app.app_context():
        product = db.session.get(Product, product_id)
        order_count = Order.query.filter_by(product_id=product_id).count()
        
        assert product.stock == 0, f'Expected stock 0, got {product.stock}'
        assert product.stock >= 0, f'Stock became negative: {product.stock}'
        assert success_count == 10, f'Expected 10 successful orders, got {success_count}'
        assert order_count == 10, f'Expected 10 orders, got {order_count}'


def test_multiple_products_concurrent_seckill(app):
    with app.app_context():
        product1 = Product(name='Product A', stock=5, price=100.00)
        product2 = Product(name='Product B', stock=8, price=200.00)
        db.session.add_all([product1, product2])
        db.session.commit()
        product1_id = product1.id
        product2_id = product2.id
    
    results = {'p1_success': 0, 'p2_success': 0}
    lock = threading.Lock()
    
    def seckill_product1():
        with app.test_client() as client:
            response = client.post(f'/seckill/{product1_id}')
            with lock:
                if response.status_code == 200:
                    results['p1_success'] += 1
    
    def seckill_product2():
        with app.test_client() as client:
            response = client.post(f'/seckill/{product2_id}')
            with lock:
                if response.status_code == 200:
                    results['p2_success'] += 1
    
    threads = []
    for _ in range(50):
        t1 = threading.Thread(target=seckill_product1)
        t2 = threading.Thread(target=seckill_product2)
        threads.append(t1)
        threads.append(t2)
        t1.start()
        t2.start()
    
    for t in threads:
        t.join()
    
    with app.app_context():
        p1 = db.session.get(Product, product1_id)
        p2 = db.session.get(Product, product2_id)
        
        assert p1.stock == 0
        assert p2.stock == 0
        assert results['p1_success'] == 5
        assert results['p2_success'] == 8
