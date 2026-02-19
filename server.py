"""
Platzi Viewer - Drive API Server
Serves content from Google Drive via the service account API.
Course structure is loaded from courses_cache.json (built by rebuild_cache_drive.py).
"""

import os
import json
import re
import errno
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote, urlparse
import mimetypes
import threading
import time
import subprocess
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIEWER_PATH = os.environ.get('PLATZI_VIEWER_PATH', BASE_DIR)
DATA_PATH = os.environ.get('PLATZI_DATA_PATH', VIEWER_PATH)
PORT = int(os.environ.get('PORT', '8080'))
PROGRESS_FILE = os.path.join(DATA_PATH, "progress.json")
VIEWER_CACHE_FILE = os.path.join(VIEWER_PATH, "courses_cache.json")
DATA_CACHE_FILE = os.path.join(DATA_PATH, "courses_cache.json")
MAX_PROGRESS_BYTES = int(os.environ.get('MAX_PROGRESS_BYTES', '2097152'))  # 2MB
LOOPBACK_HOSTS = {'localhost', '127.0.0.1', '::1'}

# Caché global
courses_cache = None
cache_lock = threading.Lock()
cache_reload_lock = threading.Lock()
cache_mtime = None
cache_file_path = None

# Google Drive service (lazy loaded)
_drive_service = None
DRIVE_ID_RE = re.compile(r'^[A-Za-z0-9_-]{10,}$')


def analyze_drive_references(data):
    """Validate that file references in cache are Drive IDs (not local refs)."""
    summary = {
        'generatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'totalRefs': 0,
        'validDriveRefs': 0,
        'localRefs': 0,
        'invalidRefs': 0,
        'emptyRefs': 0,
        'issues': []
    }

    def add_issue(location, value, reason):
        if len(summary['issues']) < 30:
            summary['issues'].append({
                'location': location,
                'value': value,
                'reason': reason
            })

    def validate_ref(ref, location):
        summary['totalRefs'] += 1

        if ref is None:
            summary['emptyRefs'] += 1
            return

        if not isinstance(ref, str):
            summary['invalidRefs'] += 1
            add_issue(location, str(ref), 'non_string_ref')
            return

        value = ref.strip()
        if not value:
            summary['emptyRefs'] += 1
            return

        if value.startswith('local:'):
            summary['localRefs'] += 1
            add_issue(location, value, 'local_ref_detected')
            return

        if value.startswith('http://') or value.startswith('https://'):
            summary['invalidRefs'] += 1
            add_issue(location, value, 'url_ref_detected')
            return

        if not DRIVE_ID_RE.match(value):
            summary['invalidRefs'] += 1
            add_issue(location, value, 'invalid_drive_id_format')
            return

        summary['validDriveRefs'] += 1

    categories = (data or {}).get('categories', [])
    for cat_idx, category in enumerate(categories):
        routes = category.get('routes', [])
        for route_idx, route in enumerate(routes):
            courses = [route] if route.get('isCourse') else route.get('courses', [])
            for course_idx, course in enumerate(courses):
                modules = course.get('modules', [])
                for mod_idx, module in enumerate(modules):
                    classes = module.get('classes', [])
                    for cls_idx, cls in enumerate(classes):
                        files = cls.get('files', {}) or {}
                        for field_name, ref in files.items():
                            validate_ref(ref, f'cat[{cat_idx}].route[{route_idx}].course[{course_idx}].mod[{mod_idx}].class[{cls_idx}].files.{field_name}')

                        resources = cls.get('resources', []) or []
                        for res_idx, resource in enumerate(resources):
                            validate_ref(resource.get('file'), f'cat[{cat_idx}].route[{route_idx}].course[{course_idx}].mod[{mod_idx}].class[{cls_idx}].resources[{res_idx}].file')

    summary['ok'] = summary['localRefs'] == 0 and summary['invalidRefs'] == 0
    summary['message'] = 'drive_only_ok' if summary['ok'] else 'drive_only_issues_found'
    return summary


def get_drive_service():
    global _drive_service
    if _drive_service is None:
        try:
            from drive_service import drive_service
            _drive_service = drive_service
        except Exception as e:
            print(f"⚠️ Drive service not available: {e}")
    return _drive_service


def resolve_cache_file_path():
    if os.path.exists(DATA_CACHE_FILE):
        return DATA_CACHE_FILE
    return VIEWER_CACHE_FILE


def init_cache():
    """Inicializa el caché cargando courses_cache.json."""
    global courses_cache, cache_mtime, cache_file_path

    selected_cache_file = resolve_cache_file_path()

    if os.path.exists(selected_cache_file):
        print(f"📖 Cargando datos desde {os.path.basename(selected_cache_file)}...")
        try:
            current_mtime = os.path.getmtime(selected_cache_file)
            with open(selected_cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, dict) or 'categories' not in data:
                raise ValueError('courses_cache.json inválido: falta clave categories')

            with cache_lock:
                courses_cache = data
                cache_mtime = current_mtime
                cache_file_path = selected_cache_file

            stats = data.get('stats', {})
            print(f"\n✅ Datos cargados: {stats.get('totalCategories', 0)} categorías, "
                  f"{stats.get('totalRoutes', 0)} rutas, {stats.get('totalCourses', 0)} cursos, "
                  f"{stats.get('totalClasses', 0)} clases")
        except Exception as e:
            print(f"❌ Error cargando courses_cache.json: {e}")
            with cache_lock:
                has_previous_cache = courses_cache is not None

            if has_previous_cache:
                print("⚠️ Conservando caché anterior en memoria por error temporal de lectura")
            else:
                with cache_lock:
                    courses_cache = {'categories': [], 'stats': {'totalCategories': 0, 'totalRoutes': 0, 'totalCourses': 0, 'totalClasses': 0}}
                    cache_mtime = None
                    cache_file_path = selected_cache_file
    else:
        print("❌ courses_cache.json no encontrado.")
        print("   Ejecuta: python rebuild_cache_drive.py")
        with cache_lock:
            courses_cache = {'categories': [], 'stats': {'totalCategories': 0, 'totalRoutes': 0, 'totalCourses': 0, 'totalClasses': 0}}
            cache_mtime = None
            cache_file_path = selected_cache_file
    
    print(f"🌐 Servidor listo en http://localhost:{PORT}\n")


def refresh_cache_if_changed():
    """Recarga el caché si courses_cache.json cambió en disco."""
    current_cache_file = resolve_cache_file_path()

    if not os.path.exists(current_cache_file):
        return

    try:
        current_mtime = os.path.getmtime(current_cache_file)
    except OSError:
        return

    with cache_lock:
        previous_mtime = cache_mtime
        previous_cache_file = cache_file_path

    if previous_cache_file != current_cache_file:
        with cache_reload_lock:
            with cache_lock:
                if cache_file_path != current_cache_file:
                    print("🔄 Cambio de origen de caché detectado, recargando...")
                    init_cache()
        return

    if previous_mtime is not None and current_mtime <= previous_mtime:
        return

    with cache_reload_lock:
        with cache_lock:
            latest_mtime = cache_mtime

        if latest_mtime is not None and current_mtime <= latest_mtime:
            return

        print("🔄 Detectado cambio en courses_cache.json, recargando caché...")
        init_cache()


class PlatziHandler(SimpleHTTPRequestHandler):
    """Manejador HTTP personalizado."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=VIEWER_PATH, **kwargs)

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cross-Origin-Resource-Policy', 'same-site')
        super().end_headers()

    def _is_allowed_origin(self, origin):
        if not origin:
            return False
        try:
            parsed = urlparse(origin)
            return parsed.scheme in {'http', 'https'} and parsed.hostname in LOOPBACK_HOSTS
        except Exception:
            return False

    def _set_cors_headers(self):
        origin = self.headers.get('Origin')
        if self._is_allowed_origin(origin):
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')

    def _send_json(self, status_code, payload):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))

    def _is_local_client(self):
        host = self.client_address[0]
        return host in LOOPBACK_HOSTS

    def _is_client_disconnect_error(self, error):
        if isinstance(error, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)):
            return True

        winerror = getattr(error, 'winerror', None)
        if winerror in {10053, 10054}:
            return True

        err_no = getattr(error, 'errno', None)
        if err_no in {errno.EPIPE, errno.ECONNRESET, errno.ECONNABORTED}:
            return True

        return False

    def _safe_send_error(self, code, message):
        try:
            self.send_error(code, message)
        except OSError as error:
            if not self._is_client_disconnect_error(error):
                raise
    
    def do_GET(self):
        # API endpoint
        if self.path == '/api/courses':
            refresh_cache_if_changed()

            with cache_lock:
                if courses_cache:
                    data = courses_cache
                else:
                    data = {'categories': [], 'stats': {'totalCategories': 0, 'totalRoutes': 0, 'totalCourses': 0, 'totalClasses': 0}}

            self._send_json(200, data)
            return
        
        # Refrescar caché
        if self.path == '/api/refresh':
            if not self._is_local_client():
                self._send_json(403, {'error': 'forbidden'})
                return

            threading.Thread(target=init_cache, daemon=True).start()
            self._send_json(200, {'status': 'refreshing'})
            return
        
        # Cargar progreso desde JSON
        if self.path == '/api/progress':
            try:
                if os.path.exists(PROGRESS_FILE):
                    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                else:
                    data = {}
            except:
                data = {}

            self._send_json(200, data)
            return

        # Self-check: validate cache references are Drive IDs (no local refs)
        if self.path == '/api/self-check-drive':
            with cache_lock:
                data = courses_cache or {'categories': [], 'stats': {}}

            report = analyze_drive_references(data)
            self._send_json(200, report)
            return
        
        # Google Drive file streaming (all files served via Drive API)
        if self.path.startswith('/drive/files/'):
            file_id = unquote(self.path[13:])

            if file_id.startswith('local:'):
                self.send_error(400, 'Local file refs are disabled in Drive mode. Rebuild cache with rebuild_cache_drive.py')
                return
            
            if not file_id or not DRIVE_ID_RE.match(file_id):
                self.send_error(400, 'Invalid file ID')
                return
            
            ds = get_drive_service()
            if not ds:
                self.send_error(503, 'Drive service not available')
                return
            
            try:
                # Get file metadata for content type and size
                metadata = ds.get_file_metadata(file_id)
                mime_type = metadata.get('mimeType', 'application/octet-stream')
                file_size = int(metadata.get('size', 0))
                is_video = mime_type and mime_type.startswith('video')
                
                # Fix mime types that Drive returns as generic
                file_name = metadata.get('name', '')
                if mime_type == 'application/octet-stream':
                    guessed, _ = mimetypes.guess_type(file_name)
                    if guessed:
                        mime_type = guessed
                
                range_header = self.headers.get('Range')
                
                if range_header and file_size > 0:
                    range_match = re.match(r'^bytes=(\d*)-(\d*)$', range_header)
                    if not range_match:
                        self.send_error(416, 'Invalid range header')
                        return

                    start_str, end_str = range_match.groups()
                    start = int(start_str) if start_str else 0
                    end = int(end_str) if end_str else file_size - 1

                    if start < 0 or end < 0 or start > end or start >= file_size:
                        self.send_error(416, 'Requested Range Not Satisfiable')
                        return

                    end = min(end, file_size - 1)
                    content_length = end - start + 1
                    
                    # Stream from Drive
                    resp = ds.download_file_range(file_id, start, end)
                    
                    self.send_response(206)
                    self.send_header('Content-Type', mime_type)
                    self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                    self.send_header('Content-Length', content_length)
                    self.send_header('Accept-Ranges', 'bytes')
                    self._set_cors_headers()
                    self.send_header('Connection', 'keep-alive')
                    if is_video:
                        self.send_header('Cache-Control', 'public, max-age=3600')
                    self.end_headers()
                    
                    try:
                        for chunk in resp.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                self.wfile.write(chunk)
                    except OSError as error:
                        if not self._is_client_disconnect_error(error):
                            raise
                else:
                    # Full file download
                    resp = ds.download_file_range(file_id)
                    
                    self.send_response(200)
                    self.send_header('Content-Type', mime_type)
                    if file_size > 0:
                        self.send_header('Content-Length', file_size)
                    self.send_header('Accept-Ranges', 'bytes')
                    self._set_cors_headers()
                    if is_video:
                        self.send_header('Cache-Control', 'public, max-age=3600')
                    self.end_headers()
                    
                    try:
                        for chunk in resp.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                self.wfile.write(chunk)
                    except OSError as error:
                        if not self._is_client_disconnect_error(error):
                            raise
            except Exception as e:
                if self._is_client_disconnect_error(e):
                    return

                print(f"❌ Drive streaming error for {file_id}: {e}")
                self._safe_send_error(502, 'Failed to stream file from Drive')
            return
        
        # Static files (index.html, js/, css, etc.)
        return super().do_GET()
    
    def do_POST(self):
        # Guardar progreso en JSON
        if self.path == '/api/progress':
            content_length = int(self.headers.get('Content-Length', 0))

            if content_length <= 0 or content_length > MAX_PROGRESS_BYTES:
                self._send_json(413, {'error': 'payload_too_large'})
                return

            post_data = self.rfile.read(content_length)
            
            try:
                # Validar que es JSON válido
                parsed = json.loads(post_data.decode('utf-8'))
                if not isinstance(parsed, dict):
                    raise ValueError('progress payload must be a JSON object')
                
                # Guardar en archivo
                progress_dir = os.path.dirname(PROGRESS_FILE)
                if progress_dir:
                    os.makedirs(progress_dir, exist_ok=True)
                with open(PROGRESS_FILE, 'wb') as f:
                    f.write(post_data)

                self._send_json(200, {'status': 'saved'})
            except Exception as e:
                self._send_json(400, {'error': str(e)})
            return

        # Abrir en reproductor externo (VLC)
        if self.path == '/api/open-external':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                payload = json.loads(post_data.decode('utf-8'))
                video_url = payload.get('url')
                
                if not video_url:
                    self._send_json(400, {'error': 'missing_url'})
                    return

                # Si es una ruta relativa, agregar localhost
                if video_url.startswith('/'):
                    video_url = f"http://localhost:{PORT}{video_url}"
                
                # Buscar VLC en rutas comunes de Windows
                vlc_path = None
                possible_paths = [
                    r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                    r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        vlc_path = path
                        break
                
                if vlc_path:
                    # subprocess.Popen detaches the process so server keeps running
                    subprocess.Popen([vlc_path, video_url])
                    self._send_json(200, {'status': 'opened_vlc', 'player': vlc_path})
                else:
                    # Intentar comando global 'vlc'
                    try:
                        subprocess.Popen(['vlc', video_url])
                        self._send_json(200, {'status': 'opened_vlc_cmd'})
                    except FileNotFoundError:
                        self._send_json(404, {'error': 'vlc_not_found'})

            except Exception as e:
                self._send_json(500, {'error': str(e)})
            return


    def do_OPTIONS(self):
        # Manejar CORS preflight
        origin = self.headers.get('Origin')
        if not self._is_allowed_origin(origin):
            self.send_response(403)
            self.end_headers()
            return

        self.send_response(200)
        self._set_cors_headers()
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '600')
        self.end_headers()
    
    def log_message(self, format, *args):
        # Evitar errores cuando args[0] no es un string
        try:
            msg = str(args[0]) if args else ''
            # No mostrar logs de favicon o api
            if '/api/' in msg or 'favicon' in msg:
                return
            print(f"[{self.log_date_time_string()}] {msg}")
        except Exception:
            return

    def handle(self):
        try:
            super().handle()
        except OSError as error:
            if not self._is_client_disconnect_error(error):
                raise


def main():
    print("=" * 50)
    print("🎓 Platzi Viewer - Drive API Server")
    print("=" * 50)
    print(f"🌐 URL: http://localhost:{PORT}")
    print("=" * 50)
    print()
    
    # Cargar caché ANTES de iniciar el servidor
    server = create_server('localhost', PORT)
    
    try:
        run_server(server)
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido")
        server.shutdown()


def create_server(host='localhost', port=PORT):
    init_cache()
    return ThreadingHTTPServer((host, port), PlatziHandler)


def run_server(server):
    server.serve_forever()


if __name__ == '__main__':
    main()
