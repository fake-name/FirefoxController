#!/usr/bin/env python3

"""
Simple local web server for FirefoxController testing
This server provides test pages that don't require internet access
"""

import http.server
import socketserver
import threading
import os
import json
from urllib.parse import urlparse, parse_qs
import time

class TestHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler for test pages"""
    
    def __init__(self, *args, **kwargs):
        # Use the tests/html_pages directory as the base directory
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        html_pages_dir = os.path.join(tests_dir, "html_pages")
        super().__init__(*args, directory=html_pages_dir, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_url = urlparse(self.path)
        
        # Handle different test pages
        if parsed_url.path == "/":
            self.path = "test_index.html"
        elif parsed_url.path == "/simple":
            self.path = "test_simple.html"
        elif parsed_url.path == "/cookies":
            self.path = "test_cookies.html"
        elif parsed_url.path == "/javascript":
            self.path = "test_javascript.html"
        elif parsed_url.path == "/dom":
            self.path = "test_dom.html"
        elif parsed_url.path == "/form":
            self.path = "test_form.html"
        elif parsed_url.path == "/redirect":
            # Test redirect
            self.send_response(302)
            self.send_header("Location", "/simple")
            self.end_headers()
            return
        elif parsed_url.path == "/set-cookie":
            # Set a test cookie
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Set-Cookie", "test_cookie=test_value; Path=/")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Cookie Set</h1></body></html>")
            return
        elif parsed_url.path == "/check-cookie":
            # Check if cookie was sent
            cookies = self.headers.get("Cookie", "")
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            response = f"<html><body><h1>Cookies: {cookies}</h1></body></html>"
            self.wfile.write(response.encode())
            return
        
        # Handle static files
        return super().do_GET()
    
    def do_POST(self):
        """Handle POST requests for form testing"""
        parsed_url = urlparse(self.path)
        
        if parsed_url.path == "/form-submit":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            response = f"""<html><body>
                <h1>Form Submitted</h1>
                <p>Data: {post_data.decode()}</p>
            </body></html>"""
            self.wfile.write(response.encode())
            return
        
        self.send_response(404)
        self.end_headers()

class TestServer:
    """Test server that can be started and stopped"""
    
    def __init__(self, port=9000):
        self.port = port
        self.server = None
        self.server_thread = None
        self.base_url = f"http://localhost:{port}"
    
    def start(self):
        """Start the test server in a background thread"""
        if self.server is not None:
            return
        
        # Try to create server, handle port conflicts
        try:
            self.server = socketserver.TCPServer(("localhost", self.port), TestHTTPRequestHandler)
            
            # Start server in background thread
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            # Wait a moment for server to start
            time.sleep(0.5)
            
            print(f"Test server started on {self.base_url}")
        except OSError as e:
            if "Address already in use" in str(e):
                # Try to find an available port
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(("localhost", 0))
                self.port = sock.getsockname()[1]
                sock.close()
                
                self.base_url = f"http://localhost:{self.port}"
                
                # Create server with new port
                self.server = socketserver.TCPServer(("localhost", self.port), TestHTTPRequestHandler)
                self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
                self.server_thread.start()
                
                # Wait a moment for server to start
                time.sleep(0.5)
                
                print(f"Test server started on {self.base_url} (port {self.port} was in use)")
            else:
                raise
    
    def stop(self):
        """Stop the test server"""
        if self.server is None:
            return
        
        self.server.shutdown()
        self.server.server_close()
        self.server = None
        self.server_thread = None
        
        print("Test server stopped")
    
    def get_url(self, path=""):
        """Get full URL for a path"""
        return f"{self.base_url}{path}"
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()

# Create test HTML files if they don't exist
def create_test_html_files():
    """Create test HTML files"""
    
    test_files = {
        "test_index.html": """<html>
<head>
    <title>Test Index</title>
</head>
<body>
    <h1>Welcome to FirefoxController Test Server</h1>
    <p>This is the main test page.</p>
    <nav>
        <a href="/simple">Simple Page</a> |
        <a href="/javascript">JavaScript Page</a> |
        <a href="/dom">DOM Page</a> |
        <a href="/form">Form Page</a> |
        <a href="/cookies">Cookies Page</a>
    </nav>
</body>
</html>""",
        
        "test_simple.html": """<html>
<head>
    <title>Simple Test Page</title>
</head>
<body>
    <h1>Simple Test Page</h1>
    <p>This is a simple page for basic testing.</p>
    <div id="content">
        <p>Some content here.</p>
    </div>
</body>
</html>""",
        
        "test_javascript.html": """<html>
<head>
    <title>JavaScript Test Page</title>
    <script>
        function testFunction(a, b) {
            return a + b;
        }
        
        var testVariable = "Hello from JavaScript";
    </script>
</head>
<body>
    <h1>JavaScript Test Page</h1>
    <p id="js-test">This page has JavaScript functions.</p>
    <button onclick="document.getElementById('js-test').innerText = 'Button clicked!'">Click Me</button>
</body>
</html>""",
        
        "test_dom.html": """<html>
<head>
    <title>DOM Test Page</title>
</head>
<body>
    <h1>DOM Test Page</h1>
    <div id="test-div">
        <p class="test-paragraph">First paragraph</p>
        <p class="test-paragraph">Second paragraph</p>
        <a href="/simple" id="test-link">Go to simple page</a>
    </div>
    <button id="test-button">Test Button</button>
    <input type="text" id="test-input" value="test input">
</body>
</html>""",
        
        "test_form.html": """<html>
<head>
    <title>Form Test Page</title>
</head>
<body>
    <h1>Form Test Page</h1>
    <form action="/form-submit" method="post" id="test-form">
        <input type="text" name="username" value="testuser">
        <input type="password" name="password" value="testpass">
        <button type="submit">Submit</button>
    </form>
</body>
</html>""",
        
        "test_cookies.html": """<html>
<head>
    <title>Cookies Test Page</title>
</head>
<body>
    <h1>Cookies Test Page</h1>
    <p>This page is for testing cookie functionality.</p>
    <a href="/set-cookie">Set Test Cookie</a> |
    <a href="/check-cookie">Check Cookies</a>
</body>
</html>"""
    }
    
    # Create html_pages directory if it doesn't exist
    html_pages_dir = "tests/html_pages"
    if not os.path.exists(html_pages_dir):
        os.makedirs(html_pages_dir)
    
    for filename, content in test_files.items():
        filepath = os.path.join(html_pages_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, "w") as f:
                f.write(content)

def get_test_server():
    """Get a test server instance"""
    create_test_html_files()
    return TestServer()

if __name__ == "__main__":
    # Create test files
    create_test_html_files()
    
    # Start server
    server = TestServer()
    server.start()
    
    print(f"Test server running on {server.base_url}")
    print("Press Ctrl+C to stop...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()