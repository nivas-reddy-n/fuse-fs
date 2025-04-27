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
    os.makedirs(args.mount, exist_ok=True)
    os.makedirs(args.storage, exist_ok=True)
    
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