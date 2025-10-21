import socket
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def make_request(host, port, path, request_id):
    """Make a single HTTP request and measure time"""
    start_time = time.time()
    
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
        
        request = f"GET {path} HTTP/1.1\r\n"
        request += f"Host: {host}:{port}\r\n"
        request += "Connection: close\r\n"
        request += "\r\n"
        
        client_socket.sendall(request.encode('utf-8'))
        
        # Receive response
        response_data = b''
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            response_data += chunk
        
        client_socket.close()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Check status code
        status_line = response_data.split(b'\r\n')[0].decode('utf-8', errors='ignore')
        status_code = status_line.split()[1] if len(status_line.split()) > 1 else '???'
        
        return {
            'id': request_id,
            'duration': duration,
            'status': status_code,
            'start': start_time,
            'end': end_time,
            'success': True
        }
    
    except Exception as e:
        end_time = time.time()
        return {
            'id': request_id,
            'duration': end_time - start_time,
            'status': 'ERROR',
            'start': start_time,
            'end': end_time,
            'success': False,
            'error': str(e)
        }

def test_concurrent_requests(host, port, path, num_requests, num_workers=10):
    """Test server with concurrent requests"""
    print(f"\n{'='*70}")
    print(f"CONCURRENT REQUEST TEST")
    print(f"{'='*70}")
    print(f"Target: {host}:{port}{path}")
    print(f"Number of requests: {num_requests}")
    print(f"Concurrent workers: {num_workers}")
    print(f"{'='*70}\n")
    
    overall_start = time.time()
    results = []
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(make_request, host, port, path, i) 
            for i in range(1, num_requests + 1)
        ]
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            status_symbol = "✓" if result['success'] else "✗"
            print(f"  {status_symbol} Request #{result['id']:2d} - "
                  f"Status: {result['status']:3s} - "
                  f"Duration: {result['duration']:.3f}s")
    
    overall_end = time.time()
    total_time = overall_end - overall_start
    
    # Calculate statistics
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    if successful:
        durations = [r['duration'] for r in successful]
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        
        # Calculate actual concurrency (overlap)
        first_start = min(r['start'] for r in results)
        last_end = max(r['end'] for r in results)
        actual_time = last_end - first_start
    else:
        avg_duration = 0
        min_duration = 0
        max_duration = 0
        actual_time = total_time
    
    # Print results
    print(f"\n{'='*70}")
    print(f"RESULTS")
    print(f"{'='*70}")
    print(f"Total execution time: {total_time:.3f}s")
    print(f"Actual request span:  {actual_time:.3f}s")
    print(f"Successful requests:  {len(successful)}/{num_requests}")
    print(f"Failed requests:      {len(failed)}/{num_requests}")
    
    if successful:
        print(f"\nResponse time statistics:")
        print(f"  Average: {avg_duration:.3f}s")
        print(f"  Minimum: {min_duration:.3f}s")
        print(f"  Maximum: {max_duration:.3f}s")
        print(f"\nThroughput: {len(successful)/actual_time:.2f} requests/second")
    
    print(f"{'='*70}\n")
    
    return {
        'total_time': total_time,
        'actual_time': actual_time,
        'successful': len(successful),
        'failed': len(failed),
        'avg_duration': avg_duration if successful else 0,
        'throughput': len(successful)/actual_time if actual_time > 0 else 0
    }

def main():
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python(3) test_concurrent.py <host> <port> <num_requests> [path]")
        print("Example: python(3) test_concurrent.py localhost 8080 10")
        print("Example: python(3) test_concurrent.py localhost 8080 10 /test.txt")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    num_requests = int(sys.argv[3])
    path = sys.argv[4] if len(sys.argv) > 4 else '/test.txt'
    
    test_concurrent_requests(host, port, path, num_requests)

if __name__ == '__main__':
    main()
