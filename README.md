# Platzi Viewer

🎓 **Plataforma web para visualizar y organizar cursos de Platzi mediante Google Drive API**

Una aplicación web progresiva (PWA) que permite navegar, organizar y hacer seguimiento del progreso de los cursos de Platzi almacenados en Google Drive, con streaming de video en tiempo real, sincronización de progreso y una interfaz moderna y responsiva. Todo el contenido se sirve exclusivamente a través de la API de Google Drive usando una cuenta de servicio.

## 🚀 Características Principales

### 📚 Gestión de Contenido
- **Navegación jerárquica**: Categorías → Rutas → Cursos → Módulos → Clases
- **Búsqueda avanzada**: Encuentra cursos y clases rápidamente
- **Filtros por tipo**: Video, Resumen, Lectura, Sandbox/HTML
- **Vista de progreso**: Seguimiento detallado del avance en cada curso

### 🎥 Reproducción de Video
- **Streaming desde Google Drive**: Los videos se transmiten en tiempo real desde la API de Drive
- **Soporte HTTP Range Requests**: Permite seek/buffering parcial sin descargar el archivo completo
- **Sincronización A/V adaptativa**: Corrección automática de drift, monitoreo por frames y ajuste dinámico para sesiones largas
- **Navegación entre clases**: Avanzar/retroceder con atajos de teclado
- **Cierre limpio al navegar**: Al salir del reproductor se detiene y desmonta cualquier reproducción activa (sin audio residual)

### 📊 Seguimiento de Progreso
- **Persistencia local**: Almacenamiento en localStorage del navegador
- **Sincronización con servidor**: Backup automático en `progress.json`
- **Estadísticas detalladas**: Tiempo de visualización y estado de completion
- **Progreso por módulo**: Vista granular del avance

### 🎨 Interfaz Moderna
- **Diseño responsivo**: Adaptable a desktop y móviles
- **Modo oscuro**: Tema moderno para reducir fatiga visual
- **Animaciones suaves**: Transiciones y microinteracciones
- **Atajos de teclado**: Navegación rápida sin mouse

## 🏗️ Arquitectura

### Estructura del Proyecto
```
platzi-viewer/
├── 📁 js/                        # Aplicación modular (v2)
│   ├── 📁 components/            # Componentes UI (navbar, card)
│   ├── 📁 services/              # Servicios (API, Estado)
│   │   ├── api.js                # Cliente API - genera URLs /drive/files/{id}
│   │   └── state.js              # Gestión de estado global
│   ├── 📁 views/                 # Vistas (home, explore, course, player...)
│   ├── app_v2.js                 # Entry point principal
│   └── router.js                 # Sistema de routing hash-based
├── 🐍 server.py                  # Servidor HTTP + proxy Drive API
├── 🐍 drive_service.py           # Wrapper de Google Drive API v3
├── 🐍 rebuild_cache_drive.py     # Constructor del caché desde Drive
├── 🐍 parse_routes.py            # Parser de PlatziRoutes.md
├── 📄 courses_cache.json         # Caché de cursos con Drive file IDs (~20MB)
├── 📄 service_account.json       # Credenciales de cuenta de servicio Google
├── 📄 PlatziRoutes.md            # Definición de categorías/rutas/cursos
├── 📄 index.html                 # Página principal
├── 🎨 styles.css                 # Estilos completos
└── 📄 progress.json              # Progreso del usuario (backup servidor)
```

### Arquitectura Cliente-Servidor
- **Frontend**: JavaScript ES6+ con módulos, routing con hash (`#home`, `#course`, `#player`)
- **Backend**: Python `ThreadingHTTPServer` que sirve archivos estáticos y actúa como proxy de Google Drive API
- **Almacenamiento**: `courses_cache.json` para estructura de cursos, `localStorage` + `progress.json` para progreso
- **Streaming**: Proxy transparente a Google Drive con soporte de HTTP Range Requests para videos

## 🔌 Cómo se Obtienen los Recursos y Videos (Google Drive API)

### Visión General

**Todo el contenido (videos, resúmenes, lecturas, subtítulos, recursos) se obtiene exclusivamente desde Google Drive** a través de la API v3. No hay archivos de cursos almacenados localmente. El flujo es:

```
┌─────────────┐    HTTP      ┌──────────────┐    Drive API v3    ┌──────────────┐
│  Navegador  │ ────────────→│  server.py   │ ──────────────────→│ Google Drive  │
│  (Frontend) │ ←────────────│  (Proxy)     │ ←──────────────────│ (Contenido)   │
└─────────────┘   Streaming  └──────────────┘    Streaming       └──────────────┘
```

### Paso 1: Construcción del Caché (`rebuild_cache_drive.py`)

Antes de usar la aplicación, se debe construir `courses_cache.json`. Este archivo mapea toda la estructura de cursos con los **Google Drive file IDs** de cada recurso.

#### Proceso de escaneo:

1. **Lectura de rutas**: Se parsea `PlatziRoutes.md` usando `parse_routes.py` para obtener la lista completa de categorías, rutas de aprendizaje y cursos de Platzi.

2. **Escaneo del Drive compartido**: Se conecta a la carpeta raíz compartida en Drive (`17kPqqPSheDtQ5S1HM6Qvvh2qJ7O3YADm`) y lista todas las carpetas de cursos.

3. **Matching fuzzy**: Para cada curso definido en `PlatziRoutes.md`, se busca la carpeta correspondiente en Drive usando coincidencia difusa (normalización de nombres, eliminación de caracteres especiales, comparación insensible a acentos).

4. **Escaneo de estructura interna**: Para cada carpeta de curso encontrada:
   ```
   Carpeta del Curso/
   ├── 1. Módulo Uno/
   │   ├── 1. Clase Uno.mp4           → video (Drive file ID)
   │   ├── 1. Clase Uno_summary.html  → summary (Drive file ID)
   │   ├── 1. Clase Uno.vtt           → subtitles (Drive file ID)
   │   ├── 1. Clase Uno - Lecturas recomendadas.txt → reading (Drive file ID)
   │   ├── 2. Clase Dos.mp4
   │   └── ...
   ├── 2. Módulo Dos/
   │   └── ...
   └── presentation.html              → presentación del curso
   ```

5. **Almacenamiento de IDs**: Los archivos se clasifican por tipo (video, summary, subtitles, reading, html, resources) y se almacena el **Drive file ID** de cada uno:
   ```json
   {
     "name": "Clase Uno",
     "hasVideo": true,
     "hasSummary": true,
     "files": {
       "video": "1OOJ5lrsLfFEnp6AKVKZKYZH5A-NasCjl",
       "summary": "1WWggG3NLugsK6dZ37wzbNeLAPqFdOVfj",
       "subtitles": "1ABCdef...",
       "reading": "1XYZ789...",
       "html": null
     },
     "resources": [
       {"name": "slides.pdf", "file": "1QWE456...", "ext": ".pdf", "viewable": true}
     ]
   }
   ```

6. **Resume capability**: El progreso del escaneo se guarda en `drive_scan_progress.json`, permitiendo retomar el escaneo si se interrumpe.

#### Ejecución:
```bash
python rebuild_cache_drive.py
# Escanea ~500 carpetas de cursos en Drive
# Genera courses_cache.json (~20MB, ~20,000 clases)
# Tiempo estimado: 15-30 minutos (por rate limiting de la API)
```

### Paso 2: Carga del Caché en el Servidor (`server.py`)

Al iniciar `server.py`, el servidor carga `courses_cache.json` en memoria:

```python
# server.py - init_cache()
with open("courses_cache.json", 'r', encoding='utf-8') as f:
    courses_cache = json.load(f)  # ~20MB con toda la estructura de cursos
```

El endpoint `/api/courses` devuelve este caché completo al frontend cuando lo solicita.

### Paso 3: Solicitud de Recursos desde el Frontend

Cuando el usuario navega a un curso o reproduce un video, el frontend usa los Drive file IDs almacenados en el caché:

```javascript
// js/services/api.js
getVideoUrl(fileId) {
    return `${API_URL}/drive/files/${fileId}`;
}
getFileUrl(fileId) {
    return `${API_URL}/drive/files/${fileId}`;
}
```

Por ejemplo, para reproducir un video:
```javascript
// js/views/player.js
const videoUrl = ApiService.getVideoUrl(classData.files.video);
// videoUrl = "http://localhost:8080/drive/files/1OOJ5lrsLfFEnp6AKVKZKYZH5A-NasCjl"
videoElement.src = videoUrl;
```

Para cargar un resumen HTML:
```javascript
const summaryUrl = ApiService.getFileUrl(classData.files.summary);
const response = await fetch(summaryUrl);
const html = await response.text();
```

### Paso 4: Proxy de Drive en el Servidor (`/drive/files/{fileId}`)

El servidor actúa como **proxy transparente** entre el navegador y Google Drive:

1. **Recibe la solicitud** del navegador en `/drive/files/{fileId}`
2. **Obtiene metadata** del archivo desde Drive API (`get_file_metadata`)
3. **Detecta el tipo MIME** (con fallback por extensión si Drive retorna `application/octet-stream`)
4. **Gestiona Range Requests**: Para videos, el navegador envía headers `Range: bytes=0-1048575` para buffering parcial
5. **Descarga y transmite** el contenido desde Drive al navegador en chunks de 1MB

#### Flujo para un video (con Range Request):
```
Browser                    server.py                    Google Drive API
   │                          │                              │
   │ GET /drive/files/ABC123  │                              │
   │ Range: bytes=0-1048575   │                              │
   │─────────────────────────→│                              │
   │                          │ get_file_metadata("ABC123")  │
   │                          │─────────────────────────────→│
   │                          │ {name, size, mimeType}       │
   │                          │←─────────────────────────────│
   │                          │                              │
   │                          │ download_file_range(          │
   │                          │   "ABC123", 0, 1048575)      │
   │                          │─────────────────────────────→│
   │                          │ [streaming bytes...]         │
   │                          │←─────────────────────────────│
   │ HTTP 206 Partial Content │                              │
   │ Content-Range: bytes     │                              │
   │   0-1048575/52428800     │                              │
   │ [streaming bytes...]     │                              │
   │←─────────────────────────│                              │
```

#### Flujo para un archivo pequeño (resumen, lectura, subtítulos):
```
Browser                    server.py                    Google Drive API
   │                          │                              │
   │ GET /drive/files/XYZ789  │                              │
   │─────────────────────────→│                              │
   │                          │ get_file_metadata + download  │
   │                          │─────────────────────────────→│
   │                          │ [complete file]              │
   │                          │←─────────────────────────────│
   │ HTTP 200 OK              │                              │
   │ Content-Type: text/html  │                              │
   │ [complete file]          │                              │
   │←─────────────────────────│                              │
```

### Paso 5: Autenticación con Google Drive

La conexión a Google Drive se realiza mediante una **cuenta de servicio** (Service Account):

```python
# drive_service.py
from google.oauth2.service_account import Credentials

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
credentials = Credentials.from_service_account_file(
    'service_account.json', scopes=SCOPES
)
```

- **Cuenta de servicio**: Configurable por archivo JSON local
- **Scope**: Solo lectura (`drive.readonly`)
- **No requiere OAuth del usuario**: La autenticación es automática con el archivo `service_account.json`
- **Acceso**: La carpeta compartida de Drive debe estar compartida con el email de la cuenta de servicio

### Resumen de Endpoints de la API

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/courses` | GET | Retorna la estructura completa de cursos (desde `courses_cache.json`) |
| `/api/health` | GET | Estado del servidor + Drive + FFmpeg + telemetría de `compatStream` |
| `/api/video-compatible/{fileId}` | GET | Stream de compatibilidad A/V (FFmpeg remux/transcode) para videos conflictivos |
| `/api/refresh` | GET | Recarga `courses_cache.json` desde disco (solo cliente local / loopback) |
| `/api/progress` | GET | Retorna el progreso guardado del usuario |
| `/api/progress` | POST | Guarda el progreso del usuario en `progress.json` |
| `/drive/files/{fileId}` | GET | Proxy a Google Drive - transmite el archivo indicado por su file ID |

### Diagnóstico A/V y matriz de pruebas reproducible

Para aislar desincronización progresiva usa esta matriz mínima en el mismo video/clase:

1. **Modo normal** (`/drive/files/{id}`) en navegador web durante 10-15 min.
2. **Modo normal** en `PlatziViewerDesktop.exe` durante 10-15 min.
3. **Modo compatibilidad** (`/api/video-compatible/{id}`) en web.
4. **Modo compatibilidad** en desktop.
5. Repite cada caso con red estable y con jitter (VPN/móvil/hotspot).

En cada corrida registra:
- Drift estimado (ms) al minuto 1, 5, 10.
- Número de correcciones soft/hard (`window.__platziAvSyncLastStats`).
- Cambios automáticos de calidad y activaciones de compatibilidad.
- Snapshot de `http://localhost:8080/api/health` (`compatStream.lastMode`, `lastError`, `lastSpeedMBps`, `failedStreams`).

Si el archivo falla en `copy` pero mejora en transcode, puedes forzar reencode del endpoint compatible:

```bash
# Windows PowerShell
$env:PLATZI_COMPAT_FORCE_REENCODE="1"
python server.py
```

Esto aumenta uso de CPU, pero suele estabilizar archivos con timestamps dañados.

### Tipos de Archivo y cómo se Sirven

| Tipo | Extensión | MIME Type | Método de Entrega |
|---|---|---|---|
| Video | `.mp4` | `video/mp4` | Streaming con Range Requests (HTTP 206) |
| Resumen | `_summary.html` | `text/html` | Descarga completa (HTTP 200) |
| Subtítulos | `.vtt` | `text/vtt` | Descarga completa (HTTP 200) |
| Lectura | `.txt` | `text/plain` | Descarga completa (HTTP 200) |
| HTML interactivo | `.html` | `text/html` | Descarga completa (HTTP 200) |
| Recursos | `.pdf`, `.png`, etc. | Varía | Descarga completa (HTTP 200) |

## 🛠️ Instalación y Configuración

### Calidad y pruebas

Una vez creado el entorno virtual y antes de tocar código, instala el tooling de validación:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm install
```

Comandos disponibles:

```powershell
npm run test
npm run test:frontend:smoke
npm run lint
npm run lint:fix
npm run format
```

## 🧳 Crear .exe Portable (Windows)

No necesitas Docker para generar el ejecutable en Windows.

1. Activa tu entorno virtual (`.venv`) y verifica que exista `pyinstaller`.
2. Instala dependencias de runtime si aun no estan:
```powershell
pip install -r requirements.txt
```
3. Ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_portable_exe.ps1
```

4. Se generará:
- `dist/PlatziViewer/PlatziViewer.exe`

5. Antes de compartir, valida dentro de `dist/PlatziViewer`:
- `service_account.json` (solo si quieres que funcione sin configuración manual)
- `courses_cache.json`

El `.exe` usa el icono `favicon.ico` (derivado de tu diseño `favicon.svg`).

### 🪟 App de escritorio en un único EXE (sin navegador)

Si quieres abrir todo como aplicación de Windows (backend + frontend juntos, ventana nativa):

```powershell
powershell -ExecutionPolicy Bypass -File .\build_desktop_exe.ps1
```

Salida:
- `dist/PlatziViewerDesktop.exe`

Ese archivo abre la app de escritorio directamente (no pestaña de navegador).

### ⚙️ Forzar aceleración por GPU dedicada (Windows)

Para videos conflictivos, la app de escritorio ahora solicita aceleración hardware (Chromium/Qt) automáticamente. Además, en Windows puedes forzar GPU dedicada por proceso:

1. Ve a **Configuración > Sistema > Pantalla > Gráficos**.
2. Agrega `PlatziViewerDesktop.exe` (o tu navegador si usas versión web).
3. En Opciones, selecciona **Alto rendimiento**.
4. Reinicia la app.

Notas:
- Esto puede mejorar fluidez/decodificación, pero no corrige todos los videos con timestamps dañados.
- Si el archivo sigue desincronizado, usa el **modo compatibilidad** o **Abrir VLC** desde el reproductor.

## Docker (backend + frontend)

Puedes correr toda la app en Docker (servidor Python + frontend estatico):

1. Crear carpetas locales:
```bash
mkdir secrets runtime-data
```
2. Copiar credenciales en `secrets/service_account.json`.
3. Levantar contenedor:
```bash
docker compose up --build -d
```
4. Abrir `http://localhost:8080`.

### Diagnostico del 503 "Drive service not available"

Consulta:
- `http://localhost:8080/api/health`

Si ves `"drive": {"available": false, ...}` revisa:
- Ruta de credenciales (`GOOGLE_SERVICE_ACCOUNT_FILE`).
- JSON inline (`GOOGLE_SERVICE_ACCOUNT_JSON`) si no usas archivo.
- Permisos de comparticion del Drive para la cuenta de servicio.

### Prerrequisitos
- **Python 3.7+**: Para el servidor backend
- **Navegador moderno**: Chrome, Firefox, Safari, Edge
- **Cuenta de servicio de Google Cloud**: Con acceso a Google Drive API
- **Carpeta compartida en Google Drive**: Con los cursos organizados

### Paso 1: Clonar el Repositorio
```bash
git clone https://github.com/tu-usuario/platzi-viewer.git
cd platzi-viewer
```

### Paso 2: Instalar Dependencias Python
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

Las dependencias principales son:
- `google-api-python-client` - Cliente de Google Drive API
- `google-auth` - Autenticación con cuenta de servicio
- `google-auth-httplib2` - Transporte HTTP para la autenticación

### Paso 3: Configurar la Cuenta de Servicio de Google

1. **Crear un proyecto en Google Cloud Console**: https://console.cloud.google.com/
2. **Habilitar la API de Google Drive** en el proyecto
3. **Crear una cuenta de servicio**:
   - Ir a "IAM & Admin" → "Service Accounts"
   - Crear nueva cuenta de servicio
   - Descargar la clave JSON
4. **Colocar el archivo de credenciales** como `service_account.json` en la raíz del proyecto **o** definir `GOOGLE_SERVICE_ACCOUNT_FILE` en `.env`
5. **Compartir la carpeta de Drive** con el email de la cuenta de servicio (con permiso de lectura)

### Paso 4: Construir el Caché de Cursos
```bash
python rebuild_cache_drive.py
```
Este proceso escanea toda la estructura de carpetas en Drive y genera `courses_cache.json`. Tarda ~15-30 minutos la primera vez. Si se interrumpe, se puede retomar (guarda progreso en `drive_scan_progress.json`).

### Paso 5: Iniciar el Servidor
```bash
python server.py
```

Opcionalmente puedes configurar variables de entorno copiando `.env.example` a `.env`.

### Paso 6: Acceder a la Aplicación
- Abrir `http://localhost:8080` en el navegador
- La aplicación cargará automáticamente la estructura de cursos desde el caché

#### Actualizar el Caché
```bash
# Reconstruir caché completo desde Drive
python rebuild_cache_drive.py

# Si se interrumpe, ejecutar de nuevo (retoma desde donde se quedó)
python rebuild_cache_drive.py
```

## 📖 Uso de la Aplicación

### Navegación Básica
1. **Inicio**: Vista general de categorías disponibles
2. **Categoría**: Lista de rutas de aprendizaje
3. **Ruta**: Cursos individuales o rutas completas
4. **Curso**: Módulos y clases del curso
5. **Clase**: Reproducción de video y materiales (todo desde Drive)

### Atajos de Teclado
- **Escape**: Cerrar modal actual
- **←/→**: Navegar entre clases
- **Espacio**: Pausar/reanudar video
- **F**: Pantalla completa

### Gestión de Progreso
- **Auto-marcar**: Las clases se marcan completadas al 90% de reproducción
- **Manual**: Click en el icono de estado para cambiar
- **Sincronización**: El progreso se guarda automáticamente en `localStorage` y en `progress.json`

## 🔧 Desarrollo

### Scripts del Proyecto

| Script | Descripción |
|---|---|
| `server.py` | Servidor HTTP + proxy de Google Drive API |
| `rebuild_cache_drive.py` | Escanea Drive y genera `courses_cache.json` con Drive file IDs |
| `drive_service.py` | Wrapper de Google Drive API v3 (autenticación, descargas, listados) |
| `parse_routes.py` | Parsea `PlatziRoutes.md` en estructura de categorías/rutas/cursos |
| `check_remaining.py` | Verifica archivos/cursos faltantes |

### Archivos de Datos

| Archivo | Descripción |
|---|---|
| `courses_cache.json` | Caché completo de cursos con Drive file IDs (~20MB) |
| `progress.json` | Progreso del usuario (backup del servidor) |
| `PlatziRoutes.md` | Definición de categorías, rutas y cursos de Platzi |
| `service_account.json` | Credenciales de la cuenta de servicio de Google |
| `drive_scan_progress.json` | Progreso del escaneo de Drive (para resume) |

### Estructura de Código

#### Frontend Modular (v2)
```javascript
// js/app_v2.js - Entry point
import { Router } from './router.js';
import { state } from './services/state.js';
import { Navbar } from './components/navbar.js';

// Sistema de routing cliente (hash-based)
const routes = {
    '#home': HomeView,
    '#explore': ExploreView,
    '#learning': LearningView,
    '#course': CourseView,
    '#player': PlayerView,
    '#route': RouteView
};
```

#### Backend Python (Drive API Proxy)
```python
# server.py - Servidor HTTP con threading
class PlatziHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # /api/courses    → Sirve courses_cache.json
        # /api/progress   → Sirve progress.json
        # /drive/files/ID → Proxy streaming desde Drive API
        # Otros           → Archivos estáticos (index.html, js/, css)
    
    def do_POST(self):
        # /api/progress   → Guarda progreso del usuario
```

## 🐛 Problemas Conocidos y Soluciones

### Drive API
- **Error 500 de Google**: Ocasionalmente la API retorna errores internos. `drive_service.py` incluye retry automático con backoff exponencial (hasta 5 reintentos).
- **Rate limiting**: `rebuild_cache_drive.py` incluye throttling para no superar las cuotas de Google Drive API (~12,000 queries/minuto).
- **MIME types incorrectos**: Drive a veces retorna `application/octet-stream` para archivos conocidos. El servidor aplica detección por extensión como fallback.

### General
- **Caché grande en memoria**: `courses_cache.json` (~20MB) se carga completamente en RAM. En sistemas con poca memoria, esto podría ser un problema.
- **Tiempo de escaneo**: La primera construcción del caché puede tomar 15-30 minutos por la cantidad de llamadas a la API.

## 🔐 Seguridad al Compartir con Familiares

- Mantén `service_account.json` fuera del repositorio y compártelo por canal privado.
- El servidor usa permisos de solo lectura (`drive.readonly`), sin operaciones de escritura o borrado en Drive.
- El endpoint `/api/refresh` está restringido a loopback para evitar recargas remotas.
- `progress.json` ahora valida tamaño máximo de payload para reducir abuso.
- Antes de compartir, confirma que no incluyes: `service_account.json`, `drive_scan_progress.json`, `server_metadata.json`, `rebuild_log.txt`.

## 📋 Roadmap de Desarrollo

### v1.1 - Optimizaciones
- [ ] Caché parcial (lazy loading por categoría)
- [ ] Compresión gzip en respuestas del servidor
- [ ] Caché local de archivos Drive frecuentes

### v1.2 - Mejoras de Funcionalidad
- [ ] Implementar PWA completo con service worker
- [ ] Mejorar sincronización de progreso

### v2.0 - Características Avanzadas
- [ ] Soporte multiusuario
- [ ] Integración con API de Platzi
- [ ] Sistema de recomendaciones
- [ ] Análisis de aprendizaje

## 🤝 Contribución

### Flujo de Trabajo
1. Fork del repositorio
2. Crear rama feature/nombre-característica
3. Commits descriptivos y atómicos
4. Pull request con template completo

### Estándares de Código
- **JavaScript**: ES6+, módulos nativos del navegador
- **Python**: PEP 8, type hints donde aplique
- **CSS**: BEM methodology, variables CSS
- **Commits**: Conventional Commits specification

## 📄 Licencia

Este proyecto está bajo licencia MIT. Ver archivo [LICENSE](LICENSE) para detalles.

---

**⚠️ Nota**: Este proyecto es para uso personal y educativo. No afiliado oficialmente con Platzi. Todo el contenido se obtiene exclusivamente desde Google Drive mediante una cuenta de servicio autorizada.
