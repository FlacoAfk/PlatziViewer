
import os
import json
from drive_service import drive_service

FOLDER_ID = "17kPqqPSheDtQ5S1HM6Qvvh2qJ7O3YADm"

def list_folder_recursive(folder_id, depth=0, max_depth=2):
    if depth > max_depth:
        return
    
    print(f"{'  ' * depth}📂 Scanning folder {folder_id}...")
    try:
        files = drive_service.list_files(folder_id)
        print(f"{'  ' * depth}   Found {len(files)} items.")
        
        for f in files[:20]: # Limit to 20 items per folder for debug
            name = f['name']
            mime = f['mimeType']
            fid = f['id']
            print(f"{'  ' * depth}   - {name} [{mime}] ({fid})")
            
            if mime == 'application/vnd.google-apps.folder':
                # Recurse a bit to verify structure
                list_folder_recursive(fid, depth + 1, max_depth)
                
    except Exception as e:
        print(f"❌ Error scanning {folder_id}: {e}")

def main():
    print("🚀 Starting Drive API Debug...")
    print(f"Target Folder: {FOLDER_ID}")
    
    try:
        # Check if service account exists
        if not os.path.exists('service_account.json'):
            print("❌ service_account.json not found!")
            return

        # Test listing
        list_folder_recursive(FOLDER_ID, max_depth=2)
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")

if __name__ == '__main__':
    main()
