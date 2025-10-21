from dataclasses import dataclass
from typing import Dict, Optional
from urllib.parse import unquote


@dataclass
class HttpRequest:
    method: str
    path: str
    headers: Dict[str, str]
    body: bytes
    client_ip: str
    
    @property
    def decoded_path(self) -> str:
        return unquote(self.path)


class RequestParser:
    
    @staticmethod
    def parse(request_data: str, client_ip: str) -> Optional[HttpRequest]:

        if not request_data:
            return None
        
        lines = request_data.split('\r\n')
        if not lines:
            return None
        
        # Parse request line
        request_line = lines[0]
        parts = request_line.split()
        
        if len(parts) < 2:
            return None
        
        method = parts[0]
        path = parts[1]
        
        # Parse headers
        headers = {}
        body_start = 0
        
        for i, line in enumerate(lines[1:], 1):
            if line == '':
                body_start = i + 1
                break
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        
        # Parse body
        body_lines = lines[body_start:]
        body = '\r\n'.join(body_lines).encode('utf-8')
        
        return HttpRequest(
            method=method,
            path=path,
            headers=headers,
            body=body,
            client_ip=client_ip
        )
