"""
Google Drive integration for cloud synchronization.
"""
import os
import io
import logging
import hashlib
import threading
import time
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from fuse_fs import config
from fuse_fs.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class GoogleDriveSync:
    """Google Drive synchronization for FUSE filesystem."""
    
    def __init__(self, storage_path=None):
        """Initialize Google Drive synchronization."""
        self.storage_path = storage_path or config.DEFAULT_STORAGE_PATH
        self.credentials_file = config.GOOGLE_CREDENTIALS_FILE
        self.token_file = config.GOOGLE_TOKEN_FILE
        self.scopes = config.GOOGLE_API_SCOPES
        
        # Initialize database connection
        self.db = DatabaseManager()
        
        # Map of local path hashes to Google Drive file IDs
        self.file_id_map = {}
        
        # For thread safety
        self.lock = threading.Lock()
        
        # Initialize Google Drive service
        self.service = self._get_drive_service()
        
        # Thread for background synchronization
        self.sync_thread = None
        self.stop_sync = threading.Event()
        
        # Load existing file mapping
        self._load_file_mapping()
        
        logger.info("Initialized Google Drive synchronization")
    
    def _get_drive_service(self):
        """Get authenticated Google Drive service."""
        creds = None
        
        # Check if token.json exists
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_info(
                    info=eval(open(self.token_file, 'r').read()),
                    scopes=self.scopes
                )
            except Exception as e:
                logger.error(f"Error loading credentials from token file: {e}")
        
        # If credentials don't exist or are invalid, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {e}")
                    creds = None
            
            # If still no valid credentials, start OAuth flow
            if not creds:
                if not os.path.exists(self.credentials_file):
                    logger.error(f"Credentials file {self.credentials_file} not found")
                    return None
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.scopes)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    logger.error(f"Error during OAuth flow: {e}")
                    return None
            
            # Save the credentials for the next run
            try:
                with open(self.token_file, 'w') as token:
                    token.write(str(creds.to_json()))
            except Exception as e:
                logger.error(f"Error saving credentials to token file: {e}")
        
        try:
            # Build the service
            service = build('drive', 'v3', credentials=creds)
            logger.info("Successfully authenticated with Google Drive")
            return service
        except Exception as e:
            logger.error(f"Error building Drive service: {e}")
            return None
    
    def _load_file_mapping(self):
        """Load existing file mapping from database."""
        with self.lock:
            # Query database for files with Google Drive IDs
            files = self.db.get_files_with_drive_ids()
            
            for file in files:
                file_hash = self._hash_path(file['path'])
                self.file_id_map[file_hash] = file['google_drive_id']
    
    def _hash_path(self, path):
        """Create a hash for the file path."""
        return hashlib.sha256(path.encode()).hexdigest()
    
    def _hash_file_content(self, file_path):
        """Create a SHA-256 hash of file content for deduplication."""
        if not os.path.exists(file_path):
            return None
            
        try:
            sha256_hash = hashlib.sha256()
            
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
                    
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error hashing file {file_path}: {e}")
            return None
    
    def _full_path(self, partial_path):
        """Helper to get the full path for a file in the storage directory."""
        if partial_path.startswith("/"):
            partial_path = partial_path[1:]
        path = os.path.join(self.storage_path, partial_path)
        return path
    
    def _check_file_exists_by_hash(self, file_hash):
        """Check if file with the same content (hash) exists on Google Drive."""
        if not self.service:
            return None
            
        try:
            # Search for file with the same hash property
            query = f"appProperties has {{ key='content_hash' and value='{file_hash}' }}"
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = response.get('files', [])
            if files:
                return files[0]['id']
            
            return None
        except Exception as e:
            logger.error(f"Error checking file exists by hash: {e}")
            return None
    
    def _create_file_hierarchy(self, path):
        """Create directory hierarchy on Google Drive to match the local path."""
        if not self.service:
            return None
            
        # Split path into components
        path_parts = path.strip('/').split('/')
        
        # If it's just a filename, no hierarchy needed
        if len(path_parts) <= 1:
            return 'root'
            
        # Directory path (without the filename)
        dir_path = '/'.join(path_parts[:-1])
        
        # Check if we already have this path mapped
        dir_hash = self._hash_path(dir_path)
        if dir_hash in self.file_id_map:
            return self.file_id_map[dir_hash]
        
        # Start from root
        parent_id = 'root'
        current_path = ''
        
        # Create each directory in the path if needed
        for i, part in enumerate(path_parts[:-1]):
            if not part:
                continue
                
            current_path = current_path + '/' + part if current_path else part
            current_hash = self._hash_path(current_path)
            
            # Check if we already have this directory
            if current_hash in self.file_id_map:
                parent_id = self.file_id_map[current_hash]
                continue
            
            # Search for the directory in the current parent
            query = f"name='{part}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            items = response.get('files', [])
            
            if items:
                # Directory exists
                directory_id = items[0]['id']
            else:
                # Create directory
                file_metadata = {
                    'name': part,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_id]
                }
                
                try:
                    directory = self.service.files().create(
                        body=file_metadata,
                        fields='id'
                    ).execute()
                    directory_id = directory.get('id')
                except Exception as e:
                    logger.error(f"Error creating directory {part}: {e}")
                    return parent_id
            
            # Update parent for next iteration
            parent_id = directory_id
            
            # Update mapping
            self.file_id_map[current_hash] = parent_id
        
        return parent_id
    
    def start_background_sync(self):
        """Start background synchronization thread."""
        if self.sync_thread and self.sync_thread.is_alive():
            logger.warning("Background sync is already running")
            return
            
        self.stop_sync.clear()
        self.sync_thread = threading.Thread(
            target=self._background_sync_task,
            daemon=True
        )
        self.sync_thread.start()
        logger.info("Started background synchronization thread")
    
    def stop_background_sync(self):
        """Stop background synchronization thread."""
        if not self.sync_thread:
            return
            
        self.stop_sync.set()
        self.sync_thread.join(timeout=5)
        logger.info("Stopped background synchronization thread")
    
    def _background_sync_task(self):
        """Background task for synchronizing files to Google Drive."""
        while not self.stop_sync.is_set():
            try:
                # Get files that need to be synced
                files_to_sync = self.db.get_files_for_sync(limit=10)
                
                if files_to_sync:
                    logger.info(f"Found {len(files_to_sync)} files to sync")
                    
                    for file_info in files_to_sync:
                        if self.stop_sync.is_set():
                            break
                            
                        file_id = file_info['id']
                        file_path = file_info['path']
                        
                        # Sync file
                        success, drive_id, error = self.sync_file(file_path)
                        
                        # Update database with sync status
                        self.db.update_sync_status(file_id, success, drive_id, error)
                
                # Sleep before checking again
                for _ in range(config.SYNC_INTERVAL):
                    if self.stop_sync.is_set():
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in background sync task: {e}")
                time.sleep(60)  # Sleep for a minute if there's an error
    
    def sync_file(self, path):
        """Synchronize a file to Google Drive."""
        if not self.service:
            return False, None, "Google Drive service not initialized"
            
        # Get full path
        full_path = self._full_path(path)
        
        if not os.path.exists(full_path):
            return False, None, f"File not found: {full_path}"
            
        if os.path.isdir(full_path):
            # For directories, just create the folder structure
            parent_id = self._create_file_hierarchy(path)
            return True, parent_id, None
        
        try:
            # Compute file hash for deduplication
            file_hash = self._hash_file_content(full_path)
            
            if not file_hash:
                return False, None, f"Unable to compute hash for {full_path}"
                
            # Check if file with same content already exists on Drive
            existing_file_id = self._check_file_exists_by_hash(file_hash)
            
            if existing_file_id:
                # File already exists, update our mapping
                path_hash = self._hash_path(path)
                self.file_id_map[path_hash] = existing_file_id
                logger.info(f"File already exists on Drive (deduplication): {path}")
                return True, existing_file_id, None
            
            # Get or create parent folder
            parent_id = self._create_file_hierarchy(path)
            
            # File metadata
            filename = os.path.basename(path)
            file_metadata = {
                'name': filename,
                'parents': [parent_id],
                'appProperties': {
                    'content_hash': file_hash,
                    'original_path': path
                }
            }
            
            # Check if file already exists (by path)
            path_hash = self._hash_path(path)
            update = path_hash in self.file_id_map
            
            if update:
                # Update existing file
                file_id = self.file_id_map[path_hash]
                
                # Remove parents field for update
                del file_metadata['parents']
                
                media = MediaFileUpload(full_path, resumable=True)
                file = self.service.files().update(
                    fileId=file_id,
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                
                logger.info(f"Updated file on Drive: {path}")
                return True, file_id, None
            else:
                # Create new file
                media = MediaFileUpload(full_path, resumable=True)
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                
                file_id = file.get('id')
                self.file_id_map[path_hash] = file_id
                
                logger.info(f"Created file on Drive: {path}")
                return True, file_id, None
                
        except Exception as e:
            error_msg = f"Error syncing file {path}: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def download_file(self, path, drive_id=None):
        """Download a file from Google Drive."""
        if not self.service:
            return False, "Google Drive service not initialized"
            
        try:
            # Get file ID
            file_id = drive_id
            if not file_id:
                path_hash = self._hash_path(path)
                file_id = self.file_id_map.get(path_hash)
                
            if not file_id:
                return False, f"File not found on Drive: {path}"
                
            # Get full local path
            full_path = self._full_path(path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Download file
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                
            # Save to file
            with open(full_path, 'wb') as f:
                f.write(fh.getvalue())
                
            logger.info(f"Downloaded file from Drive: {path}")
            return True, None
            
        except Exception as e:
            error_msg = f"Error downloading file {path}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg 