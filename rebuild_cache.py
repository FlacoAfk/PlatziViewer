"""
rebuild_cache.py - Rebuild courses_cache.json combining:
  1. PlatziRoutes.md structure (from parse_routes.py)
  2. Existing courses_cache.json Drive data (modules, classes, file IDs)
  3. DriveCourses.md folder listing for matching
  4. Local filesystem scan for courses missing content (PlatziCoursesFlat)

This avoids re-scanning Drive API while incorporating new courses from MD.
For courses matched to Drive but without cached content, it scans the local
filesystem to populate modules/classes with local file paths.
"""

import json
import os
import re

# Import the parser
import parse_routes

CACHE_FILE = "courses_cache.json"
DRIVE_COURSES_FILE = "DriveCourses.md"
OUTPUT_FILE = "courses_cache.json"
COURSES_PATH = r"H:\Mi unidad\PlatziCoursesFlat"


def sanitize_for_match(name):
    """Normalize a name for fuzzy matching."""
    name = name.strip()
    name = name.replace(":", "").replace("/", "").replace(",", "")
    # Remove emoji and special unicode
    cleaned = []
    for ch in name:
        cp = ord(ch)
        if cp < 0x250 or ch in "().,;!-+&@#%=":
            cleaned.append(ch)
    name = "".join(cleaned)
    name = re.sub(r"\s+", " ", name)
    return name.strip().lower()


def load_drive_courses():
    """Load the list of Drive folder names from DriveCourses.md."""
    courses = []
    with open(DRIVE_COURSES_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("- "):
                courses.append(line[2:].strip())
    return courses


def load_old_cache():
    """Load existing cache to reuse Drive data (modules, classes, file IDs)."""
    if not os.path.exists(CACHE_FILE):
        return {}

    with open(CACHE_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # Build lookup: sanitized course name -> course data (with modules)
    lookup = {}
    for cat in data.get("categories", []):
        for route in cat.get("routes", []):
            for course in route.get("courses", []):
                name = course.get("name", "")
                san = sanitize_for_match(name)
                if course.get("foundInDrive") and course.get("modules"):
                    lookup[san] = course
                # Also index by matchedFolder
                matched = course.get("matchedFolder", "")
                if matched:
                    lookup[sanitize_for_match(matched)] = course
                # Also index by folderName
                folder = course.get("folderName", "")
                if folder:
                    lookup[sanitize_for_match(folder)] = course

    return lookup


def match_course_to_drive(md_name, drive_names_san, drive_names_map):
    """Try to match an MD course name to a Drive folder.

    Returns (drive_folder_name, match_type) or (None, None).
    """
    san = sanitize_for_match(md_name)

    # 1. Exact match (after sanitization)
    if san in drive_names_san:
        return drive_names_map[san], "exact"

    # 2. MD name starts with Drive name (Drive has truncated name)
    for ds, orig in drive_names_map.items():
        if san.startswith(ds) and len(ds) > 20:
            return orig, "prefix"

    # 3. Drive name starts with MD name (MD has truncated name)
    for ds, orig in drive_names_map.items():
        if ds.startswith(san) and len(san) > 20:
            return orig, "prefix"

    # 4. High word overlap (>80% of words match)
    san_words = set(san.split())
    best_match = None
    best_overlap = 0
    for ds, orig in drive_names_map.items():
        ds_words = set(ds.split())
        overlap = len(san_words & ds_words)
        # Require at least 80% overlap on the smaller set
        min_len = min(len(san_words), len(ds_words))
        if min_len > 0 and overlap / min_len >= 0.8 and overlap > best_overlap:
            best_overlap = overlap
            best_match = (orig, "fuzzy")

    if best_match and best_overlap >= 4:
        return best_match

    return None, None


def get_sort_key(name):
    """Extract leading number for sorting: '1. Intro' -> (0, 1, name)."""
    parts = name.split(". ", 1)
    if parts[0].isdigit():
        return (0, int(parts[0]), name)
    return (1, 0, name)


def scan_local_classes(module_path):
    """Scan class files inside a module folder on local filesystem.

    Returns list of class dicts with local: prefixed file paths.
    """
    classes = []
    if not os.path.exists(module_path):
        return classes

    try:
        files = os.listdir(module_path)
    except Exception:
        return classes

    class_files = {}
    for f in files:
        if f.startswith("desktop") or f.startswith("."):
            continue
        parts = f.split(". ", 1)
        if len(parts) >= 2 and parts[0].isdigit():
            num = int(parts[0])
            if num not in class_files:
                class_files[num] = []
            class_files[num].append(f)

    # Build local path helper
    module_rel = os.path.relpath(module_path, COURSES_PATH)

    def local_ref(filename):
        if filename is None:
            return None
        return "local:" + module_rel.replace("\\", "/") + "/" + filename

    # Viewable extensions (opened inline in browser)
    viewable_ext = {
        ".html",
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".svg",
        ".webp",
        ".gif",
        ".md",
        ".txt",
        ".js",
        ".py",
        ".css",
        ".json",
        ".csv",
        ".sql",
        ".xml",
    }

    for num in sorted(class_files.keys()):
        flist = class_files[num]
        video = summary = vtt = reading = html = None
        resources = []  # extra files: pdf, zip, images, code, etc.

        for f in flist:
            if f.endswith(".mp4"):
                video = f
            elif f.endswith("_summary.html"):
                summary = f
            elif f.endswith(".vtt"):
                vtt = f
            elif "Lecturas recomendadas" in f and f.endswith(".txt"):
                reading = f
            elif f.endswith(".html") and not f.endswith("_summary.html"):
                html = f
            else:
                # Extra resource file
                ext = os.path.splitext(f)[1].lower()
                if ext and ext != ".ini":
                    # Clean display name: remove leading number and hash suffix
                    display = f.split(". ", 1)[-1] if ". " in f else f
                    resources.append(
                        {"name": display, "file": local_ref(f), "ext": ext, "viewable": ext in viewable_ext}
                    )

        if video:
            name = video.rsplit(".", 1)[0]
            name = name.split(". ", 1)[-1] if ". " in name else name
        elif html:
            name = html.rsplit(".", 1)[0]
            name = name.split(". ", 1)[-1] if ". " in name else name
        else:
            continue

        classes.append(
            {
                "num": num,
                "name": name[:60],
                "hasVideo": video is not None,
                "hasSummary": summary is not None,
                "hasSubtitles": vtt is not None,
                "hasReading": reading is not None,
                "hasHtml": html is not None and video is None,
                "files": {
                    "video": local_ref(video),
                    "summary": local_ref(summary),
                    "subtitles": local_ref(vtt),
                    "reading": local_ref(reading),
                    "html": local_ref(html),
                },
                "resources": resources,
            }
        )

    return classes


def scan_local_course(course_folder_name):
    """Scan a course folder in PlatziCoursesFlat for modules/classes.

    Handles two layouts:
    - Standard: CourseFolder/ModuleFolders/ClassFiles
    - Flat: CourseFolder/ClassFiles (no module subfolders)

    Returns (modules_list, has_presentation).
    """
    course_path = os.path.join(COURSES_PATH, course_folder_name)
    modules = []
    has_presentation = False

    if not os.path.exists(course_path):
        return modules, has_presentation

    try:
        items = sorted(os.listdir(course_path), key=get_sort_key)
    except Exception:
        return modules, has_presentation

    for item in items:
        item_path = os.path.join(course_path, item)
        if os.path.isdir(item_path) and not item.startswith(".") and item != "desktop.ini":
            classes = scan_local_classes(item_path)
            name = item.split(". ", 1)[-1] if ". " in item else item
            modules.append({"name": name, "folderName": item, "classes": classes, "classCount": len(classes)})
        elif item == "presentation.html":
            has_presentation = True

    # If no subdirectories had any classes, try flat layout
    # (all class files directly in course root)
    total_classes = sum(len(m["classes"]) for m in modules)
    if total_classes == 0:
        flat_classes = scan_local_classes(course_path)
        if flat_classes:
            modules = [
                {"name": "Contenido", "folderName": "", "classes": flat_classes, "classCount": len(flat_classes)}
            ]

    return modules, has_presentation


def main():
    print("=" * 60)
    print("📦 Rebuilding courses_cache.json")
    print("=" * 60)

    # 1. Parse PlatziRoutes.md
    print("\n📖 Parsing PlatziRoutes.md...")
    parsed = parse_routes.parse()
    categories = parsed["categories"]
    print(
        f"   {len(categories)} categories, {parsed['stats']['totalRoutes']} routes, {parsed['stats']['totalCourses']} course entries"
    )

    # 2. Load Drive folder names
    print("\n📁 Loading Drive folder names...")
    drive_folders = load_drive_courses()
    print(f"   {len(drive_folders)} folders")

    # Build Drive lookup
    drive_san = {}  # sanitized -> True
    drive_map = {}  # sanitized -> original name
    for df in drive_folders:
        san = sanitize_for_match(df)
        drive_san[san] = True
        drive_map[san] = df

    # 3. Load old cache for existing data
    print("\n📋 Loading existing cache data...")
    old_cache = load_old_cache()
    print(f"   {len(old_cache)} cached course entries with Drive data")

    # 4. Match courses and build new cache
    print("\n🔗 Matching courses to Drive folders...")
    total_matched = 0
    total_with_content = 0
    total_courses = 0
    total_classes = 0
    total_scanned_local = 0

    for cat in categories:
        for route in cat["routes"]:
            enriched_courses = []
            for course in route.get("courses", []):
                total_courses += 1
                md_name = course["name"]
                folder_name = course["folder"]  # sanitized by parse_routes

                # Try to match to Drive
                drive_folder, match_type = match_course_to_drive(md_name, drive_san, drive_map)

                # Build enriched course entry
                enriched = {
                    "name": md_name,
                    "folderName": folder_name,
                    "url": course.get("url", ""),
                    "modules": [],
                    "moduleCount": 0,
                    "classCount": 0,
                    "foundInDrive": drive_folder is not None,
                }

                if drive_folder:
                    total_matched += 1
                    enriched["id"] = ""
                    enriched["hasPresentation"] = False
                    enriched["presentationId"] = None
                    enriched["matchType"] = match_type
                    enriched["matchedFolder"] = drive_folder

                    # Always scan local filesystem to capture resources
                    modules, has_pres = scan_local_course(drive_folder)
                    if modules:
                        cc = sum(len(m.get("classes", [])) for m in modules)
                        enriched["modules"] = modules
                        enriched["moduleCount"] = len(modules)
                        enriched["classCount"] = cc
                        enriched["hasPresentation"] = has_pres
                        if cc > 0:
                            total_with_content += 1
                            total_scanned_local += 1
                        total_classes += cc
                    else:
                        # Folder exists in Drive list but has no local content
                        # Fall back to old cache if available
                        san_key = sanitize_for_match(md_name)
                        san_folder = sanitize_for_match(drive_folder)
                        old_data = old_cache.get(san_key) or old_cache.get(san_folder)
                        if old_data and old_data.get("modules"):
                            enriched["modules"] = old_data["modules"]
                            enriched["moduleCount"] = old_data.get("moduleCount", len(old_data["modules"]))
                            enriched["classCount"] = old_data.get("classCount", 0)
                            enriched["id"] = old_data.get("id", "")
                            enriched["hasPresentation"] = old_data.get("hasPresentation", False)
                            enriched["presentationId"] = old_data.get("presentationId", None)
                            if enriched["classCount"] > 0:
                                total_with_content += 1
                            total_classes += enriched["classCount"]

                enriched_courses.append(enriched)

            route["courses"] = enriched_courses
            route["courseCount"] = len(enriched_courses)

            # Remove parse_routes fields not needed
            if "url" in route and "courses" in route:
                pass  # keep both

    # 5. Build stats
    total_routes = sum(len(cat["routes"]) for cat in categories)

    result = {
        "categories": categories,
        "stats": {
            "totalCategories": len(categories),
            "totalRoutes": total_routes,
            "totalCourses": total_courses,
            "totalClasses": total_classes,
        },
    }

    # 6. Save
    print(f"\n💾 Saving {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    file_size = os.path.getsize(OUTPUT_FILE)

    print(f"\n{'=' * 60}")
    print("✅ Cache rebuilt!")
    print(f"   Categories:     {len(categories)}")
    print(f"   Routes:         {total_routes}")
    print(f"   Course entries: {total_courses}")
    print(f"   Matched Drive:  {total_matched}")
    print(f"   With content:   {total_with_content}")
    print(f"   Scanned local:  {total_scanned_local}")
    print(f"   Total classes:  {total_classes}")
    print(f"   File size:      {file_size / 1024 / 1024:.1f} MB")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
