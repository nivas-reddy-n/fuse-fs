"""
Logging utilities for the FUSE filesystem.
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler

from fuse_fs import config

def setup_logging(log_level=None, log_file=None):
    """
    Set up logging for the FUSE filesystem.
    
    Args:
        log_level: The log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: The log file path
    """
    level = log_level or config.LOG_LEVEL
    file_path = log_file or config.LOG_FILE
    
    # Convert string log level to numeric value
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger('fuse_fs')
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers = []
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log file is specified
    if file_path:
        # Ensure log directory exists
        log_dir = os.path.dirname(file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Create rotating file handler (10 MB max size, keep 5 backups)
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=10*1024*1024,
            backupCount=5
        )
        file_handler.setLevel(level)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Log startup message
    logger.info(f"Logging initialized with level {logging.getLevelName(level)}")
    if file_path:
        logger.info(f"Logging to file: {file_path}")
    
    return logger

def get_logger(name=None):
    """
    Get a logger for a specific module.
    
    Args:
        name: The name of the module (optional)
        
    Returns:
        A logger instance
    """
    if name:
        return logging.getLogger(f'fuse_fs.{name}')
    return logging.getLogger('fuse_fs') 