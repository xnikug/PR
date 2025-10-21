import socket
import time
import threading
from collections import defaultdict

def make_request(host, port, path):
    """Make a single HTTP request"""
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
        
        # Check status code
        status_line = response_data.split(b'\r\n')[0].decode('utf-8', errors='ignore')
        status_code = int(status_line.split()[1]) if len(status_line.split()) > 1 else 0
        
        return status_code
    
    except Exception as e:
        return 0

def spam_requests(host, port, path, duration=10, name="Spammer"):
    """Spam requests as fast as possible"""
    print(f"\n[{name}] Starting spam test for {duration} seconds...")
    
    start_time = time.time()
    end_time = start_time + duration
    
    results = defaultdict(int)
    total_requests = 0
    
    while time.time() < end_time:
        status = make_request(host, port, path)
        total_requests += 1
        
        if status == 200:
            results['success'] += 1
        elif status == 429:
            results['rate_limited'] += 1
        else:
            results['error'] += 1
    
    actual_duration = time.time() - start_time
    
    print(f"\n[{name}] RESULTS:")
    print(f"  Duration: {actual_duration:.2f}s")
    print(f"  Total requests: {total_requests}")
    print(f"  Successful (200): {results['success']}")
    print(f"  Rate limited (429): {results['rate_limited']}")
    print(f"  Errors: {results['error']}")
    print(f"  Request rate: {total_requests/actual_duration:.2f} req/s")
    print(f"  Success rate: {results['success']/actual_duration:.2f} req/s")
    print(f"  Success ratio: {results['success']/total_requests*100:.1f}%")
    
    return {
        'total': total_requests,
        'success': results['success'],
        'rate_limited': results['rate_limited'],
        'throughput': results['success']/actual_duration
    }

def controlled_requests(host, port, path, rate=4.5, duration=10, name="Controlled"):
    """Send requests at a controlled rate (below limit)"""
    print(f"\n[{name}] Starting controlled test at {rate} req/s for {duration} seconds...")
    
    start_time = time.time()
    end_time = start_time + duration
    
    results = defaultdict(int)
    total_requests = 0
    interval = 1.0 / rate
    
    next_request_time = start_time
    
    while time.time() < end_time:
        current_time = time.time()
        
        if current_time >= next_request_time:
            status = make_request(host, port, path)
            total_requests += 1
            
            if status == 200:
                results['success'] += 1
            elif status == 429:
                results['rate_limited'] += 1
            else:
                results['error'] += 1
            
            next_request_time += interval
        else:
            time.sleep(0.01)  # Small sleep to avoid busy waiting
    
    actual_duration = time.time() - start_time
    
    print(f"\n[{name}] RESULTS:")
    print(f"  Duration: {actual_duration:.2f}s")
    print(f"  Total requests: {total_requests}")
    print(f"  Successful (200): {results['success']}")
    print(f"  Rate limited (429): {results['rate_limited']}")
    print(f"  Errors: {results['error']}")
    print(f"  Request rate: {total_requests/actual_duration:.2f} req/s")
    print(f"  Success rate: {results['success']/actual_duration:.2f} req/s")
    print(f"  Success ratio: {results['success']/total_requests*100:.1f}%")
    
    return {
        'total': total_requests,
        'success': results['success'],
        'rate_limited': results['rate_limited'],
        'throughput': results['success']/actual_duration
    }

def main():
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python test_rate_limit.py <host> <port> [mode] [duration]")
        print("\nModes:")
        print("  spam      - Spam requests as fast as possible (default)")
        print("  controlled - Send requests at 4.5 req/s (below limit)")
        print("  both      - Run both tests sequentially")
        print("\nExample: python test_rate_limit.py localhost 8080 spam 10")
        print("Example: python test_rate_limit.py localhost 8080 both 10")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    mode = sys.argv[3] if len(sys.argv) > 3 else 'spam'
    duration = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    path = '/test.txt'
    
    print("="*70)
    print("RATE LIMITING TEST")
    print("="*70)
    print(f"Target: {host}:{port}{path}")
    print(f"Mode: {mode}")
    print(f"Duration: {duration}s")
    print("="*70)
    
    if mode == 'spam':
        spam_requests(host, port, path, duration, "Spammer")
    elif mode == 'controlled':
        controlled_requests(host, port, path, 4.5, duration, "Controlled")
    elif mode == 'both':
        print("\n--- TEST 1: SPAM REQUESTS ---")
        result1 = spam_requests(host, port, path, duration, "Spammer")
        
        print("\n\nWaiting 2 seconds before next test...")
        time.sleep(2)
        
        print("\n--- TEST 2: CONTROLLED REQUESTS ---")
        result2 = controlled_requests(host, port, path, 4.5, duration, "Controlled")
        
        print("\n" + "="*70)
        print("COMPARISON")
        print("="*70)
        print(f"Spammer throughput:    {result1['throughput']:.2f} successful req/s")
        print(f"Controlled throughput: {result2['throughput']:.2f} successful req/s")
        print(f"\nSpammer was rate-limited {result1['rate_limited']} times")
        print(f"Controlled was rate-limited {result2['rate_limited']} times")
        print("="*70)
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)

if __name__ == '__main__':
    main()
