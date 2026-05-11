"""
CSV Encoder - Encode CSV data for embedding into source files
"""

import base64
import os
import secrets


def encode_csv_base64(csv_path: str) -> str:
    """
    Encode CSV file to base64 string.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        Base64 encoded string
    """
    with open(csv_path, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode('ascii')


def encode_csv_xor(csv_path: str, key: bytes = None) -> tuple:
    """
    Encode CSV file with XOR encryption.
    
    Args:
        csv_path: Path to CSV file
        key: XOR key (auto-generated if None)
        
    Returns:
        Tuple of (encoded_data, key)
    """
    with open(csv_path, 'rb') as f:
        data = f.read()
    
    # Generate random key if not provided
    if key is None:
        key = secrets.token_bytes(secrets.randbelow(32) + 16)  # 16-47 bytes
    
    # XOR encrypt
    encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    
    return base64.b64encode(encrypted).decode('ascii'), key


def encode_csv_hex(csv_path: str) -> str:
    """
    Encode CSV file as hex string.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        Hex encoded string
    """
    with open(csv_path, 'rb') as f:
        data = f.read()
    return data.hex()


def get_csv_info(csv_path: str) -> dict:
    """
    Get information about CSV file.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        Dict with file info
    """
    stat = os.stat(csv_path)
    with open(csv_path, 'rb') as f:
        raw_size = len(f.read())
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    return {
        'filename': os.path.basename(csv_path),
        'path': csv_path,
        'size_bytes': stat.st_size,
        'raw_size': raw_size,
        'lines': len(lines),
        'columns': len(lines[0].strip().split(',')) if lines else 0
    }
