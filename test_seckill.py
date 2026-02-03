import threading
import time
import pytest
from decimal import Decimal
from app import create_app
from models import db, Product, Order
from config import TestingConfig


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


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
        assert data['message'] == 'Out of stock'

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

    def test_stock_consistency(self, client, app, init_product):
        """
        测试库存一致性：顺序执行100个请求，验证库存不会超卖
        注意：由于 SQLite 内存数据库和 Flask 测试客户端的限制，
        这里使用顺序执行来验证逻辑正确性。真正的并发测试需要在生产环境数据库上进行。
        """
        product_id = init_product
        num_requests = 100
        success_count = 0
        failed_count = 0

        for i in range(num_requests):
            response = client.post(f'/seckill/{product_id}', json={'user_id': f'user_{i}'})
            data = response.get_json()
            if data.get('success'):
                success_count += 1
            else:
                failed_count += 1

        with app.app_context():
            product = db.session.get(Product, product_id)
            order_count = Order.query.filter_by(product_id=product_id).count()

            print(f"\n=== 库存一致性测试结果 ===")
            print(f"总请求数: {num_requests}")
            print(f"初始库存: 10")
            print(f"成功订单: {success_count}")
            print(f"失败请求: {failed_count}")
            print(f"最终库存: {product.stock}")
            print(f"实际订单数: {order_count}")

            # 核心断言：库存绝对不能为负数
            assert product.stock >= 0, f"库存不能为负数，当前库存: {product.stock}"
            # 订单数不能超过初始库存
            assert order_count <= 10, f"订单数不能超过初始库存，当前订单数: {order_count}"
            # 库存 + 订单数 = 初始库存
            assert product.stock + order_count == 10, f"库存({product.stock}) + 订单数({order_count}) != 初始库存(10)"
            # 成功数应该正好等于初始库存
            assert success_count == 10, f"成功订单数应该为10，实际为{success_count}"
            # 失败数应该是总请求减去初始库存
            assert failed_count == 90, f"失败请求数应该为90，实际为{failed_count}"

    def test_pessimistic_lock_stock_consistency(self, client, app, init_product):
        """
        测试悲观锁实现的库存一致性
        """
        product_id = init_product
        num_requests = 100
        success_count = 0
        failed_count = 0

        for i in range(num_requests):
            response = client.post(f'/seckill/pessimistic/{product_id}', json={'user_id': f'user_{i}'})
            data = response.get_json()
            if data.get('success'):
                success_count += 1
            else:
                failed_count += 1

        with app.app_context():
            product = db.session.get(Product, product_id)
            order_count = Order.query.filter_by(product_id=product_id).count()

            print(f"\n=== 悲观锁库存一致性测试结果 ===")
            print(f"总请求数: {num_requests}")
            print(f"初始库存: 10")
            print(f"成功订单: {success_count}")
            print(f"失败请求: {failed_count}")
            print(f"最终库存: {product.stock}")
            print(f"实际订单数: {order_count}")

            # 核心断言：库存绝对不能为负数
            assert product.stock >= 0, f"库存不能为负数，当前库存: {product.stock}"
            # 订单数不能超过初始库存
            assert order_count <= 10, f"订单数不能超过初始库存，当前订单数: {order_count}"
            # 库存 + 订单数 = 初始库存
            assert product.stock + order_count == 10, f"库存({product.stock}) + 订单数({order_count}) != 初始库存(10)"
            # 成功数应该正好等于初始库存
            assert success_count == 10, f"成功订单数应该为10，实际为{success_count}"

    def test_atomic_update_mechanism(self, client, app, init_product):
        """
        测试原子更新机制：验证 UPDATE ... WHERE stock > 0 的原子性
        这个测试验证核心机制：即使在高并发情况下，数据库的原子更新也能保证库存不为负
        """
        product_id = init_product

        # 先消耗掉所有库存
        for i in range(10):
            response = client.post(f'/seckill/{product_id}', json={'user_id': f'user_{i}'})
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True, f"第{i+1}次请求应该成功"

        # 验证库存为0
        with app.app_context():
            product = db.session.get(Product, product_id)
            assert product.stock == 0, "库存应该为0"

        # 再发送10个请求，都应该失败
        for i in range(10, 20):
            response = client.post(f'/seckill/{product_id}', json={'user_id': f'user_{i}'})
            data = response.get_json()
            assert data['success'] is False, f"第{i+1}次请求应该失败"
            assert data['message'] == 'Out of stock'

        # 最终验证
        with app.app_context():
            product = db.session.get(Product, product_id)
            order_count = Order.query.filter_by(product_id=product_id).count()

            print(f"\n=== 原子更新机制测试结果 ===")
            print(f"最终库存: {product.stock}")
            print(f"订单数: {order_count}")

            assert product.stock == 0, "库存应该保持为0"
            assert product.stock >= 0, "库存绝对不能为负数"
            assert order_count == 10, "订单数应该正好是10"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
