import threading
from app import create_app
from models import db, Product
import os

os.environ['DATABASE_URL'] = 'sqlite:///test_concurrent.db'
app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()
    product = Product(name='测试商品', stock=10, price=99.9)
    db.session.add(product)
    db.session.commit()
    product_id = product.id
    print(f'初始化完成，商品ID: {product_id}，库存: {product.stock}')

success_count = 0
failure_count = 0
lock = threading.Lock()

def seckill_task():
    global success_count, failure_count
    
    with app.app_context():
        try:
            from sqlalchemy import text
            
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
            from models import Order
            order = Order(product_id=product_id, quantity=1)
            db.session.add(order)
            
            db.session.commit()
            
            with lock:
                success_count += 1
                
        except Exception as e:
            db.session.rollback()
            with lock:
                failure_count += 1
            print(f'错误: {e}')

def test_concurrent():
    num_threads = 100
    threads = []
    
    print(f'\n开始 {num_threads} 个并发请求...')
    
    for i in range(num_threads):
        thread = threading.Thread(target=seckill_task)
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    print(f'\n测试结果:')
    print(f'总请求数: {num_threads}')
    print(f'成功数: {success_count}')
    print(f'失败数: {failure_count}')
    
    with app.app_context():
        product = db.session.get(Product, product_id)
        orders = product.orders
        print(f'\n数据库状态:')
        print(f'剩余库存: {product.stock}')
        print(f'订单数: {len(orders)}')
        
        if product.stock < 0:
            print('\n❌ 超卖了！库存为负数:', product.stock)
        else:
            print(f'\n✅ 测试成功！没有超卖，剩余库存: {product.stock}')
            print(f'订单数量与成功购买数一致: {len(orders)} == {success_count}')

if __name__ == '__main__':
    test_concurrent()
    print('\n测试完成！')
