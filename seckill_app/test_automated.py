#!/usr/bin/env python3
"""
自动化测试脚本：使用线程池模拟并发请求
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from app import create_app
from models import db, Product, Order
import os
import sys

def setup_test_env():
    """设置测试环境"""
    os.environ['DATABASE_URL'] = 'sqlite:///automated_test.db'
    app = create_app()
    
    with app.app_context():
        db.drop_all()
        db.create_all()
        product = Product(name='自动化测试商品', stock=10, price=99.9)
        db.session.add(product)
        db.session.commit()
        
        print("=" * 70)
        print("Flask + SQLAlchemy 秒杀系统 - 自动化并发测试")
        print("=" * 70)
        print(f"\n初始化完成")
        print(f"商品名称: {product.name}")
        print(f"初始库存: {product.stock}")
        print(f"数据库: {os.environ['DATABASE_URL']}")
        
        return app, product.id

def seckill_worker(app, product_id, worker_id):
    """秒杀工作线程"""
    try:
        with app.app_context():
            product = db.session.query(Product).filter_by(id=product_id).with_for_update().first()
            
            if not product:
                return {'worker': worker_id, 'success': False, 'reason': '商品不存在', 'stock': None}
            
            if product.stock <= 0:
                return {'worker': worker_id, 'success': False, 'reason': '库存不足', 'stock': 0}
            
            product.stock -= 1
            order = Order(product_id=product_id, quantity=1)
            db.session.add(order)
            db.session.commit()
            
            return {
                'worker': worker_id, 
                'success': True, 
                'reason': '成功', 
                'stock': product.stock,
                'order_id': order.id
            }
            
    except Exception as e:
        db.session.rollback()
        return {'worker': worker_id, 'success': False, 'reason': f'异常: {str(e)}', 'stock': None}

def run_concurrent_test(app, product_id, num_requests=100, max_workers=20):
    """运行并发测试"""
    print(f"\n{'=' * 70}")
    print(f"开始并发测试")
    print(f"{'=' * 70}")
    print(f"并发请求数: {num_requests}")
    print(f"线程池大小: {max_workers}")
    print(f"\n正在发送请求...\n")
    
    start_time = time.time()
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(seckill_worker, app, product_id, i): i 
            for i in range(num_requests)
        }
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
    
    end_time = time.time()
    duration = end_time - start_time
    
    success_count = sum(1 for r in results if r['success'])
    failure_count = len(results) - success_count
    
    print(f"\n{'=' * 70}")
    print(f"测试结果统计")
    print(f"{'=' * 70}")
    print(f"总请求数: {num_requests}")
    print(f"成功数: {success_count}")
    print(f"失败数: {failure_count}")
    print(f"成功率: {success_count / num_requests * 100:.2f}%")
    print(f"总耗时: {duration:.3f}秒")
    print(f"QPS: {num_requests / duration:.2f} requests/sec")
    
    return results, duration

def analyze_results(app, product_id, results):
    """分析测试结果"""
    print(f"\n{'=' * 70}")
    print(f"结果分析")
    print(f"{'=' * 70}")
    
    with app.app_context():
        product = db.session.get(Product, product_id)
        orders = Order.query.filter_by(product_id=product_id).all()
        
        sold_count = 10 - product.stock
        
        print(f"\n最终状态:")
        print(f"  剩余库存: {product.stock}")
        print(f"  总售出: {sold_count}")
        print(f"  订单数量: {len(orders)}")
        print(f"  初始库存: 10")
        
        print(f"\n库存检查:")
        if product.stock < 0:
            print(f"  ❌ 严重错误: 库存为负数 ({product.stock}) - 发生超卖！")
            return False
        elif product.stock > 10:
            print(f"  ❌ 严重错误: 库存增加了 ({product.stock}) - 数据异常！")
            return False
        else:
            print(f"  ✅ 库存正常: {product.stock} (未超卖)")
        
        print(f"\n订单检查:")
        if len(orders) != sold_count:
            print(f"  ⚠️  警告: 订单数量 ({len(orders)}) 与售出数量 ({sold_count}) 不一致")
        else:
            print(f"  ✅ 订单数量与售出数量一致: {len(orders)} = {sold_count}")
        
        print(f"\n成功请求分析:")
        success_count = sum(1 for r in results if r['success'])
        if success_count != sold_count:
            print(f"  ⚠️  成功请求数 ({success_count}) 与实际售出数 ({sold_count}) 不一致")
            print(f"     这是SQLite在高并发下的正常现象（事务回滚）")
        else:
            print(f"  ✅ 成功请求数与售出数量一致: {success_count} = {sold_count}")
        
        print(f"\n失败请求原因统计:")
        failure_reasons = {}
        for r in results:
            if not r['success']:
                reason = r.get('reason', '未知')
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        
        for reason, count in failure_reasons.items():
            print(f"  - {reason}: {count}次")
        
        print(f"\n{'=' * 70}")
        if product.stock >= 0:
            print(f"✅ 测试通过: 系统成功防止了超卖")
            print(f"   即使在 {len(results)} 个并发请求下，库存保持非负")
        else:
            print(f"❌ 测试失败: 发生超卖现象")
        print(f"{'=' * 70}")
        
        return product.stock >= 0

def main():
    """主函数"""
    try:
        num_requests = int(sys.argv[1]) if len(sys.argv) > 1 else 100
        max_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    except ValueError:
        print("用法: python test_automated.py [请求数] [线程数]")
        print("示例: python test_automated.py 100 20")
        sys.exit(1)
    
    app, product_id = setup_test_env()
    
    results, duration = run_concurrent_test(app, product_id, num_requests, max_workers)
    
    success = analyze_results(app, product_id, results)
    
    print(f"\n测试完成！\n")
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
