# Agent Instructions — Platzi Viewer

## Core Commands

```powershell
# Development
npm run dev              # Start server (Python ThreadingHTTPServer + frontend)
npm run serve            # Static serve only (python -m http.server 8080)

# Quality gates (run in this order)
npm run lint             # ruff check + eslint + stylelint
npm run lint:fix         # Auto-fix all
npm run format           # ruff format .
npm run test             # Python tests (pytest via run_with_repo_python.py)
npm run test:frontend:smoke  # JS smoke tests
```

## Architecture (Verified Facts)

- **Frontend**: Vanilla JS ES6+ modules, hash-based routing (`#home`, `#course`, `#player`). Entry: `js/app_v2.js`
- **Backend**: `server.py` — `ThreadingHTTPServer` que sirve estáticos + proxy a Google Drive API v3
- **Data flow**: `PlatziRoutes.md` → `rebuild_cache_drive.py` → `courses_cache.json` (~20MB, ~20k clases) → server loads en memoria → frontend consume vía `/api/courses`
- **Video streaming**: Proxy transparente `/drive/files/{fileId}` con HTTP Range Requests (206 Partial Content)
- **Progreso**: `localStorage` (cliente) + `progress.json` (backup servidor)
- **Auth**: Service Account (`service_account.json`) con scope `drive.readonly`

## Critical Gotchas

1. **`courses_cache.json` NO está en el repo** — se genera con `python rebuild_cache_drive.py` (15-30 min, con resume si se interrumpe)
2. **`service_account.json` es local** — la carpeta de Drive debe estar compartida con el email de la cuenta de servicio
3. **Server carga TODO el caché en RAM** (~20MB) — no hay lazy loading por categoría
4. **FFmpeg es opcional pero recomendado** — se usa para `/api/video-compatible/{id}` (remux/transcode para videos con timestamps dañados)
5. **`.env` no existe por defecto** — copiar de `.env.example` si necesitas configurar `PORT`, `HOST`, o `GOOGLE_SERVICE_ACCOUNT_FILE`

## Testing Details

```powershell
# Python tests (pytest con run_with_repo_python.py para usar .venv)
python tools/run_with_repo_python.py -m pytest tests/ -v

# Smoke test frontend (sin servidor, carga index.html y valida JS)
npm run test:frontend:smoke
```

**Tests existentes**:
- `test_server_cache.py` — validación de carga de caché
- `test_tooling_contracts.py` — verifica herramientas (FFmpeg, Python, Node)
- `test_frontend_smoke.py` — carga index.html y chequea errores de sintaxis JS
- `test_desktop_app.py` — validación de build PyInstaller (si existe)

## Build & Deploy

```powershell
# EXE portable (web en navegador)
powershell -ExecutionPolicy Bypass -File .\build_portable_exe.ps1
# Output: dist/PlatziViewer/PlatziViewer.exe

# EXE desktop (ventana nativa con pywebview)
powershell -ExecutionPolicy Bypass -File .\build_desktop_exe.ps1
# Output: dist/PlatziViewerDesktop.exe
```

**Docker**:
```bash
mkdir secrets runtime-data
# Copiar service_account.json en secrets/
docker compose up --build -d
# Acceso: http://localhost:8080
```

## Endpoints de la API

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/courses` | GET | Retorna `courses_cache.json` completo |
| `/api/health` | GET | Estado: Drive, FFmpeg, telemetría `compatStream` |
| `/api/video-compatible/{id}` | GET | Stream con FFmpeg (remux/transcode) para videos conflictivos |
| `/api/refresh` | GET | Recarga caché desde disco (solo loopback) |
| `/api/progress` | GET/POST | Leer/guardar progreso en `progress.json` |
| `/drive/files/{id}` | GET | Proxy a Google Drive — streaming con Range Requests |

## CI/CD (GitHub Actions)

- **Lint**: flake8 (Python), eslint+stylelint (JS/CSS), black (format)
- **Security**: bandit (Python), pip-audit (dependencias)
- **Deploy**: develop → staging, main → production (release automático con tag `v{run_number}`)

## Files to Know

| File | Purpose |
|---|---|
| `server.py` | Backend principal (HTTP + Drive proxy + compat A/V) |
| `drive_service.py` | Wrapper de Drive API v3 (auth, downloads, listados) |
| `rebuild_cache_drive.py` | Construye `courses_cache.json` desde Drive |
| `js/app_v2.js` | Entry point frontend |
| `js/router.js` | Router hash-based |
| `js/services/api.js` | Cliente API — genera URLs `/drive/files/{id}` |
| `PlatziRoutes.md` | Definición de categorías/rutas/cursos de Platzi |

## Security Notes

- `service_account.json` **NUNCA** se commitea — está en `.gitignore`
- `/api/refresh` restringido a loopback (evita recargas remotas del caché)
- `progress.json` valida payload máximo (2MB) para reducir abuso
- Scope de Drive: solo lectura (`drive.readonly`)