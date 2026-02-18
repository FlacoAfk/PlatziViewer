"""
rebuild_cache.py - Rebuild courses_cache.json combining:
  1. PlatziRoutes.md structure (from parse_routes.py)
  2. Google Drive API scanning (for remote files)
  3. Local filesystem scan (for local files, fallback)

This version scans Google Drive directly to populate file IDs for streaming.
"""

import json
import re
import os
import sys

# Import the parser
import parse_routes

# Import Drive service
try:
    from drive_service import drive_service
    DRIVE_AVAILABLE = True
except ImportError:
    print("⚠️ drive_service.py not found or dependencies missing.")
    DRIVE_AVAILABLE = False


CACHE_FILE = "courses_cache.json"
DRIVE_COURSES_FILE = "DriveCourses.md"
OUTPUT_FILE = "courses_cache.json"

# Configuración
COURSES_PATH = r"C:\Users\elkaw\Desktop\platzi-downloader" # Ruta local base (opcional si se usa Drive)
DRIVE_ROOT_ID = "17kPqqPSheDtQ5S1HM6Qvvh2qJ7O3YADm" # Carpeta compartida con cursos


def sanitize_for_match(name):
    """Normalize a name for fuzzy matching."""
    if not name: return ""
    name = name.strip()
    name = name.replace(":", "").replace("/", "").replace(",", "")
    # Remove emoji and special unicode
    cleaned = []
    for ch in name:
        cp = ord(ch)
        if cp < 0x250 or ch in '().,;!-+&@#%=':
            cleaned.append(ch)
    name = ''.join(cleaned)
    name = re.sub(r'\s+', ' ', name)
    return name.strip().lower()


def get_sort_key(name):
    """Extract leading number for sorting: '1. Intro' -> (0, 1, name)."""
    parts = name.split('. ', 1)
    if parts[0].isdigit():
        return (0, int(parts[0]), name)
    return (1, 0, name)


def scan_local_classes(module_path):
    """Scan class files inside a module folder on local filesystem."""
    classes = []
    if not os.path.exists(module_path):
        return classes
    
    try:
        files = os.listdir(module_path)
    except Exception:
        return classes
    
    class_files = {}
    for f in files:
        if f.startswith('desktop') or f.startswith('.'):
            continue
        parts = f.split('. ', 1)
        if len(parts) >= 2 and parts[0].isdigit():
            num = int(parts[0])
            if num not in class_files:
                class_files[num] = []
            class_files[num].append(f)
    
    # Build local path helper
    # For local server, we want paths relative to COURSES_PATH if possible,
    # prefixed with "local:"
    try:
        module_rel = os.path.relpath(module_path, COURSES_PATH)
    except ValueError:
        # If paths are on different drives
        module_rel = module_path

    def local_ref(filename):
        if filename is None:
            return None
        # Ensure forward slashes
        rel = os.path.join(module_rel, filename).replace('\\', '/')
        return f"local:{rel}"
    
    VIEWABLE_EXT = {'.html', '.pdf', '.png', '.jpg', '.jpeg', '.svg', '.webp',
                    '.gif', '.md', '.txt', '.js', '.py', '.css', '.json', '.csv',
                    '.sql', '.xml'}
    
    for num in sorted(class_files.keys()):
        flist = class_files[num]
        video = summary = vtt = reading = html = None
        resources = []
        
        for f in flist:
            if f.endswith('.mp4'):
                video = f
            elif f.endswith('_summary.html'):
                summary = f
            elif f.endswith('.vtt'):
                vtt = f
            elif 'Lecturas recomendadas' in f and f.endswith('.txt'):
                reading = f
            elif f.endswith('.html') and not f.endswith('_summary.html'):
                html = f
            else:
                ext = os.path.splitext(f)[1].lower()
                if ext and ext != '.ini':
                    display = f.split('. ', 1)[-1] if '. ' in f else f
                    resources.append({
                        'name': display,
                        'file': local_ref(f),
                        'ext': ext,
                        'viewable': ext in VIEWABLE_EXT
                    })
        
        if video:
            name = video.rsplit('.', 1)[0]
            name = name.split('. ', 1)[-1] if '. ' in name else name
        elif html:
            name = html.rsplit('.', 1)[0]
            name = name.split('. ', 1)[-1] if '. ' in name else name
        else:
            continue
        
        classes.append({
            'num': num,
            'name': name[:100],
            'hasVideo': video is not None,
            'hasSummary': summary is not None,
            'hasSubtitles': vtt is not None,
            'hasReading': reading is not None,
            'hasHtml': html is not None and video is None,
            'files': {
                'video': local_ref(video),
                'summary': local_ref(summary),
                'subtitles': local_ref(vtt),
                'reading': local_ref(reading),
                'html': local_ref(html),
            },
            'resources': resources
        })
    
    return classes


def scan_local_course(course_path):
    """Scan a course folder on local filesystem."""
    modules = []
    has_presentation = False
    
    if not os.path.exists(course_path):
        return modules, has_presentation
    
    try:
        items = sorted(os.listdir(course_path), key=get_sort_key)
    except Exception:
        return modules, has_presentation
    
    has_subdirs = False
    for item in items:
        item_path = os.path.join(course_path, item)
        if os.path.isdir(item_path) and not item.startswith('.') and item != 'desktop.ini':
            has_subdirs = True
            classes = scan_local_classes(item_path)
            name = item.split('. ', 1)[-1] if '. ' in item else item
            modules.append({
                'name': name,
                'folderName': item,
                'classes': classes,
                'classCount': len(classes)
            })
        elif item == 'presentation.html':
            has_presentation = True
    
    if not has_subdirs:
        flat_classes = scan_local_classes(course_path)
        if flat_classes:
            modules = [{
                'name': 'Contenido',
                'folderName': '',
                'classes': flat_classes,
                'classCount': len(flat_classes)
            }]
    
    return modules, has_presentation


# ==========================================
# Google Drive Scanning Logic
# ==========================================

def scan_drive_root(root_id):
    """List all folders in the root Drive folder."""
    print(f"☁️ Scanning Drive root: {root_id}...")
    try:
        updated_files = drive_service.list_files(root_id)
        courses = []
        for f in updated_files:
            if f['mimeType'] == 'application/vnd.google-apps.folder':
                courses.append({
                    'name': f['name'],
                    'id': f['id']
                })
        return courses
    except Exception as e:
        print(f"❌ Error scanning Drive root: {e}")
        return []

def scan_drive_classes(folder_id):
    """Scan files in a Drive folder and organize into classes."""
    classes = []
    try:
        files = drive_service.list_files(folder_id)
    except Exception as e:
        print(f"❌ Error scanning folder {folder_id}: {e}")
        return classes

    # Group files by class number
    class_files = {}
    
    for f in files:
        name = f['name']
        if name.startswith('.'): continue
        if f['mimeType'] == 'application/vnd.google-apps.folder': continue # Ignore subfolders here?
        
        parts = name.split('. ', 1)
        if len(parts) >= 2 and parts[0].isdigit():
            num = int(parts[0])
            if num not in class_files:
                class_files[num] = []
            class_files[num].append(f)
            
    # Process each class group
    for num in sorted(class_files.keys()):
        flist = class_files[num]
        video = summary = vtt = reading = html = None
        
        for f in flist:
            fname = f['name']
            fid = f['id']
            # mime = f['mimeType']
            
            if fname.endswith('.mp4'):
                video = fid
                video_name = fname
            elif fname.endswith('_summary.html'):
                summary = fid
            elif fname.endswith('.vtt'):
                vtt = fid
            elif 'Lecturas recomendadas' in fname and fname.endswith('.txt'):
                reading = fid
            elif fname.endswith('.html') and not fname.endswith('_summary.html'):
                html = fid
                html_name = fname

        name = ""
        if video:
            name = video_name.rsplit('.', 1)[0]
            name = name.split('. ', 1)[-1] if '. ' in name else name
        elif html:
            name = html_name.rsplit('.', 1)[0]
            name = name.split('. ', 1)[-1] if '. ' in name else name
        else:
            continue
            
        classes.append({
            'num': num,
            'name': name[:100],
            'hasVideo': video is not None,
            'hasSummary': summary is not None,
            'hasSubtitles': vtt is not None,
            'hasReading': reading is not None,
            'hasHtml': html is not None and video is None,
            'files': {
                'video': video,       # Stores Drive ID
                'summary': summary,   # Stores Drive ID
                'subtitles': vtt,     # Stores Drive ID
                'reading': reading,   # Stores Drive ID
                'html': html          # Stores Drive ID
            }
        })
        
    return classes

def scan_drive_course(course_folder_id):
    """Recursively scan a course folder on Drive."""
    modules = []
    has_presentation = False
    
    try:
        items = drive_service.list_files(course_folder_id)
    except Exception as e:
        print(f"❌ Error scanning course {course_folder_id}: {e}")
        return modules, has_presentation

    # Check for subfolders (modules)
    subfolders = [f for f in items if f['mimeType'] == 'application/vnd.google-apps.folder']
    
    # Sort subfolders
    def get_sort_key_drive(f):
        return get_sort_key(f['name'])
    
    subfolders.sort(key=get_sort_key_drive)
    
    if subfolders:
        for folder in subfolders:
            classes = scan_drive_classes(folder['id'])
            name = folder['name'].split('. ', 1)[-1] if '. ' in folder['name'] else folder['name']
            modules.append({
                'name': name,
                'folderName': folder['name'],
                'classes': classes,
                'classCount': len(classes)
            })
    else:
        # Flat structure check
        flat_classes = scan_drive_classes(course_folder_id)
        if flat_classes:
            modules = [{
                'name': 'Contenido',
                'folderName': '',
                'classes': flat_classes,
                'classCount': len(flat_classes)
            }]
            
    # Check for presentation
    for f in items:
        if f['name'] == 'presentation.html':
            has_presentation = True # We can return ID if needed
            # For now boolean is enough, logic elsewhere might assume local file?
            # actually app.js expects presentationId if hasPresentation is true? 
            # rebuild_cache populated presentationId in original code from old cache.
            # Let's adjust main logic to support presentationId.
    
    return modules, has_presentation


def match_course_to_drive(md_name, drive_courses):
    """Match MD course name to a Drive folder item."""
    san = sanitize_for_match(md_name)
    
    # Create maps
    exact_map = {sanitize_for_match(c['name']): c for c in drive_courses}
    
    # 1. Exact match
    if san in exact_map:
        return exact_map[san], "exact"
    
    # 2. Prefix match
    for c in drive_courses:
        c_san = sanitize_for_match(c['name'])
        if (san.startswith(c_san) or c_san.startswith(san)) and len(san) > 10:
             return c, "prefix"
             
    # 3. Fuzzy overlap
    san_words = set(san.split())
    best_match = None
    best_overlap = 0
    
    for c in drive_courses:
        c_san = sanitize_for_match(c['name'])
        c_words = set(c_san.split())
        
        overlap = len(san_words & c_words)
        min_len = min(len(san_words), len(c_words))
        
        if min_len > 0 and overlap / min_len >= 0.8 and overlap > best_overlap:
            best_overlap = overlap
            best_match = c
            
    if best_match and best_overlap >= 3:
        return best_match, "fuzzy"
        
    return None, None


def main():
    print("=" * 60)
    print("📦 Rebuilding courses_cache.json with Drive Scan")
    print("=" * 60)
    
    # 1. Parse PlatziRoutes.md
    print("\n📖 Parsing PlatziRoutes.md...")
    parsed = parse_routes.parse()
    categories = parsed['categories']
    print(f"   {len(categories)} categories found.")
    
    # 2. Scan Drive Root
    drive_courses = []
    if DRIVE_AVAILABLE:
        drive_courses = scan_drive_root(DRIVE_ROOT_ID)
        print(f"   ☁️ Found {len(drive_courses)} folders in Drive root.")
    else:
        print("   ⚠️ Drive scanning skipped (unavailable).")

    # 3. Match and Build
    print("\n🔗 Matching and Scanning...")
    total_matched_drive = 0
    total_local = 0
    total_classes = 0
    
    for cat in categories:
        for route in cat['routes']:
            enriched_courses = []
            for course in route.get('courses', []):
                md_name = course['name']
                
                # Default empty course structure
                enriched = {
                    'name': md_name,
                    'folderName': '',
                    'url': course.get('url', ''),
                    'modules': [],
                    'moduleCount': 0,
                    'classCount': 0,
                    'foundInDrive': False
                }
                
                # Try Drive Match
                drive_match = None
                if drive_courses:
                    match, mtype = match_course_to_drive(md_name, drive_courses)
                    if match:
                        drive_match = match
                        # print(f"   ✅ Matched: {md_name} -> {match['name']} ({mtype})")
                
                if drive_match:
                    # Scan content from Drive
                    print(f"   ☁️ Scanning Drive: {drive_match['name']}...")
                    modules, has_pres = scan_drive_course(drive_match['id'])
                    
                    if modules:
                        enriched['foundInDrive'] = True
                        enriched['folderName'] = drive_match['name']
                        enriched['matchedFolder'] = drive_match['name'] # Legacy compat
                        enriched['modules'] = modules
                        enriched['moduleCount'] = len(modules)
                        enriched['hasPresentation'] = has_pres
                        
                        cc = sum(len(m['classes']) for m in modules)
                        enriched['classCount'] = cc
                        total_matched_drive += 1
                        total_classes += cc
                    else:
                        print(f"      ⚠️ Folder matched but empty/error: {drive_match['name']}")
                
                # Fallback: Check local filesystem if not found in Drive or empty
                if not enriched['foundInDrive']:
                    # Try to guess local folder name (often same as MD name without special chars)
                    # For simplicity, we can try matching against local directories using the same logic if needed
                    # checking COURSES_PATH
                    pass 

                enriched_courses.append(enriched)
            
            route['courses'] = enriched_courses
            route['courseCount'] = len(enriched_courses)

    # 4. Save
    # Recalculate stats
    total_routes = sum(len(cat['routes']) for cat in categories)
    total_courses_count = sum(route['courseCount'] for cat in categories for route in cat['routes'])
    
    result = {
        'categories': categories,
        'stats': {
            'totalCategories': len(categories),
            'totalRoutes': total_routes,
            'totalCourses': total_courses_count,
            'totalClasses': total_classes
        }
    }
    
    print(f"\n💾 Saving {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ Done!")
    print(f"   Drive Matches: {total_matched_drive}")
    print(f"   Total Classes: {total_classes}")

if __name__ == '__main__':
    main()
