"""
Platzi Viewer - Servidor Local (Versión Optimizada)
Escanea automáticamente las carpetas de cursos y sirve el contenido.
Con caché para respuesta rápida.
"""

import os
import json
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote
import mimetypes
import threading
import time
import sys
import subprocess


# Configuración
COURSES_PATH = r"C:\Users\elkaw\Desktop\platzi-downloader"
VIEWER_PATH = r"C:\Users\elkaw\Desktop\platzi-viewer"
PORT = 8080
PROGRESS_FILE = os.path.join(VIEWER_PATH, "progress.json")
CACHE_FILE = os.path.join(VIEWER_PATH, "courses_cache.json")

# Categorías para estructura plana
CATEGORIES = {
    'Courses': {
        'id': 'downloads',
        'name': 'Descargas',
        'icon': '📂',
        'description': 'Cursos descargados localmente'
    }
}

# Caché global
courses_cache = None
cache_lock = threading.Lock()

# Google Drive service (lazy loaded)
_drive_service = None
def get_drive_service():
    global _drive_service
    if _drive_service is None:
        try:
            from drive_service import drive_service
            _drive_service = drive_service
        except Exception as e:
            print(f"⚠️ Drive service not available: {e}")
    return _drive_service

def get_sort_key(name):
    """Extrae el número al inicio del nombre para ordenamiento numérico."""
    # Buscar número al inicio: "1. Curso..." -> 1, "10. Curso..." -> 10
    parts = name.split('. ', 1)
    if parts[0].isdigit():
        return (0, int(parts[0]), name)  # (prioridad, número, nombre)
    return (1, 0, name)  # Los que no tienen número van al final

def sorted_items(items):
    """Ordena una lista de nombres numéricamente."""
    return sorted(items, key=get_sort_key)


def scan_classes(module_path):
    """Escanea las clases dentro de un módulo."""
    classes = []
    if not os.path.exists(module_path):
        return classes
    
    try:
        files = os.listdir(module_path)
    except:
        return classes
    
    class_files = {}
    for f in files:
        if f.startswith('desktop') or f.startswith('.'):
            continue
        
        parts = f.split('. ', 1)
        if len(parts) >= 2 and parts[0].isdigit():
            class_num = int(parts[0])
            if class_num not in class_files:
                class_files[class_num] = {'files': []}
            class_files[class_num]['files'].append(f)
    
    for class_num in sorted(class_files.keys()):
        files_list = class_files[class_num]['files']
        
        video_file = None
        summary_file = None
        vtt_file = None
        reading_file = None
        html_file = None
        
        for f in files_list:
            if f.endswith('.mp4'):
                video_file = f
            elif f.endswith('_summary.html'):
                summary_file = f
            elif f.endswith('.vtt'):
                vtt_file = f
            elif 'Lecturas recomendadas' in f and f.endswith('.txt'):
                reading_file = f
            elif f.endswith('.html') and not f.endswith('_summary.html'):
                html_file = f
        
        if video_file:
            name = video_file.rsplit('.', 1)[0]
            name = name.split('. ', 1)[-1] if '. ' in name else name
        elif html_file:
            name = html_file.rsplit('.', 1)[0]
            name = name.split('. ', 1)[-1] if '. ' in name else name
        else:
            continue
            
        # Generar paths relativos con prefijo local:
        def get_local_path(filename):
            if not filename: return None
            # Ruta absoluta del archivo
            abs_path = os.path.join(module_path, filename)
            # Ruta relativa desde COURSES_PATH
            rel_path = os.path.relpath(abs_path, start=COURSES_PATH)
            # Normalizar separadores a /
            rel_path = rel_path.replace(os.sep, '/')
            return f"local:{rel_path}"

        classes.append({
            'num': class_num,
            'name': name[:60],
            'hasVideo': video_file is not None,
            'hasSummary': summary_file is not None,
            'hasSubtitles': vtt_file is not None,
            'hasReading': reading_file is not None,
            'hasHtml': html_file is not None and video_file is None,
            'files': {
                'video': get_local_path(video_file),
                'summary': get_local_path(summary_file),
                'subtitles': get_local_path(vtt_file),
                'reading': get_local_path(reading_file),
                'html': get_local_path(html_file)
            }
        })
    
    return classes


def scan_modules(course_path):
    """Escanea los módulos dentro de un curso."""
    modules = []
    has_presentation = False
    
    if not os.path.exists(course_path):
        return modules, has_presentation
    
    try:
        items = sorted_items(os.listdir(course_path))
    except:
        return modules, has_presentation
    
    for item in items:
        item_path = os.path.join(course_path, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            classes = scan_classes(item_path)
            name = item.split('. ', 1)[-1] if '. ' in item else item
            
            modules.append({
                'name': name,
                'folderName': item,
                'classes': classes,
                'classCount': len(classes)
            })
        elif item == 'presentation.html':
            has_presentation = True
    
    return modules, has_presentation


def scan_courses(route_path):
    """Escanea los cursos dentro de una ruta."""
    courses = []
    if not os.path.exists(route_path):
        return courses
    
    try:
        items = sorted_items(os.listdir(route_path))
    except:
        return courses
    
    for item in items:
        item_path = os.path.join(route_path, item)
        # Detect courses: "Curso", "Audiocurso", "Minicurso", "Taller", 
        # "Guía", "Glosario", "Audioglosario", "Bites", etc.
        item_lower = item.lower()
        is_curso = any(keyword in item_lower for keyword in [
            'curso', 'taller', 'guía', 'guia', 'glosario', 
            'bites', 'mindset', 'founders', 'hack ', 
            'optimización de linkedin', 'optimizacion de linkedin',
            'creación de filtro', 'creacion de filtro',
            'cuadrante de dinero'
        ])
        
        if os.path.isdir(item_path) and is_curso:
            modules, has_presentation = scan_modules(item_path)
            name = item.split('. ', 1)[-1] if '. ' in item else item
            
            courses.append({
                'name': name,
                'folderName': item,
                'modules': modules,
                'moduleCount': len(modules),
                'hasPresentation': has_presentation
            })
    
    return courses


def scan_routes(category_path):
    """Escanea las rutas dentro de una categoría."""
    routes = []
    if not os.path.exists(category_path):
        return routes
    
    try:
        items = sorted_items(os.listdir(category_path))
    except:
        return routes
    
    route_index = 0
    for item in items:
        item_path = os.path.join(category_path, item)
        if not os.path.isdir(item_path) or item.startswith('.'):
            continue
            
        is_course = 'curso' in item.lower()
        # Usar índice único para evitar colisiones de IDs
        unique_id = f"route-{route_index}"
        route_index += 1
        
        if is_course:
            modules, has_presentation = scan_modules(item_path)
            routes.append({
                'id': unique_id,
                'name': item,
                'folderName': item,
                'isCourse': True,
                'modules': modules,
                'moduleCount': len(modules),
                'hasPresentation': has_presentation
            })
        else:
            courses = scan_courses(item_path)
            routes.append({
                'id': unique_id,
                'name': item,
                'folderName': item,
                'isCourse': False,
                'courses': courses,
                'courseCount': len(courses)
            })
    
    return routes


def scan_all_courses():
    """Escanea toda la estructura de cursos."""
    categories = []
    
    for folder_name, cat_info in CATEGORIES.items():
        category_path = os.path.join(COURSES_PATH, folder_name)
        
        if os.path.exists(category_path):
            print(f"  📂 Escaneando {folder_name}...")
            routes = scan_routes(category_path)
            
            total_courses = 0
            total_classes = 0
            for route in routes:
                if route.get('isCourse'):
                    total_courses += 1
                    for mod in route.get('modules', []):
                        total_classes += len(mod.get('classes', []))
                else:
                    total_courses += len(route.get('courses', []))
                    for course in route.get('courses', []):
                        for mod in course.get('modules', []):
                            total_classes += len(mod.get('classes', []))
            
            categories.append({
                'id': cat_info['id'],
                'name': folder_name,
                'icon': cat_info['icon'],
                'description': cat_info['description'],
                'folderName': folder_name,
                'routes': routes,
                'routeCount': len(routes),
                'courseCount': total_courses,
                'classCount': total_classes
            })
            print(f"     ✓ {len(routes)} rutas, {total_courses} cursos, {total_classes} clases")
    
    total_routes = sum(len(cat['routes']) for cat in categories)
    total_courses = sum(cat['courseCount'] for cat in categories)
    total_classes = sum(cat['classCount'] for cat in categories)
    
    return {
        'categories': categories,
        'stats': {
            'totalCategories': len(categories),
            'totalRoutes': total_routes,
            'totalCourses': total_courses,
            'totalClasses': total_classes
        }
    }


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
        # Fallback: scan filesystem
        print("📖 Escaneando cursos del sistema de archivos...")
        data = scan_all_courses()
        with cache_lock:
            courses_cache = data
        print(f"\n✅ Escaneo completado: {data['stats']['totalCourses']} cursos, {data['stats']['totalClasses']} clases")
    
    print(f"🌐 Servidor listo en http://localhost:{PORT}\n")


class PlatziHandler(SimpleHTTPRequestHandler):
    """Manejador HTTP personalizado."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=VIEWER_PATH, **kwargs)

    def handle(self):
        try:
            super().handle()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
    
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
        
        # Google Drive file streaming
        if self.path.startswith('/drive/files/'):
            file_id = unquote(self.path[13:])
            
            # Handle local filesystem files (prefixed with "local:")
            if file_id.startswith('local:'):
                local_rel = file_id[6:]  # Remove "local:" prefix
                full_path = os.path.join(COURSES_PATH, local_rel)
                
                if not os.path.exists(full_path) or not os.path.isfile(full_path):
                    self.send_error(404, f'File not found: {local_rel}')
                    return
                
                mime_type, _ = mimetypes.guess_type(full_path)
                if mime_type is None:
                    mime_type = 'application/octet-stream'
                
                file_size = os.path.getsize(full_path)
                is_video = mime_type and mime_type.startswith('video')
                range_header = self.headers.get('Range')
                
                # Optimized for portable/network drive execution
                CHUNK_SIZE = 1024 * 1024 # 1MB
                BUFFER_SIZE = 4 * 1024 * 1024 # 4MB
                
                if range_header and file_size > 0:
                    range_match = range_header.replace('bytes=', '').split('-')
                    start = int(range_match[0]) if range_match[0] else 0
                    end = int(range_match[1]) if range_match[1] else file_size - 1
                    end = min(end, file_size - 1)
                    content_length = end - start + 1
                    
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
                        with open(full_path, 'rb', buffering=BUFFER_SIZE) as f:
                            f.seek(start)
                            remaining = content_length
                            while remaining > 0:
                                chunk = f.read(min(CHUNK_SIZE, remaining))
                                if not chunk:
                                    break
                                self.wfile.write(chunk)
                                remaining -= len(chunk)
                    except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError):
                        pass
                else:
                    self.send_response(200)
                    self.send_header('Content-Type', mime_type)
                    self.send_header('Content-Length', file_size)
                    self.send_header('Accept-Ranges', 'bytes')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    if is_video:
                        self.send_header('Cache-Control', 'public, max-age=3600')
                    self.end_headers()
                    
                    try:
                        with open(full_path, 'rb', buffering=BUFFER_SIZE) as f:
                            while True:
                                chunk = f.read(CHUNK_SIZE)
                                if not chunk:
                                    break
                                self.wfile.write(chunk)
                    except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError):
                        pass
                return
            
            # Regular Google Drive file ID
            ds = get_drive_service()
            if not ds:
                self.send_error(503, 'Drive service not available')
                return
            
            try:
                range_header = self.headers.get('Range')
                start = None
                end = None
                
                if range_header:
                    range_match = range_header.replace('bytes=', '').split('-')
                    start = int(range_match[0]) if range_match[0] else None
                    end = int(range_match[1]) if len(range_match) > 1 and range_match[1] else None

                resp = ds.download_file_range(file_id, start, end)

                self.send_response(resp.status_code)

                drive_headers = resp.headers

                content_type = drive_headers.get('Content-Type', 'video/mp4')
                self.send_header('Content-Type', content_type)

                if 'Content-Length' in drive_headers:
                    self.send_header('Content-Length', drive_headers['Content-Length'])

                if 'Content-Range' in drive_headers:
                    self.send_header('Content-Range', drive_headers['Content-Range'])

                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Connection', 'keep-alive')
                self.send_header('Keep-Alive', 'timeout=60, max=1000')

                is_video = content_type.startswith('video')
                if is_video:
                    self.send_header('Cache-Control', 'public, max-age=3600')

                self.end_headers()

                try:
                    for chunk in resp.iter_content(chunk_size=256 * 1024):
                        if chunk:
                            self.wfile.write(chunk)
                            self.wfile.flush()
                except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError):
                    pass
            except Exception as e:
                print(f"❌ Drive streaming error for {file_id}: {e}")
                self.send_error(500, str(e))
            return
        
        # Archivos de cursos (local filesystem)
        if self.path.startswith('/courses/'):
            file_path = unquote(self.path[9:])
            full_path = os.path.join(COURSES_PATH, file_path)
            
            if os.path.exists(full_path) and os.path.isfile(full_path):
                mime_type, _ = mimetypes.guess_type(full_path)
                if mime_type is None:
                    mime_type = 'application/octet-stream'
                
                file_size = os.path.getsize(full_path)
                range_header = self.headers.get('Range')
                
                # Google Drive Streaming Optimization
                # Para archivos en la nube o portables, pedazos más grandes reducen la latencia y overhead de IOPS
                CHUNK_SIZE = 1024 * 1024  # 1MB - Mucho más eficiente para streaming
                BUFFER_SIZE = 4 * 1024 * 1024 # 4MB de buffer de lectura del sistema operativo

                # Cache headers for video files (1 hour cache)
                is_video = mime_type and mime_type.startswith('video')
                
                if range_header:
                    range_match = range_header.replace('bytes=', '').split('-')
                    start = int(range_match[0]) if range_match[0] else 0
                    # For range requests, honor the full requested range (browser knows best)
                    requested_end = int(range_match[1]) if range_match[1] else file_size - 1
                    end = min(requested_end, file_size - 1)
                    
                    content_length = end - start + 1
                    
                    self.send_response(206)
                    self.send_header('Content-Type', mime_type)
                    self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                    self.send_header('Content-Length', content_length)
                    self.send_header('Accept-Ranges', 'bytes')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Connection', 'keep-alive')
                    self.send_header('Keep-Alive', 'timeout=60, max=1000')
                    if is_video:
                        self.send_header('Cache-Control', 'public, max-age=3600')
                        self.send_header('X-Content-Type-Options', 'nosniff')
                    self.end_headers()
                    
                    # Stream in larger chunks
                    try:
                        # Usar buffering grande para que el sistema operativo intente precargar
                        # datos de Drive en segundo plano mientras nosotros enviamos chunks
                        with open(full_path, 'rb', buffering=BUFFER_SIZE) as f:
                            f.seek(start)
                            remaining = content_length
                            while remaining > 0:
                                chunk = f.read(min(CHUNK_SIZE, remaining))
                                if not chunk:
                                    break
                                try:
                                    self.wfile.write(chunk)
                                except (ConnectionAbortedError, BrokenPipeError):
                                    raise # Relanzar para salir del loop
                                remaining -= len(chunk)
                    except (ConnectionAbortedError, BrokenPipeError):
                        pass  # Cliente cerró la conexión

                else:
                    # Full file request - still use chunked transfer for large files
                    self.send_response(200)
                    self.send_header('Content-Type', mime_type)
                    self.send_header('Content-Length', file_size)
                    self.send_header('Accept-Ranges', 'bytes')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Connection', 'keep-alive')
                    if is_video:
                        self.send_header('Cache-Control', 'public, max-age=3600')
                    self.end_headers()
                    
                    # Stream in chunks
                    try:
                        with open(full_path, 'rb') as f:
                            while True:
                                chunk = f.read(CHUNK_SIZE)
                                if not chunk:
                                    break
                                self.wfile.write(chunk)
                    except (ConnectionAbortedError, BrokenPipeError):
                        pass  # Cliente cerró la conexión

                return
            else:
                self.send_error(404, f'File not found')
                return
        
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

        # Abrir archivo en reproductor externo
        if self.path == '/api/open':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            try:
                data = json.loads(post_data.decode('utf-8'))
                file_ref = data.get('path', '')

                # Handle local: prefixed paths (new format)
                if file_ref.startswith('local:'):
                    local_rel = file_ref[6:]  # Remove "local:" prefix
                    full_path = os.path.join(COURSES_PATH, local_rel)
                else:
                    # Legacy: raw relative path
                    if file_ref.startswith('/'):
                        file_ref = file_ref[1:]
                    full_path = os.path.join(COURSES_PATH, unquote(file_ref))

                if os.path.exists(full_path):
                    if os.name == 'nt':  # Windows
                        os.startfile(full_path)
                    else:  # Linux/Mac
                        opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
                        subprocess.Popen([opener, full_path])

                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(b'{"status": "opened"}')
                else:
                    print(f"⚠️ /api/open file not found: {full_path}")
                    self.send_error(404, f'File not found: {full_path}')
            except Exception as e:
                print(f"❌ /api/open error: {e}")
                self.send_error(500, str(e))
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
    print("🎓 Platzi Viewer - Servidor Local")
    print("=" * 50)
    print(f"📁 Cursos: {COURSES_PATH}")
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
