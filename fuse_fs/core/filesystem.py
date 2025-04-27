"""
Core FUSE filesystem implementation.
"""
import os
import errno
import logging
from datetime import datetime
from fuse import FUSE, FuseOSError, Operations

from fuse_fs import config
from fuse_fs.database.db_manager import DatabaseManager
from fuse_fs.cache.lfu_cache import LFUCache

logger = logging.getLogger(__name__)

class FuseFS(Operations):
    """FUSE Virtual File System implementation with metadata storage and LFU caching."""
    
    def __init__(self, storage_path=None, mount_point=None):
        """Initialize the filesystem."""
        self.storage_path = storage_path or config.DEFAULT_STORAGE_PATH
        self.mount_point = mount_point or config.DEFAULT_MOUNT_POINT
        
        # Create storage directory if it doesn't exist
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Initialize database connection
        self.db = DatabaseManager()
        
        # Initialize LFU cache
        self.cache = LFUCache(max_size=config.CACHE_SIZE, cache_dir=config.CACHE_DIR)
        
        # For keeping file handles
        self.open_files = {}
        self.fd = 0
        
        logger.info(f"Initialized FUSE filesystem with storage at {self.storage_path}")

    def _full_path(self, partial_path):
        """Helper to get the full path for a file in the storage directory."""
        if partial_path.startswith("/"):
            partial_path = partial_path[1:]
        path = os.path.join(self.storage_path, partial_path)
        return path

    # Filesystem methods
    # ==================

    def access(self, path, mode):
        """Check if the file exists and has the requested permissions."""
        full_path = self._full_path(path)
        if not os.access(full_path, mode):
            raise FuseOSError(errno.EACCES)

    def chmod(self, path, mode):
        """Change the mode (permissions) of a file."""
        full_path = self._full_path(path)
        return os.chmod(full_path, mode)

    def chown(self, path, uid, gid):
        """Change the owner of a file."""
        full_path = self._full_path(path)
        return os.chown(full_path, uid, gid)

    def getattr(self, path, fh=None):
        """Get file attributes."""
        full_path = self._full_path(path)
        
        # If it's in our cache, use that metadata
        cached_attr = self.cache.get_attr(path)
        if cached_attr:
            return cached_attr
            
        if not os.path.exists(full_path):
            raise FuseOSError(errno.ENOENT)
            
        st = os.lstat(full_path)
        attr = {key: getattr(st, key) for key in ('st_atime', 'st_ctime',
                 'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid')}
                 
        # Store in database for extended metadata tracking
        self.db.update_file_metadata(path, attr)
                 
        return attr

    def readdir(self, path, fh):
        """Read directory and yield entries."""
        full_path = self._full_path(path)
        
        dirents = ['.', '..']
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))
            
        # Check for any files that might be in the database but not in the filesystem
        db_files = self.db.get_directory_files(path)
        for file_name in db_files:
            if file_name not in dirents:
                dirents.append(file_name)
                
        for entry in dirents:
            yield entry

    def mkdir(self, path, mode):
        """Create a directory."""
        full_path = self._full_path(path)
        os.makedirs(full_path, mode)
        
        # Store directory metadata in database
        self.db.add_directory(path, mode)
        
        return 0

    def rmdir(self, path):
        """Remove a directory."""
        full_path = self._full_path(path)
        os.rmdir(full_path)
        
        # Remove directory metadata from database
        self.db.remove_directory(path)
        
        return 0

    def create(self, path, mode, fi=None):
        """Create a file."""
        full_path = self._full_path(path)
        
        try:
            # Create the file properly with both read and write permissions
            f = open(full_path, 'wb+')
            f.close()
            
            # Set the proper permissions
            os.chmod(full_path, mode)
            
            # Create a file descriptor
            self.fd += 1
            self.open_files[self.fd] = os.open(full_path, os.O_RDWR)
            
            # Add file metadata to database
            self.db.add_file(path, mode)
            
            return self.fd
        except Exception as e:
            logger.error(f"Create error for {path}: {e}")
            raise FuseOSError(errno.EIO)

    def open(self, path, flags):
        """Open a file and return a file descriptor."""
        full_path = self._full_path(path)
        
        # Check if file is in cache
        if self.cache.has(path):
            logger.debug(f"Cache hit for {path}")
        else:
            logger.debug(f"Cache miss for {path}")
            # Add to cache if it's a read operation
            if flags & os.O_RDONLY:
                self.cache.add(path, full_path)
        
        self.fd += 1
        self.open_files[self.fd] = os.open(full_path, flags)
        
        # Update access timestamp in database
        self.db.update_access_time(path)
        
        return self.fd

    def read(self, path, length, offset, fh):
        """Read data from a file."""
        # Try to read from cache first
        if self.cache.has(path):
            data = self.cache.read(path, length, offset)
            if data is not None:
                return data
        
        # If not in cache or cache read failed, read from disk
        try:
            with open(self._full_path(path), 'rb') as f:
                f.seek(offset)
                return f.read(length)
        except Exception as e:
            logger.error(f"Read error for {path}: {e}")
            raise FuseOSError(errno.EIO)

    def write(self, path, buf, offset, fh):
        """Write data to a file."""
        try:
            with open(self._full_path(path), 'r+b') as f:
                f.seek(offset)
                bytes_written = f.write(buf)
                
                # Update file in cache if it's there
                if self.cache.has(path):
                    self.cache.invalidate(path)
                    
                # Update file size and modification time in database
                self.db.update_file_size(path, offset + bytes_written)
                self.db.update_modification_time(path)
                
                # Mark file for synchronization
                self.db.mark_for_sync(path)
                
                return bytes_written
        except Exception as e:
            logger.error(f"Write error for {path}: {e}")
            raise FuseOSError(errno.EIO)

    def truncate(self, path, length, fh=None):
        """Truncate a file to the specified length."""
        full_path = self._full_path(path)
        
        with open(full_path, 'r+') as f:
            f.truncate(length)
            
        # Invalidate cache
        if self.cache.has(path):
            self.cache.invalidate(path)
            
        # Update file size in database
        self.db.update_file_size(path, length)
        
        return 0

    def flush(self, path, fh):
        """Flush cached data to disk."""
        try:
            if fh in self.open_files:
                return os.fsync(self.open_files[fh])
            return 0
        except Exception as e:
            logger.error(f"Flush error for {path}: {e}")
            return 0

    def release(self, path, fh):
        """Release an open file."""
        if fh in self.open_files:
            os.close(self.open_files[fh])
            del self.open_files[fh]
        return 0

    def fsync(self, path, fdatasync, fh):
        """Sync file contents to disk."""
        try:
            full_path = self._full_path(path)
            if os.path.exists(full_path):
                with open(full_path, 'rb') as f:
                    os.fsync(f.fileno())
            return 0
        except Exception as e:
            logger.error(f"Fsync error for {path}: {e}")
            return 0
        
    def unlink(self, path):
        """Delete a file."""
        full_path = self._full_path(path)
        os.unlink(full_path)
        
        # Remove from cache if present
        if self.cache.has(path):
            self.cache.invalidate(path)
            
        # Remove file metadata from database
        self.db.remove_file(path)
        
        return 0

    def rename(self, old, new):
        """Rename a file."""
        old_full_path = self._full_path(old)
        new_full_path = self._full_path(new)
        
        os.rename(old_full_path, new_full_path)
        
        # Update cache and database
        if self.cache.has(old):
            self.cache.invalidate(old)
            
        self.db.rename_file(old, new)
        
        return 0

def mount_filesystem(storage_path=None, mount_point=None, foreground=True):
    """Mount the FUSE filesystem."""
    storage = storage_path or config.DEFAULT_STORAGE_PATH
    mount = mount_point or config.DEFAULT_MOUNT_POINT
    
    # Create mount directory if it doesn't exist
    os.makedirs(mount, exist_ok=True)
    
    logger.info(f"Mounting filesystem at {mount} with storage at {storage}")
    
    # Start the FUSE filesystem
    FUSE(
        FuseFS(storage, mount),
        mount,
        foreground=foreground,
        nothreads=True,
        allow_other=True,
    )
    
    return True