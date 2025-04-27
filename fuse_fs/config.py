"""
Configuration settings for the FUSE Virtual File System.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MOUNT_POINT = os.getenv('MOUNT_POINT', os.path.expanduser('~/fuse_mount'))
DEFAULT_STORAGE_PATH = os.getenv('STORAGE_PATH', os.path.expanduser('~/fuse_storage'))

# MySQL database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'fuse_fs'),
    'port': int(os.getenv('DB_PORT', '3306')),
}

# Google Drive API settings
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
GOOGLE_TOKEN_FILE = os.getenv('GOOGLE_TOKEN_FILE', 'token.json')
GOOGLE_API_SCOPES = ['https://www.googleapis.com/auth/drive']

# LFU Cache settings
CACHE_SIZE = int(os.getenv('CACHE_SIZE', '100'))  # Number of files to cache
CACHE_DIR = os.getenv('CACHE_DIR', os.path.join(DEFAULT_STORAGE_PATH, 'cache'))

# Sync settings
SYNC_INTERVAL = int(os.getenv('SYNC_INTERVAL', '300'))  # In seconds (default: 5 minutes)
MAX_SYNC_RETRIES = int(os.getenv('MAX_SYNC_RETRIES', '3'))

# Security settings
ENCRYPTION_ENABLED = os.getenv('ENCRYPTION_ENABLED', 'False').lower() == 'true'
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', '')

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', os.path.join(BASE_DIR, 'fuse_fs.log'))

# Performance tuning
BUFFER_SIZE = int(os.getenv('BUFFER_SIZE', '4096'))  # Read/write buffer size in bytes 