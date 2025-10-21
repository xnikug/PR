from dataclasses import dataclass
from typing import Union


@dataclass
class HttpResponse:
    status_code: int
    status_text: str
    content_type: str
    body: bytes
    
    def to_bytes(self) -> bytes:
        if isinstance(self.body, str):
            body_bytes = self.body.encode('utf-8')
        else:
            body_bytes = self.body
        
        response = f"HTTP/1.1 {self.status_code} {self.status_text}\r\n"
        response += f"Content-Type: {self.content_type}\r\n"
        response += f"Content-Length: {len(body_bytes)}\r\n"
        response += "Connection: close\r\n"
        response += "\r\n"
        
        return response.encode('utf-8') + body_bytes


class ResponseBuilder:
    
    @staticmethod
    def ok(content_type: str, body: Union[str, bytes]) -> HttpResponse:
        # Create 200 OK response
        return HttpResponse(200, "OK", content_type, body)
    
    @staticmethod
    def not_found(body: Union[str, bytes]) -> HttpResponse:
        # Create 404 Not Found response.
        return HttpResponse(404, "Not Found", "text/html", body)
    
    @staticmethod
    def forbidden(body: Union[str, bytes]) -> HttpResponse:
        # Create 403 Forbidden response.
        return HttpResponse(403, "Forbidden", "text/html", body)
    
    @staticmethod
    def method_not_allowed(body: Union[str, bytes]) -> HttpResponse:
        # Create 405 Method Not Allowed response.
        return HttpResponse(405, "Method Not Allowed", "text/html", body)
    
    @staticmethod
    def too_many_requests(body: Union[str, bytes]) -> HttpResponse:
       # Create 429 Too Many Requests response.
        return HttpResponse(429, "Too Many Requests", "text/html", body)
    
    @staticmethod
    def internal_error(body: Union[str, bytes]) -> HttpResponse:
        # Create 500 Internal Server Error response.
        return HttpResponse(500, "Internal Server Error", "text/html", body)
