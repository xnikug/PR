import socket
import sys
import os
from concurrent.futures import ThreadPoolExecutor

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.http import RequestParser, ResponseBuilder
from src.services import CounterService, UnsafeCounterService, RateLimiter
from src.handlers import RequestHandler


class HttpServer:
    """Main HTTP server class."""
    
    def __init__(
        self,
        directory: str,
        host: str = '0.0.0.0',
        port: int = 8080,
        use_threads: bool = True,
        max_workers: int = None,
        enable_rate_limiting: bool = True,
        rate_limit: int = 5,
        simulate_delay: bool = False,
        delay_time: float = 1.0,
        use_unsafe_counter: bool = False
    ):
        """
        Initialize HTTP server.
        
        Args:
            directory: Directory to serve files from
            host: Host address to bind to
            port: Port number to listen on
            use_threads: Whether to use multithreading
            max_workers: Maximum number of worker threads
            enable_rate_limiting: Whether to enable rate limiting
            rate_limit: Maximum requests per second per IP
            simulate_delay: Whether to simulate processing delay
            delay_time: Delay time in seconds
            use_unsafe_counter: Whether to use unsafe counter (for race condition demo)
        """
        if not os.path.isdir(directory):
            raise ValueError(f"Directory '{directory}' does not exist")
        
        self.directory = os.path.abspath(directory)
        self.host = host
        self.port = port
        self.use_threads = use_threads
        self.max_workers = max_workers
        self.use_unsafe_counter = use_unsafe_counter
        
        # Initialize services
        if use_unsafe_counter:
            self.counter_service = UnsafeCounterService(delay=0.01)
            print("[WARNING] Using UNSAFE counter - race conditions will occur!")
        else:
            self.counter_service = CounterService()
        
        self.rate_limiter = RateLimiter(max_requests=rate_limit) if enable_rate_limiting else None
        
        # Initialize request handler
        self.request_handler = RequestHandler(
            base_directory=self.directory,
            counter_service=self.counter_service,
            rate_limiter=self.rate_limiter,
            simulate_delay=simulate_delay,
            delay_time=delay_time
        )
        
        self.server_socket = None
    
    def _handle_client(self, client_socket: socket.socket, client_address: tuple):
        """Handle individual client connection."""
        try:
            # Receive request data
            request_data = client_socket.recv(4096).decode('utf-8')
            if not request_data:
                return
            
            # Parse request
            request = RequestParser.parse(request_data, client_address[0])
            if not request:
                return
            
            # Handle request
            response = self.request_handler.handle(request)
            
            # Send response
            client_socket.sendall(response.to_bytes())
            
        except Exception as e:
            print(f"[ERROR] Client handling: {e}")
            try:
                error_response = ResponseBuilder.internal_error(
                    f"<html><body><h1>500 Internal Server Error</h1><p>{str(e)}</p></body></html>"
                )
                client_socket.sendall(error_response.to_bytes())
            except:
                pass
        
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def start(self):
        """Start the HTTP server."""
        server_mode = "Multithreaded" if self.use_threads else "Single-threaded"
        counter_mode = "UNSAFE (Race Condition Demo)" if self.use_unsafe_counter else "Thread-Safe"
        
        print(f"\n{'='*70}")
        print(f"HTTP FILE SERVER")
        print(f"{'='*70}")
        print(f"Mode: {server_mode}")
        print(f"Counter: {counter_mode}")
        print(f"Serving from: {self.directory}")
        print(f"Address: {self.host}:{self.port}")
        if self.rate_limiter:
            print(f"Rate limiting: Enabled (5 req/s per IP)")
        else:
            print(f"Rate limiting: Disabled")
        
        if self.use_unsafe_counter:
            print(f"\n{'WARNING!'}")
            print(f"Running with UNSAFE counter to demonstrate race conditions!")
            print(f"Expect incorrect counter values with concurrent requests.")
        
        print(f"{'='*70}\n")
        
        # Create socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            print(f"[SERVER] Running at http://{self.host}:{self.port}")
            print(f"[SERVER] Press Ctrl+C to stop\n")
            
            if self.use_threads:
                self._run_multithreaded()
            else:
                self._run_single_threaded()
        
        except KeyboardInterrupt:
            print("\n[SERVER] Stopping server...")
            self._print_statistics()
        
        except Exception as e:
            print(f"[ERROR] Server error: {e}")
        
        finally:
            if self.server_socket:
                self.server_socket.close()
    
    def _run_multithreaded(self):
        """Run server in multithreaded mode."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while True:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"[CONNECTION] {address[0]}:{address[1]}")
                    executor.submit(self._handle_client, client_socket, address)
                except Exception as e:
                    print(f"[ERROR] Connection error: {e}")
    
    def _run_single_threaded(self):
        """Run server in single-threaded mode."""
        while True:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"[CONNECTION] {address[0]}:{address[1]}")
                self._handle_client(client_socket, address)
            except Exception as e:
                print(f"[ERROR] Connection error: {e}")
    
    def _print_statistics(self):
        """Print server statistics on shutdown."""
        print("\n" + "="*70)
        print("SERVER STATISTICS")
        print("="*70)
        
        counts = self.counter_service.get_all_counts()
        if counts:
            print(f"\nFile Request Counts:")
            total_expected = sum(counts.values())
            for file_path, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
                filename = os.path.basename(file_path)
                print(f"  {filename}: {count} requests")
            
            if self.use_unsafe_counter:
                print(f"The counter values above are likely incorrect due to race conditions.")
                print(f"Compare with the safe version to see the difference.")
        else:
            print("\nNo files were requested")
        
        print("\n" + "="*70 + "\n")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python(3) server.py <directory> [port] [options]")
        print("\nOptions:")
        print("  --single-threaded    Run in single-threaded mode")
        print("  --delay              Simulate 1s delay per request")
        print("  --no-rate-limit      Disable rate limiting")
        print("  --unsafe-counter     Use unsafe counter (demonstrates race conditions)")
        print("\nExamples:")
        print("  python(3) server.py ./public 8080")
        print("  python(3) server.py ./public 8080 --delay")
        print("  python(3) server.py ./public 8080 --single-threaded")
        print("\n  Race Condition Demo:")
        print("  python(3) server.py ./public 8081 --unsafe-counter")
        print("  python(3) test_concurrent.py localhost 8081 20 /test.txt")
        sys.exit(1)
    
    directory = sys.argv[1]
    port = 8080
    use_threads = True
    simulate_delay = False
    enable_rate_limiting = True
    use_unsafe_counter = False
    
    # Parse arguments
    for i in range(2, len(sys.argv)):
        arg = sys.argv[i]
        if arg.isdigit():
            port = int(arg)
        elif arg == '--single-threaded':
            use_threads = False
        elif arg == '--delay':
            simulate_delay = True
        elif arg == '--no-rate-limit':
            enable_rate_limiting = False
        elif arg == '--unsafe-counter':
            use_unsafe_counter = True
    
    # Create and start server
    server = HttpServer(
        directory=directory,
        port=port,
        use_threads=use_threads,
        enable_rate_limiting=enable_rate_limiting,
        simulate_delay=simulate_delay,
        use_unsafe_counter=use_unsafe_counter
    )
    
    server.start()


if __name__ == '__main__':
    main()
