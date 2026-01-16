import pytest
from app import app, db, Product, Order

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_seckill.db'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            product = Product(name='Test Product', stock=10)
            db.session.add(product)
            db.session.commit()
        yield client
        
        with app.app_context():
            db.drop_all()

def test_seckill_success(client):
    response = client.post('/seckill/1')
    data = response.get_json()
    
    assert response.status_code == 200
    assert data['success'] is True
    assert 'order_id' in data
    
    with app.app_context():
        product = db.session.get(Product, 1)
        assert product.stock == 9
        order = db.session.get(Order, data['order_id'])
        assert order is not None
        assert order.product_id == 1

def test_seckill_sold_out(client):
    with app.app_context():
        product = db.session.get(Product, 1)
        product.stock = 0
        db.session.commit()
    
    response = client.post('/seckill/1')
    data = response.get_json()
    
    assert response.status_code == 400
    assert data['error'] == 'Sold out'

def test_seckill_product_not_found(client):
    response = client.post('/seckill/999')
    data = response.get_json()
    
    assert response.status_code == 404
    assert data['error'] == 'Product not found'

def test_concurrent_seckill(client):
    import concurrent.futures
    from flask.testing import FlaskClient
    
    results = []
    
    def seckill_task():
        thread_client = FlaskClient(app)
        try:
            response = thread_client.post('/seckill/1')
            return response.status_code, response.get_json()
        finally:
            thread_client.__exit__(None, None, None)
    
    # Use ThreadPoolExecutor for better thread management
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(seckill_task) for _ in range(100)]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                status_code, data = future.result()
                results.append((status_code, data))
            except Exception as e:
                print(f"Thread error: {e}")
    
    # Count results
    success_count = sum(1 for status, _ in results if status == 200)
    failure_count = len(results) - success_count
    
    with app.app_context():
        product = db.session.get(Product, 1)
        order_count = db.session.query(Order).count()
        
        print(f"=== Concurrent Seckill Test Results ===")
        print(f"Initial stock: 10")
        print(f"Final stock: {product.stock}")
        print(f"Order count: {order_count}")
        print(f"Success count: {success_count}")
        print(f"Failure count: {failure_count}")
        print(f"Total requests: {len(results)}")
        
        # Check for sold out responses
        sold_out_count = sum(1 for status, data in results if status == 400 and data.get('error') == 'Sold out')
        print(f"Sold out responses: {sold_out_count}")
        
        # Verify no over-sold
        assert product.stock >= 0, "Stock cannot be negative"
        assert order_count == 10, f"Expected 10 orders, got {order_count}"
        assert success_count == 10, f"Expected 10 successful requests, got {success_count}"
        assert product.stock == 0, f"Expected stock to be 0, got {product.stock}"
