import os
import sys
import socket
import threading
import time

import webview

from server import create_server, run_server


def _resource_dir():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _executable_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _wait_for_server(host, port, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def main():
    host = 'localhost'
    port = int(os.environ.get('PORT', '8080'))

    resources = _resource_dir()
    exe_dir = _executable_dir()

    os.environ.setdefault('PLATZI_VIEWER_PATH', resources)
    os.environ.setdefault('PLATZI_DATA_PATH', exe_dir)

    service_account_in_exe_dir = os.path.join(exe_dir, 'service_account.json')
    service_account_in_bundle = os.path.join(resources, 'service_account.json')
    if os.path.exists(service_account_in_exe_dir):
        os.environ.setdefault('GOOGLE_SERVICE_ACCOUNT_FILE', service_account_in_exe_dir)
    elif os.path.exists(service_account_in_bundle):
        os.environ.setdefault('GOOGLE_SERVICE_ACCOUNT_FILE', service_account_in_bundle)

    server = create_server(host, port)
    server_thread = threading.Thread(target=run_server, args=(server,), daemon=True)
    server_thread.start()

    if not _wait_for_server(host, port, timeout=15):
        raise RuntimeError(f'No se pudo iniciar el servidor local en {host}:{port}')

    window = webview.create_window(
        'Platzi Viewer',
        f'http://{host}:{port}',
        width=1280,
        height=820,
        min_size=(980, 640),
        text_select=True,
    )

    def _on_closed():
        try:
            server.shutdown()
            server.server_close()
        except Exception:
            return

    window.events.closed += _on_closed
    webview.start(debug=False)


if __name__ == '__main__':
    main()
