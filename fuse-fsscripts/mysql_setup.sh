#!/bin/bash

# Script to setup MySQL for FUSE filesystem in WSL

# Update package lists
sudo apt update

# Install MySQL if not already installed
sudo apt install -y mysql-server

# Start MySQL service
sudo service mysql start

# Set root password and configure for native password auth
echo "Setting MySQL root password and permissions..."
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'password';"
sudo mysql -e "FLUSH PRIVILEGES;"

echo "MySQL configured successfully. Now run: cd /mnt/c/Users/Nivas\ Reddy/Desktop/fuse-fs/ && python setup_db.py"

