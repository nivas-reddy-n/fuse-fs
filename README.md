# FUSE Virtual File System

A FUSE-based virtual file system with metadata storage, cloud synchronization, and LFU caching.

## Features

- **FUSE Integration**: Mount a virtual file system that works with standard tools and applications
- **Metadata Storage**: Store and query file metadata using MySQL database
- **LFU Caching**: Improve read performance with a Least Frequently Used caching system
- **Google Drive Sync**: Asynchronously synchronize files to Google Drive
- **File Deduplication**: Avoid storing duplicate files using SHA-256 hashing
- **Security**: Optional file encryption for sensitive data

## Requirements

- Python 3.7+
- MySQL Server
- FUSE kernel module (for Linux) or macFUSE (for macOS)
- Google account for Drive synchronization

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd fuse-fs
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up MySQL database:
   ```
   mysql -u root -p
   ```
   
   ```sql
   CREATE DATABASE fuse_fs;
   CREATE USER 'fuse_user'@'localhost' IDENTIFIED BY 'your-password';
   GRANT ALL PRIVILEGES ON fuse_fs.* TO 'fuse_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

4. Create a `.env` file with your configuration:
   ```
   DB_HOST=localhost
   DB_USER=fuse_user
   DB_PASSWORD=your-password
   DB_NAME=fuse_fs
   MOUNT_POINT=~/fuse_mount
   STORAGE_PATH=~/fuse_storage
   ENCRYPTION_ENABLED=False
   LOG_LEVEL=INFO
   ```

5. Set up Google Drive API:
   - Go to [Google Developer Console](https://console.developers.google.com/)
   - Create a new project
   - Enable the Google Drive API
   - Create OAuth credentials
   - Download the credentials JSON file and save it as `credentials.json` in the project directory

## Usage

### Mount the filesystem

```
python -m fuse_fs --mount ~/fuse_mount --storage ~/fuse_storage
```

Available options:
- `-m, --mount`: Mount point (default: ~/fuse_mount)
- `-s, --storage`: Storage directory (default: ~/fuse_storage)
- `-f, --foreground`: Run in foreground (for debugging)
- `-d, --debug`: Enable debug logging
- `--no-sync`: Disable Google Drive synchronization
- `--no-cache`: Disable LFU caching

### Using the filesystem

Once mounted, you can use the filesystem like any other directory:

```
cd ~/fuse_mount
touch test.txt
echo "Hello World" > test.txt
cat test.txt
```

Files are automatically:
1. Stored in the configured storage directory
2. Indexed in the MySQL database with metadata
3. Cached using LFU algorithm if frequently accessed
4. Synchronized to Google Drive in the background

### Unmount the filesystem

```
fusermount -u ~/fuse_mount   # Linux
umount ~/fuse_mount          # macOS
```

## Architecture

The system consists of several components:

1. **Core FUSE Implementation**: Implements filesystem operations
2. **Database Manager**: Handles metadata storage in MySQL
3. **LFU Cache**: Improves read performance for frequently accessed files
4. **Google Drive Sync**: Asynchronously synchronizes files to cloud storage
5. **Crypto Utilities**: Provides file encryption and decryption

## Development

### Project Structure

```
fuse_fs/
├── __init__.py
├── __main__.py
├── config.py
├── core/
│   └── filesystem.py
├── database/
│   └── db_manager.py
├── cache/
│   └── lfu_cache.py
├── cloud/
│   └── google_drive.py
└── utils/
    ├── crypto.py
    └── logger.py
```

### Running Tests

```
pytest tests/
```

## Performance Metrics

The system tracks several performance metrics:

- **Throughput (MB/s)**: Measures the speed of data transfer
- **Cache Hit Ratio (%)**: Measures how effectively the LFU cache serves requests
- **Sync Success Rate (%)**: Measures how often file sync to Google Drive is successful

You can view these metrics in the log file.

## Troubleshooting

### Common Issues

1. **Mount fails with "Operation not permitted"**:
   - Ensure you have FUSE installed and proper permissions
   - Try running with sudo or adding your user to the fuse group

2. **Database connection fails**:
   - Check your .env file for correct database credentials
   - Ensure MySQL server is running

3. **Google Drive sync doesn't work**:
   - Verify credentials.json is in the correct location
   - Check internet connection
   - Look for specific error messages in the log file

### Logs

Logs are stored in `fuse_fs.log` by default. Enable debug logging with the `-d` flag for more detailed information.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 