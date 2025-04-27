#!/usr/bin/env python3
"""
Database setup script for FUSE Virtual File System.
This script creates the necessary database and tables for the filesystem.
"""
import os
import sys
import argparse
import getpass
import mysql.connector
from mysql.connector import Error

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Setup database for FUSE Virtual File System"
    )
    
    parser.add_argument(
        "--host",
        help="MySQL host (default: localhost)",
        default="localhost"
    )
    
    parser.add_argument(
        "--port",
        help="MySQL port (default: 3306)",
        type=int,
        default=3306
    )
    
    parser.add_argument(
        "--admin-user",
        help="MySQL admin username (default: root)",
        default="root"
    )
    
    parser.add_argument(
        "--db-name",
        help="Database name to create (default: fuse_fs)",
        default="fuse_fs"
    )
    
    parser.add_argument(
        "--db-user",
        help="Database user to create (default: fuse_user)",
        default="fuse_user"
    )
    
    return parser.parse_args()

def setup_database(host, port, admin_user, admin_password, db_name, db_user, db_password):
    """Set up the database and user."""
    try:
        # Connect to MySQL server as admin
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=admin_user,
            password=admin_password
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            print(f"Database '{db_name}' created or already exists.")
            
            # Create user if it doesn't exist
            # Note: The syntax varies depending on MySQL version
            try:
                cursor.execute(f"CREATE USER IF NOT EXISTS '{db_user}'@'localhost' IDENTIFIED BY '{db_password}'")
            except Error:
                # Fallback for older MySQL versions
                try:
                    cursor.execute(f"SELECT User FROM mysql.user WHERE User = '{db_user}' AND Host = 'localhost'")
                    if not cursor.fetchone():
                        cursor.execute(f"CREATE USER '{db_user}'@'localhost' IDENTIFIED BY '{db_password}'")
                except Error as e:
                    print(f"Error creating user: {e}")
                    return False
            
            print(f"User '{db_user}' created or already exists.")
            
            # Grant privileges
            cursor.execute(f"GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'localhost'")
            cursor.execute("FLUSH PRIVILEGES")
            print(f"Privileges granted to user '{db_user}'.")
            
            # Create a .env file with database configuration
            env_content = f"""
# Database configuration
DB_HOST={host}
DB_USER={db_user}
DB_PASSWORD={db_password}
DB_NAME={db_name}
DB_PORT={port}

# Filesystem paths
MOUNT_POINT=~/fuse_mount
STORAGE_PATH=~/fuse_storage

# Google Drive API
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json

# LFU Cache settings
CACHE_SIZE=100
CACHE_DIR=~/fuse_storage/cache

# Sync settings
SYNC_INTERVAL=300
MAX_SYNC_RETRIES=3

# Security settings
ENCRYPTION_ENABLED=False
ENCRYPTION_KEY=

# Logging configuration
LOG_LEVEL=INFO
LOG_FILE=fuse_fs.log

# Performance tuning
BUFFER_SIZE=4096
"""
            
            with open(".env", "w") as f:
                f.write(env_content)
            
            print("Created .env file with database configuration.")
            
            return True
            
    except Error as e:
        print(f"Error: {e}")
        return False
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def main():
    """Main entry point."""
    args = parse_args()
    
    print("FUSE Virtual File System - Database Setup")
    print("----------------------------------------")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Admin user: {args.admin_user}")
    print(f"Database name: {args.db_name}")
    print(f"Database user: {args.db_user}")
    print()
    
    # Get admin password
    admin_password = getpass.getpass(f"Enter password for MySQL admin user '{args.admin_user}': ")
    
    # Get database password
    db_password = getpass.getpass(f"Enter password for new database user '{args.db_user}': ")
    confirm_password = getpass.getpass("Confirm password: ")
    
    if db_password != confirm_password:
        print("Error: Passwords do not match.")
        return 1
    
    success = setup_database(
        args.host,
        args.port,
        args.admin_user,
        admin_password,
        args.db_name,
        args.db_user,
        db_password
    )
    
    if success:
        print("\nDatabase setup completed successfully.")
        print("You can now run the FUSE filesystem with:")
        print("  python -m fuse_fs")
        return 0
    else:
        print("\nDatabase setup failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 