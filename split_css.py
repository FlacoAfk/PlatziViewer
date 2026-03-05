import os
import re

CSS_DIR = "css"
MAPPINGS = {
    # Base
    "CSS Variables & Reset": "base/_reset.css",
    "App Container": "base/_reset.css",
    "Scrollbar": "base/_reset.css",
    "Animations": "base/_animations.css",

    # Layouts
    "Navigation": "layouts/_navbar.css",
    "Mobile Navbar Styles": "layouts/_navbar.css",
    "Grid Layout": "layouts/_grid.css",
    "Course 2-Column Layout": "layouts/_grid.css",

    # Components
    "Route Card": "components/_cards.css",
    "Course Card (in timeline)": "components/_cards.css",
    "Class Card": "components/_cards.css",
    "Buttons": "components/_buttons.css",
    "Loading": "components/_loading.css",
    "Error & Empty States": "components/_states.css",
    "Availability Indicators": "components/_states.css",

    # Views
    "Hero Section": "views/_home.css",
    "Categories": "views/_home.css",
    "Routes Sections": "views/_home.css",
    "Route View": "views/_route-view.css",
    "Timeline": "views/_route-view.css",
    "Breadcrumb": "views/_route-view.css",
    "Explore View": "views/_route-view.css",
    "Course View": "views/_course-view.css",
    "Syllabus": "views/_course-view.css",
    "Module Accordion": "views/_course-view.css",
    "Learning View": "views/_course-view.css",
    "Player View (YouTube-Style)": "views/_player-view.css",
    "Player Sidebar (Redesigned)": "views/_player-view.css",
    "Responsive": "views/_responsive.css",
}

def setup_dirs():
    os.makedirs("css/base", exist_ok=True)
    os.makedirs("css/layouts", exist_ok=True)
    os.makedirs("css/components", exist_ok=True)
    os.makedirs("css/views", exist_ok=True)

def parse_css():
    with open("styles.css", "r", encoding="utf-8") as f:
        content = f.read()

    # Split using the headers
    # The regex finds "/* ===== HEADER ===== */"
    pattern = re.compile(r'/\*\s*=====\s*(.*?)\s*=====\s*\*/')
    
    # We want to keep everything before the first header (usually empty or just comments)
    blocks = []
    last_pos = 0
    current_header = None
    
    for match in pattern.finditer(content):
        header = match.group(1).strip()
        # Text from last pos to start of this match is the body for the previous header
        if current_header:
            body = content[last_pos:match.start()].strip()
            blocks.append((current_header, body))
        
        current_header = header
        last_pos = match.end()
        
    # Add the last block
    if current_header:
        body = content[last_pos:].strip()
        blocks.append((current_header, body))
        
    return blocks

def generate_files(blocks):
    file_contents = {}
    
    for header, body in blocks:
        if header not in MAPPINGS:
            print(f"Warning: Unknown section '{header}', putting it in views/_misc.css")
            file_path = "views/_misc.css"
        else:
            file_path = MAPPINGS[header]
            
        full_path = os.path.join(CSS_DIR, file_path)
        
        if full_path not in file_contents:
            file_contents[full_path] = ""
            
        file_contents[full_path] += f"\n/* ===== {header} ===== */\n{body}\n\n"
        
    # Write to files
    for path, text in file_contents.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.strip() + "\n")
            
    # Generate main.css
    main_imports = []
    
    # Define import order explicitly
    sections = ["base", "layouts", "components", "views"]
    
    for section in sections:
        section_dir = os.path.join(CSS_DIR, section)
        if os.path.exists(section_dir):
            files = sorted([f for f in os.listdir(section_dir) if f.endswith('.css')])
            
            # special sorting for base to ensure variables/reset are first
            if section == "base":
                if "_reset.css" in files:
                    files.remove("_reset.css")
                    files.insert(0, "_reset.css")
                    
            for file in files:
                main_imports.append(f"@import '{section}/{file}';")
                
    with open(os.path.join(CSS_DIR, "main.css"), "w", encoding="utf-8") as f:
        f.write("/* ===== Main CSS Entry File ===== */\n")
        f.write("\n".join(main_imports) + "\n")
        
    print(f"✅ Extracted {len(blocks)} sections into CSS modular files.")

if __name__ == "__main__":
    setup_dirs()
    blocks = parse_css()
    generate_files(blocks)
