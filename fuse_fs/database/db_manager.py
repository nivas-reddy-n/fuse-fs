"""
Database manager for FUSE filesystem metadata storage.
"""
import os
import logging
import datetime
import mysql.connector
from mysql.connector import Error

from fuse_fs import config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database operations for the FUSE filesystem."""
    
    def __init__(self):
        """Initialize the database connection and create tables if needed."""
        self.connection = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """Connect to the MySQL database."""
        try:
            self.connection = mysql.connector.connect(**config.DB_CONFIG)
            if self.connection.is_connected():
                logger.info("Connected to MySQL database")
        except Error as e:
            logger.error(f"Error connecting to MySQL database: {e}")
            
    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        if not self.connection or not self.connection.is_connected():
            logger.error("Cannot create tables: Database connection not established")
            return
            
        cursor = self.connection.cursor()
        
        try:
            # Files table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    path VARCHAR(255) NOT NULL UNIQUE,
                    filename VARCHAR(255) NOT NULL,
                    directory VARCHAR(255) NOT NULL,
                    size BIGINT DEFAULT 0,
                    mode INT NOT NULL,
                    uid INT NOT NULL DEFAULT 0,
                    gid INT NOT NULL DEFAULT 0,
                    atime DATETIME NOT NULL,
                    mtime DATETIME NOT NULL,
                    ctime DATETIME NOT NULL,
                    is_directory BOOLEAN DEFAULT FALSE,
                    needs_sync BOOLEAN DEFAULT TRUE,
                    last_synced DATETIME,
                    google_drive_id VARCHAR(255),
                    hash VARCHAR(64),
                    content_type VARCHAR(100),
                    INDEX (directory),
                    INDEX (needs_sync)
                )
            """)
            
            # Extended attributes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS extended_attributes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    file_id INT NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    value TEXT,
                    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
                    UNIQUE KEY name_per_file (file_id, name)
                )
            """)
            
            # Access history for LFU algorithm
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS access_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    file_id INT NOT NULL,
                    access_time DATETIME NOT NULL,
                    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
                    INDEX (file_id, access_time)
                )
            """)
            
            # Sync history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    file_id INT NOT NULL,
                    sync_time DATETIME NOT NULL,
                    status ENUM('success', 'failed') NOT NULL,
                    error_message TEXT,
                    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
                )
            """)
            
            self.connection.commit()
            logger.info("Database tables created or already exist")
            
        except Error as e:
            logger.error(f"Error creating database tables: {e}")
        finally:
            cursor.close()
    
    def _ensure_connection(self):
        """Ensure database connection is active, reconnect if needed."""
        if not self.connection or not self.connection.is_connected():
            self._connect()
    
    def add_file(self, path, mode):
        """Add a new file to the database."""
        self._ensure_connection()
        if not self.connection:
            return False
            
        cursor = self.connection.cursor()
        
        try:
            # Extract directory and filename
            directory = os.path.dirname(path)
            filename = os.path.basename(path)
            
            # Get current timestamp
            now = datetime.datetime.now()
            
            cursor.execute("""
                INSERT INTO files 
                (path, filename, directory, mode, atime, mtime, ctime, is_directory, needs_sync) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                mode=%s, mtime=%s, ctime=%s, needs_sync=%s
            """, (path, filename, directory, mode, now, now, now, False, True,
                 mode, now, now, True))
                 
            self.connection.commit()
            logger.debug(f"Added file {path} to database")
            return True
            
        except Error as e:
            logger.error(f"Error adding file to database: {e}")
            return False
        finally:
            cursor.close()
    
    def add_directory(self, path, mode):
        """Add a new directory to the database."""
        self._ensure_connection()
        if not self.connection:
            return False
            
        cursor = self.connection.cursor()
        
        try:
            # Extract parent directory and directory name
            parent_dir = os.path.dirname(path)
            dirname = os.path.basename(path)
            
            # Get current timestamp
            now = datetime.datetime.now()
            
            cursor.execute("""
                INSERT INTO files 
                (path, filename, directory, mode, atime, mtime, ctime, is_directory, needs_sync) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                mode=%s, mtime=%s, ctime=%s, needs_sync=%s
            """, (path, dirname, parent_dir, mode, now, now, now, True, True,
                 mode, now, now, True))
                 
            self.connection.commit()
            logger.debug(f"Added directory {path} to database")
            return True
            
        except Error as e:
            logger.error(f"Error adding directory to database: {e}")
            return False
        finally:
            cursor.close()
    
    def remove_file(self, path):
        """Remove a file from the database."""
        self._ensure_connection()
        if not self.connection:
            return False
            
        cursor = self.connection.cursor()
        
        try:
            cursor.execute("DELETE FROM files WHERE path = %s", (path,))
            self.connection.commit()
            logger.debug(f"Removed file {path} from database")
            return True
            
        except Error as e:
            logger.error(f"Error removing file from database: {e}")
            return False
        finally:
            cursor.close()
    
    def remove_directory(self, path):
        """Remove a directory from the database."""
        self._ensure_connection()
        if not self.connection:
            return False
            
        cursor = self.connection.cursor()
        
        try:
            # Remove the directory
            cursor.execute("DELETE FROM files WHERE path = %s", (path,))
            
            # Also remove any files that were inside this directory
            # This ensures we clean up orphaned records
            cursor.execute("DELETE FROM files WHERE directory LIKE %s", (path + '%',))
            
            self.connection.commit()
            logger.debug(f"Removed directory {path} from database")
            return True
            
        except Error as e:
            logger.error(f"Error removing directory from database: {e}")
            return False
        finally:
            cursor.close()
    
    def rename_file(self, old_path, new_path):
        """Rename a file in the database."""
        self._ensure_connection()
        if not self.connection:
            return False
            
        cursor = self.connection.cursor()
        
        try:
            # Extract new directory and filename
            new_directory = os.path.dirname(new_path)
            new_filename = os.path.basename(new_path)
            
            # Update file record
            cursor.execute("""
                UPDATE files
                SET path = %s, filename = %s, directory = %s, needs_sync = TRUE
                WHERE path = %s
            """, (new_path, new_filename, new_directory, old_path))
            
            self.connection.commit()
            logger.debug(f"Renamed file from {old_path} to {new_path} in database")
            return True
            
        except Error as e:
            logger.error(f"Error renaming file in database: {e}")
            return False
        finally:
            cursor.close()
    
    def update_file_metadata(self, path, attr):
        """Update file metadata in the database."""
        self._ensure_connection()
        if not self.connection:
            return False
            
        cursor = self.connection.cursor()
        
        try:
            # Check if file exists
            cursor.execute("SELECT id FROM files WHERE path = %s", (path,))
            result = cursor.fetchone()
            
            if result:
                file_id = result[0]
                
                # Convert timestamps
                atime = datetime.datetime.fromtimestamp(attr['st_atime'])
                mtime = datetime.datetime.fromtimestamp(attr['st_mtime'])
                ctime = datetime.datetime.fromtimestamp(attr['st_ctime'])
                
                # Update file record
                cursor.execute("""
                    UPDATE files
                    SET size = %s, mode = %s, uid = %s, gid = %s, atime = %s, mtime = %s, ctime = %s
                    WHERE id = %s
                """, (attr['st_size'], attr['st_mode'], attr['st_uid'], attr['st_gid'], 
                     atime, mtime, ctime, file_id))
                
                self.connection.commit()
                logger.debug(f"Updated metadata for file {path}")
                return True
            else:
                # File not found, add it if it's a valid path and not root
                if path != "/" and os.path.exists(os.path.join(config.DEFAULT_STORAGE_PATH, path.lstrip('/'))):
                    self.add_file(path, attr['st_mode'])
                    return True
                
                return False
            
        except Error as e:
            logger.error(f"Error updating file metadata in database: {e}")
            return False
        finally:
            cursor.close()
    
    def update_access_time(self, path):
        """Update the access time for a file and add to access history."""
        self._ensure_connection()
        if not self.connection:
            return False
            
        cursor = self.connection.cursor()
        
        try:
            now = datetime.datetime.now()
            
            # Update atime in files table
            cursor.execute("UPDATE files SET atime = %s WHERE path = %s", (now, path))
            
            # Add to access history (for LFU algorithm)
            cursor.execute("""
                INSERT INTO access_history (file_id, access_time)
                SELECT id, %s FROM files WHERE path = %s
            """, (now, path))
            
            self.connection.commit()
            return True
            
        except Error as e:
            logger.error(f"Error updating access time in database: {e}")
            return False
        finally:
            cursor.close()
    
    def update_modification_time(self, path):
        """Update the modification time for a file."""
        self._ensure_connection()
        if not self.connection:
            return False
            
        cursor = self.connection.cursor()
        
        try:
            now = datetime.datetime.now()
            
            # Update mtime in files table
            cursor.execute("UPDATE files SET mtime = %s WHERE path = %s", (now, path))
            
            self.connection.commit()
            return True
            
        except Error as e:
            logger.error(f"Error updating modification time in database: {e}")
            return False
        finally:
            cursor.close()
    
    def update_file_size(self, path, size):
        """Update the file size in the database."""
        self._ensure_connection()
        if not self.connection:
            return False
            
        cursor = self.connection.cursor()
        
        try:
            # Update size in files table
            cursor.execute("UPDATE files SET size = %s WHERE path = %s", (size, path))
            
            self.connection.commit()
            return True
            
        except Error as e:
            logger.error(f"Error updating file size in database: {e}")
            return False
        finally:
            cursor.close()
    
    def mark_for_sync(self, path):
        """Mark a file for synchronization to Google Drive."""
        self._ensure_connection()
        if not self.connection:
            return False
            
        cursor = self.connection.cursor()
        
        try:
            # Mark file for sync
            cursor.execute("UPDATE files SET needs_sync = TRUE WHERE path = %s", (path,))
            
            self.connection.commit()
            return True
            
        except Error as e:
            logger.error(f"Error marking file for sync in database: {e}")
            return False
        finally:
            cursor.close()
    
    def get_files_for_sync(self, limit=10):
        """Get files that need to be synchronized to Google Drive."""
        self._ensure_connection()
        if not self.connection:
            return []
            
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT id, path, size, mtime
                FROM files
                WHERE needs_sync = TRUE
                ORDER BY mtime ASC
                LIMIT %s
            """, (limit,))
            
            return cursor.fetchall()
            
        except Error as e:
            logger.error(f"Error getting files for sync from database: {e}")
            return []
        finally:
            cursor.close()
    
    def update_sync_status(self, file_id, success, drive_id=None, error_message=None):
        """Update the synchronization status for a file."""
        self._ensure_connection()
        if not self.connection:
            return False
            
        cursor = self.connection.cursor()
        
        try:
            now = datetime.datetime.now()
            
            # Update sync status
            if success:
                cursor.execute("""
                    UPDATE files
                    SET needs_sync = FALSE, last_synced = %s, google_drive_id = %s
                    WHERE id = %s
                """, (now, drive_id, file_id))
            else:
                # Keep needs_sync as TRUE if sync failed
                cursor.execute("""
                    UPDATE files
                    SET last_synced = %s
                    WHERE id = %s
                """, (now, file_id))
            
            # Add to sync history
            status = "success" if success else "failed"
            cursor.execute("""
                INSERT INTO sync_history (file_id, sync_time, status, error_message)
                VALUES (%s, %s, %s, %s)
            """, (file_id, now, status, error_message))
            
            self.connection.commit()
            return True
            
        except Error as e:
            logger.error(f"Error updating sync status in database: {e}")
            return False
        finally:
            cursor.close()
    
    def get_directory_files(self, directory):
        """Get files in a directory from the database."""
        self._ensure_connection()
        if not self.connection:
            return []
            
        cursor = self.connection.cursor()
        
        try:
            cursor.execute("""
                SELECT filename
                FROM files
                WHERE directory = %s AND is_directory = FALSE
            """, (directory,))
            
            return [row[0] for row in cursor.fetchall()]
            
        except Error as e:
            logger.error(f"Error getting directory files from database: {e}")
            return []
        finally:
            cursor.close()
    
    def get_most_accessed_files(self, limit=10):
        """Get the most frequently accessed files (for LFU algorithm)."""
        self._ensure_connection()
        if not self.connection:
            return []
            
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT f.path, f.size, COUNT(a.id) as access_count
                FROM files f
                JOIN access_history a ON f.id = a.file_id
                WHERE f.is_directory = FALSE
                GROUP BY f.id
                ORDER BY access_count DESC
                LIMIT %s
            """, (limit,))
            
            return cursor.fetchall()
            
        except Error as e:
            logger.error(f"Error getting most accessed files from database: {e}")
            return []
        finally:
            cursor.close()
    
    def get_files_with_drive_ids(self):
        """Get all files that have Google Drive IDs."""
        self._ensure_connection()
        if not self.connection:
            return []
            
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            cursor.execute("""
                SELECT path, google_drive_id
                FROM files
                WHERE google_drive_id IS NOT NULL AND google_drive_id != ''
            """)
            
            return cursor.fetchall()
            
        except Error as e:
            logger.error(f"Error getting files with drive ids from database: {e}")
            return []
        finally:
            cursor.close()
    
    def close(self):
        """Close the database connection."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("Database connection closed")