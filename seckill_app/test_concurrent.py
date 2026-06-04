import threading
import requests
import time
from app import create_app
from models import db, Product
import os

app = None
product_id = None

def setup():
    global app, product_id
    os.environ['DATABASE_URL'] = 'sqlite:///test_seckill.db'
    app = create_app()
    
    with app.app_context():
        db.drop_all()
        db.create_all()
        product = Product(name='测试商品', stock=10, price=99.9)
        db.session.add(product)
        db.session.commit()
        product_id = product.id
        print(f'初始化完成，商品ID: {product_id}，库存: {product.stock}')

def make_request():
    try:
        response = requests.post(f'http://localhost:5000/seckill/{product_id}', timeout=5)
        return response.json()
    except Exception as e:
        return {'success': False, 'message': str(e)}

def test_concurrent():
    num_threads = 100
    results = []
    lock = threading.Lock()
    
    def worker():
        result = make_request()
        with lock:
            results.append(result)
    
    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    
    start_time = time.time()
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    
    success_count = sum(1 for r in results if r.get('success'))
    failure_count = len(results) - success_count
    
    print(f'\n测试结果:')
    print(f'总请求数: {num_threads}')
    print(f'成功数: {success_count}')
    print(f'失败数: {failure_count}')
    print(f'耗时: {end_time - start_time:.2f}秒')
    
    with app.app_context():
        product = Product.query.get(product_id)
        orders = product.orders
        print(f'\n数据库状态:')
        print(f'剩余库存: {product.stock}')
        print(f'订单数: {len(orders)}')
        
        if product.stock < 0:
            print('\n❌ 超卖了！库存为负数:', product.stock)
        else:
            print(f'\n✅ 测试成功！没有超卖，剩余库存: {product.stock}')

if __name__ == '__main__':
    setup()
    
    import threading
    import time
    
    def run_server():
        app.run(port=5000, use_reloader=False)
    
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    time.sleep(1)
    
    test_concurrent()
    
    print('\n测试完成！')
