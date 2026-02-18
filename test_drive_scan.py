
import sys
import os
import json

# Add current dir to path
sys.path.append(os.getcwd())

from server import scan_drive_structure, DRIVE_ROOT_ID, load_course_metadata

print("🔍 Testing scan_drive_structure...")
print(f"Root ID: {DRIVE_ROOT_ID}")

# Load metadata first to check if it works
print("Loading metadata...")
mapping = load_course_metadata()
print(f"Metadata entries: {len(mapping)}")

# Run scan
print("Running Drive Scan (this might take time)...")
result = scan_drive_structure(DRIVE_ROOT_ID)

print("\n--- SCAN RESULT ---")
print(f"Categories: {len(result['categories'])}")
print(f"Stats: {result['stats']}")

# Check for drive: paths
found_drive_path = False
for cat in result['categories']:
    for route in cat['routes']:
        courses = route.get('courses', [])
        for course in courses:
            print(f"Course: {course['name']}")
            if course.get('modules'):
                # Check first module/class
                first_mod = course['modules'][0]
                if first_mod.get('classes'):
                     first_class = first_mod['classes'][0]
                     print(f"  First Class: {first_class['name']}")
                     print(f"  Files: {first_class['files']}")
                     if 'drive:' in str(first_class['files']):
                         found_drive_path = True
            break # Only check one course per route
        if found_drive_path: break
    if found_drive_path: break

if found_drive_path:
    print("\n✅ SUCCESS: Found 'drive:' paths in output!")
else:
    print("\n❌ FAILURE: No 'drive:' paths found.")
