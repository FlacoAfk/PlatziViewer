
import os.path
import io
import google.auth
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import AuthorizedSession
import threading

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), 'service_account.json')

class DriveService:
    def __init__(self):
        self.creds = None
        self._thread_local = threading.local()
        self.authenticate()

    def authenticate(self):
        if os.path.exists(SERVICE_ACCOUNT_FILE):
             self.creds = Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        else:
            raise Exception("service_account.json not found")

    def get_service(self):
        if not hasattr(self._thread_local, 'service'):
            self._thread_local.service = build('drive', 'v3', credentials=self.creds)
        return self._thread_local.service

    def find_folder(self, name, parent_id=None):
        """Busca una carpeta por nombre."""
        query = f"mimeType='application/vnd.google-apps.folder' and name='{name}' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        # Ordenar por nombre para consistencia
        service = self.get_service()
        results = service.files().list(
            q=query, 
            fields="files(id, name)",
            orderBy="name"
        ).execute()
        files = results.get('files', [])
        if files:
            return files[0]['id']
        return None

    def list_files(self, folder_id):
        """Lista archivos y carpetas en un directorio con reintentos."""
        files_list = []
        page_token = None
        query = f"'{folder_id}' in parents and trashed = false"
        
        service = self.get_service()
        
        page_num = 1
        while True:
            retry_count = 0
            max_retries = 5
            success = False
            
            while not success and retry_count < max_retries:
                try:
                    # print(f"Fetching page {page_num} for folder {folder_id}...")
                    results = service.files().list(
                        q=query, 
                        fields="nextPageToken, files(id, name, mimeType, size)", 
                        pageSize=500,
                        pageToken=page_token,
                        orderBy="name"
                    ).execute()
                    success = True
                except Exception as e:
                    retry_count += 1
                    wait_time = 2 ** retry_count
                    print(f"⚠️ Drive API Error listing files (try {retry_count}/{max_retries}): {e}")
                    print(f"   Query: {query}")
                    print(f"   Waiting {wait_time}s...")
                    import time
                    time.sleep(wait_time)
            
            if not success:
                print(f"❌ Falló listado de carpeta {folder_id} tras {max_retries} intentos.")
                break

            files = results.get('files', [])
            files_list.extend(files)
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
            page_num += 1
            
        return files_list

    def get_file_metadata(self, file_id):
        service = self.get_service()
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                return service.files().get(fileId=file_id, fields="id, name, mimeType, size").execute()
            except Exception as e:
                retry_count += 1
                wait_time = 2 ** retry_count
                print(f"⚠️ Error obteniendo metadata {file_id} (intento {retry_count}/{max_retries}): {e}. Esperando {wait_time}s...")
                import time
                time.sleep(wait_time)
        raise Exception(f"Failed to get metadata for {file_id}")

    def is_folder(self, file_metadata):
        return file_metadata.get('mimeType') == 'application/vnd.google-apps.folder'

    def list_files_with_metadata(self, folder_id):
        """Lista archivos con metadata detallada."""
        return self.list_files(folder_id)

    def download_file_range(self, file_id, start=None, end=None):
        """Descarga un rango de bytes de un archivo."""
        # build the URL manually to use with requests/authorized session?
        # OR use api client.
        # using requests is better for streaming?
        # self.creds.refresh(Request()) ?
        
        # Actually, google-api-python-client `MediaIoBaseDownload` is for downloading to a file-like object.
        # For streaming to an HTTP response, we might want to get the raw stream.
        
        # Method 1: Use `files().get_media` and manually handle request?
        # Method 2: Use `service._http` (authorized http) to make GET request.
        
        # My previous implementation used `self.authed_session` which I removed from __init__ 
        # in this replacement. I need to keep `authed_session` logic BUT it must also be thread safe or 
        # re-created.
        
        # `AuthorizedSession` from `google.auth.transport.requests` is a `requests.Session`.
        # `requests.Session` is theoretically thread-safe, but if we modify headers...
        
        # Let's create a thread-local session too.
        
        if not hasattr(self._thread_local, 'session'):
             self._thread_local.session = AuthorizedSession(self.creds)
        
        session = self._thread_local.session
        
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        headers = {}
        if start is not None or end is not None:
             range_header = f"bytes={start if start is not None else ''}-{end if end is not None else ''}"
             headers['Range'] = range_header

        response = session.get(url, headers=headers, stream=True, timeout=(5, 15))
        response.raise_for_status()
        return response

drive_service = DriveService()
