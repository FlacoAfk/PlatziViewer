"""
Fix PlatziRoutes.md: Add Drive courses that are missing from the MD programmatically.
Re-written to use programmatic state injection rather than fragile string replacements.
Provides strict validation and error handling if the markdown structure changes.
"""

import re
import sys

INPUT = "PlatziRoutes.md"
OUTPUT = "PlatziRoutes.md"


class MarkdownManager:
    def __init__(self, filename):
        self.filename = filename
        try:
            with open(filename, encoding="utf-8") as f:
                self.lines = f.read().splitlines()
        except FileNotFoundError:
            print(f"❌ Error: Archivo '{filename}' no encontrado.")
            sys.exit(1)

    def save(self, output_filename):
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines))
        print(f"✅ Archivo '{output_filename}' actualizado y guardado correctamente.")

    def get_route_line_index(self, route_name):
        """Finds the line index of a given route header."""
        # Note: searches for ### [Route Name] optionally with links
        pattern = re.compile(rf"^### \[\s*{re.escape(route_name)}\s*\]")
        for i, line in enumerate(self.lines):
            if pattern.search(line):
                return i
        return -1

    def append_courses_to_route(self, route_name, courses):
        """Appends a list of courses to the end of a specific route."""
        idx = self.get_route_line_index(route_name)
        if idx == -1:
            print(f"⚠️ Aviso: Route no encontrada: '{route_name}'. Revisa si 'PlatziRoutes.md' ha cambiado.")
            return

        # Find the last course of this route before the next route or school starts
        insert_idx = idx + 1
        last_course_idx = -1

        for i in range(idx + 1, len(self.lines)):
            line = self.lines[i].strip()
            if line.startswith("### ") or line.startswith("## "):
                break
            if line.startswith("- ["):
                last_course_idx = i

        if last_course_idx != -1:
            insert_idx = last_course_idx + 1
        else:
            # If route had no courses, insert after the route header spacing
            while insert_idx < len(self.lines) and self.lines[insert_idx].strip() == "":
                insert_idx += 1

        # Check if the courses are already there to avoid duplicates
        existing_courses = "\n".join(self.lines[idx:insert_idx])

        inserted_count = 0
        for course in courses:
            # Very basic duplicate check by course markdown syntax
            if course.strip() not in existing_courses:
                self.lines.insert(insert_idx, course)
                insert_idx += 1
                inserted_count += 1

        if inserted_count > 0:
            print(f" -> [{route_name}] {inserted_count} cursos nuevos añadidos.")

    def insert_courses_after_course(self, target_course, new_courses):
        """Inserts new courses immediately following a specific target course."""
        target_idx = -1
        for i, line in enumerate(self.lines):
            if line.strip() == target_course.strip():
                target_idx = i
                break

        if target_idx == -1:
            print(f"⚠️ Aviso: Target course no encontrado: '{target_course}'. No se pudo insertar nuevos cursos.")
            return

        insert_idx = target_idx + 1
        existing_context = "\n".join(self.lines[max(0, target_idx - 5) : min(len(self.lines), target_idx + 15)])

        inserted = 0
        for course in reversed(new_courses):
            if course.strip() not in existing_context:
                self.lines.insert(insert_idx, course)
                inserted += 1

        if inserted > 0:
            print(f" -> Insertados {inserted} cursos después de '{target_course.split(']')[0][3:]}]'.")

    def insert_block_before_marker(self, marker_text, block_text):
        """Inserts a full block of markdown just before a specific marker (like '## School: ...')"""
        target_idx = -1
        for i, line in enumerate(self.lines):
            if marker_text in line:
                target_idx = i
                break

        if target_idx == -1:
            print(f"⚠️ Aviso: Marker no encontrado: '{marker_text}'. No se pudo insertar el bloque.")
            return

        block_lines = block_text.strip("\n").split("\n")
        # Simple duplicate block check (checking just the first title line of the block)
        if block_lines and block_lines[0] not in "\n".join(self.lines):
            for i, line in enumerate(block_lines):
                self.lines.insert(target_idx + i, line)
            print(f" -> Bloque nuevo insertado antes de '{marker_text}'.")


def main():
    print("Iniciando inyección de cursos en PlatziRoutes.md...")
    md = MarkdownManager(INPUT)

    try:
        # ======================================================================
        # SECTION 1: Fix English Academy (add missing courses to existing routes)
        # ======================================================================

        md.append_courses_to_route(
            "Inglés Avanzado C1",
            [
                "- [Curso de Inglés Avanzado C1: Argumentos y Discusiones](https://platzi.com/cursos/c1-argumentos/)",
                "- [Curso de Inglés Avanzado C1: Comunicación Persuasiva y Efectiva](https://platzi.com/cursos/c1-comunicacion/)",
                "- [Curso de Inglés Avanzado C1: Lenguaje Coloquial y Habitual](https://platzi.com/cursos/c1-lenguaje-coloquial/)",
                "- [Curso de Inglés Avanzado C1: Presentaciones y Expresión Oral](https://platzi.com/cursos/c1-presentaciones/)",
                "- [Curso de Inglés Avanzado C1: Recursos Conversacionales y Lingüísticos](https://platzi.com/cursos/c1-recursos/)",
            ],
        )

        md.append_courses_to_route(
            "Inglés Básico A1",
            [
                "- [Curso de Inglés Básico A1: Fechas, Horas y Expresiones Simples](https://platzi.com/cursos/a1-fechas-horas/)",
                "- [Curso de Inglés Básico A1 para Principiantes](https://platzi.com/cursos/a1-principiantes/)",
            ],
        )

        md.append_courses_to_route(
            "Inglés Básico A2",
            [
                "- [Curso de Inglés Básico A2: Conectores y Artículos](https://platzi.com/cursos/a2-conectores/)",
                "- [Curso de Inglés Básico A2: Conjunciones y Verbos](https://platzi.com/cursos/a2-conjunciones/)",
                "- [Curso de Inglés Básico A2: Cuantificadores y Superlativos](https://platzi.com/cursos/a2-cuantificadores/)",
                "- [Curso de Inglés Básico A2: Descripciones y Comparaciones](https://platzi.com/cursos/a2-descripciones/)",
                "- [Curso de Inglés Básico A2: Experiencias Pasadas y Planes](https://platzi.com/cursos/a2-experiencias/)",
                "- [Curso de Inglés Básico A2: Infinitivos y Presente Continuo](https://platzi.com/cursos/a2-infinitivos/)",
                "- [Curso de Inglés Básico A2: Preguntas y Respuestas Comunes](https://platzi.com/cursos/a2-preguntas/)",
                "- [Curso de Inglés Básico A2: Sustantivos e Intenciones Futuras](https://platzi.com/cursos/a2-sustantivos/)",
            ],
        )

        md.append_courses_to_route(
            "Inglés Intermedio Alto B2",
            [
                "- [Curso de Inglés Intermedio Alto B2: Comentarios y Opiniones](https://platzi.com/cursos/b2-comentarios/)",
                "- [Curso de Inglés Intermedio Alto B2: Discurso Indirecto y Condicionales](https://platzi.com/cursos/b2-discurso/)",
                "- [Curso de Inglés Intermedio Alto B2: Hábitos y Aproximaciones](https://platzi.com/cursos/b2-habitos/)",
                "- [Curso de Inglés Intermedio Alto B2: Pasado Perfecto y Frases Adverbiales](https://platzi.com/cursos/b2-pasado-perfecto/)",
                "- [Curso de Inglés Intermedio Alto B2: Suposiciones e Instrucciones](https://platzi.com/cursos/b2-suposiciones/)",
            ],
        )

        md.append_courses_to_route(
            "Inglés Intermedio B1",
            [
                "- [Curso de Inglés Intermedio B1: Adjetivos y Preguntas Indirectas](https://platzi.com/cursos/b1-adjetivos/)",
                "- [Curso de Inglés Intermedio B1: Comparativos y Planes Futuros](https://platzi.com/cursos/b1-comparativos/)",
                "- [Curso de Inglés Intermedio B1: Descripción de Eventos y Preferencias](https://platzi.com/cursos/b1-descripcion/)",
                "- [Curso de Inglés Intermedio B1: Expresiones de Tiempo y Cantidad](https://platzi.com/cursos/b1-expresiones/)",
                "- [Curso de Inglés Intermedio B1: Palabras Interrogativas y Propósitos](https://platzi.com/cursos/b1-palabras/)",
                "- [Curso de Inglés Intermedio B1: Preguntas Negativas y Recomendaciones](https://platzi.com/cursos/b1-preguntas-negativas/)",
                "- [Curso de Inglés Intermedio B1: Preguntas de Confirmación y Posibilidades](https://platzi.com/cursos/b1-preguntas-confirmacion/)",
                "- [Curso de Inglés Intermedio B1: Presente Perfecto y Preposiciones](https://platzi.com/cursos/b1-presente-perfecto/)",
                "- [Curso de Inglés Intermedio B1: Primer Condicional y Pasado Continuo](https://platzi.com/cursos/b1-primer-condicional/)",
                "- [Curso de Inglés Intermedio B1: Pronombres y Cláusulas Relativas](https://platzi.com/cursos/b1-pronombres/)",
                "- [Curso de Inglés Intermedio B1: Solicitudes y Pronombres Reflexivos](https://platzi.com/cursos/b1-solicitudes/)",
                "- [Curso de Inglés Intermedio B1: Voz Pasiva y Consejos](https://platzi.com/cursos/b1-voz-pasiva/)",
            ],
        )

        md.append_courses_to_route(
            "Inglés para Propósitos Específicos",
            [
                "- [Curso de Preparación para TOEFL](https://platzi.com/cursos/preparacion-toefl/)",
                "- [Curso de Preparación para IELTS](https://platzi.com/cursos/preparacion-ielts/)",
                "- [Curso de Inglés Práctico con ChatGPT](https://platzi.com/cursos/ingles-chatgpt/)",
            ],
        )

        # Routes additions for English School
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
        md.insert_block_before_marker("## School: Marketing Digital", english_new_routes)

        # ======================================================================
        # SECTION 2: Add missing non-English courses to exact positions
        # ======================================================================

        md.insert_courses_after_course(
            "- [Curso de Materialize](https://platzi.com/cursos/materialize/)",
            ["- [Curso de Responsive Design: Maquetación Mobile First](https://platzi.com/cursos/responsive-design/)"],
        )

        md.insert_courses_after_course(
            "- [Curso de Git y GitHub](https://platzi.com/cursos/gitgithub/)",
            ["- [Curso Gratis de Lovable para Crear Páginas Web sin Programar](https://platzi.com/cursos/lovable/)"],
        )

        md.insert_courses_after_course(
            "- [Curso de Node.js Avanzado](https://platzi.com/cursos/nodejs-avanzado/)",
            ["- [Curso Práctico de Backend con Node.js](https://platzi.com/cursos/practico-backend-nodejs/)"],
        )

        md.insert_courses_after_course(
            "- [Curso de Rust básico](https://platzi.com/cursos/rust/)",
            [
                "- [Curso de COBOL desde Cero](https://platzi.com/cursos/cobol/)",
                "- [Curso Práctico de COBOL](https://platzi.com/cursos/cobol-practico/)",
            ],
        )

        md.insert_courses_after_course(
            "- [Curso Profesional de Redes Neuronales con TensorFlow](https://platzi.com/cursos/redes-neuronales-tensorflow/)",
            [
                "- [Curso de Deep Learning con TensorFlow y Keras](https://platzi.com/cursos/deep-learning-tensorflow-keras/)"
            ],
        )

        md.insert_courses_after_course(
            "- [Curso de Inteligencia Artificial para SEO](https://platzi.com/cursos/ia-seo/)",
            ["- [Curso de AI para SEO](https://platzi.com/cursos/ai-seo/)"],
        )

        md.insert_courses_after_course(
            "- [Curso de Inteligencia Artificial para Servicio al Cliente](https://platzi.com/cursos/ai-servicio-cliente/)",
            [
                "- [Curso de Growth Marketing con Inteligencia Artificial](https://platzi.com/cursos/growth-marketing-ia/)"
            ],
        )

        md.insert_courses_after_course(
            "- [Curso de Despliegue de Aplicaciones Python en la Nube](https://platzi.com/cursos/deploying-python/)",
            [
                "- [Curso de Python Profesional: Arquitectura de Proyectos, Entornos y PyPI](https://platzi.com/cursos/python-profesional/)"
            ],
        )

        md.insert_courses_after_course(
            "- [Curso de Excel Básico](https://platzi.com/cursos/excel-basico/)",
            [
                "- [Curso de Excel Básico: Tablas y Fórmulas para la Gestión de Datos](https://platzi.com/cursos/excel-basico-tablas/)"
            ],
        )

        md.insert_courses_after_course(
            "- [Curso de Introducción a Excel para Principiantes: Fundamentos](https://platzi.com/cursos/excel-principiantes/)",
            ["- [Curso de Excel Intermedio](https://platzi.com/cursos/excel-intermedio/)"],
        )

        md.insert_courses_after_course(
            "- [Curso de Desarrollo en Laravel con Test Driven Development](https://platzi.com/cursos/laravel-tdd/)",
            [
                "- [Curso de Single Page Applications en Laravel con Inertia y Vue](https://platzi.com/cursos/laravel-inertia-vue/)"
            ],
        )

        md.insert_courses_after_course(
            "- [Curso de Android: Integración de APIs nativas](https://platzi.com/cursos/android-apis-nativas/)",
            ["- [Curso de Android: Modo Offline](https://platzi.com/cursos/android-offline/)"],
        )

        md.insert_courses_after_course(
            "- [Audiocurso Glosario de Términos de Diseño](https://platzi.com/cursos/glosario-ux/)",
            ["- [Curso de Glosario de términos](https://platzi.com/cursos/glosario-terminos/)"],
        )

        md.insert_courses_after_course(
            "- [Curso de Fundamentos de React Native](https://platzi.com/cursos/fundamentos-react-native/)",
            [
                "- [Curso de Fundamentos de React Native (nuevo sin descargar)](https://platzi.com/cursos/fundamentos-react-native-nuevo/)"
            ],
        )

        md.insert_courses_after_course(
            "- [Curso de TypeScript: Tipos Avanzados y Funciones](https://platzi.com/cursos/typescript-tipos-avanzados/)",
            ["- [Curso de TypeScript](https://platzi.com/cursos/typescript/)"],
        )

        md.insert_courses_after_course(
            "- [Curso de Symfony Framework](https://platzi.com/cursos/symfony-framework/)",
            ["- [Curso de Symfony](https://platzi.com/cursos/symfony/)"],
        )

        md.insert_courses_after_course(
            "- [Curso para Desarrollar tu Creatividad: Técnicas y Hábitos](https://platzi.com/cursos/tecnicas-creatividad-2020/)",
            ["- [Curso para Desarrollar tu Creatividad](https://platzi.com/cursos/creatividad/)"],
        )

        md.insert_courses_after_course(
            "- [Curso de Estructuras de Datos con JavaScript](https://platzi.com/cursos/estructuras-datos/)",
            ["- [Curso de Estructuras de Datos](https://platzi.com/cursos/estructuras-datos-general/)"],
        )

    except Exception as e:
        print(f"❌ Error crítico durante la inyección de rutas: {repr(e)}")
        sys.exit(1)

    # Save
    md.save(OUTPUT)

    # Re-verify logic exactly as before for reporting
    course_pat = re.compile(r"^- \[(.+?)\]\((.+?)\)\s*$", re.MULTILINE)
    all_courses = course_pat.findall("\n".join(md.lines))
    unique = set(m[0] for m in all_courses)
    print(f"Total entries resultantes: {len(all_courses)}")
    print(f"Cursos únicos: {len(unique)}")


if __name__ == "__main__":
    main()
