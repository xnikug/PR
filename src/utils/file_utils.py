import os
from pathlib import Path
from typing import Optional


class FileUtils:
    
    @staticmethod
    def get_mime_type(filename: str) -> str:
        MIME_TYPES = {
            '.html': 'text/html',
            '.htm': 'text/html',
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.txt': 'text/plain',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.xml': 'application/xml'
        }
        ext = Path(filename).suffix.lower()
        return MIME_TYPES.get(ext, 'application/octet-stream')
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    @staticmethod
    def is_safe_path(requested_path: str, base_directory: str) -> bool:
        # Check if the requested path is within the base directory
        abs_base = os.path.abspath(base_directory)
        abs_requested = os.path.abspath(requested_path)
        return abs_requested.startswith(abs_base)
    
    @staticmethod
    def get_file_type_description(filename: str) -> str:
        ext = Path(filename).suffix.lower()
        
        type_descriptions = {
            '.html': 'HTML Document',
            '.htm': 'HTML Document',
            '.txt': 'Text Document',
            '.md': 'Text Document',
            '.png': 'Image File',
            '.jpg': 'Image File',
            '.jpeg': 'Image File',
            '.gif': 'Image File',
            '.bmp': 'Image File',
            '.pdf': 'PDF Document',
            '.py': 'Python Script',
            '.js': 'JavaScript File',
            '.css': 'CSS Stylesheet',
            '.json': 'JSON Data',
            '.xml': 'XML Document'
        }
        
        return type_descriptions.get(ext, f'{ext[1:].upper()} File' if ext else 'File')
