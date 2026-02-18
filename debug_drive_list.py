
from drive_service import drive_service

ROOT_ID = "17kPqqPSheDtQ5S1HM6Qvvh2qJ7O3YADm"

def list_root_contents():
    print(f"📂 Listando contenido de {ROOT_ID}...")
    files = drive_service.list_files(ROOT_ID)
    print(f"Total archivos/carpetas encontrados: {len(files)}")
    
    for f in files[:20]:
        print(f"{f['name']} ({f['mimeType']})")

if __name__ == "__main__":
    list_root_contents()
