
import os

COURSES_PATH = r"H:\Mi unidad\PlatziCoursesFlat"
OUTPUT_FILE = "DriveCourses.md"

def get_sort_key(name):
    # Normalize for sorting
    return name.lower()

def main():
    print(f"Scanning {COURSES_PATH}...")
    
    if not os.path.exists(COURSES_PATH):
        print(f"Error: Path {COURSES_PATH} does not exist.")
        return

    md_lines = ["# Platzi Courses (Drive Scan)", ""]
    
    try:
        # List all directories, assuming they are courses
        courses = sorted([d for d in os.listdir(COURSES_PATH) 
                        if os.path.isdir(os.path.join(COURSES_PATH, d)) and not d.startswith('.')])
    except Exception as e:
        print(f"Error reading root: {e}")
        return

    count = len(courses)
    md_lines.append(f"**Total Courses found:** {count}\n")
    
    # Group by first letter for better readability? Or just a flat list.
    # User asked for "un .md de los nombres", a simple list is best.
    
    for course in courses:
        md_lines.append(f"- {course}")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    
    print(f"\nDone! Generated {OUTPUT_FILE} with {count} courses.")

if __name__ == "__main__":
    main()
