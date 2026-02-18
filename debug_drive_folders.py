
from drive_service import drive_service

ROOT_ID = "17kPqqPSheDtQ5S1HM6Qvvh2qJ7O3YADm"

def list_root_folders():
    print(f"📂 Listando carpetas en {ROOT_ID}...")
    
    # Query only for folders
    query = f"'{ROOT_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    service = drive_service.get_service()
    
    results = service.files().list(
        q=query, 
        fields="files(id, name)", 
        pageSize=50
    ).execute()
    
    files = results.get('files', [])
    print(f"Total carpetas encontradas: {len(files)}")
    
    for f in files:
        print(f"📁 {f['name']} ({f['id']})")

if __name__ == "__main__":
    list_root_folders()
