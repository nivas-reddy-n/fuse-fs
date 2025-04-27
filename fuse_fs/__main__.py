"""
Main entry point for the FUSE Virtual File System.
"""
import os
import sys
import argparse
import signal
import logging

# Enable relative imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fuse_fs import config
from fuse_fs.utils.logger import setup_logging
from fuse_fs.core.filesystem import mount_filesystem, FuseFS
from fuse_fs.cloud.google_drive import GoogleDriveSync

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="FUSE Virtual File System with Metadata Storage, Cloud Sync, and LFU Caching"
    )
    
    parser.add_argument(
        "-m", "--mount",
        help=f"Mount point (default: {config.DEFAULT_MOUNT_POINT})",
        default=config.DEFAULT_MOUNT_POINT
    )
    
    parser.add_argument(
        "-s", "--storage",
        help=f"Storage directory (default: {config.DEFAULT_STORAGE_PATH})",
        default=config.DEFAULT_STORAGE_PATH
    )
    
    parser.add_argument(
        "-f", "--foreground",
        help="Run in foreground (for debugging)",
        action="store_true"
    )
    
    parser.add_argument(
        "-d", "--debug",
        help="Enable debug logging",
        action="store_true"
    )
    
    parser.add_argument(
        "--no-sync",
        help="Disable Google Drive synchronization",
        action="store_true"
    )
    
    parser.add_argument(
        "--no-cache",
        help="Disable LFU caching",
        action="store_true"
    )
    
    return parser.parse_args()

def setup_signal_handlers(sync_manager=None):
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(sig, frame):
        print("\nShutting down FUSE filesystem...")
        if sync_manager:
            sync_manager.stop_background_sync()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def main():
    """Main entry point."""
    args = parse_args()
    
    # Set up logging
    log_level = 'DEBUG' if args.debug else config.LOG_LEVEL
    setup_logging(log_level=log_level)
    
    logger = logging.getLogger('fuse_fs')
    
    # Create necessary directories
    os.makedirs(args.storage, exist_ok=True)
    
    # Check if mount point is already mounted and try to unmount it
    mount_point_exists = os.path.exists(args.mount)
    if mount_point_exists:
        try:
            import subprocess
            logger.info(f"Checking if {args.mount} is already mounted")
            # Check if it's a mount point
            is_mounted = os.path.ismount(args.mount)
            if is_mounted:
                logger.warning(f"Mount point {args.mount} is already mounted, attempting to unmount")
                if sys.platform == 'win32':
                    # Windows unmount
                    subprocess.run(['taskkill', '/f', '/im', 'winfsp-x64.exe'], stderr=subprocess.PIPE)
                else:
                    # Linux/macOS unmount
                    subprocess.run(['fusermount', '-u', args.mount], stderr=subprocess.PIPE)
                    # If the above fails, try force unmount (requires sudo)
                    if os.path.ismount(args.mount):
                        logger.warning("Attempting force unmount (may require sudo)")
                        subprocess.run(['sudo', 'umount', '-l', args.mount], stderr=subprocess.PIPE)
        except Exception as e:
            logger.error(f"Failed to unmount existing mount point: {e}")
            logger.warning("You may need to manually unmount the filesystem")
    
    # Create mount point directory if it doesn't exist
    os.makedirs(args.mount, exist_ok=True)
    
    # Initialize Google Drive sync if enabled
    sync_manager = None
    if not args.no_sync:
        try:
            sync_manager = GoogleDriveSync(storage_path=args.storage)
            sync_manager.start_background_sync()
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive sync: {e}")
            logger.warning("Continuing without Google Drive synchronization")
    
    # Set up signal handlers
    setup_signal_handlers(sync_manager)
    
    # Mount the filesystem
    try:
        logger.info(f"Mounting filesystem at {args.mount} with storage at {args.storage}")
        mount_filesystem(
            storage_path=args.storage,
            mount_point=args.mount,
            foreground=args.foreground or args.debug
        )
    except Exception as e:
        logger.error(f"Failed to mount filesystem: {e}")
        if sync_manager:
            sync_manager.stop_background_sync()
        sys.exit(1)

if __name__ == "__main__":
    main()