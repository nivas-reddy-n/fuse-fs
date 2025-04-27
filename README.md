# FUSE Virtual File System

A virtual file system built with FUSE (Filesystem in Userspace) that provides:
- LFU (Least Frequently Used) caching for improved performance
- Google Drive synchronization for cloud backup
- Metadata storage for enhanced file management

## Features

- **Virtual FUSE Filesystem**: Mount a virtual filesystem on your local machine
- **LFU Caching**: Automatically cache frequently accessed files for faster access
- **Google Drive Sync**: Automatically sync files to Google Drive for backup
- **Metadata Storage**: Store additional file metadata for improved organization

## Installation

### Prerequisites

- Python 3.8 or higher
- FUSE or equivalent (e.g., WinFSP on Windows)
- Required Python packages (see requirements.txt)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/fuse-fs.git
   cd fuse-fs
   ```

2. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up Google Drive API credentials:
   - Create a project in the Google Cloud Console
   - Enable the Google Drive API
   - Create OAuth 2.0 credentials and download as `credentials.json`
   - Place the credentials.json file in the project root directory

4. Configure the environment variables (copy env.example to .env and update):
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

## Usage

### Basic Usage

Run the `run.sh` script in the scripts directory to start the filesystem:

```bash
./scripts/run.sh
```

By default, this will:
- Mount the filesystem at `~/fuse_mount`
- Store data at `~/fuse_storage`
- Enable Google Drive sync
- Enable LFU caching

### Command-Line Options

You can customize the behavior with command-line options:

```bash
./scripts/run.sh --mount /custom/mount/point --storage /custom/storage/path --debug --foreground
```

Optional arguments:
- `--mount PATH`: Custom mount point
- `--storage PATH`: Custom storage path
- `--foreground`: Run in foreground (useful for debugging)
- `--debug`: Enable debug logging
- `--no-sync`: Disable Google Drive synchronization
- `--no-cache`: Disable LFU caching

### Demo

Run the demo script to see the filesystem in action:

```bash
./examples/demo.sh
```

For Windows users:

```powershell
.\examples\demo.ps1
```

## Project Structure

```
fuse-fs/
├── examples/             # Example usage scripts
│   ├── demo.ps1          # PowerShell demo script
│   └── demo.sh           # Bash demo script
├── fuse_fs/              # Main package
│   ├── cache/            # LFU caching implementation
│   ├── cloud/            # Cloud storage integration
│   ├── core/             # Core filesystem implementation
│   ├── database/         # Metadata storage
│   └── utils/            # Utility functions
├── scripts/              # Utility scripts
│   ├── run.sh            # Main startup script
│   └── setup_db.py       # Database setup script
├── tests/                # Test files
├── .gitignore            # Git ignore file
├── env.example           # Example environment variables
├── README.md             # This file
├── requirements.txt      # Python dependencies
└── setup.py              # Package setup script
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.