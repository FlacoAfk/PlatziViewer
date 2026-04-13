from __future__ import annotations

import socketserver
import threading

import desktop_app


class _PingHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.recv(1)


def test_get_free_port_returns_positive_port():
    port = desktop_app._get_free_port()
    assert isinstance(port, int)
    assert port > 0


def test_wait_for_server_detects_local_listener():
    with socketserver.TCPServer(("127.0.0.1", 0), _PingHandler) as server:
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            assert desktop_app._wait_for_server("127.0.0.1", port, timeout=2) is True
        finally:
            server.shutdown()
            thread.join(timeout=2)
