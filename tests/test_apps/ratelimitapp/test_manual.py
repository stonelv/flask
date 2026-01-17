#!/usr/bin/env python3
"""手动测试速率限制装饰器。"""
import sys
import time

# 添加项目路径
sys.path.insert(0, '/Users/lvzhe/github/GSB/flask-2/tests/test_apps/ratelimitapp')

from __init__ import app, request_counts

def test_10_requests_per_minute():
    """测试每分钟 10 次请求的限制。"""
    print("\n========================================")
    print("测试: 10 次/分钟 速率限制")
    print("========================================\n")
    
    # 使用测试客户端
    client = app.test_client()
    
    # 清除之前的计数
    request_counts.clear()
    print("✓ 已清除之前的计数\n")
    
    # 测试前 10 次请求
    print("阶段 1: 前 10 次请求（应该全部成功）")
    for i in range(1, 11):
        response = client.get('/api/limited')
        data = response.get_json()
        print(f"  请求 {i}: HTTP {response.status_code} (计数: {data['count']})")
        assert response.status_code == 200, f"第 {i} 次请求应该成功"
    print("✓ 前 10 次请求全部成功\n")
    
    # 测试第 11 次请求
    print("阶段 2: 第 11 次请求（应该被限制）")
    response = client.get('/api/limited')
    data = response.get_json()
    print(f"  请求 11: HTTP {response.status_code}")
    print(f"  错误信息: {data['error']}")
    print(f"  提示信息: {data['message']}")
    print(f"  重试时间: {data['retry_after']} 秒")
    assert response.status_code == 429, "第 11 次请求应该返回 429"
    print("✓ 第 11 次请求成功被限制\n")
    
    # 验证计数未增加
    ip_address = '127.0.0.1'
    if ip_address in request_counts:
        count, window_start = request_counts[ip_address]
        print(f"验证: 当前计数仍为 {count}（未增加）")
        assert count == 10, "计数应该保持为 10"
    print("\n========================================")
    print("✅ 测试通过！速率限制正常工作")
    print("========================================\n")

if __name__ == '__main__':
    try:
        test_10_requests_per_minute()
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
