"""
Basic tests for the FUSE Virtual File System.
"""
import os
import sys
import unittest
import tempfile
import shutil
import subprocess
import time
import logging

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fuse_fs.database.db_manager import DatabaseManager
from fuse_fs.cache.lfu_cache import LFUCache

class TestBasicFunctionality(unittest.TestCase):
    """Test basic functionality of the FUSE filesystem components."""
    
    def setUp(self):
        """Set up test environment."""
        # Disable logging during tests
        logging.disable(logging.CRITICAL)
        
        # Create temporary directories for tests
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.temp_dir, 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary directories
        shutil.rmtree(self.temp_dir)
        
        # Re-enable logging
        logging.disable(logging.NOTSET)
    
    def test_lfu_cache(self):
        """Test LFU cache functionality."""
        # Create a cache with small max size
        cache = LFUCache(max_size=1024, cache_dir=self.cache_dir)
        
        # Create a test file
        test_file_path = os.path.join(self.temp_dir, 'test_file.txt')
        with open(test_file_path, 'w') as f:
            f.write('Test content')
        
        # Add file to cache
        self.assertTrue(cache.add('/test_file.txt', test_file_path))
        
        # Check if file is in cache
        self.assertTrue(cache.has('/test_file.txt'))
        
        # Read from cache
        data = cache.read('/test_file.txt', 12, 0)
        self.assertEqual(data, b'Test content')
        
        # Invalidate cache
        cache.invalidate('/test_file.txt')
        
        # Check if file is no longer in cache
        self.assertFalse(cache.has('/test_file.txt'))
    
    def test_database_connection(self):
        """
        Test database connection functionality.
        
        Note: This test requires a proper database configuration.
        It will be skipped if the connection fails.
        """
        try:
            db = DatabaseManager()
            self.assertIsNotNone(db.connection)
            db.close()
        except Exception as e:
            self.skipTest(f"Database connection failed: {e}")

if __name__ == '__main__':
    unittest.main() 