"""
Encryption and decryption utilities for the FUSE filesystem.
"""
import os
import logging
import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

from fuse_fs import config

logger = logging.getLogger(__name__)

class Crypto:
    """
    Encryption and decryption utilities for the FUSE filesystem.
    
    Uses AES-256 in CBC mode for file encryption.
    """
    
    def __init__(self, key=None):
        """Initialize crypto with the encryption key."""
        self.enabled = config.ENCRYPTION_ENABLED
        
        if not self.enabled:
            logger.info("Encryption is disabled")
            return
            
        # Use provided key or get from config
        if key:
            self.key = self._process_key(key)
        elif config.ENCRYPTION_KEY:
            self.key = self._process_key(config.ENCRYPTION_KEY)
        else:
            # Generate a random key if none is provided
            self.key = get_random_bytes(32)  # 256 bits
            logger.warning("Using generated encryption key. This key will not persist between restarts!")
        
        logger.info("Initialized crypto module")
    
    def _process_key(self, key):
        """Process the encryption key into correct format."""
        if isinstance(key, bytes):
            # If it's already bytes and the right length, use it
            if len(key) == 32:
                return key
            # Otherwise, hash it to get a consistent length
            return self._hash_key(key)
            
        # If it's a string, convert to bytes and hash
        key_bytes = key.encode('utf-8') if isinstance(key, str) else key
        return self._hash_key(key_bytes)
    
    def _hash_key(self, key_bytes):
        """Hash the key to get a 32-byte key."""
        from hashlib import sha256
        return sha256(key_bytes).digest()
    
    def encrypt(self, data):
        """
        Encrypt data using AES-256-CBC.
        
        Args:
            data: The data to encrypt (bytes)
            
        Returns:
            The encrypted data with IV prepended
        """
        if not self.enabled:
            return data
            
        try:
            # Generate a random 16-byte initialization vector
            iv = get_random_bytes(16)
            
            # Create cipher with key and IV
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            
            # Encrypt and pad the data
            encrypted_data = cipher.encrypt(pad(data, AES.block_size))
            
            # Return IV + encrypted data
            return iv + encrypted_data
            
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            # If encryption fails, return the original data
            return data
    
    def decrypt(self, data):
        """
        Decrypt data using AES-256-CBC.
        
        Args:
            data: The encrypted data with IV prepended
            
        Returns:
            The decrypted data
        """
        if not self.enabled:
            return data
            
        try:
            # Extract the 16-byte IV from the beginning of the data
            iv = data[:16]
            ciphertext = data[16:]
            
            # Create cipher with key and IV
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            
            # Decrypt and unpad the data
            decrypted_data = unpad(cipher.decrypt(ciphertext), AES.block_size)
            
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            # If decryption fails, return the original data
            return data
    
    def encrypt_file(self, source_path, dest_path=None):
        """
        Encrypt a file.
        
        Args:
            source_path: Path to the file to encrypt
            dest_path: Path to save the encrypted file (optional)
            
        Returns:
            The path to the encrypted file
        """
        if not self.enabled:
            return source_path
            
        dest_path = dest_path or source_path + '.encrypted'
        
        try:
            with open(source_path, 'rb') as f_in:
                data = f_in.read()
                
            encrypted_data = self.encrypt(data)
            
            with open(dest_path, 'wb') as f_out:
                f_out.write(encrypted_data)
                
            return dest_path
            
        except Exception as e:
            logger.error(f"File encryption error for {source_path}: {e}")
            return source_path
    
    def decrypt_file(self, source_path, dest_path=None):
        """
        Decrypt a file.
        
        Args:
            source_path: Path to the encrypted file
            dest_path: Path to save the decrypted file (optional)
            
        Returns:
            The path to the decrypted file
        """
        if not self.enabled:
            return source_path
            
        dest_path = dest_path or source_path.replace('.encrypted', '')
        
        try:
            with open(source_path, 'rb') as f_in:
                data = f_in.read()
                
            decrypted_data = self.decrypt(data)
            
            with open(dest_path, 'wb') as f_out:
                f_out.write(decrypted_data)
                
            return dest_path
            
        except Exception as e:
            logger.error(f"File decryption error for {source_path}: {e}")
            return source_path 