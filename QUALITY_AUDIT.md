# Auditoría de estabilización

## Hallazgos en archivos con cambios locales activos

### Alta prioridad
- `test_drive_scan.py` estaba roto por imports obsoletos hacia símbolos que ya no exporta `server.py`; se sustituyó por una suite reproducible en `tests/`.
- `js/views/player.js` concentra mucha lógica de reproducción, sincronización A/V, navegación y UI en un solo archivo, lo que eleva el riesgo de regresión y hace difícil aislar bugs.
- `server.py` tiene varios `except Exception` amplios en rutas críticas de streaming y procesos externos; hoy favorecen continuidad operativa, pero dificultan diagnóstico fino y esconden clases de error distintas.

### Prioridad media
- `js/views/player.js` ya no depende de `window.__playerView` para la UI, pero mantiene `window.__platziAvSyncLastStats` como salida de diagnóstico; conviene decidir si esa telemetría debe seguir expuesta globalmente o migrar a un canal más explícito.
- `js/services/api.js` resuelve `API_URL` en tiempo de carga y mezcla timeouts, retries y elección de endpoint; conviene separar construcción de URL, política de retry y detección de compatibilidad.
- `desktop_app.py` mantiene varios fallbacks UI válidos, pero con manejo silencioso de errores al cerrar servidor o descargar archivos, lo que dificulta soporte en desktop.

### Prioridad baja
- `js/services/state.js` ya hace merge y lazy loading útiles, pero sigue cargando demasiadas responsabilidades en un singleton mutable.
- `drive_service.py` tiene buena validación de IDs y reintentos, aunque todavía usa `Exception` genérica para errores de red/API en varios puntos.

## Limpieza y política de artefactos
- `build/`, `dist/`, `courses_cache.json`, `progress.json`, logs y cachés de calidad quedan tratados como artefactos generados o locales en `.gitignore`.
- Esta ronda no elimina artefactos existentes automáticamente; solo fija la política para que la limpieza futura sea demostrablemente segura.

## Validación nueva
- `package.json` ahora ejecuta `pytest`, `ruff`, `eslint` y `stylelint` de verdad.
- La suite `tests/` cubre caché/refs Drive, smoke tests del launcher desktop y un smoke test del frontend limpio sin depender de red ni credenciales reales.
- `player.js` quedó sin handlers inline para las acciones principales del reproductor y sin warnings activos de ESLint.
