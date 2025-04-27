#!/bin/bash
# install.sh - Setup script for FUSE Virtual File System

set -e  # Exit on error

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print section headers
section() {
    echo -e "${YELLOW}\n===== $1 =====${NC}\n"
}

# Check Python version
section "Checking Prerequisites"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "Python version detected: $PYTHON_VERSION"

# Check FUSE installation
if command -v fusermount &> /dev/null; then
    echo "FUSE is installed."
else
    echo "FUSE not detected. You may need to install FUSE:"
    echo "  - Ubuntu/Debian: sudo apt-get install fuse libfuse-dev"
    echo "  - Fedora: sudo dnf install fuse fuse-devel"
    echo "  - macOS: brew install macfuse"
    echo "  - Windows: Download and install WinFSP from http://www.secfs.net/winfsp/"
    echo ""
    echo "Continuing installation, but the filesystem may not work without FUSE."
fi

# Create virtual environment
section "Setting up Virtual Environment"
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Skipping creation."
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}Virtual environment created.${NC}"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
section "Installing Dependencies"
echo "Installing required packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Set up environment file
section "Setting up Environment"
if [ -f ".env" ]; then
    echo ".env file already exists. Skipping creation."
else
    echo "Creating .env file from template..."
    cp env.example .env
    echo -e "${GREEN}.env file created. Please edit it with your configuration.${NC}"
fi

# Set up Google Drive credentials
section "Google Drive Integration"
if [ -f "credentials.json" ]; then
    echo "Google Drive credentials file found."
else
    echo -e "${YELLOW}Google Drive credentials not found.${NC}"
    echo "To enable Google Drive synchronization, you need to:"
    echo "1. Create a project in the Google Cloud Console"
    echo "2. Enable the Google Drive API"
    echo "3. Create OAuth 2.0 credentials"
    echo "4. Download the credentials as 'credentials.json'"
    echo "5. Place the file in the project root directory"
fi

# Make scripts executable
section "Finalizing Setup"
echo "Making scripts executable..."
chmod +x scripts/*.sh
chmod +x examples/*.sh

echo -e "\n${GREEN}Installation completed successfully!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Edit the .env file with your configuration"
echo "2. Start the filesystem: ./scripts/run.sh"
echo "3. Run the demo: ./examples/demo.sh"
echo ""
echo "To clean up and unmount: ./scripts/cleanup.sh"