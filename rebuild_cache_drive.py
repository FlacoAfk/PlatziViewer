"""
rebuild_cache_drive.py - Rebuild courses_cache.json using Google Drive API.

Scans the shared Drive folder structure and stores Drive file IDs
so all content is served via Drive API (no local filesystem dependency).

Structure: Root → Course Folders → Module Folders → Class Files
"""

import json
import re
import os
import time

import parse_routes
from drive_service import drive_service

DRIVE_ROOT_ID = "17kPqqPSheDtQ5S1HM6Qvvh2qJ7O3YADm"
OUTPUT_FILE = "courses_cache.json"

# Rate limiting
API_CALL_COUNT = 0
API_CALL_START = time.time()


def api_call_throttle():
    """Simple rate limiter to avoid hitting Drive API quotas."""
    global API_CALL_COUNT, API_CALL_START
    API_CALL_COUNT += 1
    elapsed = time.time() - API_CALL_START
    # Google Drive API: 12,000 queries per minute for service accounts
    # Be conservative: max ~100 calls per second
    if API_CALL_COUNT % 50 == 0 and elapsed < 1.0:
        wait = 1.0 - elapsed
        time.sleep(wait)
        API_CALL_START = time.time()
        API_CALL_COUNT = 0


def sanitize_for_match(name):
    """Normalize a name for fuzzy matching."""
    name = name.strip()
    name = name.replace(":", "").replace("/", "").replace(",", "")
    cleaned = []
    for ch in name:
        cp = ord(ch)
        if cp < 0x250 or ch in "().,;!-+&@#%=":
            cleaned.append(ch)
    name = "".join(cleaned)
    name = re.sub(r"\s+", " ", name)
    return name.strip().lower()


def get_sort_key(name):
    """Extract leading number for sorting: '1. Intro' -> (0, 1, name)."""
    parts = name.split(". ", 1)
    if parts[0].isdigit():
        return (0, int(parts[0]), name)
    return (1, 0, name)


def list_drive_folder(folder_id):
    """List files in a Drive folder with throttling."""
    api_call_throttle()
    return drive_service.list_files(folder_id)


def scan_drive_classes(folder_id):
    """Scan class files inside a Drive module folder.

    Returns list of class dicts with Drive file IDs.
    """
    classes = []
    files = list_drive_folder(folder_id)

    # Group files by class number
    class_files = {}
    for f in files:
        name = f["name"]
        if name.startswith("desktop") or name.startswith("."):
            continue
        parts = name.split(". ", 1)
        if len(parts) >= 2 and parts[0].isdigit():
            num = int(parts[0])
            if num not in class_files:
                class_files[num] = []
            class_files[num].append(f)

    # Viewable extensions
    VIEWABLE_EXT = {
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
        video_id = summary_id = vtt_id = reading_id = html_id = None
        resources = []

        for f in flist:
            fname = f["name"]
            fid = f["id"]

            if fname.endswith(".mp4"):
                video = fname
                video_id = fid
            elif fname.endswith("_summary.html"):
                summary = fname
                summary_id = fid
            elif fname.endswith(".vtt") and not fname.endswith("_es.vtt"):
                vtt = fname
                vtt_id = fid
            elif "Lecturas recomendadas" in fname and fname.endswith(".txt"):
                reading = fname
                reading_id = fid
            elif fname.endswith(".html") and not fname.endswith("_summary.html"):
                html = fname
                html_id = fid
            else:
                ext = os.path.splitext(fname)[1].lower()
                if ext and ext != ".ini":
                    display = fname.split(". ", 1)[-1] if ". " in fname else fname
                    resources.append({"name": display, "file": fid, "ext": ext, "viewable": ext in VIEWABLE_EXT})

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
                    "video": video_id,
                    "summary": summary_id,
                    "subtitles": vtt_id,
                    "reading": reading_id,
                    "html": html_id,
                },
                "resources": resources,
            }
        )

    return classes


def scan_drive_course(course_folder_id, course_folder_name):
    """Scan a course folder in Drive for modules/classes.

    Returns (modules_list, has_presentation, presentation_id).
    """
    modules = []
    has_presentation = False
    presentation_id = None

    items = list_drive_folder(course_folder_id)

    # Separate folders and files
    sub_folders = []
    for item in items:
        if item["mimeType"] == "application/vnd.google-apps.folder":
            sub_folders.append(item)
        elif item["name"] == "presentation.html":
            has_presentation = True
            presentation_id = item["id"]

    # Sort module folders by name
    sub_folders.sort(key=lambda x: get_sort_key(x["name"]))

    for folder in sub_folders:
        classes = scan_drive_classes(folder["id"])
        name = folder["name"].split(". ", 1)[-1] if ". " in folder["name"] else folder["name"]
        modules.append({"name": name, "folderName": folder["name"], "classes": classes, "classCount": len(classes)})

    # If no module subfolders had classes, try flat layout (classes directly in course root)
    total_classes = sum(len(m["classes"]) for m in modules)
    if total_classes == 0 and not sub_folders:
        flat_classes = scan_drive_classes(course_folder_id)
        if flat_classes:
            modules = [
                {"name": "Contenido", "folderName": "", "classes": flat_classes, "classCount": len(flat_classes)}
            ]

    return modules, has_presentation, presentation_id


def match_course_to_drive(md_name, drive_names_san, drive_names_map):
    """Try to match an MD course name to a Drive folder.

    Returns (drive_folder_name, drive_folder_id, match_type) or (None, None, None).
    """
    san = sanitize_for_match(md_name)

    # 1. Exact match
    if san in drive_names_san:
        info = drive_names_map[san]
        return info["name"], info["id"], "exact"

    # 2. MD name starts with Drive name
    for ds, info in drive_names_map.items():
        if san.startswith(ds) and len(ds) > 20:
            return info["name"], info["id"], "prefix"

    # 3. Drive name starts with MD name
    for ds, info in drive_names_map.items():
        if ds.startswith(san) and len(san) > 20:
            return info["name"], info["id"], "prefix"

    # 4. High word overlap
    san_words = set(san.split())
    best_match = None
    best_overlap = 0
    for ds, info in drive_names_map.items():
        ds_words = set(ds.split())
        overlap = len(san_words & ds_words)
        min_len = min(len(san_words), len(ds_words))
        if min_len > 0 and overlap / min_len >= 0.8 and overlap > best_overlap:
            best_overlap = overlap
            best_match = (info["name"], info["id"], "fuzzy")

    if best_match and best_overlap >= 4:
        return best_match

    return None, None, None


PROGRESS_FILE = "drive_scan_progress.json"


def load_scan_progress():
    """Load previously scanned course data to allow resuming."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_scan_progress(progress):
    """Save scan progress for resume capability."""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False)


def main():
    print("=" * 60)
    print("📦 Rebuilding courses_cache.json from Google Drive")
    print("=" * 60)

    # 1. Parse PlatziRoutes.md
    print("\n📖 Parsing PlatziRoutes.md...")
    parsed = parse_routes.parse()
    categories = parsed["categories"]
    print(
        f"   {len(categories)} categories, {parsed['stats']['totalRoutes']} routes, "
        f"{parsed['stats']['totalCourses']} course entries"
    )

    # 2. List all course folders from Drive root
    print("\n📁 Listing Drive root folder...")
    root_items = list_drive_folder(DRIVE_ROOT_ID)
    drive_folders = [f for f in root_items if f["mimeType"] == "application/vnd.google-apps.folder"]
    print(f"   {len(drive_folders)} course folders found in Drive")

    # Build Drive lookup: sanitized name -> {name, id}
    drive_san = {}
    drive_map = {}
    for df in drive_folders:
        san = sanitize_for_match(df["name"])
        drive_san[san] = True
        drive_map[san] = {"name": df["name"], "id": df["id"]}

    # 3. Load previous scan progress (for resume)
    scanned = load_scan_progress()
    print(f"   {len(scanned)} courses already scanned (resumable)")

    # 4. Match courses and scan Drive content
    print("\n🔗 Matching courses to Drive folders and scanning content...")
    total_matched = 0
    total_with_content = 0
    total_courses = 0
    total_classes = 0
    courses_scanned_this_run = 0

    for cat in categories:
        print(f"\n  {cat['icon']} {cat['name']}...")
        cat_matched = 0

        for route in cat["routes"]:
            enriched_courses = []
            for course in route.get("courses", []):
                total_courses += 1
                md_name = course["name"]

                drive_folder_name, drive_folder_id, match_type = match_course_to_drive(md_name, drive_san, drive_map)

                enriched = {
                    "name": md_name,
                    "folderName": course.get("folder", md_name),
                    "url": course.get("url", ""),
                    "modules": [],
                    "moduleCount": 0,
                    "classCount": 0,
                    "foundInDrive": drive_folder_name is not None,
                }

                if drive_folder_name:
                    total_matched += 1
                    cat_matched += 1
                    enriched["id"] = drive_folder_id
                    enriched["matchType"] = match_type
                    enriched["matchedFolder"] = drive_folder_name

                    # Check if already scanned
                    if drive_folder_id in scanned:
                        cached = scanned[drive_folder_id]
                        enriched["modules"] = cached.get("modules", [])
                        enriched["moduleCount"] = cached.get("moduleCount", 0)
                        enriched["classCount"] = cached.get("classCount", 0)
                        enriched["hasPresentation"] = cached.get("hasPresentation", False)
                        enriched["presentationId"] = cached.get("presentationId", None)
                        cc = enriched["classCount"]
                    else:
                        # Scan Drive for modules/classes
                        try:
                            modules, has_pres, pres_id = scan_drive_course(drive_folder_id, drive_folder_name)
                        except Exception as e:
                            print(f"     ⚠️ Error scanning '{drive_folder_name}': {e}")
                            modules, has_pres, pres_id = [], False, None

                        cc = sum(len(m.get("classes", [])) for m in modules)
                        enriched["modules"] = modules
                        enriched["moduleCount"] = len(modules)
                        enriched["classCount"] = cc
                        enriched["hasPresentation"] = has_pres
                        enriched["presentationId"] = pres_id

                        # Save progress
                        scanned[drive_folder_id] = {
                            "modules": modules,
                            "moduleCount": len(modules),
                            "classCount": cc,
                            "hasPresentation": has_pres,
                            "presentationId": pres_id,
                        }
                        courses_scanned_this_run += 1

                        # Save progress every 10 courses
                        if courses_scanned_this_run % 10 == 0:
                            save_scan_progress(scanned)
                            print(f"     💾 Progress saved ({courses_scanned_this_run} scanned this run)")

                    if cc > 0:
                        total_with_content += 1
                    total_classes += cc

                enriched_courses.append(enriched)

            route["courses"] = enriched_courses
            route["courseCount"] = len(enriched_courses)

        print(f"     ✓ {cat_matched} courses matched to Drive")

    # Save final progress
    save_scan_progress(scanned)

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
    print(f"✅ Cache rebuilt from Google Drive!")
    print(f"   Categories:     {len(categories)}")
    print(f"   Routes:         {total_routes}")
    print(f"   Course entries: {total_courses}")
    print(f"   Matched Drive:  {total_matched}")
    print(f"   With content:   {total_with_content}")
    print(f"   Total classes:  {total_classes}")
    print(f"   File size:      {file_size / 1024 / 1024:.1f} MB")
    print(f"   Scanned this run: {courses_scanned_this_run}")
    print(f"   API calls:      ~{API_CALL_COUNT}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
