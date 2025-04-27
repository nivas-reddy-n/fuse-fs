#!/bin/bash

# Default values
MOUNT_POINT="$HOME/fuse_mount"
STORAGE_PATH="$HOME/fuse_storage"
FOREGROUND=false
DEBUG=false
NO_SYNC=false
NO_CACHE=false

# Display usage information
function show_usage {
    echo "FUSE Virtual File System"
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -m, --mount PATH       Mount point (default: $MOUNT_POINT)"
    echo "  -s, --storage PATH     Storage directory (default: $STORAGE_PATH)"
    echo "  -f, --foreground       Run in foreground (for debugging)"
    echo "  -d, --debug            Enable debug logging"
    echo "  --no-sync              Disable Google Drive synchronization"
    echo "  --no-cache             Disable LFU caching"
    echo "  -h, --help             Show this help message"
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mount)
            MOUNT_POINT="$2"
            shift 2
            ;;
        -s|--storage)
            STORAGE_PATH="$2"
            shift 2
            ;;
        -f|--foreground)
            FOREGROUND=true
            shift
            ;;
        -d|--debug)
            DEBUG=true
            shift
            ;;
        --no-sync)
            NO_SYNC=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            ;;
    esac
done

# Build command
CMD="python -m fuse_fs --mount \"$MOUNT_POINT\" --storage \"$STORAGE_PATH\""

if $FOREGROUND; then
    CMD="$CMD --foreground"
fi

if $DEBUG; then
    CMD="$CMD --debug"
fi

if $NO_SYNC; then
    CMD="$CMD --no-sync"
fi

if $NO_CACHE; then
    CMD="$CMD --no-cache"
fi

# Create directories if they don't exist
mkdir -p "$MOUNT_POINT"
mkdir -p "$STORAGE_PATH"

# Display configuration
echo "Starting FUSE filesystem with the following configuration:"
echo "  Mount point: $MOUNT_POINT"
echo "  Storage path: $STORAGE_PATH"
echo "  Foreground mode: $FOREGROUND"
echo "  Debug logging: $DEBUG"
echo "  Google Drive sync: $([[ $NO_SYNC == true ]] && echo "disabled" || echo "enabled")"
echo "  LFU caching: $([[ $NO_CACHE == true ]] && echo "disabled" || echo "enabled")"
echo ""

# Run the command
echo "Running: $CMD"
echo ""
eval $CMD 