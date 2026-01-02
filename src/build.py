import os
import shutil
import subprocess
import sys
import time

def run_build():
    SPEC_FILE = "librewall_suite.spec"
    DIST_DIR = "dist"
    OUTPUT_FOLDER_NAME = "librewall_suite"
    ASSETS_TO_COPY = [
        ("wallpapers", "wallpapers"),
        ("include", "include"),
        ("hdr", "hdr"),
        ("build", "build"),
        ("library", "library"),
        ("app_config.json", None), 

        ("1.ico", None) 

    ]

    print(f" Starting Build Process for Librewall...")
    print(f" Running PyInstaller on {SPEC_FILE}...")

    start_time = time.time()

    try:

        process = subprocess.Popen(
            [sys.executable, "-m", "PyInstaller", SPEC_FILE, "--noconfirm"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace' 

        )

        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"[PyInstaller] {output.strip()}")

        return_code = process.poll()

        if return_code != 0:
            print(f" PyInstaller failed with return code {return_code}")
            sys.exit(1)
        else:
            print(" PyInstaller build completed successfully.")

    except FileNotFoundError:
        print(" Error: PyInstaller not found. Please ensure it is installed (pip install pyinstaller).")
        sys.exit(1)
    except Exception as e:
        print(f" An unexpected error occurred during PyInstaller execution: {e}")
        sys.exit(1)

    destination_root = os.path.join(DIST_DIR, OUTPUT_FOLDER_NAME)

    if not os.path.exists(destination_root):
        print(f" Error: Output directory '{destination_root}' does not exist. Did the build fail?")
        sys.exit(1)

    print(f"\n Copying assets to {destination_root}...")

    for src, dest_name in ASSETS_TO_COPY:
        source_path = os.path.abspath(src)

        if dest_name:
            dest_path = os.path.join(destination_root, dest_name)
        else:

            dest_path = os.path.join(destination_root, os.path.basename(src))

        try:
            if os.path.isdir(source_path):

                if os.path.exists(dest_path):
                    print(f"   ⚠️  Removing existing directory: {dest_path}")
                    shutil.rmtree(dest_path)

                print(f"   Copying directory: {src} -> {dest_path}")
                shutil.copytree(source_path, dest_path)

            elif os.path.isfile(source_path):

                print(f"   Copying file: {src} -> {dest_path}")
                shutil.copy2(source_path, dest_path)

            else:
                print(f"  Warning: Source '{src}' not found. Skipping.")

        except Exception as e:
            print(f" Error copying {src}: {e}")

    end_time = time.time()
    duration = end_time - start_time

    print("-" * 50)
    print(f" BUILD COMPLETED in {duration:.2f} seconds!")
    print(f" Output Directory: {os.path.abspath(destination_root)}")
    print("-" * 50)

if __name__ == "__main__":
    run_build()