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
    
    def do_HEAD(self):
        """Handle HEAD requests - call do_GET but don't send body"""
        # Save the command and call do_GET
        self.command = 'HEAD'
        self.do_GET()

    def do_GET(self):
        """Handle GET and HEAD requests"""
        parsed_url = urlparse(self.path)
        is_head = (self.command == 'HEAD')
        
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
        elif parsed_url.path == "/async-fetch":
            self.path = "test_async_fetch.html"
        elif parsed_url.path == "/async-xhr":
            self.path = "test_async_xhr.html"
        elif parsed_url.path == "/async-multiple":
            self.path = "test_async_multiple.html"
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
        elif parsed_url.path == "/set-persistent-cookie":
            # Set a PERSISTENT test cookie with expiry
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            # Set cookie with Max-Age of 24 hours (86400 seconds)
            self.send_header("Set-Cookie", "persistent_test_cookie=persistent_value; Path=/; Max-Age=86400")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Persistent Cookie Set</h1><p>Cookie: persistent_test_cookie=persistent_value (expires in 24 hours)</p></body></html>")
            return
        elif parsed_url.path == "/check-cookie":
            # Check if cookie was sent
            cookies = self.headers.get("Cookie", "")
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            response = "<html><body><h1>Cookies: {}</h1></body></html>".format(cookies)
            self.wfile.write(response.encode())
            return
        elif parsed_url.path == "/api/data":
            # API endpoint for async fetch testing
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            response = json.dumps({
                "status": "success",
                "data": "This is async fetched data",
                "timestamp": time.time()
            })
            self.wfile.write(response.encode())
            return
        elif parsed_url.path == "/api/delayed":
            # API endpoint with delay for testing async timing
            time.sleep(1)  # Simulate slow API
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            response = json.dumps({
                "status": "success",
                "data": "This is delayed async data",
                "delay": "1 second"
            })
            self.wfile.write(response.encode())
            return
        elif parsed_url.path == "/api/text":
            # Plain text API endpoint
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"Plain text async response")
            return
        elif parsed_url.path == "/download/image.png":
            # Serve a small test PNG image (1x1 red pixel)
            self.send_response(200)
            self.send_header("Content-type", "image/png")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            # 1x1 red pixel PNG (base64 decoded)
            png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            self.wfile.write(png_data)
            return
        elif parsed_url.path == "/download/document.pdf":
            # Serve a minimal PDF file
            self.send_response(200)
            self.send_header("Content-type", "application/pdf")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            # Minimal PDF content
            pdf_data = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Test PDF) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000317 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n410\n%%EOF\n'
            self.wfile.write(pdf_data)
            return
        elif parsed_url.path == "/download/archive.zip":
            # Serve a small ZIP file
            self.send_response(200)
            self.send_header("Content-type", "application/zip")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            # Minimal ZIP file with one text file
            import zipfile
            import io
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr("test.txt", "This is a test file in a ZIP archive")
            self.wfile.write(zip_buffer.getvalue())
            return
        elif parsed_url.path == "/download/data.json":
            # Serve JSON file that might be downloaded
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            response = json.dumps({
                "type": "downloadable_data",
                "content": "This JSON might trigger download",
                "size": 1024
            })
            self.wfile.write(response.encode())
            return
        elif parsed_url.path == "/download/text.txt":
            # Serve a plain text file
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"This is a plain text file that could be downloaded.")
            return
        elif parsed_url.path == "/download/binary.bin":
            # Serve arbitrary binary data
            self.send_response(200)
            self.send_header("Content-type", "application/octet-stream")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            # Some binary data (not valid file format, just bytes)
            binary_data = bytes(range(256))
            self.wfile.write(binary_data)
            return
        elif parsed_url.path == "/timeout/infinite":
            # Page that never finishes loading - sends headers but never completes
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()

            # Send partial content but never finish
            chunk = b"<html><head><title>Infinite Loading</title></head><body><h1>This page will never finish loading..."
            self.wfile.write(b"%X\r\n%s\r\n" % (len(chunk), chunk))
            self.wfile.flush()

            # Wait for server shutdown or client timeout
            import threading
            event = threading.Event()
            if hasattr(self.server, 'test_server_instance'):
                self.server.test_server_instance.shutdown_events.append(event)
            event.wait(timeout=120)  # Wait max 120s or until shutdown
            return

        elif parsed_url.path == "/timeout/slow":
            # Page that loads very slowly but eventually completes
            delay = int(parse_qs(parsed_url.query).get('delay', ['10'])[0])

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            # Wait before sending content
            time.sleep(delay)

            html = """<html>
<head><title>Slow Page</title></head>
<body>
    <h1>Slow Loading Page</h1>
    <p>This page took {delay} seconds to load.</p>
</body>
</html>""".format(delay=delay)
            self.wfile.write(html.encode())
            return

        elif parsed_url.path == "/timeout/partial":
            # Page that sends partial content then stalls
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()

            # Send some chunks with delays
            chunks = [
                b"<html><head><title>Partial Page</title></head><body>",
                b"<h1>Loading...</h1>",
                b"<p>This page sends partial content</p>",
            ]

            for chunk in chunks:
                self.wfile.write(b"%X\r\n%s\r\n" % (len(chunk), chunk))
                self.wfile.flush()
                time.sleep(1)

            # Wait for server shutdown or client timeout
            import threading
            event = threading.Event()
            if hasattr(self.server, 'test_server_instance'):
                self.server.test_server_instance.shutdown_events.append(event)
            event.wait(timeout=120)  # Wait max 120s or until shutdown
            return

        elif parsed_url.path == "/timeout/stuck-resource":
            # Page that loads but has a stuck resource (image/script that never loads)
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            html = """<html>
<head>
    <title>Stuck Resource Page</title>
    <!-- This script will never load -->
    <script src="/timeout/infinite-resource.js"></script>
</head>
<body>
    <h1>Page with Stuck Resource</h1>
    <p>The HTML loaded but a resource is stuck.</p>
    <!-- This image will never load -->
    <img src="/timeout/infinite-resource.png" alt="Stuck image">
</body>
</html>"""
            self.wfile.write(html.encode())
            return

        elif parsed_url.path == "/timeout/infinite-resource.js" or parsed_url.path == "/timeout/infinite-resource.png":
            # Resource that never finishes loading
            self.send_response(200)
            if parsed_url.path.endswith('.js'):
                self.send_header("Content-type", "application/javascript")
            else:
                self.send_header("Content-type", "image/png")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()

            # Send partial content and stall
            chunk = b"// Partial content..."
            self.wfile.write(b"%X\r\n%s\r\n" % (len(chunk), chunk))
            self.wfile.flush()

            # Wait for server shutdown or client timeout
            import threading
            event = threading.Event()
            if hasattr(self.server, 'test_server_instance'):
                self.server.test_server_instance.shutdown_events.append(event)
            event.wait(timeout=120)  # Wait max 120s or until shutdown
            return

        elif parsed_url.path == "/download/large.bin":
            # Serve a large file (5MB) to test chunking
            file_size = 5 * 1024 * 1024  # 5MB
            range_header = self.headers.get('Range')
            print(f"[DEBUG] Large file request - Range header: {range_header}, All headers: {dict(self.headers)}")

            if range_header:
                # Parse Range header: bytes=start-end
                range_match = range_header.replace('bytes=', '').split('-')
                start = int(range_match[0])
                end = int(range_match[1]) if range_match[1] else file_size - 1

                self.send_response(206)  # Partial Content
                self.send_header("Content-type", "application/octet-stream")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Range", "bytes {}-{}/{}".format(start, end, file_size))
                self.send_header("Content-Length", str(end - start + 1))
                self.end_headers()

                # Send the requested chunk (repeating pattern for testing)
                if not is_head:
                    chunk_size = end - start + 1
                    for i in range(chunk_size):
                        self.wfile.write(bytes([(start + i) % 256]))
            else:
                self.send_response(200)
                self.send_header("Content-type", "application/octet-stream")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", str(file_size))
                self.end_headers()

                # Send full file (repeating pattern) - skip for HEAD
                if not is_head:
                    for i in range(file_size):
                        self.wfile.write(bytes([i % 256]))
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
            
            response = """<html><body>
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
        self.base_url = "http://localhost:{}".format(port)
        self.shutdown_events = []  # Track events to signal on shutdown
    
    def start(self):
        """Start the test server in a background thread"""
        if self.server is not None:
            return
        
        # Try to create server, handle port conflicts
        try:
            self.server = socketserver.TCPServer(("localhost", self.port), TestHTTPRequestHandler)
            # Give request handler access to this instance for shutdown events
            self.server.test_server_instance = self
            
            # Start server in background thread
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            # Wait a moment for server to start
            time.sleep(0.5)
            
            print("Test server started on {}".format(self.base_url))
        except OSError as e:
            if "Address already in use" in str(e):
                # Try to find an available port
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(("localhost", 0))
                self.port = sock.getsockname()[1]
                sock.close()
                
                self.base_url = "http://localhost:{}".format(self.port)
                
                # Create server with new port
                self.server = socketserver.TCPServer(("localhost", self.port), TestHTTPRequestHandler)
                # Give request handler access to this instance for shutdown events
                self.server.test_server_instance = self
                self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
                self.server_thread.start()
                
                # Wait a moment for server to start
                time.sleep(0.5)
                
                print("Test server started on {} (port {} was in use)".format(self.base_url, self.port))
            else:
                raise
    
    def stop(self):
        """Stop the test server"""
        if self.server is None:
            return

        # Signal all waiting threads to finish
        for event in self.shutdown_events:
            event.set()

        self.server.shutdown()
        self.server.server_close()
        self.server = None
        self.server_thread = None

        print("Test server stopped")

    def __del__(self):
        """Ensure server is stopped on deletion"""
        try:
            self.stop()
        except:
            pass
    
    def get_url(self, path=""):
        """Get full URL for a path"""
        return "{}{}".format(self.base_url, path)
    
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
        <label for="username">Username:</label>
        <input type="text" id="username" name="username" value="">
        <label for="password">Password:</label>
        <input type="password" id="password" name="password" value="">
        <label for="email">Email:</label>
        <input type="email" id="email" name="email" value="">
        <button type="submit" id="submit-btn">Submit</button>
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
</html>""",

        "test_async_fetch.html": """<html>
<head>
    <title>Async Fetch Test Page</title>
    <script>
        // Perform async fetch after page load
        window.addEventListener('load', function() {
            console.log('Page loaded, starting async fetch...');

            // Fetch data after 500ms delay
            setTimeout(function() {
                fetch('/api/data')
                    .then(response => response.json())
                    .then(data => {
                        console.log('Fetched data:', data);
                        document.getElementById('result').textContent = JSON.stringify(data);
                        document.getElementById('status').textContent = 'Fetch completed!';
                    })
                    .catch(error => {
                        console.error('Fetch error:', error);
                        document.getElementById('status').textContent = 'Fetch failed!';
                    });
            }, 500);
        });
    </script>
</head>
<body>
    <h1>Async Fetch Test Page</h1>
    <p>This page performs an async fetch after page load.</p>
    <p>Status: <span id="status">Loading...</span></p>
    <p>Result: <span id="result"></span></p>
</body>
</html>""",

        "test_async_xhr.html": """<html>
<head>
    <title>Async XHR Test Page</title>
    <script>
        // Perform async XMLHttpRequest after page load
        window.addEventListener('load', function() {
            console.log('Page loaded, starting async XHR...');

            // Make XHR after 500ms delay
            setTimeout(function() {
                var xhr = new XMLHttpRequest();
                xhr.open('GET', '/api/text', true);
                xhr.onload = function() {
                    if (xhr.status === 200) {
                        console.log('XHR response:', xhr.responseText);
                        document.getElementById('result').textContent = xhr.responseText;
                        document.getElementById('status').textContent = 'XHR completed!';
                    }
                };
                xhr.onerror = function() {
                    console.error('XHR error');
                    document.getElementById('status').textContent = 'XHR failed!';
                };
                xhr.send();
            }, 500);
        });
    </script>
</head>
<body>
    <h1>Async XHR Test Page</h1>
    <p>This page performs an async XMLHttpRequest after page load.</p>
    <p>Status: <span id="status">Loading...</span></p>
    <p>Result: <span id="result"></span></p>
</body>
</html>""",

        "test_async_multiple.html": """<html>
<head>
    <title>Multiple Async Requests Test Page</title>
    <script>
        // Perform multiple async fetches after page load
        window.addEventListener('load', function() {
            console.log('Page loaded, starting multiple async fetches...');

            var fetchCount = 0;
            var totalFetches = 3;

            function updateStatus() {
                fetchCount++;
                document.getElementById('status').textContent =
                    'Completed ' + fetchCount + ' of ' + totalFetches + ' fetches';
            }

            // Fetch 1: Immediate
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    console.log('Fetch 1 data:', data);
                    document.getElementById('result1').textContent = JSON.stringify(data);
                    updateStatus();
                });

            // Fetch 2: After 500ms
            setTimeout(function() {
                fetch('/api/text')
                    .then(response => response.text())
                    .then(data => {
                        console.log('Fetch 2 data:', data);
                        document.getElementById('result2').textContent = data;
                        updateStatus();
                    });
            }, 500);

            // Fetch 3: After 1000ms (delayed API)
            setTimeout(function() {
                fetch('/api/delayed')
                    .then(response => response.json())
                    .then(data => {
                        console.log('Fetch 3 data:', data);
                        document.getElementById('result3').textContent = JSON.stringify(data);
                        updateStatus();
                    });
            }, 1000);
        });
    </script>
</head>
<body>
    <h1>Multiple Async Requests Test Page</h1>
    <p>This page performs multiple async fetches at different times.</p>
    <p>Status: <span id="status">Loading...</span></p>
    <div>
        <h3>Fetch 1 (immediate):</h3>
        <p id="result1">Waiting...</p>
    </div>
    <div>
        <h3>Fetch 2 (after 500ms):</h3>
        <p id="result2">Waiting...</p>
    </div>
    <div>
        <h3>Fetch 3 (after 1000ms, delayed API):</h3>
        <p id="result3">Waiting...</p>
    </div>
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
    
    print("Test server running on {}".format(server.base_url))
    print("Press Ctrl+C to stop...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()