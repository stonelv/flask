import os
import threading
import time
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from app import create_app, process_seckill_atomic, process_seckill_pessimistic
from models import db, Product, Order
from config import TestingConfig


# 清理测试数据库文件
def cleanup_test_db():
    test_db_file = 'test_seckill.db'
    if os.path.exists(test_db_file):
        os.remove(test_db_file)


@pytest.fixture(scope='function')
def app():
    cleanup_test_db()
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
    cleanup_test_db()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def init_product(app):
    with app.app_context():
        product = Product(name='Test Product', stock=10, price=Decimal('99.99'))
        db.session.add(product)
        db.session.commit()
        return product.id


class TestSeckillAPI:
    """秒杀 API 基础功能测试"""

    def test_seckill_success(self, client, init_product):
        """测试正常秒杀成功"""
        product_id = init_product
        response = client.post(f'/seckill/{product_id}', json={'user_id': 'user_001'})

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == 'Order placed successfully'
        assert 'order_id' in data
        assert data['remaining_stock'] == 9

    def test_seckill_out_of_stock(self, client, init_product):
        """测试库存耗尽后返回无货"""
        product_id = init_product

        for i in range(10):
            response = client.post(f'/seckill/{product_id}', json={'user_id': f'user_{i}'})
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True

        response = client.post(f'/seckill/{product_id}', json={'user_id': 'user_extra'})
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is False
        assert data['message'] == 'Out of stock'

    def test_product_not_found(self, client):
        """测试商品不存在"""
        response = client.post('/seckill/999', json={'user_id': 'user_001'})
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is False
        assert data['message'] == 'Product not found'

    def test_get_product(self, client, init_product):
        """测试获取商品信息"""
        product_id = init_product
        response = client.get(f'/product/{product_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['name'] == 'Test Product'
        assert data['stock'] == 10


class TestSeckillConcurrency:
    """秒杀高并发测试 - 核心测试类"""

    def test_concurrent_atomic_seckill(self, app, init_product):
        """
        测试原子更新实现的并发秒杀
        使用多线程并发执行，验证竞态条件下的库存一致性
        """
        product_id = init_product
        num_threads = 100
        results = {'success': 0, 'failed': 0, 'out_of_stock': 0, 'not_found': 0}
        lock = threading.Lock()

        def seckill_request(user_id):
            with app.app_context():
                try:
                    result = process_seckill_atomic(product_id, user_id)
                    with lock:
                        if result.get('success'):
                            results['success'] += 1
                        elif result.get('message') == 'Out of stock':
                            results['out_of_stock'] += 1
                            results['failed'] += 1
                        elif result.get('message') == 'Product not found':
                            results['not_found'] += 1
                            results['failed'] += 1
                        else:
                            results['failed'] += 1
                except Exception as e:
                    with lock:
                        results['failed'] += 1

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=seckill_request, args=(f'user_{i}',))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        with app.app_context():
            product = db.session.get(Product, product_id)
            order_count = Order.query.filter_by(product_id=product_id).count()

            print(f"\n=== 原子更新并发测试结果 ===")
            print(f"并发请求数: {num_threads}")
            print(f"初始库存: 10")
            print(f"成功订单: {results['success']}")
            print(f"失败请求: {results['failed']}")
            print(f"无货返回: {results['out_of_stock']}")
            print(f"商品不存在: {results['not_found']}")
            print(f"最终库存: {product.stock}")
            print(f"实际订单数: {order_count}")

            # 核心断言：库存绝对不能为负数
            assert product.stock >= 0, f"库存不能为负数，当前库存: {product.stock}"
            # 订单数不能超过初始库存（防止超卖）
            assert order_count <= 10, f"订单数不能超过初始库存，当前订单数: {order_count}"
            # 库存 + 订单数 = 初始库存
            assert product.stock + order_count == 10, f"库存({product.stock}) + 订单数({order_count}) != 初始库存(10)"

    def test_concurrent_pessimistic_seckill(self, app, init_product):
        """
        测试悲观锁实现的并发秒杀
        使用多线程并发执行，验证竞态条件下的库存一致性
        """
        product_id = init_product
        num_threads = 100
        results = {'success': 0, 'failed': 0, 'out_of_stock': 0, 'not_found': 0}
        lock = threading.Lock()

        def seckill_request(user_id):
            with app.app_context():
                try:
                    result = process_seckill_pessimistic(product_id, user_id)
                    with lock:
                        if result.get('success'):
                            results['success'] += 1
                        elif result.get('message') == 'Out of stock':
                            results['out_of_stock'] += 1
                            results['failed'] += 1
                        elif result.get('message') == 'Product not found':
                            results['not_found'] += 1
                            results['failed'] += 1
                        else:
                            results['failed'] += 1
                except Exception as e:
                    with lock:
                        results['failed'] += 1

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=seckill_request, args=(f'user_{i}',))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        with app.app_context():
            product = db.session.get(Product, product_id)
            order_count = Order.query.filter_by(product_id=product_id).count()

            print(f"\n=== 悲观锁并发测试结果 ===")
            print(f"并发请求数: {num_threads}")
            print(f"初始库存: 10")
            print(f"成功订单: {results['success']}")
            print(f"失败请求: {results['failed']}")
            print(f"无货返回: {results['out_of_stock']}")
            print(f"商品不存在: {results['not_found']}")
            print(f"最终库存: {product.stock}")
            print(f"实际订单数: {order_count}")

            # 核心断言：库存绝对不能为负数
            assert product.stock >= 0, f"库存不能为负数，当前库存: {product.stock}"
            # 订单数不能超过初始库存（防止超卖）
            assert order_count <= 10, f"订单数不能超过初始库存，当前订单数: {order_count}"
            # 库存 + 订单数 = 初始库存
            assert product.stock + order_count == 10, f"库存({product.stock}) + 订单数({order_count}) != 初始库存(10)"

    def test_stock_never_negative_under_race_condition(self, app, init_product):
        """
        专门测试竞态条件下库存不会变为负数
        使用 Barrier 让所有线程同时开始，最大化竞态条件
        """
        product_id = init_product
        num_threads = 200
        barrier = threading.Barrier(num_threads)
        results = {'success': 0, 'failed': 0}
        lock = threading.Lock()

        def seckill_request(user_id):
            with app.app_context():
                try:
                    barrier.wait()
                    result = process_seckill_atomic(product_id, user_id)
                    with lock:
                        if result.get('success'):
                            results['success'] += 1
                        else:
                            results['failed'] += 1
                except Exception as e:
                    with lock:
                        results['failed'] += 1

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=seckill_request, args=(f'user_{i}',))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        with app.app_context():
            product = db.session.get(Product, product_id)
            order_count = Order.query.filter_by(product_id=product_id).count()

            print(f"\n=== 竞态条件测试结果 ===")
            print(f"并发请求数: {num_threads}")
            print(f"成功订单: {results['success']}")
            print(f"失败请求: {results['failed']}")
            print(f"最终库存: {product.stock}")
            print(f"实际订单数: {order_count}")

            # 核心断言：库存绝对不能为负数
            assert product.stock >= 0, f"库存绝对不能为负数！当前库存: {product.stock}"
            # 订单数不能超过初始库存
            assert order_count <= 10, f"订单数不能超过初始库存！当前订单数: {order_count}"
            # 库存 + 订单数 = 初始库存
            assert product.stock + order_count == 10, f"库存({product.stock}) + 订单数({order_count}) != 初始库存(10)"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
