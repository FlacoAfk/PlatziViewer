import re

with open("DriveCourses.md", "r", encoding="utf-8") as f:
    drive_lines = f.readlines()
drive_courses = set()
for line in drive_lines:
    line = line.strip()
    if line.startswith("- "):
        drive_courses.add(line[2:].strip())

with open("PlatziRoutes.md", "r", encoding="utf-8") as f:
    md = f.read()

course_pattern = re.compile(r"^- \[(.+?)\]\((.+?)\)\s*$", re.MULTILINE)
md_courses = set(m[0] for m in course_pattern.findall(md))


def sanitize(name):
    name = name.strip().replace(":", "").replace("/", "").replace(",", "")
    cleaned = []
    for ch in name:
        cp = ord(ch)
        if cp < 0x250 or ch in "().,;!-+&@#%=":
            cleaned.append(ch)
    name = "".join(cleaned)
    return re.sub(r"\s+", " ", name).strip()


md_san = {sanitize(c): c for c in md_courses}

still_missing = []
for dc in sorted(drive_courses):
    dc_san = sanitize(dc)
    if dc_san not in md_san:
        still_missing.append((dc, dc_san))

print(f"Still missing: {len(still_missing)}")
for c, s in still_missing:
    print(f'  Drive: "{c}"')
    print(f'    San: "{s}"')
    # Find closest match
    best = None
    best_score = 0
    for ms, orig in md_san.items():
        words_dc = set(s.lower().split())
        words_md = set(ms.lower().split())
        overlap = len(words_dc & words_md)
        if overlap > best_score:
            best_score = overlap
            best = (ms, orig)
    if best:
        print(f'    Best: "{best[1]}" (san: "{best[0]}", overlap: {best_score})')
    print()
