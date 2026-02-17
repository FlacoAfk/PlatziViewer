// Datos de los cursos de Platzi - Con rutas de archivos reales
// Estructura: Categorías → Rutas → Cursos → Módulos → Clases

const COURSES_BASE_PATH = 'H:/Mi unidad/Cursos Platzi';

const coursesData = {
    categories: [
        {
            id: "desarrollo",
            name: "Desarrollo",
            icon: "💻",
            description: "Programación y desarrollo de software",
            folderName: "Desarrollo",
            routes: [
                {
                    id: "prog-python",
                    name: "Programación con Python",
                    folderName: "Programación con Python",
                    courses: [
                        {
                            name: "1. Curso de Fundamentos de Python",
                            folderName: "1. Curso de Fundamentos de Python",
                            modules: [
                                {
                                    name: "1. Primeros Pasos con Python",
                                    folderName: "1. Primeros Pasos con Python",
                                    classes: [
                                        {
                                            name: "Fundamentos de Python variables",
                                            fileBase: "1. Fundamentos de Python variables boo",
                                            hasVideo: true,
                                            hasSummary: true,
                                            hasReading: true,
                                            readingFile: "1. Lecturas recomendadas.txt"
                                        },
                                        {
                                            name: "Instalación de Python VS Code y Git",
                                            fileBase: "2. Instalación de Python VS Code y Git",
                                            hasVideo: true,
                                            hasSummary: true,
                                            hasReading: true,
                                            readingFile: "2. Lecturas recomendadas.txt"
                                        },
                                        {
                                            name: "Configuración de variables de entorno",
                                            fileBase: "3. Configuración de variables de entor",
                                            hasVideo: true,
                                            hasSummary: true,
                                            hasReading: false
                                        },
                                        {
                                            name: "Comandos básicos de Python en terminal",
                                            fileBase: "4. Comandos básicos de Python en la te",
                                            hasVideo: true,
                                            hasSummary: true,
                                            hasReading: false
                                        },
                                        {
                                            name: "Sintaxis e indentación básica en Python",
                                            fileBase: "5. Sintaxis e indentación básica en Py",
                                            hasVideo: true,
                                            hasSummary: true,
                                            hasReading: true,
                                            readingFile: "5. Lecturas recomendadas.txt"
                                        },
                                        {
                                            name: "Comentarios en Python líneas simples",
                                            fileBase: "6. Comentarios en Python líneas simple",
                                            hasVideo: true,
                                            hasSummary: true,
                                            hasReading: true,
                                            readingFile: "6. Lecturas recomendadas.txt"
                                        },
                                        {
                                            name: "Variables en Python asignación",
                                            fileBase: "7. Variables en Python asignación nome",
                                            hasVideo: true,
                                            hasSummary: true,
                                            hasReading: true,
                                            readingFile: "7. Lecturas recomendadas.txt"
                                        },
                                        {
                                            name: "Asignación múltiple de variables",
                                            fileBase: "8. Asignación múltiple de variables en",
                                            hasVideo: true,
                                            hasSummary: true,
                                            hasReading: true,
                                            readingFile: "8. Lecturas recomendadas.txt"
                                        },
                                        {
                                            name: "Tipos de datos en Python",
                                            fileBase: "9. Tipos de datos en Python strings nú",
                                            hasVideo: true,
                                            hasSummary: true,
                                            hasReading: true,
                                            readingFile: "9. Lecturas recomendadas.txt"
                                        },
                                        {
                                            name: "Manipulación y conversión de tipos",
                                            fileBase: "10. Manipulación y conversión de tipos",
                                            hasVideo: true,
                                            hasSummary: true,
                                            hasReading: true,
                                            readingFile: "10. Lecturas recomendadas.txt"
                                        },
                                        {
                                            name: "Manejo de comillas múltiples líneas",
                                            fileBase: "11. Manejo de comillas múltiples líneas",
                                            hasVideo: true,
                                            hasSummary: true,
                                            hasReading: true,
                                            readingFile: "11. Lecturas recomendadas.txt"
                                        },
                                        {
                                            name: "Slicing replace y split",
                                            fileBase: "12. Slicing replace y split para manipu",
                                            hasVideo: true,
                                            hasSummary: true,
                                            hasReading: true,
                                            readingFile: "12. Lecturas recomendadas.txt"
                                        },
                                        {
                                            name: "Booleanos en Python True False",
                                            fileBase: "13. Booleanos en Python True False y ca",
                                            hasVideo: true,
                                            hasSummary: true,
                                            hasReading: true,
                                            readingFile: "13. Lecturas recomendadas.txt"
                                        },
                                        {
                                            name: "Tipo de dato None en Python",
                                            fileBase: "14. Tipo de dato None en Python",
                                            hasVideo: true,
                                            hasSummary: true,
                                            hasReading: true,
                                            readingFile: "14. Lecturas recomendadas.txt"
                                        }
                                    ]
                                },
                                { name: "2. Lógica de Programación y Control de Flujo", folderName: "2. Lógica de Programación y Control de", classes: 10 },
                                { name: "3. Estructuras de Datos Fundamentales", folderName: "3. Estructuras de Datos Fundamentales", classes: 6 },
                                { name: "4. Modularización del Código", folderName: "4. Modularización del Código", classes: 5 },
                                { name: "5. Manejo de Errores y Archivos", folderName: "5. Manejo de Errores y Archivos", classes: 4 },
                                { name: "6. Trabajo Práctico Final", folderName: "6. Trabajo Práctico Final", classes: 4 }
                            ]
                        },
                        { name: "2. Curso de Python Entornos virtuales", folderName: "2. Curso de Python Entornos virtu", modules: 5 },
                        { name: "3. Curso de Python Orientado a Objetos", folderName: "3. Curso de Python Orientado a Ob", modules: 4 },
                        { name: "4. Curso de Python Comprehensions", folderName: "4. Curso de Python Comprehensions", modules: 6 },
                        { name: "5. Curso de Complejidad Algorítmica", folderName: "5. Curso de Complejidad Algorítmi", modules: 4 },
                        { name: "6. Curso de Python PIP y Entornos", folderName: "6. Curso de Python PIP y Entornos", modules: 3 },
                        { name: "7. Curso de Python Profesional", folderName: "7. Curso de Python Profesional Ar", modules: 4 },
                        { name: "8. Curso Práctico de Python Creación", folderName: "8. Curso Práctico de Python Creac", modules: 6 },
                        { name: "9. Curso de Patrones de Diseño", folderName: "9. Curso de Patrones de Diseño y", modules: 5 },
                        { name: "10. Curso de Estadística Computacional", folderName: "10. Curso de Estadística Computaci", modules: 5 }
                    ]
                },
                {
                    id: "frontend-react",
                    name: "Desarrollo Frontend con Reactjs",
                    folderName: "Desarrollo Frontend con Reactjs",
                    courses: [
                        { name: "Curso Profesional de Reactjs y Redux", modules: 8 },
                        { name: "Curso de React Avanzado", modules: 6 },
                        { name: "Curso de Reactjs con TypeScript", modules: 5 }
                    ]
                },
                {
                    id: "frontend-vue",
                    name: "Desarrollo Frontend con Vuejs",
                    folderName: "Desarrollo Frontend con Vuejs",
                    courses: [
                        { name: "Curso de Vuejs Componentes y Composition API", modules: 5 },
                        { name: "Curso de Vuejs Navegación con Vue Router", modules: 4 },
                        { name: "Curso de Vuejs Manejo del Estado con Pinia", modules: 4 }
                    ]
                },
                {
                    id: "fundamentos-web",
                    name: "Fundamentos del Desarrollo Web Profesional",
                    folderName: "Fundamentos del Desarrollo Web Profesional",
                    courses: [
                        { name: "Curso de CSS", modules: 8 },
                        { name: "Curso de Git y GitHub", modules: 7 },
                        { name: "Curso Gratis de Programación Básica", modules: 10 }
                    ]
                }
            ]
        },
        {
            id: "ia",
            name: "IA y Hacking",
            icon: "🤖",
            description: "Inteligencia artificial, data science y ciberseguridad",
            folderName: "Ia y hacking",
            routes: [
                {
                    id: "claude-code",
                    name: "Curso de Claude Code",
                    folderName: "Curso de Claude Code",
                    isCourse: true,
                    modules: [
                        {
                            name: "Módulo 1: Discovery/Análisis/Planning",
                            folderName: "1. Módulo 1 DiscoveryAnálisisPlanning",
                            classes: [
                                {
                                    name: "Desarrollo conversacional con Claude",
                                    fileBase: "1. Desarrollo conversacional con Claud",
                                    hasVideo: true,
                                    hasSummary: true,
                                    hasReading: true,
                                    readingFile: "1. Lecturas recomendadas.txt"
                                },
                                {
                                    name: "Flujo profesional para desarrollar",
                                    fileBase: "2. Flujo profesional para desarrollar",
                                    hasVideo: true,
                                    hasSummary: true,
                                    hasReading: true,
                                    readingFile: "2. Lecturas recomendadas.txt"
                                },
                                {
                                    name: "Instalación y configuración básica",
                                    fileBase: "3. Instalación y configuración básica",
                                    hasVideo: true,
                                    hasSummary: true,
                                    hasReading: true,
                                    readingFile: "3. Lecturas recomendadas.txt"
                                },
                                {
                                    name: "Fundamentos de Claude Code contexto",
                                    fileBase: "4. Fundamentos de Claude Code contexto",
                                    hasVideo: true,
                                    hasSummary: true,
                                    hasReading: false
                                },
                                {
                                    name: "Análisis de arquitectura full stack",
                                    fileBase: "5. Análisis de arquitectura full stack",
                                    hasVideo: true,
                                    hasSummary: true,
                                    hasReading: true,
                                    readingFile: "5. Lecturas recomendadas.txt"
                                },
                                {
                                    name: "Análisis de impacto del feature",
                                    fileBase: "6. Análisis de impacto del feature de",
                                    hasVideo: true,
                                    hasSummary: true,
                                    hasReading: false
                                },
                                {
                                    name: "Creación de subagentes especializados",
                                    fileBase: "7. Creación de subagentes especializad",
                                    hasVideo: true,
                                    hasSummary: true,
                                    hasReading: false
                                },
                                {
                                    name: "Actualización de Claude Code",
                                    fileBase: "8. Actualización de Claude Code a vers",
                                    hasVideo: true,
                                    hasSummary: true,
                                    hasReading: true,
                                    readingFile: "8. Lecturas recomendadas.txt"
                                },
                                {
                                    name: "Creación de subagentes especializados II",
                                    fileBase: "9. Creación de subagentes especializad",
                                    hasVideo: true,
                                    hasSummary: true,
                                    hasReading: false
                                }
                            ]
                        },
                        {
                            name: "Módulo 2: Implementación Backend",
                            folderName: "2. Módulo 2 Implementación Backend",
                            classes: 5
                        },
                        {
                            name: "Módulo 3: Gestión de Contexto y Comandos",
                            folderName: "3. Módulo 3 Gestión de Contexto y Coma",
                            classes: 7
                        }
                    ]
                },
                {
                    id: "chatgpt",
                    name: "Curso de ChatGPT",
                    folderName: "Curso de ChatGPT",
                    isCourse: true,
                    modules: [
                        { name: "Fundamentos de ChatGPT", folderName: "1. Módulo 1 Fundamentos de ChatGPT", classes: 4 },
                        { name: "Uso efectivo de ChatGPT", folderName: "2. Módulo 2 Uso efectivo de ChatGPT", classes: 5 },
                        { name: "Investigación y Creación de Contenido", folderName: "3. Módulo 3 Investigación y Creación d", classes: 6 },
                        { name: "Análisis de Datos", folderName: "4. Módulo 4 Análisis de Datos", classes: 4 },
                        { name: "Automatización y Funciones", folderName: "5. Módulo 5 Automatización y Funciones", classes: 5 },
                        { name: "Proyecto Final", folderName: "6. Módulo 6 Proyecto Final Construye t", classes: 3 }
                    ]
                },
                {
                    id: "analisis-datos",
                    name: "Análisis y Visualización de Datos",
                    folderName: "Análisis y Visualización de Datos",
                    courses: [
                        { name: "Curso de Excel Básico", modules: 5 },
                        { name: "Curso de Excel Intermedio", modules: 5 },
                        { name: "Curso de Power BI", modules: 7 },
                        { name: "Curso de Tableau", modules: 5 }
                    ]
                },
                {
                    id: "data-engineer",
                    name: "Data Engineer",
                    folderName: "Data Engineer",
                    courses: [
                        { name: "Curso de Fundamentos de Ingeniería de Datos", modules: 6 },
                        { name: "Curso de PostgreSQL Aplicado a Ciencia de Datos", modules: 5 },
                        { name: "Curso de Fundamentos de Spark para Big Data", modules: 4 }
                    ]
                }
            ]
        },
        {
            id: "ingles",
            name: "Inglés",
            icon: "🌎",
            description: "Cursos de inglés desde básico hasta avanzado",
            folderName: "Ingles",
            routes: [
                {
                    id: "ingles-a1",
                    name: "Inglés Básico A1",
                    folderName: "1. Inglés Básico A1",
                    courses: [
                        { name: "Curso de Inglés Básico A1 para Principiantes", modules: 6 },
                        { name: "Curso de Inglés Básico A1 Verbo To Be", modules: 4 },
                        { name: "Curso de Inglés Básico A1 Presente Simple", modules: 5 }
                    ]
                },
                {
                    id: "ingles-a2",
                    name: "Inglés Básico A2",
                    folderName: "2. Inglés Básico A2",
                    courses: [
                        { name: "Curso de Inglés Básico A2 Preguntas y Respuestas", modules: 5 },
                        { name: "Curso de Inglés Básico A2 Conectores y Artículos", modules: 4 }
                    ]
                },
                {
                    id: "ingles-b1",
                    name: "Inglés Intermedio B1",
                    folderName: "3. Inglés Intermedio B1",
                    courses: [
                        { name: "Curso de Inglés Intermedio B1 Expresiones de Tiempo", modules: 4 },
                        { name: "Curso de Inglés Intermedio B1 Presente Perfecto", modules: 4 }
                    ]
                }
            ]
        },
        {
            id: "web",
            name: "Web Services y Testing",
            icon: "☁️",
            description: "Cloud computing, DevOps y ciberseguridad",
            folderName: "Web sevices y testing",
            routes: [
                {
                    id: "aws",
                    name: "Amazon Web Services",
                    folderName: "Amazon Web Services",
                    courses: [
                        { name: "Curso de Introducción a AWS", modules: 6 },
                        { name: "Curso Práctico de AWS Roles y Seguridad", modules: 4 },
                        { name: "Curso de Amazon DynamoDB", modules: 4 }
                    ]
                },
                {
                    id: "azure",
                    name: "Microsoft Azure",
                    folderName: "Microsoft Azure",
                    courses: [
                        { name: "Curso de Azure IaaS", modules: 5 },
                        { name: "Curso de Bases de Datos en Azure", modules: 4 }
                    ]
                }
            ]
        },
        {
            id: "complementarios",
            name: "Complementarios",
            icon: "🎨",
            description: "Diseño UX/UI, herramientas de diseño y más",
            folderName: "Complementarios",
            routes: [
                {
                    id: "fund-diseno-uxui",
                    name: "Fundamentos de Diseño UX/UI",
                    folderName: "Fundamentos de Diseño UXUI",
                    courses: [
                        {
                            name: "Curso de Photoshop",
                            folderName: "1. Curso de Photoshop",
                            modules: [
                                { name: "Introducción y entorno de trabajo", folderName: "1. Introducción y entorno de trabajo", classes: 5 },
                                { name: "Capas y Objetos Inteligentes", folderName: "2. Capas y Objetos Inteligentes", classes: 4 },
                                { name: "Estilos de capa selecciones y máscaras", folderName: "3. Estilos de capa selecciones y másca", classes: 5 },
                                { name: "Corrección Fotográfica", folderName: "4. Corrección Fotográfica", classes: 4 },
                                { name: "Herramientas de Creación Gráfica", folderName: "5. Herramientas de Creación Gráfica", classes: 4 }
                            ]
                        },
                        { name: "Curso de Sketch", modules: 6 },
                        { name: "Curso de Figma", folderName: "10. Curso de Figma", modules: 4 }
                    ]
                }
            ]
        }
    ]
};

// Calcular estadísticas
let totalRoutes = 0;
let totalCourses = 0;
let totalClasses = 0;

coursesData.categories.forEach(category => {
    category.routes.forEach(route => {
        if (route.isCourse) {
            totalCourses++;
            if (Array.isArray(route.modules)) {
                route.modules.forEach(mod => {
                    if (typeof mod.classes === 'number') {
                        totalClasses += mod.classes;
                    } else if (Array.isArray(mod.classes)) {
                        totalClasses += mod.classes.length;
                    }
                });
            }
        } else {
            totalRoutes++;
            if (route.courses) {
                totalCourses += route.courses.length;
                route.courses.forEach(course => {
                    if (typeof course.modules === 'number') {
                        totalClasses += course.modules * 5;
                    } else if (Array.isArray(course.modules)) {
                        course.modules.forEach(mod => {
                            if (typeof mod.classes === 'number') {
                                totalClasses += mod.classes;
                            } else if (Array.isArray(mod.classes)) {
                                totalClasses += mod.classes.length;
                            }
                        });
                    }
                });
            }
        }
    });
});

coursesData.stats = {
    totalCategories: coursesData.categories.length,
    totalRoutes: totalRoutes,
    totalCourses: totalCourses,
    totalClasses: totalClasses
};
