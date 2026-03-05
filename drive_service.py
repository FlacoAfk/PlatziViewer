import json
import os
import os.path
import sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import AuthorizedSession, Request as GoogleAuthRequest
import threading
import re
import time

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
DRIVE_ID_RE = re.compile(r'^[A-Za-z0-9_-]{10,}$')


def _candidate_service_account_paths():
    candidates = []
    env_path = os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE')
    if env_path:
        candidates.append(env_path)

    # PyInstaller onefile/onedir location
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        candidates.append(os.path.join(exe_dir, 'service_account.json'))

    # Local working directory and repository directory
    candidates.append(os.path.join(os.getcwd(), 'service_account.json'))
    candidates.append(os.path.join(os.path.dirname(__file__), 'service_account.json'))

    unique = []
    seen = set()
    for path in candidates:
        if not path:
            continue
        normalized = os.path.abspath(path)
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)

    return unique


class DriveService:
    def __init__(self):
        self.creds = None
        self.service_account_source = None
        self._thread_local = threading.local()
        self._shared_session = None
        self._shared_session_lock = threading.Lock()
        self.authenticate()

    def authenticate(self):
        service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if service_account_json:
            try:
                service_info = json.loads(service_account_json)
            except json.JSONDecodeError as e:
                raise Exception('GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON') from e

            self.creds = Credentials.from_service_account_info(
                service_info, scopes=SCOPES
            )
            self.service_account_source = 'env:GOOGLE_SERVICE_ACCOUNT_JSON'
        else:
            selected_path = None
            for candidate_path in _candidate_service_account_paths():
                if os.path.exists(candidate_path):
                    selected_path = candidate_path
                    break

            if not selected_path:
                searched = _candidate_service_account_paths()
                searched_text = ', '.join(searched)
                raise Exception(
                    'Service account file not found. '
                    'Set GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON. '
                    f'Searched: {searched_text}'
                )

            self.creds = Credentials.from_service_account_file(
                selected_path, scopes=SCOPES
            )
            self.service_account_source = selected_path

        try:
            if not self.creds.valid or self.creds.expired:
                self.creds.refresh(GoogleAuthRequest())
        except Exception as e:
            print(f"[WARN] Could not pre-refresh Drive credentials: {e}")

        print(f"[INFO] Drive credentials loaded from: {self.service_account_source}")

    def _validate_drive_id(self, value, field_name='id'):
        if not isinstance(value, str) or not DRIVE_ID_RE.match(value.strip()):
            raise ValueError(f'Invalid Google Drive {field_name}')
        return value.strip()

    def get_service(self):
        if not hasattr(self._thread_local, 'service'):
            self._thread_local.service = build('drive', 'v3', credentials=self.creds, cache_discovery=False)
        return self._thread_local.service

    def _get_session(self):
        # Shared session avoids cold-start latency on each per-request thread.
        if self._shared_session is None:
            with self._shared_session_lock:
                if self._shared_session is None:
                    session = AuthorizedSession(self.creds)
                    session.headers.update({'Accept-Encoding': 'identity'})
                    self._shared_session = session
        return self._shared_session

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
        folder_id = self._validate_drive_id(folder_id, 'folder_id')
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
                    print(f"[WARN] Drive API Error listing files (try {retry_count}/{max_retries}): {e}")
                    print(f"   Query: {query}")
                    print(f"   Waiting {wait_time}s...")
                    import time
                    time.sleep(wait_time)
            
            if not success:
                print(f"[ERROR] Falló listado de carpeta {folder_id} tras {max_retries} intentos.")
                break

            files = results.get('files', [])
            files_list.extend(files)
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
            page_num += 1
            
        return files_list

    def get_file_metadata(self, file_id):
        file_id = self._validate_drive_id(file_id, 'file_id')
        retry_count = 0
        max_retries = 3
        session = self._get_session()
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
        params = {
            'fields': 'id,name,mimeType,size',
            'supportsAllDrives': 'true',
        }
        
        while retry_count < max_retries:
            try:
                response = session.get(url, params=params, timeout=(5, 30))
                response.raise_for_status()
                return response.json()
            except Exception as e:
                retry_count += 1
                wait_time = 2 ** retry_count
                print(f"[WARN] Error obteniendo metadata {file_id} (intento {retry_count}/{max_retries}): {e}. Esperando {wait_time}s...")
                time.sleep(wait_time)
        raise Exception(f"Failed to get metadata for {file_id}")

    def is_folder(self, file_metadata):
        return file_metadata.get('mimeType') == 'application/vnd.google-apps.folder'

    def list_files_with_metadata(self, folder_id):
        """Lista archivos con metadata detallada."""
        return self.list_files(folder_id)

    def download_file_range(self, file_id, start=None, end=None, range_header=None):
        """Descarga un rango de bytes de un archivo."""
        file_id = self._validate_drive_id(file_id, 'file_id')
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
        
        session = self._get_session()
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
        headers = {}
        params = {
            'alt': 'media',
            'supportsAllDrives': 'true',
        }
        if range_header:
            headers['Range'] = str(range_header).strip()
        elif start is not None or end is not None:
            generated_range = f"bytes={start if start is not None else ''}-{end if end is not None else ''}"
            headers['Range'] = generated_range

        response = session.get(url, headers=headers, params=params, stream=True, timeout=(5, 60))
        response.raise_for_status()
        return response

drive_service = DriveService()
