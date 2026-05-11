"""
CSV Embedder - Main module for embedding CSV data into Python source files
"""

import os
import time
import subprocess
from dataclasses import dataclass
from typing import Optional, Literal
from .encoder import encode_csv_base64, encode_csv_xor, get_csv_info


@dataclass
class EmbedConfig:
    """Configuration for CSV embedding."""
    encryption: Literal['base64', 'xor'] = 'xor'
    output_dir: Optional[str] = None
    template_dir: Optional[str] = None
    compile_exe: bool = False
    exe_name: Optional[str] = None
    
    def __post_init__(self):
        if self.output_dir is None:
            self.output_dir = os.path.dirname(__file__)
        if self.template_dir is None:
            self.template_dir = os.path.join(os.path.dirname(__file__), 'templates')


def embed_csv(
    csv_path: str,
    output_path: Optional[str] = None,
    config: Optional[EmbedConfig] = None,
    raw_csv_content: Optional[str] = None
) -> str:
    """
    Embed CSV data into a Python source file.
    
    Args:
        csv_path: Path to input CSV file (used for metadata/default naming)
        output_path: Path for output source file (auto-generated if None)
        config: Embedding configuration
        raw_csv_content: Optional already-fluked CSV content string
        
    Returns:
        Path to generated file
    """
    if config is None:
        config = EmbedConfig()
    
    # Get CSV info
    info = get_csv_info(csv_path)
    
    # Use raw content if provided, otherwise read from file
    if raw_csv_content:
        # We need a temporary way to encode the raw string if the encoder 
        # expects a path. Let's adjust the logic slightly.
        import base64
        import secrets
        
        data_bytes = raw_csv_content.encode('utf-8')
        
        if config.encryption == 'xor':
            key = secrets.token_bytes(secrets.randbelow(32) + 16)
            encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data_bytes))
            encoded = base64.b64encode(encrypted).decode('ascii')
            xor_key = key
            encryption_label = f"XOR ({len(xor_key)}-byte key)"
        else:
            encoded = base64.b64encode(data_bytes).decode('ascii')
            xor_key = None
            encryption_label = "Base64"
    else:
        # Original file-based logic
        xor_key = None
        if config.encryption == 'xor':
            encoded, xor_key = encode_csv_xor(csv_path)
            encryption_label = f"XOR ({len(xor_key)}-byte key)"
        else:  # base64
            encoded = encode_csv_base64(csv_path)
            encryption_label = "Base64"
    
    # Load template
    template_path = os.path.join(config.template_dir, 'template_python.py')
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Format XOR key for template
    if xor_key:
        xor_key_str = ', '.join(str(b) for b in xor_key)
        key_len = len(xor_key)
        xor_key_section = f"# XOR decryption key ({key_len} bytes)\nXOR_KEY = bytes([{xor_key_str}])"
        xor_decrypt_body = "    encrypted = base64.b64decode(data)\n    return bytes(b ^ XOR_KEY[i % len(XOR_KEY)] for i, b in enumerate(encrypted))"
    else:
        xor_key_str = ''
        key_len = 0
        xor_key_section = '# No encryption key (Base64 only)'
        xor_decrypt_body = "    # Base64 only, no decryption needed"

    # Fill template
    output = template.replace('{{SOURCE_FILE}}', info['filename'])
    output = output.replace('{{TIMESTAMP}}', time.strftime('%Y-%m-%d %H:%M:%S'))
    output = output.replace('{{ENCRYPTION}}', encryption_label)
    output = output.replace('{{ENCODED_DATA}}', encoded)
    output = output.replace('{{XOR_KEY_SECTION}}', xor_key_section)
    output = output.replace('{{XOR_DECRYPT_BODY}}', xor_decrypt_body)
    
    # Determine output path
    if output_path is None:
        base_name = os.path.splitext(info['filename'])[0]
        output_path = os.path.join(config.output_dir, f'{base_name}_embedded.py')
    
    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)
    
    # Compile to .exe if requested
    if config.compile_exe:
        exe_path = compile_to_exe(output_path, config.exe_name, config.output_dir)
        return output_path, exe_path
    
    return output_path


def compile_to_exe(py_path: str, exe_name: Optional[str] = None, output_dir: Optional[str] = None) -> str:
    """
    Compile Python file to standalone .exe using PyInstaller.
    
    Args:
        py_path: Path to Python file
        exe_name: Name for output .exe (auto-generated if None)
        output_dir: Output directory (same as py_path dir if None)
        
    Returns:
        Path to generated .exe
    """
    if output_dir is None:
        output_dir = os.path.dirname(py_path)
    
    if exe_name is None:
        exe_name = os.path.splitext(os.path.basename(py_path))[0]
    
    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',
        '--noconsole',
        '--distpath', output_dir,
        '--workpath', os.path.join(output_dir, 'build'),
        '--specpath', os.path.join(output_dir, 'spec'),
        '--name', exe_name,
        py_path
    ]
    
    print(f"Running PyInstaller: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"PyInstaller failed:\n{result.stderr}")
    
    exe_path = os.path.join(output_dir, f'{exe_name}.exe')
    
    # Clean up PyInstaller artifacts
    import shutil
    for d in ['build', 'spec']:
        dpath = os.path.join(output_dir, d)
        if os.path.exists(dpath):
            shutil.rmtree(dpath)
    
    return exe_path


def embed_csv_batch(
    csv_paths: list,
    output_dir: str,
    config: Optional[EmbedConfig] = None
) -> list:
    """
    Embed multiple CSV files.
    
    Args:
        csv_paths: List of CSV file paths
        output_dir: Output directory for generated files
        config: Embedding configuration
        
    Returns:
        List of generated file paths
    """
    if config is None:
        config = EmbedConfig()
    config.output_dir = output_dir
    
    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    for csv_path in csv_paths:
        output_path = embed_csv(csv_path, config=config)
        results.append(output_path)
    
    return results
