"""
LFU (Least Frequently Used) Cache implementation for FUSE filesystem.
"""
import os
import time
import shutil
import logging
import hashlib
from collections import OrderedDict

from fuse_fs import config

logger = logging.getLogger(__name__)

class LFUCache:
    """
    LFU (Least Frequently Used) Cache for the FUSE filesystem.
    
    This cache stores frequently accessed files in memory and tracks 
    access frequency to determine which files to keep in cache.
    """
    
    def __init__(self, max_size=None, cache_dir=None):
        """Initialize the LFU cache."""
        self.max_size = max_size or config.CACHE_SIZE
        self.cache_dir = cache_dir or config.CACHE_DIR
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Dictionary to track frequency of each file
        self.frequency = {}
        
        # Dictionary to store cached file data (path -> cached_file_path)
        self.cache = {}
        
        # Dictionary to store file attributes (path -> attr)
        self.attrs = {}
        
        # Dictionary to map cache file paths to original paths
        self.cache_map = {}
        
        # Total size of cached files
        self.total_size = 0
        
        # Load existing cache files if any
        self._load_existing_cache()
        
        logger.info(f"Initialized LFU cache with max size {self.max_size}")
    
    def _load_existing_cache(self):
        """Load existing cache files from the cache directory."""
        if not os.path.exists(self.cache_dir):
            return
            
        for filename in os.listdir(self.cache_dir):
            if filename.startswith("cache_"):
                cache_path = os.path.join(self.cache_dir, filename)
                try:
                    # Get file size
                    size = os.path.getsize(cache_path)
                    
                    # We don't know the original path, so we'll use the cache file
                    # path as a placeholder until it's accessed properly
                    self.frequency[cache_path] = 0
                    self.cache[cache_path] = cache_path
                    self.cache_map[cache_path] = cache_path
                    self.total_size += size
                    
                    logger.debug(f"Loaded existing cache file: {cache_path} ({size} bytes)")
                except Exception as e:
                    logger.error(f"Error loading cache file {cache_path}: {e}")
    
    def _get_cache_path(self, path):
        """Generate a cache file path for a given file path."""
        # Create a hash of the path to avoid any path separation issues
        path_hash = hashlib.md5(path.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"cache_{path_hash}")
    
    def _evict(self):
        """Evict the least frequently used file from the cache."""
        if not self.frequency:
            return
            
        # Find the item with the lowest frequency
        min_freq = min(self.frequency.values())
        
        # Get all files with the minimum frequency
        min_freq_files = [p for p, f in self.frequency.items() if f == min_freq]
        
        # If multiple files have the same frequency, remove the oldest one
        path_to_remove = min_freq_files[0]
        
        # Get the cache path
        cache_path = self.cache.get(path_to_remove)
        
        if cache_path and os.path.exists(cache_path):
            # Update total size
            self.total_size -= os.path.getsize(cache_path)
            
            # Remove the file from the cache
            try:
                os.remove(cache_path)
                logger.debug(f"Evicted file from cache: {path_to_remove}")
            except Exception as e:
                logger.error(f"Error removing cache file {cache_path}: {e}")
        
        # Remove from tracking dictionaries
        if path_to_remove in self.frequency:
            del self.frequency[path_to_remove]
        if path_to_remove in self.cache:
            cache_file = self.cache[path_to_remove]
            del self.cache[path_to_remove]
            
            # Remove from cache map
            if cache_file in self.cache_map:
                del self.cache_map[cache_file]
                
        # Remove from attrs if present
        if path_to_remove in self.attrs:
            del self.attrs[path_to_remove]
    
    def has(self, path):
        """Check if a file is in the cache."""
        return path in self.cache and os.path.exists(self.cache[path])
    
    def add(self, path, source_path):
        """Add a file to the cache."""
        if not os.path.exists(source_path):
            logger.error(f"Cannot add nonexistent file to cache: {source_path}")
            return False
            
        # Check file size
        file_size = os.path.getsize(source_path)
        
        # If the file is too big (more than half the cache size), don't cache it
        if file_size > (self.max_size / 2):
            logger.warning(f"File too large to cache: {path} ({file_size} bytes)")
            return False
        
        # If we need to make space, evict files
        while self.total_size + file_size > self.max_size and self.frequency:
            self._evict()
        
        # Get cache file path
        cache_path = self._get_cache_path(path)
        
        # Copy the file to the cache
        try:
            shutil.copy2(source_path, cache_path)
            
            # Update tracking dictionaries
            self.frequency[path] = 1
            self.cache[path] = cache_path
            self.cache_map[cache_path] = path
            self.total_size += file_size
            
            # Get file attributes
            st = os.lstat(source_path)
            attr = {key: getattr(st, key) for key in ('st_atime', 'st_ctime',
                    'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid')}
            self.attrs[path] = attr
            
            logger.debug(f"Added file to cache: {path} ({file_size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Error adding file to cache: {e}")
            return False
    
    def read(self, path, length, offset):
        """Read data from a cached file."""
        if not self.has(path):
            return None
            
        # Increment access frequency
        self.frequency[path] = self.frequency.get(path, 0) + 1
        
        # Get cache file path
        cache_path = self.cache[path]
        
        try:
            with open(cache_path, 'rb') as f:
                f.seek(offset)
                return f.read(length)
        except Exception as e:
            logger.error(f"Error reading from cache: {e}")
            return None
    
    def invalidate(self, path):
        """Invalidate a file in the cache."""
        if not self.has(path):
            return
            
        # Get cache file path
        cache_path = self.cache[path]
        
        if os.path.exists(cache_path):
            # Update total size
            self.total_size -= os.path.getsize(cache_path)
            
            # Remove the file from the cache
            try:
                os.remove(cache_path)
                logger.debug(f"Invalidated file in cache: {path}")
            except Exception as e:
                logger.error(f"Error removing cache file {cache_path}: {e}")
        
        # Remove from tracking dictionaries
        if path in self.frequency:
            del self.frequency[path]
        if path in self.cache:
            cache_file = self.cache[path]
            del self.cache[path]
            
            # Remove from cache map
            if cache_file in self.cache_map:
                del self.cache_map[cache_file]
                
        # Remove from attrs if present
        if path in self.attrs:
            del self.attrs[path]
    
    def get_attr(self, path):
        """Get attributes for a cached file."""
        if path in self.attrs:
            # Increment access frequency
            self.frequency[path] = self.frequency.get(path, 0) + 1
            return self.attrs[path]
        return None
    
    def clear(self):
        """Clear the entire cache."""
        # Remove all cache files
        for cache_path in self.cache.values():
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except Exception as e:
                    logger.error(f"Error removing cache file {cache_path}: {e}")
        
        # Reset tracking dictionaries
        self.frequency = {}
        self.cache = {}
        self.cache_map = {}
        self.attrs = {}
        self.total_size = 0
        
        logger.info("Cache cleared") 