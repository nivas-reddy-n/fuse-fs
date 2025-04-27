#!/bin/bash

# Demo script for FUSE Filesystem with Caching and Google Drive Sync
# Created on April 27, 2025

MOUNT_POINT="$HOME/fuse_mount"
STORAGE_PATH="$HOME/fuse_storage"
CACHE_PATH="$STORAGE_PATH/cache"

# Function to display section headers
section() {
    echo ""
    echo "====================================================================="
    echo "  $1"
    echo "====================================================================="
    echo ""
}

# Check if filesystem is mounted
if ! mountpoint -q "$MOUNT_POINT"; then
    echo "Error: FUSE filesystem is not mounted at $MOUNT_POINT"
    echo "Please run ./run.sh first"
    exit 1
fi

# Begin the demo
section "FUSE FILESYSTEM DEMO"
echo "Mount Point: $MOUNT_POINT"
echo "Storage Path: $STORAGE_PATH"

# Section 1: Basic file operations
section "1. BASIC FILE OPERATIONS"

echo "Creating test directories..."
mkdir -p "$MOUNT_POINT/test_dir/nested_dir"
echo "-> Created directories at $MOUNT_POINT/test_dir/nested_dir"

echo "Creating test files with content..."
echo "This is a test file with some content." > "$MOUNT_POINT/test_file.txt"
echo "This is a nested file in a subdirectory." > "$MOUNT_POINT/test_dir/nested_file.txt"
echo "-> Created test files"

echo "Listing files in the root directory:"
ls -la "$MOUNT_POINT"

echo "Listing files in the test directory:"
ls -la "$MOUNT_POINT/test_dir"

echo "Reading file content:"
cat "$MOUNT_POINT/test_file.txt"
echo ""
cat "$MOUNT_POINT/test_dir/nested_file.txt"

# Section 2: File modification
section "2. FILE MODIFICATION"

echo "Appending to existing file..."
echo "This is an appended line." >> "$MOUNT_POINT/test_file.txt"
echo "-> File updated"

echo "Reading updated file content:"
cat "$MOUNT_POINT/test_file.txt"

# Section 3: Cache demonstration
section "3. CACHE DEMONSTRATION"

echo "Creating a large file to test caching..."
dd if=/dev/urandom of="$MOUNT_POINT/large_file.bin" bs=1M count=10 status=progress
echo "-> Created large test file (10MB)"

echo "Reading the file first time (should be slower)..."
time cat "$MOUNT_POINT/large_file.bin" > /dev/null

echo "Reading the file second time (should be faster due to caching)..."
time cat "$MOUNT_POINT/large_file.bin" > /dev/null

echo "Checking cache directory content:"
ls -la "$CACHE_PATH"

# Section 4: Google Drive Sync
section "4. GOOGLE DRIVE SYNCHRONIZATION"

echo "Creating a file to sync with Google Drive..."
echo "This file should be synchronized with Google Drive." > "$MOUNT_POINT/google_drive_sync_test.txt"
echo "-> Created file for Google Drive sync"

echo "Waiting for sync to occur (30 seconds)..."
sleep 30

echo "Checking Google Drive sync status..."
# This would ideally check the Google Drive API to confirm the file was uploaded
# For demo purposes, we're just showing that the file was created
cat "$MOUNT_POINT/google_drive_sync_test.txt"

# Section 5: Metadata exploration
section "5. METADATA STORAGE"

echo "Listing metadata storage files:"
find "$STORAGE_PATH" -type f -not -path "*/cache/*" | sort

# Clean up
section "DEMO COMPLETE"
echo "The demo has completed. You can explore the files manually."
echo "To clean up test files, run: rm -rf $MOUNT_POINT/test_*"
echo "To unmount the filesystem: fusermount -u $MOUNT_POINT"