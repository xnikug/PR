#!/usr/bin/env python3

import socket
import sys
import os
from pathlib import Path

def parse_http_response(response_data):
    header_end = response_data.find(b'\r\n\r\n')
    if header_end == -1:
        return None, None, None
    
    headers_section = response_data[:header_end].decode('utf-8', errors='ignore')
    body = response_data[header_end + 4:]
    
    lines = headers_section.split('\r\n')
    status_line = lines[0]
    status_parts = status_line.split(' ', 2)
    
    if len(status_parts) < 2:
        return None, None, None
    
    status_code = int(status_parts[1])
    
    headers = {}
    for line in lines[1:]:
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip().lower()] = value.strip()
    
    return status_code, headers, body

def extract_content_type(headers):
    content_type = headers.get('content-type', '')
    return content_type.split(';')[0].strip()

def make_http_request(host, port, path):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        print(f"[CLIENT] Connecting to {host}:{port}")
        client_socket.connect((host, port))
        
        request = f"GET {path} HTTP/1.1\r\n"
        request += f"Host: {host}:{port}\r\n"
        request += "User-Agent: HTTP-Client/1.0\r\n"
        request += "Connection: close\r\n"
        request += "\r\n"
        
        print(f"[REQUEST] {path}")
        client_socket.sendall(request.encode('utf-8'))
        
        response_data = b''
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            response_data += chunk
        
        return response_data
    
    finally:
        client_socket.close()

def save_file(filename, content, directory):
    os.makedirs(directory, exist_ok=True)
    
    file_path = os.path.join(directory, filename)
    
    with open(file_path, 'wb') as f:
        f.write(content)
    
    print(f"[SAVED] {file_path}")
    return file_path

def extract_filename(url_path):
    path = url_path.split('?')[0]
    filename = path.split('/')[-1]
    
    if not filename or filename == '':
        filename = 'index.html'
    
    return filename

def display_content(content, content_type):
    border = "=" * 80
    
    print(f"\n{border}")
    print(f"CONTENT DISPLAY")
    print(f"Content-Type: {content_type}")
    print(f"{border}")
    
    try:
        decoded_content = content.decode('utf-8', errors='ignore')
        print(decoded_content)
    except:
        print("[BINARY CONTENT - Cannot display as text]")
    
    print(f"{border}\n")

def main():
    if len(sys.argv) < 4:
        print("HTTP CLIENT USAGE:")
        print("python client.py <host> <port> <path> [download_directory]")
        print("Example: python client.py localhost 8080 /test.txt")
        print("Example: python client.py localhost 8080 /test.pdf ./custom_saves")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    path = sys.argv[3]
    download_directory = sys.argv[4] if len(sys.argv) > 4 else './client_saves'
    
    if not path.startswith('/'):
        path = '/' + path
    
    try:
        response_data = make_http_request(host, port, path)
        
        status_code, headers, body = parse_http_response(response_data)
        
        if status_code is None:
            print("[ERROR] Invalid response from server")
            sys.exit(1)
        
        print(f"[STATUS] {status_code}")
        
        if status_code != 200:
            print(f"[ERROR] Server returned status {status_code}")
            if body:
                error_content = body.decode('utf-8', errors='ignore')
                if '<html>' in error_content.lower():
                    print("[ERROR PAGE CONTENT]")
                    display_content(body, 'text/html')
                else:
                    print(error_content)
            sys.exit(1)
        
        content_type = extract_content_type(headers)
        print(f"[CONTENT] Type: {content_type}")
        print(f"[SIZE] {len(body)} bytes")
        
        # Always save files to client_saves directory
        filename = extract_filename(path)
        
        # Add appropriate file extension if missing
        if content_type == 'application/pdf' and not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        elif content_type == 'image/png' and not filename.lower().endswith('.png'):
            filename += '.png'
        elif content_type == 'image/jpeg' and not filename.lower().endswith(('.jpg', '.jpeg')):
            filename += '.jpg'
        elif content_type == 'image/gif' and not filename.lower().endswith('.gif'):
            filename += '.gif'
        elif content_type == 'text/html' and not filename.lower().endswith(('.html', '.htm')):
            filename += '.html'
        elif content_type == 'text/plain' and not filename.lower().endswith('.txt'):
            filename += '.txt'
        
        # Save the file
        saved_path = save_file(filename, body, download_directory)
        
        # Display content for text files
        if content_type in ['text/html', 'text/plain']:
            display_content(body, content_type)
        
        print(f"\n[SUCCESS] File saved to: {saved_path}")
        print(f"[INFO] Download directory: {os.path.abspath(download_directory)}")
        
    except ConnectionRefusedError:
        print(f"[ERROR] Cannot connect to server at {host}:{port}")
        print("Make sure the server is running")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Client error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()