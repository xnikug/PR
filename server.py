#!/usr/bin/env python3

import socket
import os
import sys
from pathlib import Path
from urllib.parse import unquote

# MIME types for common file extensions
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
    '.js': 'application/javascript'
}

def get_mime_type(filename):
    """Get MIME type based on file extension"""
    ext = Path(filename).suffix.lower()
    return MIME_TYPES.get(ext, 'application/octet-stream')

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def generate_directory_listing(directory_path, url_path):
    """Generate HTML directory listing with table format"""
    try:
        items = sorted(os.listdir(directory_path))
    except PermissionError:
        return None
    
    if not url_path.endswith('/'):
        url_path += '/'
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Index of {url_path}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Liberation Sans', Arial, sans-serif;
            margin: 0;
            padding: 30px;
            background: #fafafa;
            color: #333;
            line-height: 1.5;
        }}
        .header {{
            background: #fff;
            border: 1px solid #ddd;
            margin-bottom: 20px;
            padding: 20px 25px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        h1 {{
            font-size: 24px;
            margin: 0;
            font-weight: 400;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        .path-info {{
            margin-top: 10px;
            font-size: 14px;
            color: #666;
        }}
        .file-table {{
            width: 100%;
            border-collapse: collapse;
            background: #fff;
            border: 2px solid #ddd;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .file-table th {{
            background: #f8f9fa;
            border: 1px solid #ddd;
            border-bottom: 2px solid #ddd;
            padding: 12px 15px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            color: #495057;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .file-table td {{
            border: 1px solid #ddd;
            padding: 10px 15px;
            font-size: 14px;
            vertical-align: middle;
        }}
        .file-table tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        .file-table tr:hover {{
            background: #e3f2fd;
            transition: background-color 0.15s ease;
        }}
        .file-link {{
            color: #1976d2;
            text-decoration: none;
            font-weight: 500;
            display: inline-block;
            padding: 2px 0;
        }}
        .file-link:hover {{
            color: #0d47a1;
            text-decoration: underline;
        }}
        .file-link:visited {{
            color: #7b1fa2;
        }}
        .directory {{
            font-weight: 600;
        }}
        .file-size {{
            color: #666;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }}
        .file-type {{
            color: #666;
            font-size: 13px;
        }}
        .dir-emoji {{
            margin-right: 6px;
            font-size: 16px;
        }}
        .parent-dir {{
            color: #666;
            font-style: italic;
        }}
        .footer {{
            margin-top: 20px;
            padding: 15px;
            background: #fff;
            border: 1px solid #ddd;
            text-align: center;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Index of {url_path}</h1>
        <div class="path-info">Directory listing • {len(items)} item{'s' if len(items) != 1 else ''}</div>
    </div>
    
    <table class="file-table">
        <thead>
            <tr>
                <th>Name</th>
                <th class="size-header" style="width: 100px;">Size</th>
                <th style="width: 150px;">Type</th>
                <th style="width: 100px;">Download</th>
            </tr>
        </thead>
        <tbody>
"""
    
    # Add parent directory link if not root
    if url_path != '/':
        parent_path = '/'.join(url_path.rstrip('/').split('/')[:-1]) or '/'
        html += f'''            <tr>
                <td>
                    <span class="dir-emoji">📁</span>
                    <a href="{parent_path}" class="file-link directory parent-dir">Parent Directory</a>
                </td>
                <td class="file-size">-</td>
                <td class="file-type">Directory</td>
                <td>-</td>
            </tr>
'''
    
    # Add files and directories
    for item in items:
        item_path = os.path.join(directory_path, item)
        item_url = url_path + item
        
        if os.path.isdir(item_path):
            html += f'''            <tr>
                <td>
                    <span class="dir-emoji">📁</span>
                    <a href="{item_url}/" class="file-link directory">{item}</a>
                </td>
                <td class="file-size">-</td>
                <td class="file-type">Directory</td>
                <td>-</td>
            </tr>
'''
        else:
            try:
                file_size = os.path.getsize(item_path)
                size_str = format_file_size(file_size)
                
                # Determine file type description
                ext = Path(item).suffix.lower()
                if ext in ['.html', '.htm']:
                    file_type = 'HTML Document'
                elif ext in ['.txt', '.md']:
                    file_type = 'Text Document'
                elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                    file_type = 'Image File'
                elif ext == '.pdf':
                    file_type = 'PDF Document'
                elif ext == '.py':
                    file_type = 'Python Script'
                elif ext in ['.js']:
                    file_type = 'JavaScript File'
                elif ext in ['.css']:
                    file_type = 'CSS Stylesheet'
                elif ext in ['.json']:
                    file_type = 'JSON Data'
                elif ext in ['.xml']:
                    file_type = 'XML Document'
                else:
                    file_type = 'File' if not ext else f'{ext[1:].upper()} File'
                
                html += f'''            <tr>
                <td><a href="{item_url}" class="file-link">{item}</a></td>
                <td class="file-size">{size_str}</td>
                <td class="file-type">{file_type}</td>
                <td><a href="{item_url}" class="file-link" download>💾 Download</a></td>
            </tr>
'''
            except OSError:
                html += f'''            <tr>
                <td><a href="{item_url}" class="file-link">{item}</a></td>
                <td class="file-size">-</td>
                <td class="file-type">File</td>
                <td><a href="{item_url}" class="file-link" download>💾 Download</a></td>
            </tr>
'''
    
    html += f"""        </tbody>
    </table>
    
    <div class="footer">
        HTTP File Server • Serving {len([item for item in items if os.path.isfile(os.path.join(directory_path, item))])} files and {len([item for item in items if os.path.isdir(os.path.join(directory_path, item))])} directories
    </div>
</body>
</html>"""
    
    return html

def create_http_response(status_code, status_text, content_type, body):
    """Create HTTP response"""
    if isinstance(body, str):
        body = body.encode('utf-8')
    
    response = f"HTTP/1.1 {status_code} {status_text}\r\n"
    response += f"Content-Type: {content_type}\r\n"
    response += f"Content-Length: {len(body)}\r\n"
    response += "Connection: close\r\n"
    response += "\r\n"
    
    return response.encode('utf-8') + body

def create_error_response(code, message):
    """Create simple error response"""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Error {code}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Liberation Sans', Arial, sans-serif;
            margin: 0;
            padding: 30px;
            background: #fafafa;
            color: #333;
            line-height: 1.5;
        }}
        .header {{
            background: #fff;
            border: 1px solid #ddd;
            margin-bottom: 20px;
            padding: 20px 25px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        h1 {{
            font-size: 24px;
            margin: 0;
            font-weight: 400;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        .path-info {{
            margin-top: 10px;
            font-size: 14px;
            color: #666;
        }}
        .error-box {{
            background: #fff;
            border: 1px solid #ddd;
            padding: 25px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .error-title {{
            color: #c0392b;
            font-weight: 600;
            margin: 0 0 8px 0;
        }}
        .error-message {{
            color: #666;
            margin: 0 0 16px 0;
        }}
        .actions {{
            margin-top: 10px;
        }}
        .file-link {{
            color: #1976d2;
            text-decoration: none;
            font-weight: 500;
            display: inline-block;
            padding: 8px 14px;
            border: 1px solid #1976d2;
            border-radius: 6px;
        }}
        .file-link:hover {{
            color: #0d47a1;
            border-color: #0d47a1;
            text-decoration: none;
            background: #e3f2fd;
        }}
        .footer {{
            margin-top: 20px;
            padding: 15px;
            background: #fff;
            border: 1px solid #ddd;
            text-align: center;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Error {code}</h1>
        <div class="path-info">An error occurred while processing your request.</div>
    </div>

    <div class="error-box">
        <p class="error-title">Status: {code}</p>
        <p class="error-message">{message}</p>
        <div class="actions">
            <a href="/" class="file-link">Return to Home</a>
        </div>
    </div>

    <div class="footer">
        HTTP File Server
    </div>
</body>
</html>"""
    return html

def handle_request(client_socket, base_directory):
    """Handle HTTP request"""
    try:
        # Receive request
        request_data = client_socket.recv(4096).decode('utf-8')
        if not request_data:
            return
        
        # Parse request line
        lines = request_data.split('\r\n')
        request_line = lines[0]
        print(f"[REQUEST] {request_line}")
        
        parts = request_line.split()
        if len(parts) < 2:
            return
        
        method, url_path = parts[0], unquote(parts[1])
        
        # Only handle GET requests
        if method != 'GET':
            error_html = create_error_response(405, "Method Not Allowed")
            response = create_http_response(405, "Method Not Allowed", "text/html", error_html)
            client_socket.sendall(response)
            return
        
        # Remove leading slash
        if url_path.startswith('/'):
            url_path = url_path[1:]
        
        # Build file path
        file_path = os.path.normpath(os.path.join(base_directory, url_path))
        
        # Security check - prevent directory traversal
        if not file_path.startswith(os.path.abspath(base_directory)):
            error_html = create_error_response(403, "Forbidden")
            response = create_http_response(403, "Forbidden", "text/html", error_html)
            client_socket.sendall(response)
            return
        
        # Check if file/directory exists
        if not os.path.exists(file_path):
            error_html = create_error_response(404, "Not Found")
            response = create_http_response(404, "Not Found", "text/html", error_html)
            client_socket.sendall(response)
            return
        
        # Handle directory
        if os.path.isdir(file_path):
            # Always generate directory listing for browsing
            listing_html = generate_directory_listing(file_path, '/' + url_path)
            if listing_html is None:
                error_html = create_error_response(403, "Directory access denied")
                response = create_http_response(403, "Forbidden", "text/html", error_html)
            else:
                response = create_http_response(200, "OK", "text/html", listing_html)
            client_socket.sendall(response)
            return
        
        # Serve file
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
                
            mime_type = get_mime_type(file_path)
            response = create_http_response(200, "OK", mime_type, file_content)
            client_socket.sendall(response)
            print(f"[SERVED] {file_path} ({mime_type})")
            
        except Exception as e:
            print(f"[ERROR] Reading file: {e}")
            error_html = create_error_response(500, "Internal Server Error")
            response = create_http_response(500, "Internal Server Error", "text/html", error_html)
            client_socket.sendall(response)
    
    except Exception as e:
        print(f"[ERROR] Request handling: {e}")
    
    finally:
        try:
            client_socket.close()
        except:
            pass

def start_server(directory, host='0.0.0.0', port=8080):
    """Start the HTTP server"""
    if not os.path.isdir(directory):
        print(f"[ERROR] Directory '{directory}' does not exist")
        sys.exit(1)
    
    base_directory = os.path.abspath(directory)
    print(f"[SERVER] Serving files from: {base_directory}")
    print(f"[SERVER] Starting server on {host}:{port}")
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"[SERVER] Server running at http://{host}:{port}")
        print("[SERVER] Press Ctrl+C to stop")
        
        while True:
            try:
                client_socket, address = server_socket.accept()
                print(f"[CONNECTION] {address}")
                handle_request(client_socket, base_directory)
            except Exception as e:
                print(f"[ERROR] Connection error: {e}")
    
    except KeyboardInterrupt:
        print("\n[SERVER] Stopping server...")
    except Exception as e:
        print(f"[ERROR] Server error: {e}")
    
    finally:
        server_socket.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python server.py <directory> [port]")
        print("Example: python server.py ./public 8080")
        sys.exit(1)
    
    directory = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    
    start_server(directory, port=port)