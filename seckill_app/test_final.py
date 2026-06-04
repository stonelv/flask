import threading
from app import create_app
from models import db, Product, Order
import os
import time

os.environ['DATABASE_URL'] = 'sqlite:///test_final.db'
app = create_app()

success_count = 0
failure_count = 0
lock = threading.Lock()
product_id = None

def init_db():
    global product_id
    with app.app_context():
        db.drop_all()
        db.create_all()
        product = Product(name='测试商品', stock=10, price=99.9)
        db.session.add(product)
        db.session.commit()
        product_id = product.id
        print(f'初始化完成，商品ID: {product_id}，初始库存: {product.stock}')

def seckill_worker():
    global success_count, failure_count
    
    for attempt in range(3):
        try:
            with app.app_context():
                product = db.session.query(Product).filter_by(id=product_id).with_for_update().first()
                
                if not product:
                    with lock:
                        failure_count += 1
                    return
                
                if product.stock <= 0:
                    with lock:
                        failure_count += 1
                    return
                
                product.stock -= 1
                order = Order(product_id=product_id, quantity=1)
                db.session.add(order)
                
                db.session.commit()
                
                with lock:
                    success_count += 1
                return
                
        except Exception as e:
            db.session.rollback()
            if attempt == 2:
                with lock:
                    failure_count += 1
            time.sleep(0.01)

def test_concurrent():
    init_db()
    
    num_threads = 100
    threads = []
    
    print(f'\n开始 {num_threads} 个并发请求...')
    start_time = time.time()
    
    for i in range(num_threads):
        thread = threading.Thread(target=seckill_worker)
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    
    print(f'\n测试结果:')
    print(f'总请求数: {num_threads}')
    print(f'成功数: {success_count}')
    print(f'失败数: {failure_count}')
    print(f'耗时: {end_time - start_time:.2f}秒')
    
    with app.app_context():
        product = db.session.get(Product, product_id)
        orders = Order.query.filter_by(product_id=product_id).all()
        
        print(f'\n数据库状态:')
        print(f'剩余库存: {product.stock}')
        print(f'订单数: {len(orders)}')
        print(f'总售出: {10 - product.stock}')
        
        if product.stock < 0:
            print(f'\n❌ 超卖了！库存为负数: {product.stock}')
            return False
        elif success_count != 10:
            print(f'\n⚠️  成功数不等于库存数: {success_count} (预期: 10)')
            print(f'   这可能是因为SQLite在高并发下的限制')
            return False
        else:
            print(f'\n✅ 测试成功！没有超卖，成功售出10件商品')
            return True

if __name__ == '__main__':
    result = test_concurrent()
    print('\n测试完成！')
    exit(0 if result else 1)
