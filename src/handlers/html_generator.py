# HTML generation for responses.
import os
from typing import Optional
from ..utils import FileUtils
from ..services import CounterService


class HtmlGenerator:
    
    @staticmethod
    def error_page(code: int, message: str) -> str:
        return f"""<!DOCTYPE html>
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
            background: #e3f2fd;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Error {code}</h1>
    </div>
    <div class="error-box">
        <p class="error-title">Status: {code}</p>
        <p class="error-message">{message}</p>
        <div class="actions">
            <a href="/" class="file-link">Return to Home</a>
        </div>
    </div>
</body>
</html>"""
    
    @staticmethod
    def directory_listing(
        directory_path: str,
        url_path: str,
        base_directory: str,
        counter_service: Optional[CounterService] = None
    ) -> Optional[str]:
        """Generate directory listing HTML."""
        try:
            items = sorted(os.listdir(directory_path))
        except PermissionError:
            return None
        
        if not url_path.endswith('/'):
            url_path += '/'
        
        counter_badge = '<span class="stats-badge">Request Counter Mode</span>' if counter_service else ''
        
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
        .directory {{
            font-weight: 600;
        }}
        .file-size {{
            color: #666;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }}
        .request-count {{
            color: #27ae60;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            font-weight: 600;
        }}
        .stats-badge {{
            display: inline-block;
            background: #e8f5e9;
            color: #2e7d32;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            margin-left: 8px;
        }}
        .dir-emoji {{
            margin-right: 6px;
            font-size: 16px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Index of {url_path}</h1>
        <div class="path-info">Directory listing • {len(items)} item{'s' if len(items) != 1 else ''} {counter_badge}</div>
    </div>
    
    <table class="file-table">
        <thead>
            <tr>
                <th>Name</th>
                <th style="width: 100px;">Size</th>
                <th style="width: 150px;">Type</th>
                {'<th style="width: 100px;">Requests</th>' if counter_service else ''}
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
                    <a href="{parent_path}" class="file-link directory">Parent Directory</a>
                </td>
                <td class="file-size">-</td>
                <td class="file-type">Directory</td>
                {'<td class="request-count">-</td>' if counter_service else ''}
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
                {'<td class="request-count">-</td>' if counter_service else ''}
                <td>-</td>
            </tr>
'''
            else:
                try:
                    file_size = os.path.getsize(item_path)
                    size_str = FileUtils.format_file_size(file_size)
                    file_type = FileUtils.get_file_type_description(item)
                    
                    req_count = counter_service.get_count(item_path) if counter_service else 0
                    
                    html += f'''            <tr>
                <td><a href="{item_url}" class="file-link">{item}</a></td>
                <td class="file-size">{size_str}</td>
                <td class="file-type">{file_type}</td>
                {'<td class="request-count">' + str(req_count) + '</td>' if counter_service else ''}
                <td><a href="{item_url}" class="file-link" download>💾 Download</a></td>
            </tr>
'''
                except OSError:
                    html += f'''            <tr>
                <td><a href="{item_url}" class="file-link">{item}</a></td>
                <td class="file-size">-</td>
                <td class="file-type">File</td>
                {'<td class="request-count">0</td>' if counter_service else ''}
                <td><a href="{item_url}" class="file-link" download>💾 Download</a></td>
            </tr>
'''
        
        html += """        </tbody>
    </table>
    
    <div class="footer" style="margin-top: 20px; padding: 15px; background: #fff; border: 1px solid #ddd; text-align: center; font-size: 12px; color: #666;">
        HTTP File Server (Multithreaded)
    </div>
</body>
</html>"""
        
        return html
