# Contributing to Platzi Viewer

¡Gracias por tu interés en contribuir a Platzi Viewer! Este documento te guiará sobre cómo contribuir efectivamente al proyecto.

## 🤝 Cómo Contribuir

### Reportar Issues

#### 🐛 Bug Reports
Antes de reportar un bug:

1. **Buscar issues existentes**: Revisa si el problema ya fue reportado
2. **Verificar versión**: Asegúrate de estar usando la última versión
3. **Reproducir el bug**: Confirma que puedes reproducirlo consistentemente

#### Template para Bug Report
```markdown
## Descripción del Problema
Breve descripción del problema

## Pasos para Reproducir
1. Ir a '...'
2. Click en '....'
3. Scroll down to '....'
4. Ver error

## Comportamiento Esperado
Describe lo que debería pasar

## Comportamiento Actual
Describe lo que realmente pasa

## Capturas de Pantalla
Agrega capturas si ayudan a explicar el problema

## Entorno
- OS: [Windows 10/macOS/Linux]
- Navegador: [Chrome/Firefox/Safari/Edge]
- Versión: [v1.0.0]

## Información Adicional
Cualquier otra información relevante
```

#### 💡 Feature Requests
Para solicitar nuevas características:

1. **Describir el caso de uso**: ¿Qué problema resuelve?
2. **Propuesta de solución**: ¿Cómo debería funcionar?
3. **Alternativas consideradas**: ¿Qué otras opciones evaluaste?

### Contribuciones de Código

#### 🔄 Flujo de Trabajo

1. **Fork el repositorio**
   ```bash
   git clone https://github.com/tu-usuario/platzi-viewer.git
   cd platzi-viewer
   ```

2. **Crear rama de feature**
   ```bash
   git checkout -b feature/nombre-descriptivo
   ```

3. **Hacer cambios con commits atómicos**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

4. **Push a tu fork**
   ```bash
   git push origin feature/nombre-descriptivo
   ```

5. **Crear Pull Request**
   - Usa el template de PR
   - Describe los cambios claramente
   - Incluye capturas de pantalla si aplica

#### 📝 Estándares de Commits

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Tipos permitidos:**
- `feat`: Nueva característica
- `fix`: Corrección de bug
- `docs`: Cambios en documentación
- `style`: Cambios de formato (no lógica)
- `refactor`: Refactorización de código
- `test`: Agregar o modificar tests
- `chore`: Cambios de mantenimiento

**Ejemplos:**
```bash
feat(player): add keyboard shortcuts for video control
fix(server): resolve memory leak in video streaming
docs(readme): update installation instructions
```

## 🏗️ Guías de Desarrollo

### Estructura del Proyecto

#### Frontend (JavaScript)
- **ES6+**: Usa características modernas de JavaScript
- **Módulos**: Organiza el código en módulos importables
- **Componentes**: Crea componentes reutilizables
- **Estado**: Usa el servicio de estado centralizado

```javascript
// ✅ Buen ejemplo
import { ApiService } from '../services/api.js';
import { state } from '../services/state.js';

class VideoPlayer {
    constructor() {
        this.state = state;
        this.api = ApiService;
    }
}
```

#### Backend (Python)
- **PEP 8**: Sigue las convenciones de estilo de Python
- **Type hints**: Agrega anotaciones de tipo donde sea posible
- **Error handling**: Maneja excepciones apropiadamente
- **Logging**: Usa logging para depuración

```python
# ✅ Buen ejemplo
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

def scan_courses(path: str) -> List[Dict]:
    """Scan courses directory and return course data."""
    try:
        # Implementation
        pass
    except Exception as e:
        logger.error(f"Error scanning courses: {e}")
        return []
```

#### CSS
- **BEM**: Usa metodología Block Element Modifier
- **Variables CSS**: Define variables para colores y espaciado
- **Responsive**: Diseño mobile-first

```css
/* ✅ Buen ejemplo */
.video-player {
    &__controls {
        &__play-button {
            /* styles */
        }
    }
    
    &--fullscreen {
        /* fullscreen styles */
    }
}
```

### Testing

#### Tests Unitarios (cuando se implementen)
```javascript
// Ejemplo de test
describe('VideoPlayer', () => {
    it('should play video when play button is clicked', () => {
        // Test implementation
    });
});
```

#### Tests Manuales
- Prueba en múltiples navegadores
- Verifica responsividad en diferentes tamaños
- Testea con diferentes tamaños de video

## 🎯 Áreas de Contribución Prioritarias

### 🚨 Issues Críticos (Alta Prioridad)
1. **Fix CATEGORIES undefined** en `server.py:248`
2. **Path sanitization** para prevenir directory traversal
3. **Memory optimization** en streaming de video
4. **Race condition fix** en sincronización de progreso

### 🚀 Mejoras (Media Prioridad)
1. **Migración completa** a `app_v2.js`
2. **PWA implementation** para modo offline
3. **Enhanced search** con filtros avanzados
4. **Mobile optimization** y gestos táctiles

### 🎨 Características (Baja Prioridad)
1. **Theme system** con múltiples temas
2. **Analytics dashboard** para estadísticas de aprendizaje
3. **Social features** para compartir progreso
4. **Integration** con API oficial de Platzi

## 📋 Proceso de Review

### Code Review Checklist

#### Funcionalidad
- [ ] El código funciona como se espera
- [ ] No introduce regresiones
- [ ] Maneja casos de error apropiadamente
- [ ] Es compatible con navegadores objetivo

#### Calidad de Código
- [ ] Sigue las convenciones de estilo
- [ ] Está bien documentado
- [ ] No contiene código duplicado
- [ ] Es mantenible y extensible

#### Performance
- [ ] No impacta negativamente el rendimiento
- [ ] Usa eficientemente los recursos
- [ ] No introduce memory leaks
- [ ] Optimiza para el caso de uso común

#### Seguridad
- [ ] No introduce vulnerabilidades
- [ ] Valida inputs apropiadamente
- [ ] Maneja datos sensibles correctamente
- [ ] Sigue principios de seguridad

## 🏆 Reconocimiento

### Contribuidores
Todas las contribuciones son reconocidas:

- **GitHub Contributors**: Lista automática en el repo
- **CHANGELOG**: Menciones en releases
- **README**: Sección de agradecimientos

### Tipos de Contribución
- **Código**: Features, fixes, refactorización
- **Documentación**: Mejoras en docs, tutoriales
- **Testing**: Reporte de bugs, test cases
- **Diseño**: UI/UX mejoras, iconos, temas
- **Traducción**: Localización a otros idiomas

## 📞 Contacto y Soporte

### Para Contribuidores
- **Discusiones**: [GitHub Discussions](https://github.com/tu-usuario/platzi-viewer/discussions)
- **Issues**: [GitHub Issues](https://github.com/tu-usuario/platzi-viewer/issues)
- **Email**: dev@platzi-viewer.com

### Comunidad
- **Discord**: [Servidor de Discord](https://discord.gg/platzi-viewer)
- **Twitter**: [@platzi_viewer](https://twitter.com/platzi_viewer)
- **Blog**: [blog.platzi-viewer.com](https://blog.platzi-viewer.com)

## 📄 Licencia de Contribuciones

Al contribuir a este proyecto, aceptas que tus contribuciones estarán bajo la misma licencia que el proyecto (MIT).

---

## 🎉 ¡Gracias por Contribuir!

Tu ayuda hace que Platzi Viewer sea mejor para toda la comunidad. Cada contribución, por pequeña que sea, es valiosa y apreciada.

**Recuerda:** No hay contribuciones demasiado pequeñas. Desde correcciones de typos hasta características complejas, todo ayuda a mejorar el proyecto.
