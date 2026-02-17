# Platzi Viewer

🎓 **Plataforma web para visualizar y organizar cursos de Platzi de manera local**

Una aplicación web progresiva (PWA) que permite navegar, organizar y hacer seguimiento del progreso de los cursos de Platzi almacenados localmente, con soporte para streaming de video, sincronización de progreso y una interfaz moderna y responsiva.

## 🚀 Características Principales

### 📚 Gestión de Contenido
- **Navegación jerárquica**: Categorías → Rutas → Cursos → Módulos → Clases
- **Búsqueda avanzada**: Encuentra cursos y clases rápidamente
- **Filtros por tipo**: Video, Resumen, Lectura, Sandbox/HTML
- **Vista de progreso**: Seguimiento detallado del avance en cada curso

### 🎥 Reproducción de Video
- **Streaming optimizado**: Soporte para videos locales y de Google Drive
- **Buffering inteligente**: Precarga y gestión de memoria eficiente
- **Sincronización A/V**: Monitoreo avanzado de sincronización audio/video
- **Navegación entre clases**: Avanzar/retroceder con atajos de teclado

### 📊 Seguimiento de Progreso
- **Persistencia local**: Almacenamiento en localStorage
- **Sincronización con servidor**: Backup automático de progreso
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
├── 📁 js/                    # Aplicación modular (v2)
│   ├── 📁 components/        # Componentes UI reutilizables
│   ├── 📁 services/          # Servicios (API, Estado)
│   ├── 📁 views/             # Vistas de la aplicación
│   ├── app_v2.js            # Entry point principal
│   └── router.js            # Sistema de routing
├── 📄 app.js                # Aplicación legacy (monolítica)
├── 🐍 server.py             # Servidor Python local
├── 📄 index.html            # Página principal
├── 🎨 styles.css            # Estilos completos
├── 📄 PlatziRoutes.md       # Definición de rutas y cursos
└── 🐍 drive_service.py      # Integración con Google Drive
```

### Arquitectura Cliente-Servidor
- **Frontend**: JavaScript ES6+ con módulos, routing cliente
- **Backend**: Python con servidor HTTP integrado
- **Almacenamiento**: JSON para caché, localStorage para progreso
- **Streaming**: Chunked transfer para videos grandes

## 🛠️ Instalación y Configuración

### Prerrequisitos
- **Python 3.7+**: Para el servidor backend
- **Navegador moderno**: Chrome, Firefox, Safari, Edge
- **Almacenamiento local**: ~1GB para caché de cursos

### Configuración Inicial

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/tu-usuario/platzi-viewer.git
   cd platzi-viewer
   ```

2. **Configurar entorno Python**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt  # Si existe requirements.txt
   ```

3. **Configurar rutas de cursos**
   - Editar `server.py` y actualizar `COURSES_PATH`
   - Asegurar que los cursos estén en la estructura esperada

4. **Iniciar el servidor**
   ```bash
   python server.py
   ```

5. **Acceder a la aplicación**
   - Abrir `http://localhost:8080` en el navegador
   - La aplicación se inicializará automáticamente

### Configuración Opcional

#### Google Drive Integration
```python
# Colocar service_account.json en el directorio raíz
# Configurar las credenciales en Google Cloud Console
```

#### Caché de Cursos
```bash
# Reconstruir caché manualmente
python rebuild_cache.py
```

## 📖 Uso de la Aplicación

### Navegación Básica
1. **Inicio**: Vista general de categorías disponibles
2. **Categoría**: Lista de rutas de aprendizaje
3. **Ruta**: Cursos individuales o rutas completas
4. **Curso**: Módulos y clases del curso
5. **Clase**: Reproducción de video y materiales

### Atajos de Teclado
- **Escape**: Cerrar modal actual
- **←/→**: Navegar entre clases
- **Espacio**: Pausar/reanudar video
- **F**: Pantalla completa

### Gestión de Progreso
- **Auto-marcar**: Las clases se marcan completadas al 90% de reproducción
- **Manual**: Click en el icono de estado para cambiar
- **Sincronización**: El progreso se guarda automáticamente

## 🔧 Desarrollo

### Estructura de Código

#### Frontend Modular (v2)
```javascript
// js/app_v2.js - Entry point
import { Router } from './router.js';
import { state } from './services/state.js';
import { Navbar } from './components/navbar.js';

// Sistema de routing cliente
const routes = {
    '#home': HomeView,
    '#explore': ExploreView,
    '#learning': LearningView,
    // ...
};
```

#### Backend Python
```python
# server.py - Servidor HTTP con threading
class PlatziHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # API endpoints, streaming de video, archivos estáticos
    
    def do_POST(self):
        # Guardar progreso, abrir archivos externos
```

### Scripts de Mantenimiento

```bash
# Escanear y actualizar caché de cursos
python rebuild_cache.py

# Verificar archivos faltantes
python check_remaining.py

# Generar lista de Drive
python generate_drive_list.py
```

## 🐛 Problemas Conocidos y Soluciones

### Issues Críticos
- **CATEGORIES undefined**: Error en server.py línea 248 - necesita importación
- **Race condition en sync**: Posible pérdida de progreso en concurrencia
- **Memory leak en streaming**: Buffers grandes sin cleanup adecuado

### Soluciones Temporales
1. **Para CATEGORIES**: Importar desde parse_routes.py
2. **Para race condition**: Implementar mutex en sincronización
3. **Para memory leak**: Reducir tamaño de buffers y agregar cleanup

## 📋 Roadmap de Desarrollo

### v1.1 - Correcciones Críticas
- [ ] Fix undefined CATEGORIES variable
- [ ] Implementar sanitización de paths
- [ ] Agregar manejo de errores robusto
- [ ] Optimizar consumo de memoria

### v1.2 - Mejoras de Funcionalidad
- [ ] Migrar completamente a app_v2.js
- [ ] Implementar PWA completo
- [ ] Agregar modo offline
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
3. Commits descriptivos y atomics
4. Pull request con template completo

### Estándares de Código
- **JavaScript**: ES6+, ESLint configurado
- **Python**: PEP 8, type hints donde aplique
- **CSS**: BEM methodology, variables CSS
- **Commits**: Conventional Commits specification

### Testing
```bash
# Ejecutar tests (cuando existan)
npm test
python -m pytest
```

## 📄 Licencia

Este proyecto está bajo licencia MIT. Ver archivo [LICENSE](LICENSE) para detalles.

## 🙏 Agradecimientos

- **Platzi**: Por la plataforma de educación de calidad
- **Comunidad**: Por el feedback y contribuciones
- **Contribuidores**: Todas las personas que han mejorado el proyecto

## 📞 Contacto

- **Issues**: [GitHub Issues](https://github.com/tu-usuario/platzi-viewer/issues)
- **Discusiones**: [GitHub Discussions](https://github.com/tu-usuario/platzi-viewer/discussions)
- **Email**: tu-email@ejemplo.com

---

**⚠️ Nota**: Este proyecto es para uso personal y educativo. No afiliado oficialmente con Platzi.
