"""
Flask Simple Auth 演示脚本
展示如何使用 flask_simple_auth 扩展
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_endpoint(name, url, headers=None, params=None, expected_status=200):
    """测试端点并打印结果"""
    print(f"\n=== 测试 {name} ===")
    print(f"URL: {url}")
    if headers:
        print(f"Headers: {headers}")
    if params:
        print(f"Params: {params}")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"状态码: {response.status_code} (期望: {expected_status})")
        
        if response.status_code == expected_status:
            print("✅ 测试通过")
        else:
            print("❌ 测试失败")
        
        try:
            print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        except:
            print(f"响应: {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def main():
    """主函数，运行所有测试"""
    print("Flask Simple Auth 演示")
    print("=" * 50)
    print("请确保示例应用正在运行: python example_app.py")
    print("等待 3 秒...")
    time.sleep(3)
    
    # 测试公共端点
    test_endpoint(
        "公共端点",
        f"{BASE_URL}/public"
    )
    
    # 测试受保护端点 - 没有 API key
    test_endpoint(
        "受保护端点 - 没有 API key",
        f"{BASE_URL}/protected",
        expected_status=401
    )
    
    # 测试受保护端点 - 使用 header 传递有效 API key
    test_endpoint(
        "受保护端点 - 使用 header 传递有效 API key",
        f"{BASE_URL}/protected",
        headers={"X-API-Key": "api-key-1"}
    )
    
    # 测试受保护端点 - 使用查询参数传递有效 API key
    test_endpoint(
        "受保护端点 - 使用查询参数传递有效 API key",
        f"{BASE_URL}/protected",
        params={"api_key": "api-key-2"}
    )
    
    # 测试受保护端点 - 使用无效 API key
    test_endpoint(
        "受保护端点 - 使用无效 API key",
        f"{BASE_URL}/protected",
        headers={"X-API-Key": "invalid-key"},
        expected_status=401
    )
    
    # 测试可选保护端点 - 没有 API key
    test_endpoint(
        "可选保护端点 - 没有 API key",
        f"{BASE_URL}/optional"
    )
    
    # 测试可选保护端点 - 有 API key
    test_endpoint(
        "可选保护端点 - 有 API key",
        f"{BASE_URL}/optional",
        headers={"X-API-Key": "api-key-3"}
    )
    
    # 测试用户资料端点
    test_endpoint(
        "用户资料端点",
        f"{BASE_URL}/profile",
        headers={"X-API-Key": "api-key-1"}
    )
    
    print("\n" + "=" * 50)
    print("演示完成！")

if __name__ == "__main__":
    main()