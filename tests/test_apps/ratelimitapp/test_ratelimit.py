#!/usr/bin/env python3
"""测试速率限制装饰器的功能。"""
import sys

# 添加项目路径
sys.path.insert(0, '/Users/lvzhe/github/GSB/flask-2/tests/test_apps/ratelimitapp')

from __init__ import app, request_counts

def test_rate_limit():
    """测试速率限制功能。"""
    print("\n=== 测试速率限制装饰器 ===\n")
    
    # 使用测试客户端
    client = app.test_client()
    
    # 清除之前的计数
    request_counts.clear()
    
    print("测试 1: 正常访问（前10次应该成功）")
    for i in range(1, 11):
        response = client.get('/api/limited')
        print(f"  请求 {i}: 状态码 {response.status_code}")
        assert response.status_code == 200, f"第 {i} 次请求应该成功"
    
    print("\n测试 2: 超出限制（第11次应该返回 429）")
    response = client.get('/api/limited')
    print(f"  请求 11: 状态码 {response.status_code}")
    print(f"  响应内容: {response.get_data(as_text=True)}")
    assert response.status_code == 429, "第11次请求应该返回 429"
    
    print("\n测试 3: 验证返回的 JSON 格式")
    data = response.get_json()
    assert 'error' in data, "响应应该包含 error 字段"
    assert 'message' in data, "响应应该包含 message 字段"
    assert 'retry_after' in data, "响应应该包含 retry_after 字段"
    print(f"  ✓ error: {data['error']}")
    print(f"  ✓ message: {data['message']}")
    print(f"  ✓ retry_after: {data['retry_after']} 秒")
    
    print("\n测试 4: 其他端点不受影响（使用不同的限制参数）")
    # 清除计数以测试不同的限制参数
    request_counts.clear()
    # other-limited 限制为 5 次/30秒
    for i in range(1, 6):
        response = client.get('/api/other-limited')
        print(f"  其他端点请求 {i}: 状态码 {response.status_code}")
        assert response.status_code == 200, f"第 {i} 次请求应该成功"
    
    # 第6次请求 other-limited 应该被限制
    response = client.get('/api/other-limited')
    print(f"  其他端点请求 6: 状态码 {response.status_code}")
    assert response.status_code == 429, "other-limited 端点应该在第6次请求时返回 429"
    
    print("\n测试 5: 未受限的端点始终可以访问")
    for i in range(1, 20):
        response = client.get('/api/unlimited')
        assert response.status_code == 200, "unlimited 端点应该始终可以访问"
    print(f"  ✓ 成功访问 unlimited 端点 20 次")
    
    print("\n测试 6: 首页可以正常访问")
    response = client.get('/')
    print(f"  首页请求: 状态码 {response.status_code}")
    assert response.status_code == 200, "首页应该可以正常访问"
    
    print("\n=== 所有测试通过！ ===")


if __name__ == '__main__':
    try:
        test_rate_limit()
        print("\n🎉 所有测试成功完成！")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
