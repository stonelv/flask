import requests
import time
import json

def test_rate_limit():
    """测试速率限制功能"""
    base_url = "http://127.0.0.1:5001"
    
    print("测试速率限制功能...")
    print("=" * 50)
    
    # 测试无限制的端点
    print("\n1. 测试无限制的端点 (/api/public):")
    for i in range(3):
        response = requests.get(f"{base_url}/api/public")
        print(f"请求 {i+1}: 状态码 {response.status_code}")
        if response.status_code == 200:
            print(f"响应: {response.json()}")
    
    # 测试速率限制的端点
    print("\n2. 测试速率限制的端点 (/api/data, 10次/分钟):")
    success_count = 0
    for i in range(12):  # 发送12次请求，超过限制
        response = requests.get(f"{base_url}/api/data")
        print(f"请求 {i+1}: 状态码 {response.status_code}")
        
        if response.status_code == 200:
            success_count += 1
            print(f"响应: {response.json()}")
        elif response.status_code == 429:
            print(f"限制响应: {response.json()}")
        
        # 添加小延迟，避免请求过快
        time.sleep(0.1)
    
    print(f"\n成功请求次数: {success_count}")
    
    # 测试严格限制的端点
    print("\n3. 测试严格限制的端点 (/api/strict, 5次/30秒):")
    success_count = 0
    for i in range(7):  # 发送7次请求，超过限制
        response = requests.get(f"{base_url}/api/strict")
        print(f"请求 {i+1}: 状态码 {response.status_code}")
        
        if response.status_code == 200:
            success_count += 1
            print(f"响应: {response.json()}")
        elif response.status_code == 429:
            print(f"限制响应: {response.json()}")
        
        # 添加小延迟
        time.sleep(0.1)
    
    print(f"\n成功请求次数: {success_count}")
    
    # 等待时间窗口重置
    print("\n4. 等待时间窗口重置后再次测试...")
    print("等待35秒...")
    time.sleep(35)
    
    response = requests.get(f"{base_url}/api/data")
    print(f"重置后请求: 状态码 {response.status_code}")
    if response.status_code == 200:
        print(f"响应: {response.json()}")

if __name__ == "__main__":
    print("请确保Flask应用正在运行 (python app_example.py)")
    print("然后按Enter键开始测试...")
    input()
    test_rate_limit()