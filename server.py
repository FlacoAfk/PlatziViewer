"""
Platzi Viewer - Drive API Server
Serves content from Google Drive via the service account API.
Course structure is loaded from courses_cache.json (built by rebuild_cache_drive.py).
"""

import os
import json
import re
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote
import mimetypes
import threading
import time
import sys# Configuración
VIEWER_PATH = r"H:\Mi unidad\platzi-viewer"
PORT = 8080
PROGRESS_FILE = os.path.join(VIEWER_PATH, "progress.json")
CACHE_FILE = os.path.join(VIEWER_PATH, "courses_cache.json")

# Caché global
courses_cache = None
cache_lock = threading.Lock()

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


def init_cache():
    """Inicializa el caché cargando courses_cache.json."""
    global courses_cache
    
    if os.path.exists(CACHE_FILE):
        print("📖 Cargando datos desde courses_cache.json...")
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            with cache_lock:
                courses_cache = data
            stats = data.get('stats', {})
            print(f"\n✅ Datos cargados: {stats.get('totalCategories', 0)} categorías, "
                  f"{stats.get('totalRoutes', 0)} rutas, {stats.get('totalCourses', 0)} cursos, "
                  f"{stats.get('totalClasses', 0)} clases")
        except Exception as e:
            print(f"❌ Error cargando courses_cache.json: {e}")
            with cache_lock:
                courses_cache = {'categories': [], 'stats': {'totalCategories': 0, 'totalRoutes': 0, 'totalCourses': 0, 'totalClasses': 0}}
    else:
        print("❌ courses_cache.json no encontrado.")
        print("   Ejecuta: python rebuild_cache_drive.py")
        with cache_lock:
            courses_cache = {'categories': [], 'stats': {'totalCategories': 0, 'totalRoutes': 0, 'totalCourses': 0, 'totalClasses': 0}}
    
    print(f"🌐 Servidor listo en http://localhost:{PORT}\n")


class PlatziHandler(SimpleHTTPRequestHandler):
    """Manejador HTTP personalizado."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=VIEWER_PATH, **kwargs)
    
    def do_GET(self):
        # API endpoint
        if self.path == '/api/courses':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            with cache_lock:
                if courses_cache:
                    data = courses_cache
                else:
                    data = {'categories': [], 'stats': {'totalCategories': 0, 'totalRoutes': 0, 'totalCourses': 0, 'totalClasses': 0}}
            
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            return
        
        # Refrescar caché
        if self.path == '/api/refresh':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            threading.Thread(target=init_cache, daemon=True).start()
            self.wfile.write(b'{"status": "refreshing"}')
            return
        
        # Cargar progreso desde JSON
        if self.path == '/api/progress':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                if os.path.exists(PROGRESS_FILE):
                    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                        data = f.read()
                else:
                    data = '{}'
            except:
                data = '{}'
            
            self.wfile.write(data.encode('utf-8'))
            return

        # Self-check: validate cache references are Drive IDs (no local refs)
        if self.path == '/api/self-check-drive':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            with cache_lock:
                data = courses_cache or {'categories': [], 'stats': {}}

            report = analyze_drive_references(data)
            self.wfile.write(json.dumps(report, ensure_ascii=False).encode('utf-8'))
            return
        
        # Google Drive file streaming (all files served via Drive API)
        if self.path.startswith('/drive/files/'):
            file_id = unquote(self.path[13:])

            if file_id.startswith('local:'):
                self.send_error(400, 'Local file refs are disabled in Drive mode. Rebuild cache with rebuild_cache_drive.py')
                return
            
            if not file_id or len(file_id) < 10:
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
                    # Parse range request
                    range_match = range_header.replace('bytes=', '').split('-')
                    start = int(range_match[0]) if range_match[0] else 0
                    end = int(range_match[1]) if range_match[1] else file_size - 1
                    end = min(end, file_size - 1)
                    content_length = end - start + 1
                    
                    # Stream from Drive
                    resp = ds.download_file_range(file_id, start, end)
                    
                    self.send_response(206)
                    self.send_header('Content-Type', mime_type)
                    self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                    self.send_header('Content-Length', content_length)
                    self.send_header('Accept-Ranges', 'bytes')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Connection', 'keep-alive')
                    if is_video:
                        self.send_header('Cache-Control', 'public, max-age=3600')
                    self.end_headers()
                    
                    try:
                        for chunk in resp.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                self.wfile.write(chunk)
                    except (ConnectionAbortedError, BrokenPipeError):
                        pass
                else:
                    # Full file download
                    resp = ds.download_file_range(file_id)
                    
                    self.send_response(200)
                    self.send_header('Content-Type', mime_type)
                    if file_size > 0:
                        self.send_header('Content-Length', file_size)
                    self.send_header('Accept-Ranges', 'bytes')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    if is_video:
                        self.send_header('Cache-Control', 'public, max-age=3600')
                    self.end_headers()
                    
                    try:
                        for chunk in resp.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                self.wfile.write(chunk)
                    except (ConnectionAbortedError, BrokenPipeError):
                        pass
            except Exception as e:
                print(f"❌ Drive streaming error for {file_id}: {e}")
                self.send_error(500, str(e))
            return
        
        # Static files (index.html, js/, css, etc.)
        return super().do_GET()
    
    def do_POST(self):
        # Guardar progreso en JSON
        if self.path == '/api/progress':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                # Validar que es JSON válido
                json.loads(post_data.decode('utf-8'))
                
                # Guardar en archivo
                with open(PROGRESS_FILE, 'wb') as f:
                    f.write(post_data)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"status": "saved"}')
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(f'{{"error": "{str(e)}"}}'.encode('utf-8'))
            return


    def do_OPTIONS(self):
        # Manejar CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        # Evitar errores cuando args[0] no es un string
        try:
            msg = str(args[0]) if args else ''
            # No mostrar logs de favicon o api
            if '/api/' in msg or 'favicon' in msg:
                return
            print(f"[{self.log_date_time_string()}] {msg}")
        except:
            pass  # Ignorar errores de logging


def main():
    print("=" * 50)
    print("🎓 Platzi Viewer - Drive API Server")
    print("=" * 50)
    print(f"🌐 URL: http://localhost:{PORT}")
    print("=" * 50)
    print()
    
    # Cargar caché ANTES de iniciar el servidor
    init_cache()
    
    # Iniciar servidor
    server = ThreadingHTTPServer(('localhost', PORT), PlatziHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido")
        server.shutdown()


if __name__ == '__main__':
    main()
