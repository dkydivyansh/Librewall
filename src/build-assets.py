import os
import zlib
import base64
OUTPUT_DIR = 'frontend'
LAUNCHER_FILES = {
    'home.html': 'DATA_HOME',
    'settings.html': 'DATA_SETTINGS',
    'discover.html': 'DATA_DISCOVER',
    'featured.html': 'DATA_FEATURED',
    'widgets.html': 'DATA_WIDGETS',
    'cursors.html': 'DATA_CURSORS',
    '1.ico': 'ICON_1'
}
LAUNCHER_OUTPUT = 'frontend_assets.py'
ENGINE_FILES = {
    'index.html': 'DATA_INDEX',
    '1.ico': 'ICON_1'
}
ENGINE_OUTPUT = 'engine_assets.py'
LIBRARY_DIR = os.path.join('library', 'jsm')
LIBRARY_OUTPUT_DIR = os.path.join('library', 'jsm')
LIBRARY_OUTPUT = 'library_assets.py'
BUILD_LIBRARY = False

THREEJS_DIR = 'threejs'
THREEJS_OUTPUT_DIR = os.path.join('library', 'threejs')
THREEJS_OUTPUT = 'threejs_assets.py'
BUILD_THREEJS = False

def write_asset_file(filename, file_map, description):
    output_path = os.path.join(OUTPUT_DIR, filename)
    print(f" Building {description} into {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as py_file:
        py_file.write(f"# Auto-generated compressed assets for {description}. Do not edit.\n")
        py_file.write("import base64\n")
        py_file.write("import zlib\n\n")
        py_file.write("def get_asset(name):\n")
        py_file.write("    data = globals().get(name)\n")
        py_file.write("    if data:\n")
        py_file.write("        return zlib.decompress(base64.b64decode(data))\n")
        py_file.write("    return None\n\n")
        for src_file, var_name in file_map.items():
            if os.path.exists(src_file):
                with open(src_file, 'rb') as f:
                    raw_bytes = f.read()
                    compressed = zlib.compress(raw_bytes)
                    b64_encoded = base64.b64encode(compressed).decode('utf-8')
                    py_file.write(f'{var_name} = "{b64_encoded}"\n')
                    print(f" Compressed {src_file}: {len(raw_bytes)} -> {len(b64_encoded)} bytes")
            else:
                print(f"  {src_file} not found. Skipping.")
                py_file.write(f'{var_name} = None\n')
    print(f" {description} complete.\n")

def write_library_assets(output_filename, source_dir, description):
    """Pack all files from a directory recursively into a single Python asset file."""
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    print(f" Building {description} into {output_path}...")
    
    files_to_pack = {}
    for root, _, files in os.walk(source_dir):
        for file in files:
            full_path = os.path.join(root, file)
            relative_path = os.path.relpath(full_path, os.path.dirname(source_dir))
            url_path = relative_path.replace(os.sep, '/')
            files_to_pack[url_path] = full_path
    
    with open(output_path, 'w', encoding='utf-8') as py_file:
        py_file.write(f"# Auto-generated compressed assets for {description}. Do not edit.\n")
        py_file.write("import base64\n")
        py_file.write("import zlib\n\n")
        py_file.write("# Dictionary mapping URL paths to compressed data\n")
        py_file.write("LIBRARY_DATA = {\n")
        
        total_original = 0
        total_compressed = 0
        
        for url_path, full_path in sorted(files_to_pack.items()):
            try:
                with open(full_path, 'rb') as f:
                    raw_bytes = f.read()
                    compressed = zlib.compress(raw_bytes)
                    b64_encoded = base64.b64encode(compressed).decode('utf-8')
                    py_file.write(f'    "{url_path}": "{b64_encoded}",\n')
                    total_original += len(raw_bytes)
                    total_compressed += len(b64_encoded)
                    print(f"   Packed: {url_path} ({len(raw_bytes)} -> {len(b64_encoded)} bytes)")
            except Exception as e:
                print(f"   Error packing {full_path}: {e}")
        
        py_file.write("}\n\n")
        py_file.write("def get_library_asset(path):\n")
        py_file.write('    """Get a library asset by its URL path (e.g., \'jsm/loaders/GLTFLoader.js\')."""\n')
        py_file.write("    data = LIBRARY_DATA.get(path)\n")
        py_file.write("    if data:\n")
        py_file.write("        return zlib.decompress(base64.b64decode(data))\n")
        py_file.write("    return None\n\n")
        py_file.write("def has_library_asset(path):\n")
        py_file.write('    """Check if a library asset exists."""\n')
        py_file.write("    return path in LIBRARY_DATA\n")
    
    print(f" {description} complete. Total: {total_original} -> {total_compressed} bytes ({len(files_to_pack)} files)\n")

def write_library_assets_to_path(output_path, description):
    print(f" Building {description} into {output_path}...")
    
    with open(output_path, 'w', encoding='utf-8') as py_file:
        py_file.write(f"# Auto-generated compressed assets for {description}. Do not edit.\n")
        py_file.write("import base64\n")
        py_file.write("import zlib\n\n")
        py_file.write("# Dictionary mapping URL paths to compressed data\n")
        py_file.write("LIBRARY_DATA = {\n")
        py_file.write("}\n\n")
        py_file.write("def get_library_asset(path):\n")
        py_file.write('    """Get a library asset by its URL path."""\n')
        py_file.write("    data = LIBRARY_DATA.get(path)\n")
        py_file.write("    if data:\n")
        py_file.write("        return zlib.decompress(base64.b64decode(data))\n")
        py_file.write("    return None\n\n")
        py_file.write("def has_library_asset(path):\n")
        py_file.write('    """Check if a library asset exists."""\n')
        py_file.write("    return path in LIBRARY_DATA\n")
    
    print(f" {description} complete (empty stub generated).\n")

def write_library_assets_full(output_path, source_dir, description):
    print(f" Building {description} into {output_path}...")
    
    files_to_pack = {}
    base_name = os.path.basename(source_dir)
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.py') or file == '__init__.py' or file.endswith('.pyc'):
                continue
            if '__pycache__' in root:
                continue
            full_path = os.path.join(root, file)
            rel_from_source = os.path.relpath(full_path, source_dir)
            url_path = f"{base_name}/{rel_from_source}".replace(os.sep, '/')
            files_to_pack[url_path] = full_path
    
    with open(output_path, 'w', encoding='utf-8') as py_file:
        py_file.write(f"# Auto-generated compressed assets for {description}. Do not edit.\n")
        py_file.write("import base64\n")
        py_file.write("import zlib\n\n")
        py_file.write("# Dictionary mapping URL paths to compressed data\n")
        py_file.write("LIBRARY_DATA = {\n")
        
        total_original = 0
        total_compressed = 0
        
        for url_path, full_path in sorted(files_to_pack.items()):
            try:
                with open(full_path, 'rb') as f:
                    raw_bytes = f.read()
                    compressed = zlib.compress(raw_bytes)
                    b64_encoded = base64.b64encode(compressed).decode('utf-8')
                    py_file.write(f'    "{url_path}": "{b64_encoded}",\n')
                    total_original += len(raw_bytes)
                    total_compressed += len(b64_encoded)
                    print(f"   Packed: {url_path} ({len(raw_bytes)} -> {len(b64_encoded)} bytes)")
            except Exception as e:
                print(f"   Error packing {full_path}: {e}")
        
        py_file.write("}\n\n")
        py_file.write("def get_library_asset(path):\n")
        py_file.write('    """Get a library asset by its URL path."""\n')
        py_file.write("    data = LIBRARY_DATA.get(path)\n")
        py_file.write("    if data:\n")
        py_file.write("        return zlib.decompress(base64.b64decode(data))\n")
        py_file.write("    return None\n\n")
        py_file.write("def has_library_asset(path):\n")
        py_file.write('    """Check if a library asset exists."""\n')
        py_file.write("    return path in LIBRARY_DATA\n")
    
    print(f" {description} complete. Total: {total_original} -> {total_compressed} bytes ({len(files_to_pack)} files)\n")

def build():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        with open(os.path.join(OUTPUT_DIR, '__init__.py'), 'w') as f:
            f.write("") 
    write_asset_file(LAUNCHER_OUTPUT, LAUNCHER_FILES, "Launcher UI")
    write_asset_file(ENGINE_OUTPUT, ENGINE_FILES, "Engine Core")
    if BUILD_LIBRARY:
        if not os.path.exists(LIBRARY_OUTPUT_DIR):
            os.makedirs(LIBRARY_OUTPUT_DIR)
        init_file = os.path.join(LIBRARY_OUTPUT_DIR, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write("")
        library_output_path = os.path.join(LIBRARY_OUTPUT_DIR, LIBRARY_OUTPUT)
        write_library_assets_full(library_output_path, LIBRARY_DIR, "Three.js JSM Library")
    else:
        print(" Skipping Three.js JSM Library build (BUILD_LIBRARY = False)")
    
    if BUILD_THREEJS:
        if not os.path.exists(THREEJS_OUTPUT_DIR):
            os.makedirs(THREEJS_OUTPUT_DIR)
        init_file = os.path.join(THREEJS_OUTPUT_DIR, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write("")
        threejs_output_path = os.path.join(THREEJS_OUTPUT_DIR, THREEJS_OUTPUT)
        write_library_assets_full(threejs_output_path, THREEJS_DIR, "Three.js Core")
    else:
        print(" Skipping Three.js Core build (BUILD_THREEJS = False)")
    print("ALL BUILDS COMPLETE! Ready for compilation.")
if __name__ == "__main__":
    build()