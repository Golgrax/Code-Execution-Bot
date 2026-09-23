import http.server
import socketserver
import threading
import logging

logger = logging.getLogger("KeepAlive")


class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Code Execution Bot is alive and operational!")

    def log_message(self, format, *args):
        # Silence verbose request logging
        pass


def _run_server(port: int = 8080):
    try:
        with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
            logger.info(f"Keep-alive health server running on port {port}")
            httpd.serve_forever()
    except Exception as e:
        logger.warning(f"Could not bind keep-alive server on port {port}: {e}")


def keep_alive(port: int = 8080):
    """Start non-blocking background health-check HTTP server."""
    t = threading.Thread(target=_run_server, args=(port,), daemon=True)
    t.start()
