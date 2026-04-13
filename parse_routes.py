"""
parse_routes.py — Parse PlatziRoutes.md into structured categories/routes/courses.

This replaces the old server_metadata.json approach. PlatziRoutes.md is parsed
directly so it becomes the single source of truth for course organization.
"""

import os
import re

ROUTES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PlatziRoutes.md")

# Map school names to emojis (must match ## School: names in PlatziRoutes.md)
SCHOOL_ICONS = {
    "Desarrollo Web": "💻",
    "English Academy": "🇬🇧",
    "Marketing Digital": "📣",
    "Inteligencia Artificial y Data Science": "🤖",
    "Ciberseguridad": "🔒",
    "Liderazgo y Habilidades Blandas": "🎯",
    "Diseño de Producto y UX": "🎨",
    "Contenido Audiovisual": "🎬",
    "Desarrollo Móvil": "📱",
    "Diseño Gráfico y Arte Digital": "🖌️",
    "Programación": "🧑‍💻",
    "Negocios": "💼",
    "Blockchain y Web3": "🔗",
    "Recursos Humanos": "👥",
    "Finanzas e Inversiones": "💰",
    "Startups": "🚀",
    "Cloud Computing y DevOps": "☁️",
}

# School → type classification for filtering
SCHOOL_TYPE_MAP = {
    "Desarrollo Web": "development",
    "English Academy": "english",
    "Marketing Digital": "marketing",
    "Inteligencia Artificial y Data Science": "development",
    "Ciberseguridad": "hacking",
    "Liderazgo y Habilidades Blandas": "business",
    "Diseño de Producto y UX": "design",
    "Contenido Audiovisual": "design",
    "Desarrollo Móvil": "development",
    "Diseño Gráfico y Arte Digital": "design",
    "Programación": "development",
    "Negocios": "business",
    "Blockchain y Web3": "development",
    "Recursos Humanos": "business",
    "Finanzas e Inversiones": "finance",
    "Startups": "business",
    "Cloud Computing y DevOps": "development",
}


def sanitize_folder_name(course_name):
    """Convert a course title from PlatziRoutes.md into the expected Drive folder name.

    This must match the naming convention used when courses were uploaded to Drive.
    The convention strips colons, emojis, and normalizes whitespace.
    """
    name = course_name.strip()
    # Remove colons (Drive folder names don't have them)
    name = name.replace(":", "")
    # Remove emoji and other non-Latin special unicode characters
    # Keep: ASCII, Latin Extended (accented chars like áéíóúñü), basic punctuation
    cleaned = []
    for ch in name:
        cp = ord(ch)
        # Keep ASCII printable, Latin-1 Supplement, Latin Extended-A/B
        if cp < 0x250 or ch in "().,;!¿?¡-+&@#$%/=":
            cleaned.append(ch)
    name = "".join(cleaned)
    # Normalize multiple spaces to single space
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def parse(filepath=None):
    """Parse PlatziRoutes.md and return structured data.

    Returns:
        dict with keys:
            - categories: list of category dicts
            - stats: dict with totalCategories, totalRoutes, totalCourses
    """
    if filepath is None:
        filepath = ROUTES_FILE

    if not os.path.exists(filepath):
        print(f"❌ Error: {filepath} no encontrado.")
        return {"categories": [], "stats": {}}

    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()

    categories = []
    current_category = None
    current_route = None

    # Regex patterns
    school_pattern = re.compile(r"^## School:\s*(.+)$")
    route_pattern = re.compile(r"^### \[(.+?)\]\((.+?)\)\s*$")
    course_pattern = re.compile(r"^- \[(.+?)\]\((.+?)\)\s*$")

    for line in lines:
        line = line.rstrip("\r\n")

        # Match School (category)
        m = school_pattern.match(line)
        if m:
            school_name = m.group(1).strip()
            school_id = school_name.lower().replace(" ", "-").replace(",", "")
            school_id = re.sub(r"[^a-z0-9\-]", "", school_id)

            current_category = {
                "id": school_id,
                "name": school_name,
                "icon": SCHOOL_ICONS.get(school_name, "📚"),
                "description": school_name,
                "type": SCHOOL_TYPE_MAP.get(school_name, "other"),
                "routes": [],
            }
            categories.append(current_category)
            current_route = None
            continue

        # Match Route
        m = route_pattern.match(line)
        if m and current_category is not None:
            route_name = m.group(1).strip()
            route_url = m.group(2).strip()
            route_id = route_name.lower().replace(" ", "-").replace(",", "")
            route_id = re.sub(r"[^a-z0-9\-áéíóúñü]", "", route_id)

            current_route = {
                "id": route_id,
                "name": route_name,
                "url": route_url,
                "isCourse": False,
                "courses": [],
            }
            current_category["routes"].append(current_route)
            continue

        # Match Course
        m = course_pattern.match(line)
        if m and current_route is not None:
            course_name = m.group(1).strip()
            course_url = m.group(2).strip()
            folder_name = sanitize_folder_name(course_name)

            current_route["courses"].append(
                {
                    "name": course_name,
                    "folder": folder_name,
                    "url": course_url,
                }
            )
            continue

    # Build stats
    total_routes = 0
    total_courses = 0
    for cat in categories:
        total_routes += len(cat["routes"])
        for route in cat["routes"]:
            total_courses += len(route["courses"])

    stats = {
        "totalCategories": len(categories),
        "totalRoutes": total_routes,
        "totalCourses": total_courses,
        "totalClasses": 0,  # Filled at scan time from Drive
    }

    return {"categories": categories, "stats": stats}


def print_summary(data):
    """Print a human-readable summary of parsed routes."""
    cats = data["categories"]
    stats = data["stats"]

    print(f"\n{'='*60}")
    print("📊 PlatziRoutes.md Summary")
    print(f"{'='*60}")
    print(f"  Schools:  {stats['totalCategories']}")
    print(f"  Routes:   {stats['totalRoutes']}")
    print(f"  Courses:  {stats['totalCourses']}")
    print()

    for cat in cats:
        route_count = len(cat["routes"])
        course_count = sum(len(r["courses"]) for r in cat["routes"])
        print(f"  {cat['icon']} {cat['name']} — {route_count} routes, {course_count} courses [{cat['type']}]")
    print()


if __name__ == "__main__":
    data = parse()
    print_summary(data)
