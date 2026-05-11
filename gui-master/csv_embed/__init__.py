"""
CSV Embedder - Embed CSV data into Python source files

Features:
- XOR encryption with random key (key baked into output)
- Base64 encoding (no encryption)
- Optional PyInstaller compilation to .exe

Usage:
    from csv_embed import embed_csv, EmbedConfig
    
    # XOR encrypted Python file
    config = EmbedConfig(encryption='xor')
    embed_csv('data.csv', config=config)
    
    # XOR encrypted + compiled to .exe
    config = EmbedConfig(encryption='xor', compile_exe=True)
    py_path, exe_path = embed_csv('data.csv', config=config)
"""

from .encoder import encode_csv_base64, encode_csv_xor
from .csv_embedder import embed_csv, compile_to_exe, EmbedConfig

__all__ = ['embed_csv', 'compile_to_exe', 'encode_csv_base64', 'encode_csv_xor', 'EmbedConfig']
