import os
import time
import threading
from typing import Optional

from ..http import HttpRequest, HttpResponse, ResponseBuilder
from ..services import CounterService, RateLimiter
from ..utils import FileUtils
from .html_generator import HtmlGenerator


class RequestHandler:
    
    def __init__(
        self,
        base_directory: str,
        counter_service: CounterService,
        rate_limiter: Optional[RateLimiter] = None,
        simulate_delay: bool = False,
        delay_time: float = 1.0
    ):
        """
        Initialize request handler.
        
        Args:
            base_directory: Base directory to serve files from
            counter_service: Service for counting requests
            rate_limiter: Optional rate limiter service
            simulate_delay: Whether to simulate processing delay
            delay_time: Delay time in seconds
        """
        self.base_directory = os.path.abspath(base_directory)
        self.counter_service = counter_service
        self.rate_limiter = rate_limiter
        self.simulate_delay = simulate_delay
        self.delay_time = delay_time
        self.html_generator = HtmlGenerator()
    
    def handle(self, request: HttpRequest) -> HttpResponse:
        """
        Handle HTTP request and return response.
        
        Args:
            request: Parsed HTTP request
            
        Returns:
            HTTP response
        """
        thread_id = threading.current_thread().name
        
        # Check rate limit if enabled
        if self.rate_limiter:
            allowed, remaining = self.rate_limiter.is_allowed(request.client_ip)
            if not allowed:
                print(f"[RATE LIMIT] {request.client_ip} exceeded rate limit")
                error_html = self.html_generator.error_page(
                    429, 
                    "Too Many Requests - Rate limit exceeded"
                )
                return ResponseBuilder.too_many_requests(error_html)
        
        # Simulate work delay if enabled
        if self.simulate_delay:
            time.sleep(self.delay_time)
        
        # Log request
        print(f"[REQUEST] [{thread_id}] {request.method} {request.path} from {request.client_ip}")
        
        # Only handle GET requests
        if request.method != 'GET':
            error_html = self.html_generator.error_page(405, "Method Not Allowed")
            return ResponseBuilder.method_not_allowed(error_html)
        
        # Build file path
        url_path = request.decoded_path[1:] if request.decoded_path.startswith('/') else request.decoded_path
        file_path = os.path.normpath(os.path.join(self.base_directory, url_path))
        
        # Security check - prevent directory traversal
        if not FileUtils.is_safe_path(file_path, self.base_directory):
            error_html = self.html_generator.error_page(403, "Forbidden")
            return ResponseBuilder.forbidden(error_html)
        
        # Check if file/directory exists
        if not os.path.exists(file_path):
            error_html = self.html_generator.error_page(404, "Not Found")
            return ResponseBuilder.not_found(error_html)
        
        # Handle directory
        if os.path.isdir(file_path):
            return self._handle_directory(file_path, request.decoded_path)
        
        # Handle file
        return self._handle_file(file_path, thread_id)
    
    def _handle_directory(self, directory_path: str, url_path: str) -> HttpResponse:
        # Handle directory listing request.
        try:
            # Increment request counter for directory
            req_count = self.counter_service.increment(directory_path)
            thread_id = threading.current_thread().name
            
            listing_html = self.html_generator.directory_listing(
                directory_path, 
                url_path, 
                self.base_directory,
                self.counter_service
            )
            
            if listing_html is None:
                error_html = self.html_generator.error_page(403, "Directory access denied")
                return ResponseBuilder.forbidden(error_html)
            
            print(f"[SERVED] [{thread_id}] {directory_path} (directory listing) - Request #{req_count}")
            
            return ResponseBuilder.ok("text/html", listing_html)
            
        except Exception as e:
            print(f"[ERROR] Directory listing: {e}")
            error_html = self.html_generator.error_page(500, "Internal Server Error")
            return ResponseBuilder.internal_error(error_html)
    
    def _handle_file(self, file_path: str, thread_id: str) -> HttpResponse:
        # Handle file request.
        try:
            # Increment request counter
            req_count = self.counter_service.increment(file_path)
            
            # Read file
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Get MIME type
            mime_type = FileUtils.get_mime_type(file_path)
            
            print(f"[SERVED] [{thread_id}] {file_path} ({mime_type}) - Request #{req_count}")
            
            return ResponseBuilder.ok(mime_type, file_content)
            
        except Exception as e:
            print(f"[ERROR] Reading file: {e}")
            error_html = self.html_generator.error_page(500, "Internal Server Error")
            return ResponseBuilder.internal_error(error_html)
