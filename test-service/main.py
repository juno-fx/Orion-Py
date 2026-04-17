#!/usr/bin/env python3
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUTH_SERVICE_URL = "http://localhost:13000/rhea/api/v1/auth/validate"
TARGET_IDENTITY = 'argocd::Service:"testservice"'
PORT = 3000


class TestServiceHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/testservice/v1/hello":
            self.handle_hello()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/testservice/v1/echo":
            self.handle_echo()
        else:
            self.send_response(404)
            self.end_headers()

    def handle_hello(self):
        auth_header = self.headers.get("X-ORION-SERVICE-AUTH")
        
        if not auth_header:
            logger.error("Missing X-ORION-SERVICE-AUTH header")
            self.send_response(401)
            self.end_headers()
            return

        auth_body = {
            "target_url": "/testservice/v1/hello",
            "target_identity": TARGET_IDENTITY,
            "target_method": "GET"
        }

        try:
            req = urllib.request.Request(
                AUTH_SERVICE_URL,
                data=json.dumps(auth_body).encode('utf-8'),
                headers={
                    "X-ORION-SERVICE-AUTH": auth_header,
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"hello")
                else:
                    logger.error(f"Auth service returned status: {response.status}")
                    self.send_response(response.status)
                    self.end_headers()
                    
        except urllib.error.HTTPError as e:
            logger.error(f"Auth service error: {e.code} - {e.reason}")
            self.send_response(e.code)
            self.end_headers()
        except Exception as e:
            logger.error(f"Failed to validate auth: {str(e)}")
            self.send_response(500)
            self.end_headers()

    def handle_echo(self):
        auth_header = self.headers.get("X-ORION-SERVICE-AUTH")
        
        if not auth_header:
            logger.error("Missing X-ORION-SERVICE-AUTH header")
            self.send_response(401)
            self.end_headers()
            return

        content_length = int(self.headers.get('Content-Length', 0))
        request_body = self.rfile.read(content_length)

        auth_body = {
            "target_url": "/testservice/v1/echo",
            "target_identity": TARGET_IDENTITY,
            "target_method": "POST"
        }

        try:
            req = urllib.request.Request(
                AUTH_SERVICE_URL,
                data=json.dumps(auth_body).encode('utf-8'),
                headers={
                    "X-ORION-SERVICE-AUTH": auth_header,
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(request_body)
                else:
                    logger.error(f"Auth service returned status: {response.status}")
                    self.send_response(response.status)
                    self.end_headers()
                    
        except urllib.error.HTTPError as e:
            logger.error(f"Auth service error: {e.code} - {e.reason}")
            self.send_response(e.code)
            self.end_headers()
        except Exception as e:
            logger.error(f"Failed to validate auth: {str(e)}")
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        logger.info(f"{self.address_string()} - {format % args}")


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), TestServiceHandler)
    logger.info(f"Test service listening on port {PORT}")
    server.serve_forever()
