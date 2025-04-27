#!/bin/bash
# cleanup.sh - Safely unmount FUSE filesystem and clean temporary files

# Default mount point
MOUNT_POINT="$HOME/fuse_mount"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mount)
            MOUNT_POINT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -m, --mount PATH    Mount point to unmount (default: $MOUNT_POINT)"
            echo "  -h, --help          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Cleaning up FUSE filesystem..."

# Check if the mount point exists and is mounted
if [ -d "$MOUNT_POINT" ]; then
    if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
        echo "Unmounting FUSE filesystem at $MOUNT_POINT..."
        fusermount -u "$MOUNT_POINT" 2>/dev/null

        # If the first unmount fails, try with force
        if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
            echo "Trying force unmount..."
            sudo umount -l "$MOUNT_POINT" 2>/dev/null
        fi
        
        # Check if unmount was successful
        if ! mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
            echo "Successfully unmounted $MOUNT_POINT"
        else
            echo "Failed to unmount $MOUNT_POINT"
            echo "You may need to reboot to fully release the mount point"
        fi
    else
        echo "No filesystem mounted at $MOUNT_POINT"
    fi
else
    echo "Mount point $MOUNT_POINT does not exist"
fi

# Clean up any Python cache files
echo "Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete

# Remove log files
echo "Removing log files..."
find . -type f -name "*.log" -delete

echo "Cleanup complete!"