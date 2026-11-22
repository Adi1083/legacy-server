#!/usr/bin/env python3
"""
India V1 1.39 High-Performance Modular Emulation Server
Crafted for Clack by cook45
"""

import sys
import os
import json
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse

# Ensure local packages are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.logger import log_request, request_history, history_lock
from handlers.static_router import handle_static_get, VERSION, SUB_VERSION
from handlers.game_router import handle_game_post
from handlers.dashboard_api import (
    handle_dashboard_get,
    handle_dashboard_post,
    handle_dashboard_delete,
    render_dashboard_html,
)
from handlers.admin_luck_royale_api import handle_admin_luck_royale_request
from tcp_server import TCP_PORT, start_tcp_server, stop_tcp_server
from combat.udp_server import start_combat_server, get_combat_server

# Port configuration (respects Render/Cloud dynamic PORT env var)
PORT = int(os.environ.get("PORT", 8080))

class ThreadedDualStackServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 256

    def __init__(self, server_address, RequestHandlerClass):
        # Try dual-stack IPv6 first, fallback to standard IPv4 if container doesn't support IPv6
        try:
            self.address_family = socket.AF_INET6
            super().__init__(server_address, RequestHandlerClass)
        except Exception:
            self.address_family = socket.AF_INET
            ipv4_address = ("0.0.0.0", server_address[1])
            super().__init__(ipv4_address, RequestHandlerClass)

    def server_bind(self):
        if self.address_family == socket.AF_INET6:
            try:
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            except Exception as e:
                print(f"[!] Warning: IPV6_V6ONLY=0 failed: {e}", flush=True)
        super().server_bind()

class BarbosaHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    timeout = 10

    def send_headers_common(self, length, content_type):
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.end_headers()
        self.close_connection = True

    def send_bytes(self, data: bytes, status=200, content_type="application/octet-stream"):
        self.send_response(status)
        self.send_headers_common(len(data), content_type)
        try:
            self.wfile.write(data)
            self.wfile.flush()
        except Exception:
            pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_headers_common(len(body), "application/json; charset=utf-8")
        try:
            self.wfile.write(body)
            self.wfile.flush()
        except Exception:
            pass

    def send_text(self, text, status=200, content_type="text/plain; charset=utf-8"):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_headers_common(len(body), content_type)
        try:
            self.wfile.write(body)
            self.wfile.flush()
        except Exception:
            pass

    def send_file(self, file_path, content_type="application/octet-stream"):
        if not os.path.exists(file_path):
            self.send_text("Not Found", 404)
            return
        with open(file_path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_headers_common(len(data), content_type)
        try:
            self.wfile.write(data)
            self.wfile.flush()
        except Exception:
            pass

    def send_proto(self, name, data):
        print(f"  [+] Responding with {name} ({len(data)} bytes)", flush=True)
        self.send_bytes(data, content_type="application/octet-stream")

    def _clean_path(self, raw_path):
        p = raw_path
        for prefix in ["/_pad2/", "/_pad/"]:
            if p.startswith(prefix):
                p = "/" + p[len(prefix):]
                break
        return p

    def _get_client_ip(self):
        try:
            ip = self.client_address[0]
            if ip.startswith("::ffff:"):
                return ip[7:]
            return ip
        except Exception:
            return "127.0.0.1"

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            path = self._clean_path(parsed.path)
            client_ip = self._get_client_ip()

            if path != "/api/requests" and not path.startswith("/api/dashboard") and not path.startswith("/api/admin"):
                log_request("GET", self.path, client_ip)

            # Admin Luck Royale REST API
            if handle_admin_luck_royale_request(self, "GET", path, parsed.query, b""):
                return

            # Dashboard Web UI & Real-Time Control / Request API
            if handle_dashboard_get(
                self,
                path,
                parsed.query,
                version=VERSION,
                sub_version=SUB_VERSION,
                port=PORT,
            ):
                return

            if handle_static_get(self, path, client_ip):
                return

            if handle_game_post(self, path, client_ip, b""):
                return

            if "api" in path:
                self.send_json({"status": 0, "code": 0, "msg": "ok"})
            else:
                self.send_bytes(b"", status=200)
        except Exception as e:
            print(f"[-] GET Exception on {self.path}: {e}", flush=True)

    def do_POST(self):
        try:
            parsed = urlparse(self.path)
            path = self._clean_path(parsed.path)
            client_ip = self._get_client_ip()
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len) if content_len > 0 else b""

            if not path.startswith("/api/dashboard") and not path.startswith("/api/admin"):
                log_request("POST", self.path, client_ip, raw_body)

            # Admin Luck Royale REST API
            if handle_admin_luck_royale_request(self, "POST", path, parsed.query, raw_body):
                return

            if handle_dashboard_post(self, path, raw_body):
                return

            handle_game_post(self, path, client_ip, raw_body)
        except Exception as e:
            print(f"[-] POST Exception on {self.path}: {e}", flush=True)

    def do_PUT(self):
        try:
            parsed = urlparse(self.path)
            path = self._clean_path(parsed.path)
            client_ip = self._get_client_ip()
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len) if content_len > 0 else b""

            if not path.startswith("/api/dashboard") and not path.startswith("/api/admin"):
                log_request("PUT", self.path, client_ip, raw_body)

            # Admin Luck Royale REST API
            if handle_admin_luck_royale_request(self, "PUT", path, parsed.query, raw_body):
                return

            self.send_json({"ok": False, "error": f"Method PUT not supported on {path}"}, status=405)
        except Exception as e:
            print(f"[-] PUT Exception on {self.path}: {e}", flush=True)

    def do_DELETE(self):
        try:
            parsed = urlparse(self.path)
            path = self._clean_path(parsed.path)
            client_ip = self._get_client_ip()
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len) if content_len > 0 else b""

            if not path.startswith("/api/dashboard") and not path.startswith("/api/admin"):
                log_request("DELETE", self.path, client_ip, raw_body)

            # Admin Luck Royale REST API
            if handle_admin_luck_royale_request(self, "DELETE", path, parsed.query, raw_body):
                return

            # Admin & Dashboard REST API
            if handle_dashboard_delete(self, path, raw_body):
                return

            self.send_json({"ok": False, "error": f"Method DELETE not supported on {path}"}, status=405)
        except Exception as e:
            print(f"[-] DELETE Exception on {self.path}: {e}", flush=True)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_headers_common(0, "text/plain")

    def render_dashboard(self):
        self.send_text(
            render_dashboard_html(version=VERSION, sub_version=SUB_VERSION, port=PORT),
            200,
            "text/html; charset=utf-8",
        )

    def log_message(self, format, *args):
        pass

def run():
    print("=" * 65, flush=True)
    print(f"[*] India V1 Project 1.39 Modular High-Performance Server", flush=True)
    print(f"[*] HTTP Port: {PORT} | TCP Lobby Port: {TCP_PORT} (IPv4 + IPv6 dual-stack)", flush=True)
    print(f"[*] Dashboard: http://localhost:{PORT}/dashboard", flush=True)
    print("=" * 65, flush=True)

    start_tcp_server(port=TCP_PORT, background=True)
    start_combat_server()
    httpd = ThreadedDualStackServer(("::", PORT), BarbosaHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.", flush=True)
    finally:
        stop_tcp_server()
        httpd.server_close()

if __name__ == "__main__":
    run()
