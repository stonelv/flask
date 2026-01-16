import requests
import threading
from concurrent.futures import ThreadPoolExecutor

def send_request():
    try:
        response = requests.post('http://localhost:5000/seckill/1')
        return response.status_code
    except Exception as e:
        return str(e)

def main():
    num_threads = 100
    results = []
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(send_request) for _ in range(num_threads)]
        
        for future in futures:
            results.append(future.result())
    
    success_count = sum(1 for r in results if r == 200)
    failure_count = len(results) - success_count
    
    print(f"Total requests: {num_threads}")
    print(f"Success count: {success_count}")
    print(f"Failure count: {failure_count}")
    print(f"Results: {results}")

if __name__ == '__main__':
    main()
