"""
Fix PlatziRoutes.md: Add Drive courses that are missing from the MD.
This handles:
1. English Academy courses (core levels A1-C1, práctico, skills, audio)
2. Non-English courses that exist in Drive but are missing from MD
3. Name mismatches where Drive folder differs from MD name
"""

import re

INPUT = "PlatziRoutes.md"
OUTPUT = "PlatziRoutes.md"

with open(INPUT, "r", encoding="utf-8") as f:
    content = f.read()

# ======================================================================
# SECTION 1: Fix English Academy (add missing courses to existing routes)
# ======================================================================

# --- C1 courses ---
old_c1 = """### [Inglés Avanzado C1](https://platzi.com/ruta/advanced-core/)

- [Curso Gratis de Estrategias para Aprender Inglés en Línea](https://platzi.com/cursos/estrategias-ingles/)"""

new_c1 = """### [Inglés Avanzado C1](https://platzi.com/ruta/advanced-core/)

- [Curso Gratis de Estrategias para Aprender Inglés en Línea](https://platzi.com/cursos/estrategias-ingles/)
- [Curso de Inglés Avanzado C1: Argumentos y Discusiones](https://platzi.com/cursos/c1-argumentos/)
- [Curso de Inglés Avanzado C1: Comunicación Persuasiva y Efectiva](https://platzi.com/cursos/c1-comunicacion/)
- [Curso de Inglés Avanzado C1: Lenguaje Coloquial y Habitual](https://platzi.com/cursos/c1-lenguaje-coloquial/)
- [Curso de Inglés Avanzado C1: Presentaciones y Expresión Oral](https://platzi.com/cursos/c1-presentaciones/)
- [Curso de Inglés Avanzado C1: Recursos Conversacionales y Lingüísticos](https://platzi.com/cursos/c1-recursos/)"""

content = content.replace(old_c1, new_c1)

# --- A1 courses ---
old_a1 = """- [Curso de Inglés Básico A1: Verbos Comunes](https://platzi.com/cursos/verbos-comunes/)
### [Inglés Básico A2]"""

new_a1 = """- [Curso de Inglés Básico A1: Verbos Comunes](https://platzi.com/cursos/verbos-comunes/)
- [Curso de Inglés Básico A1: Fechas, Horas y Expresiones Simples](https://platzi.com/cursos/a1-fechas-horas/)
- [Curso de Inglés Básico A1 para Principiantes](https://platzi.com/cursos/a1-principiantes/)
### [Inglés Básico A2]"""

content = content.replace(old_a1, new_a1)

# --- A2 courses ---
old_a2 = """### [Inglés Básico A2](https://platzi.com/ruta/beginner-core2/)

- [Curso Gratis de Estrategias para Aprender Inglés en Línea](https://platzi.com/cursos/estrategias-ingles/)
### [Inglés Intermedio Alto B2]"""

new_a2 = """### [Inglés Básico A2](https://platzi.com/ruta/beginner-core2/)

- [Curso Gratis de Estrategias para Aprender Inglés en Línea](https://platzi.com/cursos/estrategias-ingles/)
- [Curso de Inglés Básico A2: Conectores y Artículos](https://platzi.com/cursos/a2-conectores/)
- [Curso de Inglés Básico A2: Conjunciones y Verbos](https://platzi.com/cursos/a2-conjunciones/)
- [Curso de Inglés Básico A2: Cuantificadores y Superlativos](https://platzi.com/cursos/a2-cuantificadores/)
- [Curso de Inglés Básico A2: Descripciones y Comparaciones](https://platzi.com/cursos/a2-descripciones/)
- [Curso de Inglés Básico A2: Experiencias Pasadas y Planes](https://platzi.com/cursos/a2-experiencias/)
- [Curso de Inglés Básico A2: Infinitivos y Presente Continuo](https://platzi.com/cursos/a2-infinitivos/)
- [Curso de Inglés Básico A2: Preguntas y Respuestas Comunes](https://platzi.com/cursos/a2-preguntas/)
- [Curso de Inglés Básico A2: Sustantivos e Intenciones Futuras](https://platzi.com/cursos/a2-sustantivos/)
### [Inglés Intermedio Alto B2]"""

content = content.replace(old_a2, new_a2)

# --- B2 courses ---
old_b2 = """### [Inglés Intermedio Alto B2](https://platzi.com/ruta/intermediate-core2/)

- [Curso Gratis de Estrategias para Aprender Inglés en Línea](https://platzi.com/cursos/estrategias-ingles/)
### [Inglés Intermedio B1]"""

new_b2 = """### [Inglés Intermedio Alto B2](https://platzi.com/ruta/intermediate-core2/)

- [Curso Gratis de Estrategias para Aprender Inglés en Línea](https://platzi.com/cursos/estrategias-ingles/)
- [Curso de Inglés Intermedio Alto B2: Comentarios y Opiniones](https://platzi.com/cursos/b2-comentarios/)
- [Curso de Inglés Intermedio Alto B2: Discurso Indirecto y Condicionales](https://platzi.com/cursos/b2-discurso/)
- [Curso de Inglés Intermedio Alto B2: Hábitos y Aproximaciones](https://platzi.com/cursos/b2-habitos/)
- [Curso de Inglés Intermedio Alto B2: Pasado Perfecto y Frases Adverbiales](https://platzi.com/cursos/b2-pasado-perfecto/)
- [Curso de Inglés Intermedio Alto B2: Suposiciones e Instrucciones](https://platzi.com/cursos/b2-suposiciones/)
### [Inglés Intermedio B1]"""

content = content.replace(old_b2, new_b2)

# --- B1 courses ---
old_b1 = """### [Inglés Intermedio B1](https://platzi.com/ruta/intermediate-core/)

- [Curso Gratis de Estrategias para Aprender Inglés en Línea](https://platzi.com/cursos/estrategias-ingles/)
### [Inglés para Propósitos Específicos]"""

new_b1 = """### [Inglés Intermedio B1](https://platzi.com/ruta/intermediate-core/)

- [Curso Gratis de Estrategias para Aprender Inglés en Línea](https://platzi.com/cursos/estrategias-ingles/)
- [Curso de Inglés Intermedio B1: Adjetivos y Preguntas Indirectas](https://platzi.com/cursos/b1-adjetivos/)
- [Curso de Inglés Intermedio B1: Comparativos y Planes Futuros](https://platzi.com/cursos/b1-comparativos/)
- [Curso de Inglés Intermedio B1: Descripción de Eventos y Preferencias](https://platzi.com/cursos/b1-descripcion/)
- [Curso de Inglés Intermedio B1: Expresiones de Tiempo y Cantidad](https://platzi.com/cursos/b1-expresiones/)
- [Curso de Inglés Intermedio B1: Palabras Interrogativas y Propósitos](https://platzi.com/cursos/b1-palabras/)
- [Curso de Inglés Intermedio B1: Preguntas Negativas y Recomendaciones](https://platzi.com/cursos/b1-preguntas-negativas/)
- [Curso de Inglés Intermedio B1: Preguntas de Confirmación y Posibilidades](https://platzi.com/cursos/b1-preguntas-confirmacion/)
- [Curso de Inglés Intermedio B1: Presente Perfecto y Preposiciones](https://platzi.com/cursos/b1-presente-perfecto/)
- [Curso de Inglés Intermedio B1: Primer Condicional y Pasado Continuo](https://platzi.com/cursos/b1-primer-condicional/)
- [Curso de Inglés Intermedio B1: Pronombres y Cláusulas Relativas](https://platzi.com/cursos/b1-pronombres/)
- [Curso de Inglés Intermedio B1: Solicitudes y Pronombres Reflexivos](https://platzi.com/cursos/b1-solicitudes/)
- [Curso de Inglés Intermedio B1: Voz Pasiva y Consejos](https://platzi.com/cursos/b1-voz-pasiva/)
### [Inglés para Propósitos Específicos]"""

content = content.replace(old_b1, new_b1)

# --- Add new English routes for Práctico, Skills, Audio ---
# Insert before "## School: Marketing Digital"

english_new_routes = """
### [Inglés Práctico y Conversacional](https://platzi.com/ruta/ingles-practico/)

- [Curso de Inglés Práctico y Conversacional](https://platzi.com/cursos/ingles-practico/)
- [Curso de Inglés Práctico con ChatGPT](https://platzi.com/cursos/ingles-chatgpt/)
- [Curso de Inglés Práctico para Compras](https://platzi.com/cursos/ingles-compras/)
- [Curso de Inglés Práctico para Consultas Médicas](https://platzi.com/cursos/ingles-consultas-medicas/)
- [Curso de Inglés Práctico para Conversaciones de Trabajo](https://platzi.com/cursos/ingles-conversaciones-trabajo/)
- [Curso de Inglés Práctico para Viajes de Negocios](https://platzi.com/cursos/ingles-viajes-negocios/)
- [Curso de Inglés Práctico para Viajes de Turismo](https://platzi.com/cursos/ingles-viajes-turismo/)
- [Curso de Inglés Práctico sobre Elementos de Trabajo](https://platzi.com/cursos/ingles-elementos-trabajo/)
- [Curso de Inglés Práctico sobre Nutrición y Fitness](https://platzi.com/cursos/ingles-nutricion/)
- [Curso de Inglés Práctico sobre Vocabulario de Cocina](https://platzi.com/cursos/ingles-cocina/)
- [Curso de Inglés Práctico sobre Vocabulario de Música y Arte](https://platzi.com/cursos/ingles-musica-arte/)
- [Curso de Inglés Práctico sobre las Partes del Cuerpo](https://platzi.com/cursos/ingles-partes-cuerpo/)
- [Curso de Inglés Práctico sobre los Miembros de la Familia](https://platzi.com/cursos/ingles-familia/)
### [Habilidades de Escritura, Pronunciación y Vocabulario en Inglés](https://platzi.com/ruta/habilidades-ingles/)

- [Curso Básico de Escritura en Inglés](https://platzi.com/cursos/escritura-ingles-basico/)
- [Curso Intermedio de Escritura en Inglés](https://platzi.com/cursos/escritura-ingles-intermedio/)
- [Curso Avanzado de Escritura en Inglés](https://platzi.com/cursos/escritura-ingles-avanzado/)
- [Curso Básico de Pronunciación en Inglés](https://platzi.com/cursos/pronunciacion-ingles-basico/)
- [Curso Intermedio de Pronunciación en Inglés](https://platzi.com/cursos/pronunciacion-ingles-intermedio/)
- [Curso Avanzado de Pronunciación en Inglés](https://platzi.com/cursos/pronunciacion-ingles-avanzado/)
- [Curso Básico de Vocabulario y Expresiones en Inglés](https://platzi.com/cursos/vocabulario-ingles-basico/)
- [Curso Intermedio de Vocabulario y Expresiones en Inglés](https://platzi.com/cursos/vocabulario-ingles-intermedio/)
- [Curso Avanzado de Vocabulario y Expresiones en Inglés](https://platzi.com/cursos/vocabulario-ingles-avanzado/)
- [Curso de Ortografía y Puntuación en Inglés](https://platzi.com/cursos/ortografia-ingles/)
- [Curso de Phrasal Verbs Comunes en Inglés](https://platzi.com/cursos/phrasal-verbs/)
- [Curso de Conectores y Contracciones Informales en Inglés](https://platzi.com/cursos/conectores-ingles/)
- [Curso de Construcción de Oraciones en Inglés](https://platzi.com/cursos/oraciones-ingles/)
- [Curso de Vocabulario en Inglés para el Trabajo](https://platzi.com/cursos/vocabulario-trabajo/)
### [Inglés para Carreras Profesionales](https://platzi.com/ruta/ingles-profesional/)

- [Curso de Inglés para Programadores](https://platzi.com/cursos/ingles-programadores/)
- [Curso de Inglés para Marketing](https://platzi.com/cursos/ingles-marketing/)
- [Curso de Inglés para Ciberseguridad](https://platzi.com/cursos/ingles-ciberseguridad/)
- [Curso de Inglés para Startups](https://platzi.com/cursos/ingles-startups/)
- [Curso de Inglés para Ventas](https://platzi.com/cursos/ingles-ventas/)
- [Curso de Inglés para Servicio al Cliente](https://platzi.com/cursos/ingles-servicio-cliente/)
- [Curso de Inglés para Entrevistas de Trabajo](https://platzi.com/cursos/ingles-entrevistas/)
- [Curso de Inglés para el Uso de Inteligencia Artificial](https://platzi.com/cursos/ingles-ia/)
- [Curso de Inglés de Negocios para Managers](https://platzi.com/cursos/ingles-negocios/)
- [Curso de Expresiones Idiomáticas de Negocios en Inglés](https://platzi.com/cursos/expresiones-negocios-ingles/)
- [Curso en Inglés para el Desarrollo Profesional](https://platzi.com/cursos/ingles-desarrollo-profesional/)
### [Audio Cursos e Historias en Inglés](https://platzi.com/ruta/audio-ingles/)

- [Audio Curso de Inglés para Viajes](https://platzi.com/cursos/audio-ingles-viajes/)
- [Audio Curso de Inglés para el Uso de Preposiciones](https://platzi.com/cursos/audio-ingles-preposiciones/)
- [Audio Historia en Inglés: Atrapados en la Tecnología](https://platzi.com/cursos/audio-historia-tecnologia/)
- [Audio Historia en Inglés: Misterios sin Resolver](https://platzi.com/cursos/audio-historia-misterios/)
- [Audio Historia en Inglés: Origen del idioma](https://platzi.com/cursos/audio-historia-origen/)
- [Audio Historia en Inglés: Una Aventura en la Ciudad](https://platzi.com/cursos/audio-historia-aventura/)
"""

# Also add IELTS and TOEFL to "Inglés para Propósitos Específicos"
old_propositos = """### [Inglés para Propósitos Específicos](https://platzi.com/ruta/complementary/)

- [Curso de Preparación para el Examen TOEFL](https://platzi.com/cursos/toefl/)
## School: Marketing Digital"""

new_propositos = """### [Inglés para Propósitos Específicos](https://platzi.com/ruta/complementary/)

- [Curso de Preparación para el Examen TOEFL](https://platzi.com/cursos/toefl/)
- [Curso de Preparación para TOEFL](https://platzi.com/cursos/preparacion-toefl/)
- [Curso de Preparación para IELTS](https://platzi.com/cursos/preparacion-ielts/)
- [Curso de Inglés Práctico con ChatGPT](https://platzi.com/cursos/ingles-chatgpt/)
""" + english_new_routes + """## School: Marketing Digital"""

content = content.replace(old_propositos, new_propositos)


# ======================================================================
# SECTION 2: Add missing non-English courses to appropriate routes
# ======================================================================

# These are courses in Drive that don't appear in any MD route
# We need to add them to the most appropriate existing route

# --- "Curso de Responsive Design: Maquetación Mobile First" to Diseño y Desarrollo Frontend ---
content = content.replace(
    '- [Curso de Materialize](https://platzi.com/cursos/materialize/)',
    '- [Curso de Materialize](https://platzi.com/cursos/materialize/)\n- [Curso de Responsive Design: Maquetación Mobile First](https://platzi.com/cursos/responsive-design/)'
)

# --- "Curso Gratis de Lovable para Crear Páginas Web sin Programar" to Fundamentos Web ---
content = content.replace(
    '- [Curso de Git y GitHub](https://platzi.com/cursos/gitgithub/)\n### [Seguridad Web',
    '- [Curso de Git y GitHub](https://platzi.com/cursos/gitgithub/)\n- [Curso Gratis de Lovable para Crear Páginas Web sin Programar](https://platzi.com/cursos/lovable/)\n### [Seguridad Web'
)

# --- "Curso Práctico de Backend con Node.js" to Backend Node.js ---
content = content.replace(
    '- [Curso de Node.js Avanzado](https://platzi.com/cursos/nodejs-avanzado/)',
    '- [Curso de Node.js Avanzado](https://platzi.com/cursos/nodejs-avanzado/)\n- [Curso Práctico de Backend con Node.js](https://platzi.com/cursos/practico-backend-nodejs/)'
)

# --- "Curso de COBOL desde Cero" + "Curso Práctico de COBOL" to Programación school ---
# Find an appropriate place in Programación school
content = content.replace(
    '- [Curso de Rust básico](https://platzi.com/cursos/rust/)',
    '- [Curso de Rust básico](https://platzi.com/cursos/rust/)\n- [Curso de COBOL desde Cero](https://platzi.com/cursos/cobol/)\n- [Curso Práctico de COBOL](https://platzi.com/cursos/cobol-practico/)'
)

# --- "Curso de Deep Learning con TensorFlow y Keras" to ML/Deep Learning route ---
content = content.replace(
    '- [Curso Profesional de Redes Neuronales con TensorFlow](https://platzi.com/cursos/redes-neuronales-tensorflow/)',
    '- [Curso Profesional de Redes Neuronales con TensorFlow](https://platzi.com/cursos/redes-neuronales-tensorflow/)\n- [Curso de Deep Learning con TensorFlow y Keras](https://platzi.com/cursos/deep-learning-tensorflow-keras/)'
)

# --- "Curso de AI para SEO" to IA Aplicada al Marketing ---
content = content.replace(
    '- [Curso de Inteligencia Artificial para SEO](https://platzi.com/cursos/ia-seo/)',
    '- [Curso de Inteligencia Artificial para SEO](https://platzi.com/cursos/ia-seo/)\n- [Curso de AI para SEO](https://platzi.com/cursos/ai-seo/)'
)

# --- "Curso de Growth Marketing con Inteligencia Artificial" to IA Marketing ---
content = content.replace(
    '- [Curso de Inteligencia Artificial para Servicio al Cliente](https://platzi.com/cursos/ai-servicio-cliente/)',
    '- [Curso de Inteligencia Artificial para Servicio al Cliente](https://platzi.com/cursos/ai-servicio-cliente/)\n- [Curso de Growth Marketing con Inteligencia Artificial](https://platzi.com/cursos/growth-marketing-ia/)'
)

# --- "Curso de Python Profesional: Arquitectura de Proyectos, Entornos y PyPI" to Backend Python ---
content = content.replace(
    '- [Curso de Despliegue de Aplicaciones Python en la Nube](https://platzi.com/cursos/deploying-python/)\n- [Curso de Supabase]',
    '- [Curso de Despliegue de Aplicaciones Python en la Nube](https://platzi.com/cursos/deploying-python/)\n- [Curso de Python Profesional: Arquitectura de Proyectos, Entornos y PyPI](https://platzi.com/cursos/python-profesional/)\n- [Curso de Supabase]'
)

# --- "Curso de Excel Básico: Tablas y Fórmulas para la Gestión de Datos" near Excel Básico ---
content = content.replace(
    '- [Curso de Excel Básico](https://platzi.com/cursos/excel-basico/)',
    '- [Curso de Excel Básico](https://platzi.com/cursos/excel-basico/)\n- [Curso de Excel Básico: Tablas y Fórmulas para la Gestión de Datos](https://platzi.com/cursos/excel-basico-tablas/)'
)

# --- "Curso de Introducción a Excel para Principiantes: Fundamentos" near Excel ---
content = content.replace(
    '- [Curso de Excel Intermedio](https://platzi.com/cursos/excel-intermedio/)',
    '- [Curso de Introducción a Excel para Principiantes: Fundamentos](https://platzi.com/cursos/excel-principiantes/)\n- [Curso de Excel Intermedio](https://platzi.com/cursos/excel-intermedio/)'
)

# --- "Curso de Single Page Applications en Laravel con Inertia y Vue" to Backend PHP ---
content = content.replace(
    '- [Curso de Desarrollo en Laravel con Test Driven Development](https://platzi.com/cursos/laravel-tdd/)',
    '- [Curso de Desarrollo en Laravel con Test Driven Development](https://platzi.com/cursos/laravel-tdd/)\n- [Curso de Single Page Applications en Laravel con Inertia y Vue](https://platzi.com/cursos/laravel-inertia-vue/)'
)

# --- "Curso de Android: Modo Offline" to Desarrollo Móvil Android route ---
content = content.replace(
    '- [Curso de Android: Integración de APIs nativas](https://platzi.com/cursos/android-apis-nativas/)',
    '- [Curso de Android: Integración de APIs nativas](https://platzi.com/cursos/android-apis-nativas/)\n- [Curso de Android: Modo Offline](https://platzi.com/cursos/android-offline/)'
)

# --- "Curso de Glosario de términos" -> this is "Curso de Glosario de términos" which maps to the Audiocurso Glosario ---
# It's likely the same as "Audiocurso Glosario de Términos de Diseño" or a separate one
# Add to Design school
content = content.replace(
    '- [Audiocurso Glosario de Términos de Diseño](https://platzi.com/cursos/glosario-ux/)',
    '- [Audiocurso Glosario de Términos de Diseño](https://platzi.com/cursos/glosario-ux/)\n- [Curso de Glosario de términos](https://platzi.com/cursos/glosario-terminos/)'
)

# --- "Curso de Fundamentos de React Native" to React Native route ---
content = content.replace(
    '- [Curso de Fundamentos de React Native](https://platzi.com/cursos/fundamentos-react-native/)',
    '- [Curso de Fundamentos de React Native](https://platzi.com/cursos/fundamentos-react-native/)\n- [Curso de Fundamentos de React Native (nuevo sin descargar)](https://platzi.com/cursos/fundamentos-react-native-nuevo/)'
)

# --- "Curso de TypeScript" (base course, not the advanced ones) ---
# Add to JavaScript Frontend route before the TypeScript advanced courses
content = content.replace(
    '- [Curso de TypeScript: Tipos Avanzados y Funciones](https://platzi.com/cursos/typescript-tipos-avanzados/)',
    '- [Curso de TypeScript](https://platzi.com/cursos/typescript/)\n- [Curso de TypeScript: Tipos Avanzados y Funciones](https://platzi.com/cursos/typescript-tipos-avanzados/)'
)

# --- "Curso de Symfony" (different from "Curso Práctico de Symfony" and "Curso de Symfony Framework") ---
content = content.replace(
    '- [Curso de Symfony Framework](https://platzi.com/cursos/symfony-framework/)',
    '- [Curso de Symfony](https://platzi.com/cursos/symfony/)\n- [Curso de Symfony Framework](https://platzi.com/cursos/symfony-framework/)'
)

# --- "Curso para Desarrollar tu Creatividad" (different from "Curso para Desarrollar tu Creatividad: Técnicas y Hábitos") ---
content = content.replace(
    '- [Curso para Desarrollar tu Creatividad: Técnicas y Hábitos](https://platzi.com/cursos/tecnicas-creatividad-2020/)',
    '- [Curso para Desarrollar tu Creatividad](https://platzi.com/cursos/creatividad/)\n- [Curso para Desarrollar tu Creatividad: Técnicas y Hábitos](https://platzi.com/cursos/tecnicas-creatividad-2020/)'
)

# --- "Curso de Estructuras de Datos" (without "con JavaScript" suffix) ---
content = content.replace(
    '- [Curso de Estructuras de Datos con JavaScript](https://platzi.com/cursos/estructuras-datos/)',
    '- [Curso de Estructuras de Datos](https://platzi.com/cursos/estructuras-datos-general/)\n- [Curso de Estructuras de Datos con JavaScript](https://platzi.com/cursos/estructuras-datos/)'
)

# ======================================================================
# WRITE OUTPUT
# ======================================================================

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ PlatziRoutes.md updated successfully!")

# Verify
import re as re2
course_pat = re2.compile(r'^- \[(.+?)\]\((.+?)\)\s*$', re2.MULTILINE)
all_courses = course_pat.findall(content)
unique = set(m[0] for m in all_courses)
print(f"Total course entries: {len(all_courses)}")
print(f"Unique courses: {len(unique)}")
