import os
import zlib
import base64
OUTPUT_DIR = 'frontend'
LAUNCHER_FILES = {
    'home.html': 'DATA_HOME',
    'settings.html': 'DATA_SETTINGS',
    'discover.html': 'DATA_DISCOVER'
}
LAUNCHER_OUTPUT = 'frontend_assets.py'
ENGINE_FILES = {
    'index.html': 'DATA_INDEX'
}
ENGINE_OUTPUT = 'engine_assets.py'

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
def build():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        with open(os.path.join(OUTPUT_DIR, '__init__.py'), 'w') as f:
            f.write("") 
    write_asset_file(LAUNCHER_OUTPUT, LAUNCHER_FILES, "Launcher UI")
    write_asset_file(ENGINE_OUTPUT, ENGINE_FILES, "Engine Core")
    print("ALL BUILDS COMPLETE! Ready for compilation.")
if __name__ == "__main__":
    build()