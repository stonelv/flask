import urllib.request
import urllib.error
import json
import time

def test_rate_limit():
    """测试速率限制功能"""
    base_url = "http://127.0.0.1:5001"
    
    print("测试速率限制功能...")
    print("=" * 50)
    
    # 测试无限制的端点
    print("\n1. 测试无限制的端点 (/api/public):")
    for i in range(3):
        try:
            with urllib.request.urlopen(f"{base_url}/api/public") as response:
                data = json.loads(response.read().decode())
                print(f"请求 {i+1}: 状态码 {response.status}")
                print(f"响应: {data}")
        except Exception as e:
            print(f"请求 {i+1} 失败: {e}")
    
    # 测试速率限制的端点
    print("\n2. 测试速率限制的端点 (/api/data, 10次/分钟):")
    success_count = 0
    for i in range(12):  # 发送12次请求，超过限制
        try:
            with urllib.request.urlopen(f"{base_url}/api/data") as response:
                data = json.loads(response.read().decode())
                success_count += 1
                print(f"请求 {i+1}: 状态码 {response.status}")
                print(f"响应: {data}")
        except urllib.error.HTTPError as e:
            print(f"请求 {i+1}: 状态码 {e.code}")
            try:
                error_data = json.loads(e.read().decode())
                print(f"限制响应: {error_data}")
            except:
                pass
        except Exception as e:
            print(f"请求 {i+1} 失败: {e}")
        
        # 添加小延迟，避免请求过快
        time.sleep(0.1)
    
    print(f"\n成功请求次数: {success_count}")
    
    # 测试严格限制的端点
    print("\n3. 测试严格限制的端点 (/api/strict, 5次/30秒):")
    success_count = 0
    for i in range(7):  # 发送7次请求，超过限制
        try:
            with urllib.request.urlopen(f"{base_url}/api/strict") as response:
                data = json.loads(response.read().decode())
                success_count += 1
                print(f"请求 {i+1}: 状态码 {response.status}")
                print(f"响应: {data}")
        except urllib.error.HTTPError as e:
            print(f"请求 {i+1}: 状态码 {e.code}")
            try:
                error_data = json.loads(e.read().decode())
                print(f"限制响应: {error_data}")
            except:
                pass
        except Exception as e:
            print(f"请求 {i+1} 失败: {e}")
        
        # 添加小延迟
        time.sleep(0.1)
    
    print(f"\n成功请求次数: {success_count}")
    
    # 等待时间窗口重置
    print("\n4. 等待时间窗口重置后再次测试...")
    print("等待35秒...")
    time.sleep(35)
    
    try:
        with urllib.request.urlopen(f"{base_url}/api/data") as response:
            data = json.loads(response.read().decode())
            print(f"重置后请求: 状态码 {response.status}")
            print(f"响应: {data}")
    except Exception as e:
        print(f"重置后请求失败: {e}")

if __name__ == "__main__":
    print("请确保Flask应用正在运行 (python app_example.py)")
    print("然后按Enter键开始测试...")
    input()
    test_rate_limit()