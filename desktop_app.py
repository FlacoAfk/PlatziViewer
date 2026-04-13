import os
import sys
import socket
import threading
import time

try:
    import webview
except Exception:
    webview = None

try:
    from PyQt6.QtCore import QUrl
    from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineDownloadRequest
    from PyQt6.QtGui import QIcon
except Exception:
    QApplication = None
    QMainWindow = None
    QWebEngineView = None
    QWebEngineProfile = None
    QUrl = None
    QIcon = None


def _configure_gpu_acceleration():
    chromium_gpu_flags = [
        "--ignore-gpu-blocklist",
        "--enable-gpu-rasterization",
        "--enable-zero-copy",
        "--enable-accelerated-video-decode",
        "--enable-native-gpu-memory-buffers",
    ]

    def merge_flags(existing_value):
        existing = (existing_value or "").strip().split()
        merged = existing[:]
        for flag in chromium_gpu_flags:
            if flag not in merged:
                merged.append(flag)
        return " ".join(merged).strip()

    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = merge_flags(os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS"))
    os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = merge_flags(
        os.environ.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS")
    )

    os.environ.setdefault("QT_OPENGL", "desktop")
    os.environ.setdefault("QT_ANGLE_PLATFORM", "d3d11")


def _resource_dir():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _executable_dir():
    if getattr(sys, "frozen", False):
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


def _get_free_port(host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def _run_pyqt_window(target_url, resources, exe_dir, server):
    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("Platzi Viewer")
    window.resize(1280, 820)
    window.setMinimumSize(980, 640)

    icon_path = os.path.join(resources, "favicon.ico")
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))

    storage_path = os.path.join(exe_dir, "PlatziData")
    os.makedirs(storage_path, exist_ok=True)

    profile = QWebEngineProfile.defaultProfile()
    profile.setPersistentStoragePath(storage_path)
    profile.setCachePath(storage_path)

    def handle_download(download: QWebEngineDownloadRequest):
        options = QFileDialog.Option.DontUseNativeDialog if os.name != 'nt' else QFileDialog.Option(0)
        suggested = download.suggestedFileName()
        downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        init_path = os.path.join(downloads_dir, suggested) if suggested else downloads_dir
        save_path, _ = QFileDialog.getSaveFileName(
            window, "Guardar archivo como...", init_path, "All Files (*)", options=options
        )
        if save_path:
            download.setDownloadDirectory(os.path.dirname(save_path))
            download.setDownloadFileName(os.path.basename(save_path))
            download.accept()
        else:
            download.cancel()

    profile.downloadRequested.connect(handle_download)

    browser = QWebEngineView(profile)
    browser.settings().setAttribute(browser.settings().WebAttribute.FullScreenSupportEnabled, True)

    def on_fullscreen_requested(request):
        request.accept()
        if request.toggleOn():
            window.showFullScreen()
        else:
            window.showNormal()

    browser.page().fullScreenRequested.connect(on_fullscreen_requested)
    browser.setUrl(QUrl(target_url))

    window.setCentralWidget(browser)
    window.show()

    exit_code = app.exec()

    try:
        server.shutdown()
        server.server_close()
    except Exception:
        pass

    sys.exit(exit_code)


def main():
    _configure_gpu_acceleration()

    host = os.environ.get("HOST", "127.0.0.1").strip() or "127.0.0.1"
    if host == "localhost":
        host = "127.0.0.1"
    os.environ["HOST"] = host
    configured_port = os.environ.get("PORT", "").strip()
    if configured_port.isdigit() and int(configured_port) > 0:
        port = int(configured_port)
    else:
        port = _get_free_port(host)
        os.environ["PORT"] = str(port)

    resources = _resource_dir()
    exe_dir = _executable_dir()
    data_dir = os.path.join(exe_dir, "PlatziData")
    os.makedirs(data_dir, exist_ok=True)

    os.environ.setdefault("PLATZI_VIEWER_PATH", resources)
    os.environ.setdefault("PLATZI_DATA_PATH", data_dir)
    # Desktop usa por defecto el cache del bundle para evitar stale cache externo.
    os.environ.setdefault("PLATZI_PREFER_DATA_CACHE", "0")

    service_account_in_exe_dir = os.path.join(exe_dir, "service_account.json")
    service_account_in_bundle = os.path.join(resources, "service_account.json")
    if os.path.exists(service_account_in_exe_dir):
        os.environ.setdefault("GOOGLE_SERVICE_ACCOUNT_FILE", service_account_in_exe_dir)
    elif os.path.exists(service_account_in_bundle):
        os.environ.setdefault("GOOGLE_SERVICE_ACCOUNT_FILE", service_account_in_bundle)

    from server import create_server, run_server

    server = create_server(host, port)
    server_thread = threading.Thread(target=run_server, args=(server,), daemon=True)
    server_thread.start()

    if not _wait_for_server(host, port, timeout=15):
        raise RuntimeError(f"No se pudo iniciar el servidor local en {host}:{port}")

    target_url = f"http://{host}:{port}"

    if webview is not None:
        class DesktopAPI:
            def __init__(self):
                self.window = None

            def toggle_fullscreen(self):
                if self.window:
                    self.window.toggle_fullscreen()

            def prompt_save_as(self, url, suggested_filename):
                if not self.window:
                    return
                # Only pywebview has this, we spawn a thread to download it so we don't block JS
                try:
                    import urllib.request
                    downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
                    result = self.window.create_file_dialog(
                        webview.SAVE_DIALOG, 
                        directory=downloads_dir, 
                        save_filename=suggested_filename
                    )
                    if result and len(result) > 0:
                        save_path = result[0]
                        def _download():
                            try:
                                urllib.request.urlretrieve(url, save_path)
                            except Exception as e:
                                print(f"Error downloading: {e}")
                        threading.Thread(target=_download, daemon=True).start()
                except Exception as e:
                    print(f"Error in prompt_save_as: {e}")

        api_instance = DesktopAPI()

        window = webview.create_window(
            "Platzi Viewer",
            target_url,
            width=1280,
            height=820,
            min_size=(980, 640),
            text_select=True,
            js_api=api_instance
        )
        api_instance.window = window

        def _on_closed():
            try:
                server.shutdown()
                server.server_close()
            except Exception:
                return

        window.events.closed += _on_closed
        webview.start(debug=False)
        return

    if QApplication is None or QWebEngineView is None:
        raise RuntimeError(
            "No se encontró backend UI. Instala pywebview o PyQt6 + PyQt6-WebEngine para desktop_app.py."
        )

    _run_pyqt_window(target_url, resources, exe_dir, server)


if __name__ == "__main__":
    main()
