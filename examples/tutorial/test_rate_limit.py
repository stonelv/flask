#!/usr/bin/env python3
"""测试速率限制功能的脚本"""

import sys
import time

# 尝试导入 requests，如果失败则跳过
requests = None
try:
    import requests
except ImportError:
    print("Warning: requests module not installed. Using urllib instead.")


def test_rate_limit():
    """测试速率限制是否正常工作"""
    base_url = "http://localhost:5001"
    test_endpoint = "/api/limited"
    
    print("=== 测试速率限制功能 ===")
    print(f"测试端点: {test_endpoint}")
    print("速率限制: 每分钟最多10次请求\n")
    
    # 发送11次请求
    success_count = 0
    rate_limited_count = 0
    
    for i in range(1, 12):
        try:
            if requests:
                # 使用 requests 库
                response = requests.get(f"{base_url}{test_endpoint}")
                
                if response.status_code == 200:
                    success_count += 1
                    print(f"请求 {i}: 成功 (HTTP 200)")
                    print(f"   响应: {response.json()}")
                elif response.status_code == 429:
                    rate_limited_count += 1
                    print(f"请求 {i}: 被速率限制 (HTTP 429)")
                    print(f"   响应: {response.json()}")
                else:
                    print(f"请求 {i}: 未知状态码 {response.status_code}")
            else:
                # 使用 urllib
                from urllib.request import urlopen
                from urllib.error import HTTPError
                import json
                
                try:
                    with urlopen(f"{base_url}{test_endpoint}") as response:
                        if response.status == 200:
                            success_count += 1
                            data = json.loads(response.read().decode())
                            print(f"请求 {i}: 成功 (HTTP 200)")
                            print(f"   响应: {data}")
                except HTTPError as e:
                    if e.code == 429:
                        rate_limited_count += 1
                        import json
                        error_data = json.loads(e.read().decode())
                        print(f"请求 {i}: 被速率限制 (HTTP 429)")
                        print(f"   响应: {error_data}")
                    else:
                        print(f"请求 {i}: 未知状态码 {e.code}")
                
        except Exception as e:
            print(f"请求 {i}: 错误 - {e}")
            return
        
        # 短暂延迟，避免太快
        time.sleep(0.1)
    
    print(f"\n=== 测试结果 ===")
    print(f"成功请求数: {success_count}")
    print(f"被限制请求数: {rate_limited_count}")
    print(f"\n预期结果: 前10次成功，第11次被限制")
    
    if success_count == 10 and rate_limited_count == 1:
        print("✓ 速率限制功能正常工作!")
    else:
        print("✗ 速率限制功能可能有问题")


if __name__ == "__main__":
    test_rate_limit()