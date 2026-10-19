#!/usr/bin/env python3
"""
Configuration module for MFA Manager
Handles environment variables and application configuration
"""

import os
from typing import Union

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, just use system environment variables
    pass


def get_port() -> int:
    """
    Get the port number from environment variables with fallback to default.
    
    Checks the following environment variables in order:
    1. PORT
    2. FLASK_PORT  
    3. Default: 4570
    
    Returns:
        int: Port number to use for the application
    """
    port_str = os.environ.get('PORT') or os.environ.get('FLASK_PORT')
    
    if port_str:
        try:
            port = int(port_str)
            if 1 <= port <= 65535:
                return port
            else:
                print(f"⚠️  Warning: Invalid port {port} (must be 1-65535), using default 4570")
        except ValueError:
            print(f"⚠️  Warning: Invalid port value '{port_str}', using default 4570")
    
    return 4570


def get_host() -> str:
    """
    Get the host address from environment variables with fallback logic.
    
    Returns:
        str: Host address to bind to ('0.0.0.0' for production, '127.0.0.1' for development)
    """
    # Check if explicitly set
    host = os.environ.get('HOST') or os.environ.get('FLASK_HOST')
    if host:
        return host
    
    # Production vs development logic
    return '0.0.0.0' if os.environ.get('FLASK_ENV') == 'production' else '127.0.0.1'


def is_production() -> bool:
    """
    Check if running in production mode.
    
    Returns:
        bool: True if FLASK_ENV is set to 'production'
    """
    return os.environ.get('FLASK_ENV') == 'production'


def get_database_path() -> str:
    """
    Get the database path from environment variables with fallback.
    
    Returns:
        str: Database file path
    """
    return os.environ.get('DATABASE_PATH', 'mfa_manager.db')


def get_secret_key() -> str:
    """
    Get the secret key from environment variables with fallback.

    Returns:
        str: Secret key for Flask application
    """
    import secrets
    return os.environ.get('SECRET_KEY', secrets.token_hex(32))


def get_encryption_key() -> Union[str, None]:
    """
    Get the encryption key from environment variables.
    This key must be a base64-encoded 32-byte key for Fernet.

    Returns:
        str: Encryption key or None if not set
    """
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        if is_production():
            print("❌ Error: ENCRYPTION_KEY must be set in production environment!")
        else:
            print("⚠️  Warning: ENCRYPTION_KEY not set. Secrets will not be encrypted.")
    return key