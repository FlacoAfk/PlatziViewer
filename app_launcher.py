import os
import sys
import threading
import webbrowser


def _base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _open_browser(port):
    try:
        webbrowser.open(f'http://localhost:{port}')
    except Exception:
        return


def main():
    base_dir = _base_dir()

    os.environ.setdefault('PLATZI_VIEWER_PATH', base_dir)
    os.environ.setdefault('PLATZI_DATA_PATH', base_dir)

    service_account_path = os.path.join(base_dir, 'service_account.json')
    if os.path.exists(service_account_path):
        os.environ.setdefault('GOOGLE_SERVICE_ACCOUNT_FILE', service_account_path)

    port = int(os.environ.get('PORT', '8080'))

    threading.Timer(1.2, _open_browser, args=(port,)).start()

    from server import main as server_main

    server_main()


if __name__ == '__main__':
    main()
