# CSV Embedder

Embed CSV data into encrypted Python source files, optionally to standalone .exe.

### Executable (.exe)

- Standalone Windows exec
- All dependencies bundled
- CSV data encrypted within binary
- Runs independently

## API Reference

### `embed_csv(csv_path, output_path=None, config=None)`

**Args:**
- `csv_path` (str): Path to input CSV file
- `output_path` (str, optional): Output file path (auto-generated if None)
- `config` (EmbedConfig, optional): Configuration

**Returns:**
- `str`: Path to generated .py file
- `tuple`: (py_path, exe_path) if compile_exe=True

### `EmbedConfig`

Configuration dataclass.

**Fields:**
- `encryption` (str): 'xor' or 'base64' (default: 'xor')
- `output_dir` (str, optional): Output directory
- `template_dir` (str, optional): Template directory
- `compile_exe` (bool): Compile to .exe (default: False)
- `exe_name` (str, optional): Custom .exe name

## Notes

**XOR encryption provides obfuscation, not "cryptographic security"**

- Each file gets a unique random key (16-47 bytes)
- Key is embedded in the .py file - anyone with access can decrypt
- For stronger protection compile to .exe

### PyInstaller fails
- Ensure PyInstaller is installed: `pip install pyinstaller`
- Check Python version compatibility (Python 3.8+)
- Verify output directory has write permissions

### Generated .exe is large
- PyInstaller bundles entire Python runtime
- Typical size: 5-15 MB
- Use UPX compression: `pip install upx`

### Import errors in generated file
- Only uses: `base64`, `io`, `csv` (all stdlib)
