import urllib.request
import urllib.error
import json
import time
import sys


def test_rate_limit():
    base_url = "http://127.0.0.1:5002"
    
    print("Testing rate limit decorator...")
    print("=" * 50)
    
    print("\n1. Testing /api/test endpoint (rate limited)")
    print("-" * 50)
    
    success_count = 0
    for i in range(12):
        try:
            req = urllib.request.Request(f"{base_url}/api/test", method="GET")
            with urllib.request.urlopen(req) as response:
                status = response.status
                print(f"Request {i+1}: Status {status}")
                if status == 200:
                    success_count += 1
        except urllib.error.HTTPError as e:
            print(f"Request {i+1}: Status {e.code}")
            if e.code == 429:
                error_data = json.loads(e.read().decode())
                print(f"  Response: {error_data}")
                break
    
    print(f"\nSuccessful requests before rate limit: {success_count}")
    
    print("\n2. Waiting for rate limit to reset (60 seconds)...")
    print("   (This is a test, in production you would wait)")
    
    print("\n3. Testing /api/data endpoint (rate limited)")
    print("-" * 50)
    
    success_count = 0
    for i in range(12):
        try:
            req = urllib.request.Request(f"{base_url}/api/data", method="GET")
            with urllib.request.urlopen(req) as response:
                status = response.status
                print(f"Request {i+1}: Status {status}")
                if status == 200:
                    success_count += 1
        except urllib.error.HTTPError as e:
            print(f"Request {i+1}: Status {e.code}")
            if e.code == 429:
                error_data = json.loads(e.read().decode())
                print(f"  Response: {error_data}")
                break
    
    print(f"\nSuccessful requests before rate limit: {success_count}")
    
    print("\n4. Testing POST to /api/data (rate limited)")
    print("-" * 50)
    
    success_count = 0
    for i in range(12):
        try:
            data = json.dumps({"test": "data"}).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/api/data",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req) as response:
                status = response.status
                print(f"Request {i+1}: Status {status}")
                if status == 200:
                    success_count += 1
        except urllib.error.HTTPError as e:
            print(f"Request {i+1}: Status {e.code}")
            if e.code == 429:
                error_data = json.loads(e.read().decode())
                print(f"  Response: {error_data}")
                break
    
    print(f"\nSuccessful requests before rate limit: {success_count}")
    
    print("\n5. Testing /api/info endpoint (no rate limit)")
    print("-" * 50)
    
    for i in range(5):
        try:
            req = urllib.request.Request(f"{base_url}/api/info", method="GET")
            with urllib.request.urlopen(req) as response:
                status = response.status
                print(f"Request {i+1}: Status {status}")
        except urllib.error.HTTPError as e:
            print(f"Request {i+1}: Status {e.code}")
    
    print("\n" + "=" * 50)
    print("Test completed!")


if __name__ == "__main__":
    try:
        test_rate_limit()
    except urllib.error.URLError:
        print("Error: Could not connect to the server.")
        print("Please make sure the Flask app is running first:")
        print("  python rate_limit_example.py")
        sys.exit(1)
