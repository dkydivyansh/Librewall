import sys
import os
if sys.stdout is None or sys.stderr is None:
    class NullWriter:
        def write(self, text): pass
        def flush(self): pass
        def isatty(self): return False
    sys.stdout = NullWriter()
    sys.stderr = NullWriter()

import api_config
import handler
import builtins

if not api_config.developer_enabled:
   class NullWriter:
       def write(self, text): pass
       def flush(self): pass
       def isatty(self): return False
   
   def print(*args, **kwargs): pass
   builtins.print = print
   sys.stdout = NullWriter()
   sys.stderr = NullWriter()

import gpu_utils
import http.server
import socketserver
import threading
import socket
import json
import mimetypes
import urllib.request
import webbrowser
import subprocess
import shutil
import time
import zipfile
import io
import urllib.parse
import email
import random
import string
from PyQt6.QtCore import QUrl, Qt, QTimer
try:
    from PyQt6.QtQuick import QQuickWindow, QSGRendererInterface
    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)
except ImportError:
    print("Warning: PyQt6.QtQuick or QSGRendererInterface not found. Skipping graphics API switch.")

from PyQt6.QtWidgets import QApplication, QMainWindow, QMenu
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineScript
import updater_module 
import zlib  
import base64 
import ctypes
from ctypes import wintypes
import hashlib
from PIL import Image
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--gpu-preference=high-performance "
    "--enable-gpu-rasterization "
    "--disable-gpu-driver-bug-workarounds "
    "--use-angle=default "
    "--disable-renderer-backgrounding "
    "--enable-accelerated-video-decode"
)
try:
    import win32com.client
    HAS_WIN32COM = True
except ImportError:
    HAS_WIN32COM = False
    print("Warning: win32com not found. Auto-start shortcut features will be disabled.")
try:
    from frontend import frontend_assets
    HAS_EMBEDDED_ASSETS = True
    print(" Loaded high-performance embedded assets.")
except ImportError:
    HAS_EMBEDDED_ASSETS = False
    print(" No embedded assets found. Running in dev (file-system) mode.")

try:
    from library.threejs import threejs_assets
    HAS_THREEJS_ASSETS = True
    print(" Loaded threejs/driver.js assets.")
except ImportError:
    HAS_THREEJS_ASSETS = False
    print(" No threejs assets found. Running in dev mode.")

API_BASE_URL = api_config.base_url
CURRENT_APP_VERSION = api_config.CURRENT_APP_VERSION
CURRENT_APP_VERSION_NAME = api_config.CURRENT_APP_VERSION_NAME
WALLPAPERS_DIR = api_config.WALLPAPERS_DIR
EDITOR_PORT = api_config.EDITOR_PORT
EDITOR_SERVER_URL = f"http://localhost:{EDITOR_PORT}"
EDITOR_HTML = api_config.EDITOR_HTML
DISCOVER_HTML = api_config.DISCOVER_HTML
SETTINGS_HTML = api_config.SETTINGS_HTML
FEATURED_HTML = api_config.FEATURED_HTML
WIDGETS_HTML = api_config.WIDGETS_HTML

APP_SECURITY_TOKEN = ''.join(random.choices(string.digits, k=12))
print(f"Authentication Token (User-Agent): {APP_SECURITY_TOKEN}")
if getattr(sys, 'frozen', False):
    SERVER_ROOT = os.path.dirname(sys.executable)
else:
    SERVER_ROOT = os.path.abspath(os.path.dirname(__file__))
print(f"Server Root detected as: {SERVER_ROOT}")
APP_CONFIG_FILE = api_config.APP_CONFIG_FILE
THUMBNAIL_CACHE_DIR = api_config.THUMBNAIL_CACHE_DIR
user32   = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SW_RESTORE    = 9
SW_SHOWNORMAL = 1

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

def _get_hwnd_by_title_substring(substring: str) -> int:
    substring = substring.lower()
    found_hwnd = ctypes.c_ulong(0)

    def callback(hwnd, lParam):
        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True

        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value.lower()

        if substring in title:
            found_hwnd.value = hwnd
            return False

        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return found_hwnd.value

def bring_existing_instance_to_front(window_title="librewall") -> bool:
    hwnd = user32.FindWindowW(None, window_title)

    if not hwnd:
        hwnd = _get_hwnd_by_title_substring(window_title)

    if not hwnd:
        return False

    user32.ShowWindow(hwnd, SW_RESTORE)

    foreground_hwnd = user32.GetForegroundWindow()
    foreground_thread_id = user32.GetWindowThreadProcessId(foreground_hwnd, None) if foreground_hwnd else 0
    current_thread_id = kernel32.GetCurrentThreadId()

    if foreground_thread_id != 0 and foreground_thread_id != current_thread_id:
        user32.AttachThreadInput(current_thread_id, foreground_thread_id, True)

    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.ShowWindow(hwnd, SW_SHOWNORMAL)

    if foreground_thread_id != 0 and foreground_thread_id != current_thread_id:
        user32.AttachThreadInput(current_thread_id, foreground_thread_id, False)

    return True

mutex_handle = None  

def check_single_instance(mutex_name=r"Local\librewall", window_title="librewall"):
    global mutex_handle

    mutex_handle = kernel32.CreateMutexW(None, False, mutex_name)
    gpu_utils.mutex_handle = mutex_handle

    if kernel32.GetLastError() == 183:
        if mutex_handle:
            kernel32.CloseHandle(mutex_handle)
        sys.exit(0)
        return False

    return True  

LOADING_HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>Loading Librewall...</title>
    <style>
        body { background: #121212; color: white; display: flex; flex-direction: column; 
               justify-content: center; align-items: center; height: 100vh; margin: 0; font-family: sans-serif; }
        .loader { border: 4px solid #333; border-top: 4px solid #3498db; border-radius: 50%; 
                  width: 40px; height: 40px; animation: spin 1s linear infinite; margin-bottom: 20px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="loader"></div>
    <div id="status">Initializing Engine...</div>
    <script>
        const targetUrl = "http://127.0.0.1:5001";
        async function checkServer() {
            try {
                await fetch(targetUrl, { mode: 'no-cors', cache: 'no-store' });
                window.location.replace(targetUrl);
            } catch (e) {
                setTimeout(checkServer, 500); 
            }
        }
        checkServer();
    </script>
</body>
</html>
"""

ENGINE_EXE_PATH = os.path.join(SERVER_ROOT, 'engine.exe')
MAIN_PY_PATH = os.path.join(SERVER_ROOT, 'main.py') 

if os.path.isfile(ENGINE_EXE_PATH):
    ENGINE_RUN_COMMAND = [ENGINE_EXE_PATH]
    print(f"Found engine executable: {ENGINE_EXE_PATH}")
elif os.path.isfile(MAIN_PY_PATH):
    ENGINE_RUN_COMMAND = [sys.executable, MAIN_PY_PATH] 
    print(f"Found engine script: {MAIN_PY_PATH}")
else:
    ENGINE_RUN_COMMAND = None
    print("WARNING: No 'engine.exe' or 'main.py' found in server root.")

def read_app_config():
    config_path = handler.get_app_config_path()

    defaults = {'active_theme': '', 'port': 8080, 'auto_start': True} 
    if not os.path.isfile(config_path):
        print(f"Warning: {APP_CONFIG_FILE} not found at {config_path}. Using defaults.")
        return defaults
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            defaults.update(config) 
            return defaults
    except Exception as e:
        print(f"Error reading {APP_CONFIG_FILE}: {e}. Using defaults.")
        return defaults

def _get_package_family_name():
    try:
        parts = SERVER_ROOT.replace('/', '\\').split('\\')
        for part in parts:
            if part.startswith('dkydivyansh.Librewall_') and '__' in part:
                name_and_rest = part.split('__')
                if len(name_and_rest) == 2:
                    publisher_hash = name_and_rest[1]
                    package_name = name_and_rest[0].rsplit('_', 2)[0]
                    pfn = f"{package_name}_{publisher_hash}"
                    print(f"Extracted PackageFamilyName from path: {pfn}")
                    return pfn
    except Exception as e:
        print(f"Could not extract PFN from path: {e}")

    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0 
        result = subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-Command',
             "(Get-AppxPackage -Name 'dkydivyansh.Librewall').PackageFamilyName"],
            capture_output=True, text=True, startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        pfn = result.stdout.strip()
        if pfn:
            print(f"Got PackageFamilyName from PowerShell: {pfn}")
            return pfn
    except Exception as e:
        print(f"PowerShell PFN lookup failed: {e}")

    return None

def _cleanup_old_startup_shortcut():
    try:
        if HAS_WIN32COM:
            shell = win32com.client.Dispatch("WScript.Shell")
            startup_folder = shell.SpecialFolders("Startup")
        else:
            startup_folder = os.path.join(os.environ.get('APPDATA', ''), 
                                          r'Microsoft\Windows\Start Menu\Programs\Startup')
        
        shortcut_path = os.path.join(startup_folder, "LibrewallEngine.lnk")
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
            print(f"Cleaned up old startup shortcut: {shortcut_path}")
    except Exception as e:
        print(f"Could not clean up old shortcut: {e}")

def update_startup_shortcut(enable: bool):
    import winreg

    REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    REG_VALUE_NAME = "LibrewallEngine"

    try:
        is_store_app = "WindowsApps" in SERVER_ROOT

        if enable:
            if is_store_app:
                package_family_name = _get_package_family_name()
                if not package_family_name:
                    return False, "Could not determine package family name for Store app."
                command = f'explorer.exe shell:AppsFolder\\{package_family_name}!App'
                print(f"Store app detected. Auto-start command: {command}")
            else:
                engine_exe_path = os.path.join(SERVER_ROOT, 'engine.exe')
                if os.path.isfile(engine_exe_path):
                    command = f'"{engine_exe_path}"'
                    print(f"Non-store install. Auto-start target: {engine_exe_path}")
                else:
                    command = f'"{sys.executable}" "{os.path.join(SERVER_ROOT, "main.py")}"'
                    print(f"engine.exe not found, falling back to: {command}")

            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, REG_VALUE_NAME, 0, winreg.REG_SZ, command)
            winreg.CloseKey(key)
            print(f"Added auto-start registry entry: {REG_VALUE_NAME}")
        else:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, REG_VALUE_NAME)
                winreg.CloseKey(key)
                print(f"Removed auto-start registry entry: {REG_VALUE_NAME}")
            except FileNotFoundError:
                print("Auto-start registry entry does not exist, nothing to remove.")
        _cleanup_old_startup_shortcut()

        return True, None
    except Exception as e:
        print(f"Error managing auto-start registry: {e}")
        return False, str(e)

def validate_wallpaper(theme_dir_name, theme_path):
    config_path = os.path.join(theme_path, 'config.json')

    if not os.path.isfile(config_path):
        return {'isValid': False, 'themeId': theme_dir_name, 'themeName': theme_dir_name, 'missingAssets': ['config.json']}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    except Exception as e:
        return {'isValid': False, 'themeId': theme_dir_name, 'themeName': theme_dir_name, 'missingAssets': ['config.json (Invalid JSON)'], 'error': str(e)}

    missing_assets = []

    def check_asset(filename_key, is_required=False):
        filepath = config_data.get(filename_key)

        if filepath:
            if not os.path.isfile(os.path.join(theme_path, filepath)):
                missing_assets.append(filepath)
        elif is_required:
            if filename_key == 'modelFile' and filepath is not None:
                 missing_assets.append(f"{filename_key} (key missing in config.json)")
            elif filename_key != 'modelFile':
                 missing_assets.append(f"{filename_key} (key missing in config.json)")

    if 'modelFile' in config_data and config_data['modelFile'] is not None:
        if not os.path.isfile(os.path.join(theme_path, config_data['modelFile'])):
             missing_assets.append(config_data['modelFile'])

    check_asset('backgroundMedia')
    check_asset('htmlWidgetFile')
    check_asset('cssFile')
    check_asset('logicFile')

    metadata = config_data.get('metadata', {})
    theme_name = metadata.get('themeName', theme_dir_name)

    thumbnail_file = metadata.get('thumbnailImage')
    thumbnail_url = None

    if thumbnail_file and os.path.isfile(os.path.join(theme_path, thumbnail_file)):
        thumbnail_url = f'/{WALLPAPERS_DIR}/{theme_dir_name}/{thumbnail_file}'
    elif os.path.isfile(os.path.join(theme_path, 'thumbnail.gif')):
        thumbnail_file = 'thumbnail.gif'
        thumbnail_url = f'/{WALLPAPERS_DIR}/{theme_dir_name}/{thumbnail_file}'
    elif os.path.isfile(os.path.join(theme_path, 'thumbnail.png')):
        thumbnail_file = 'thumbnail.png'
        thumbnail_url = f'/{WALLPAPERS_DIR}/{theme_dir_name}/{thumbnail_file}'
    else:
        if metadata.get('thumbnailImage'):
            missing_assets.append(metadata.get('thumbnailImage'))

    wallpaper_data = {
        'themeId': theme_dir_name,
        'themeName': theme_name,
        'author': metadata.get('author', 'Unknown'),
        'authorUrl': metadata.get('authorUrl', ''),
        'description': metadata.get('description', ''),
        'thumbnailUrl': thumbnail_url,
        'config': config_data
    }

    if missing_assets:
        wallpaper_data['isValid'] = False
        wallpaper_data['missingAssets'] = missing_assets
    else:
        wallpaper_data['isValid'] = True
        wallpaper_data['missingAssets'] = []

    return wallpaper_data

def scan_all_wallpapers():
    valid_wallpapers = []
    invalid_wallpapers = []

    app_config = read_app_config()
    active_theme_id = app_config.get('active_theme')

    base_dir = handler.get_data_path(WALLPAPERS_DIR)

    if not os.path.isdir(base_dir):
        print(f"Error: Wallpapers directory not found at {base_dir}")
        return {"error": f"Wallpapers directory not found at {base_dir}"}

    for theme_dir_name in os.listdir(base_dir):
        theme_path = os.path.join(base_dir, theme_dir_name)

        if os.path.isdir(theme_path):
            result = validate_wallpaper(theme_dir_name, theme_path)

            if result['isValid']:
                valid_wallpapers.append(result)
            else:
                invalid_wallpapers.append(result)

    valid_wallpapers.sort(key=lambda x: x['themeId'] != active_theme_id)

    return {
        'validWallpapers': valid_wallpapers,
        'invalidWallpapers': invalid_wallpapers,
        'activeThemeId': active_theme_id,
        'enginePort': app_config.get('port'),
        'appVersion': CURRENT_APP_VERSION
    }

def is_engine_running(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1) 

            return s.connect_ex(('localhost', int(port))) == 0
    except:
        return False

def start_engine_process():
    if not ENGINE_RUN_COMMAND:
        raise FileNotFoundError("Engine executable or script not found.")

    print(f"Starting engine with command: {' '.join(ENGINE_RUN_COMMAND)}")
    flags = subprocess.CREATE_NEW_PROCESS_GROUP 
    subprocess.Popen(
        ENGINE_RUN_COMMAND,
        cwd=SERVER_ROOT,
        creationflags=flags
    )

class EditorHTTPHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SERVER_ROOT, **kwargs)

    def send_json_response(self, status_code, data):
        response_data = json.dumps(data).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_data)))
        self.send_header('Access-Control-Allow-Origin', '*') 
        self.end_headers()
        self.wfile.write(response_data)

    def do_OPTIONS(self):
        self.send_response(204) 

        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def validate_request(self):
        user_agent = self.headers.get('User-Agent', '')
        return user_agent == APP_SECURITY_TOKEN

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if not self.validate_request():
            self.send_error(403, "Forbidden: Access Denied")
            return

        routes = {
            '/': ('DATA_HOME', EDITOR_HTML),
            f'/{EDITOR_HTML}': ('DATA_HOME', EDITOR_HTML),
            f'/{DISCOVER_HTML}': ('DATA_DISCOVER', DISCOVER_HTML),
            f'/{SETTINGS_HTML}': ('DATA_SETTINGS', SETTINGS_HTML),
            f'/{FEATURED_HTML}': ('DATA_FEATURED', FEATURED_HTML),
            f'/{WIDGETS_HTML}': ('DATA_WIDGETS', WIDGETS_HTML),
        }

        if self.path in routes:
            asset_var, disk_filename = routes[self.path]

            if os.path.exists(disk_filename):
                self.path = f'/{disk_filename}'

                return super().do_GET()

            if HAS_EMBEDDED_ASSETS:
                html_bytes = frontend_assets.get_asset(asset_var)

                if html_bytes:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(html_bytes)))
                    self.end_headers()
                    self.wfile.write(html_bytes) 
                    return

        if self.path == '/installed_themes':
            try:
                base_dir = handler.get_data_path(WALLPAPERS_DIR)
                if not os.path.isdir(base_dir):
                    self.send_json_response(500, {'error': 'Wallpapers directory not found'})
                    return
                installed_ids = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
                self.send_json_response(200, {'installedIds': installed_ids, 'appVersion': CURRENT_APP_VERSION })
            except Exception as e:
                self.send_json_response(500, {'error': str(e)})
            return

        elif self.path == '/wallpapers':
            try:
                data = scan_all_wallpapers()
                self.send_json_response(200, data)
            except Exception as e:
                self.send_json_response(500, {'error': f"Error generating wallpaper list: {e}"})
            return

        elif self.path == '/get_app_settings':
            try:
                config = read_app_config()
                config['appVersion'] = CURRENT_APP_VERSION
                config['appVersionName'] = CURRENT_APP_VERSION_NAME
                config['enginePort'] = config.get('port')
                config['apiBaseUrl'] = API_BASE_URL 
                config['gpu_preference'] = gpu_utils.get_gpu_preference()
                config['gpu_names'] = gpu_utils.get_gpu_info()
                self.send_json_response(200, config)
            except Exception as e:
                self.send_json_response(500, {'error': f"Error reading config: {e}"})
            return

        elif self.path.startswith('/proxy_thumbnail'):
            try:
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                target_url = params.get('url', [None])[0]

                if not target_url:
                    self.send_json_response(400, {'error': 'Missing url parameter'})
                    return

                cache_dir = handler.get_data_path(THUMBNAIL_CACHE_DIR)
                os.makedirs(cache_dir, exist_ok=True)

                filename_hash = hashlib.md5(target_url.encode('utf-8')).hexdigest()
                cached_file_path = os.path.join(cache_dir, filename_hash + ".jpg")

                if os.path.exists(cached_file_path):
                    with open(cached_file_path, 'rb') as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return

                req = urllib.request.Request(target_url, headers={'User-Agent': APP_SECURITY_TOKEN})
                try:
                    with urllib.request.urlopen(req, timeout=10) as response:
                        image_data = response.read()
                except Exception as dl_err:
                     print(f"Failed to download thumbnail: {dl_err}")
                     self.send_json_response(404, {'error': 'Image download failed'})
                     return

                try:
                    img = Image.open(io.BytesIO(image_data))
                    img = img.convert('RGB')
                    
                    temp_path = cached_file_path + ".tmp"
                    img.save(temp_path, 'JPEG', quality=85)
                    os.replace(temp_path, cached_file_path)
                    
                except Exception as img_err:
                     print(f"Failed to process image: {img_err}")
                     if os.path.exists(cached_file_path + ".tmp"):
                         try: os.remove(cached_file_path + ".tmp")
                         except: pass
                     self.send_json_response(500, {'error': 'Image processing failed'})
                     return

                with open(cached_file_path, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            except Exception as e:
                print(f"Error in proxy_thumbnail: {e}")
                self.send_json_response(500, {'error': str(e)})
            return

        elif self.path.startswith('/threejs/'):
            threejs_path = self.path.lstrip('/')
            ext = os.path.splitext(self.path)[1].lower()
            mime_type = {
                ".js": "application/javascript",
                ".css": "text/css",
                ".json": "application/json"
            }.get(ext, "application/octet-stream")
            
            if HAS_THREEJS_ASSETS:
                asset_data = threejs_assets.get_library_asset(threejs_path)
                if asset_data:
                    self.send_response(200)
                    self.send_header('Content-type', mime_type)
                    self.send_header('Cache-Control', 'max-age=31536000')
                    self.send_header('Content-Length', str(len(asset_data)))
                    self.end_headers()
                    self.wfile.write(asset_data)
                    return
            
            file_path = os.path.join(SERVER_ROOT, threejs_path)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header('Content-type', mime_type)
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except Exception as e:
                    self.send_error(500, f"Error serving threejs file: {e}")
                return
            else:
                self.send_error(404, f"ThreeJS file not found: {self.path}")
                return

        clean_path = self.path.split('?')[0]
        if clean_path.startswith(f'/{WALLPAPERS_DIR}/') or clean_path.startswith('/widgets/'):
            relative_path = clean_path.lstrip('/')
            file_path = os.path.join(handler.get_appdata_dir(), relative_path)
            if os.path.isfile(file_path):
                ext = os.path.splitext(file_path)[1].lower()
                mime_map = {
                    ".css": "text/css", ".js": "application/javascript", ".html": "text/html",
                    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
                    ".mp4": "video/mp4", ".webm": "video/webm", ".json": "application/json",
                    ".glb": "model/gltf-binary", ".gltf": "model/gltf+json",
                    ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf",
                    ".hdr": "application/octet-stream",
                }
                mime_type = mime_map.get(ext, "application/octet-stream")
                try:
                    with open(file_path, 'rb') as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', mime_type)
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except Exception as e:
                    self.send_error(500, f"Error serving file: {e}")
                return
            else:
                self.send_error(404, f"File not found: {self.path}")
                return

        return super().do_GET()

    def do_POST(self):
        if not self.validate_request():
            self.send_error(403, "Forbidden: Access Denied")
            return

        if self.path == '/save_app_settings':
            try:
                content_len = int(self.headers.get('Content-Length'))
                post_body = self.rfile.read(content_len)
                data = json.loads(post_body)

                app_config = read_app_config()
                if 'tour_v2' in data:
                    app_config['tour_v2'] = bool(data.get('tour_v2'))
                new_auto_start = data.get('auto_start')
                if new_auto_start is not None:
                    app_config['auto_start'] = bool(new_auto_start)

                config_path = handler.get_app_config_path()
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(app_config, f, indent=2)

                if new_auto_start is not None:
                    success, msg = update_startup_shortcut(bool(new_auto_start))
                    if not success:
                         print(f"Failed to update startup shortcut: {msg}")

                self.send_json_response(200, {'status': 'success', 'message': 'Settings saved'})
            except Exception as e:
                print(f"Error saving settings: {e}")
                self.send_json_response(500, {'error': str(e)})
            return
        
        elif self.path == '/set_gpu_preference':
            try:
                content_len = int(self.headers.get('Content-Length'))
                post_body = self.rfile.read(content_len)
                data = json.loads(post_body)
                level = int(data.get('level', 0))

                success = gpu_utils.set_gpu_preference(level)
                
                if success:
                    self.send_json_response(200, {'status': 'success', 'message': f'GPU preference set to {level}'})
                else:
                    self.send_json_response(500, {'error': 'Failed to modify Windows Registry.'})

            except Exception as e:
                print(f"Error setting GPU preference: {e}")
                self.send_json_response(500, {'error': str(e)})
            return

        elif self.path == '/restart_app':
            try:
                self.send_json_response(200, {'status': 'success', 'message': 'Initiating restart sequence...'})
                gpu_utils.restart_librewall()
            except Exception as e:
                print(f"Error triggering restart: {e}")
                self.send_json_response(500, {'error': str(e)})
            return

        elif self.path == '/install_theme':
            try:
                content_len = int(self.headers.get('Content-Length'))
                post_body = self.rfile.read(content_len)
                data = json.loads(post_body)

                theme_id = str(data.get('themeId'))
                if not theme_id:
                    self.send_json_response(400, {'error': "Missing 'themeId'"})
                    return

                theme_path = handler.get_data_path(WALLPAPERS_DIR, theme_id)
                if os.path.isdir(theme_path):
                    self.send_json_response(400, {'error': 'Theme already installed.'})
                    return

                api_url = f"{API_BASE_URL}?action=get_theme_by_id&id={theme_id}"
                print(f"Fetching theme info from: {api_url}")

                with urllib.request.urlopen(api_url, timeout=10) as response:
                    api_data = json.load(response)
                    theme_data = api_data.get('data')

                if not theme_data or not theme_data.get('zipUrl'):
                    self.send_json_response(404, {'error': 'Theme not found on API or API missing zipUrl.'})
                    return

                zip_url = theme_data['zipUrl']
                print(f"Downloading theme from: {zip_url}")

                with urllib.request.urlopen(zip_url, timeout=30) as response:
                    zip_data = response.read()

                with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                    root_folder = ""
                    if len(zf.namelist()) > 0:
                         root_folder_parts = zf.namelist()[0].split('/')
                         if len(root_folder_parts) > 1:
                             root_folder = root_folder_parts[0] + '/'

                    os.makedirs(theme_path, exist_ok=True)

                    for file_info in zf.infolist():
                        if file_info.is_dir():
                            continue

                        relative_path = file_info.filename
                        if relative_path.startswith(root_folder):
                             relative_path = relative_path[len(root_folder):]

                        if not relative_path:
                            continue

                        target_path = os.path.join(theme_path, relative_path)
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)

                        with zf.open(file_info) as source, open(target_path, 'wb') as target:
                            target.write(source.read())

                print(f"Successfully installed theme: {theme_id}")
                self.send_json_response(200, {'status': 'success', 'installed': theme_id})

            except Exception as e:
                print(f"Error installing theme: {e}")

        elif self.path == '/preview_import':
            try:
                content_type = self.headers.get('Content-Type')
                if not content_type:
                    self.send_json_response(400, {'error': "Missing Content-Type"})
                    return

                content_len = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_len)

                msg = email.message_from_bytes(
                    f'Content-Type: {content_type}\r\n\r\n'.encode() + body
                )

                file_item_name = None
                file_item_data = None
                
                if msg.is_multipart():
                    for part in msg.get_payload():
                         if part.get_param('name', header='Content-Disposition') == 'themeFile':
                             file_item_name = part.get_filename()
                             file_item_data = part.get_payload(decode=True)
                             break
                
                if not file_item_data:
                     self.send_json_response(400, {'error': "Missing 'themeFile' in form data or empty file"})
                     return

                if not file_item_name:
                    self.send_json_response(400, {'error': 'No filename provided.'})
                    return
                
                if not file_item_name.endswith('.zip'):
                     self.send_json_response(400, {'error': 'File must be a .zip archive.'})
                     return

                safe_basename = os.path.basename(file_item_name)
                theme_id = os.path.splitext(safe_basename)[0]

                if not theme_id:
                    self.send_json_response(400, {'error': 'Invalid zip filename.'})
                    return

                zip_data = file_item_data

                asset_type = 'wallpaper'
                asset_name = f"Theme {theme_id}"
                asset_author = "Unknown"

                with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                    root_folder = ""
                    if len(zf.namelist()) > 0:
                         root_folder_parts = zf.namelist()[0].split('/')
                         if len(root_folder_parts) > 1 and zf.namelist()[0].endswith('/'):
                             root_folder = zf.namelist()[0]
                         elif len(root_folder_parts) > 1:
                             root_folder = root_folder_parts[0] + '/'

                    is_widget = False
                    for file_info in zf.infolist():
                        if file_info.filename == root_folder + 'main.js' or file_info.filename == 'main.js':
                            is_widget = True
                            break
                    
                    if is_widget:
                        asset_type = 'widget'
                        asset_name = f"Widget {theme_id}"
                        try:
                            main_js_path = root_folder + 'main.js' if root_folder + 'main.js' in zf.namelist() else 'main.js'
                            with zf.open(main_js_path) as source:
                                js_content = source.read().decode('utf-8', errors='ignore')
                                import re
                                name_match = re.search(r'@name:\s*([^\n\r]+)', js_content)
                                if not name_match: name_match = re.search(r'name:\s*[\'"]([^\'"]+)[\'"]', js_content)
                                author_match = re.search(r'@author:\s*([^\n\r]+)', js_content)
                                if not author_match: author_match = re.search(r'author:\s*[\'"]([^\'"]+)[\'"]', js_content)
                                desc_match = re.search(r'@description:\s*([^\n\r]+)', js_content)
                                minv_match = re.search(r'@min_version:\s*([^\n\r]+)', js_content)

                                if name_match: asset_name = name_match.group(1).strip()
                                if author_match: asset_author = author_match.group(1).strip()
                        except Exception as e: 
                            print(f"Error reading widget metadata: {e}")
                            
                        try:
                            api_url = f"{api_config.API_BASE_URL}?action=get_widgets&query={theme_id}"
                            with urllib.request.urlopen(api_url, timeout=5) as response:
                                api_resp = json.loads(response.read().decode('utf-8'))
                                if api_resp.get('data'):
                                    for w in api_resp['data']:
                                        if str(w.get('id')) == theme_id:
                                            if w.get('name') or w.get('widgetName'): 
                                                asset_name = w.get('widgetName', w.get('name'))
                                            if w.get('author'): 
                                                asset_author = w.get('author')
                                            break
                        except Exception as e:
                            pass
                    else:
                        asset_type = 'wallpaper'
                        asset_name = theme_id
                        try:
                            config_path = root_folder + 'config.json' if root_folder + 'config.json' in zf.namelist() else 'config.json'
                            if config_path in zf.namelist():
                                with zf.open(config_path) as source:
                                    config_json = json.loads(source.read().decode('utf-8', errors='ignore'))
                                    metadata = config_json.get('metadata', {})
                                    asset_name = metadata.get('themeName', config_json.get('themeName', theme_id))
                                    asset_author = metadata.get('author', config_json.get('author', 'Unknown'))
                        except Exception as e:
                            print(f"Error reading wallpaper metadata: {e}")

                self.send_json_response(200, {
                    'status': 'success',
                    'type': asset_type,
                    'name': asset_name,
                    'author': asset_author,
                    'id': theme_id
                })

            except Exception as e:
                print(f"Error previewing theme: {e}")
                self.send_json_response(500, {'error': str(e)})
            return
        elif self.path == '/import_theme':
            try:
                content_type = self.headers.get('Content-Type')
                if not content_type:
                    self.send_json_response(400, {'error': "Missing Content-Type"})
                    return

                content_len = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_len)

                msg = email.message_from_bytes(
                    f'Content-Type: {content_type}\r\n\r\n'.encode() + body
                )

                file_item_name = None
                file_item_data = None
                
                if msg.is_multipart():
                    for part in msg.get_payload():
                         if part.get_param('name', header='Content-Disposition') == 'themeFile':
                             file_item_name = part.get_filename()
                             file_item_data = part.get_payload(decode=True)
                             break
                
                if not file_item_data:
                     self.send_json_response(400, {'error': "Missing 'themeFile' in form data or empty file"})
                     return

                if not file_item_name:
                    self.send_json_response(400, {'error': 'No filename provided.'})
                    return
                
                if not file_item_name.endswith('.zip'):
                     self.send_json_response(400, {'error': 'File must be a .zip archive.'})
                     return

                safe_basename = os.path.basename(file_item_name)
                theme_id = os.path.splitext(safe_basename)[0]

                if not theme_id:
                    self.send_json_response(400, {'error': 'Invalid zip filename.'})
                    return

                zip_data = file_item_data

                with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                    root_folder = ""
                    if len(zf.namelist()) > 0:
                         root_folder_parts = zf.namelist()[0].split('/')
                         if len(root_folder_parts) > 1 and zf.namelist()[0].endswith('/'):
                             root_folder = zf.namelist()[0]
                         elif len(root_folder_parts) > 1:
                             root_folder = root_folder_parts[0] + '/'

                    is_widget = False
                    for file_info in zf.infolist():
                        if file_info.filename == root_folder + 'main.js' or file_info.filename == 'main.js':
                            is_widget = True
                            break
                    
                    if is_widget:
                        widgets_dir = handler.get_data_path(api_config.WIDGETS_DIR, theme_id)
                        os.makedirs(widgets_dir, exist_ok=True)

                        for file_info in zf.infolist():
                            if file_info.is_dir(): continue
                            relative_path = file_info.filename
                            if root_folder and relative_path.startswith(root_folder):
                                 relative_path = relative_path[len(root_folder):]
                            if not relative_path: continue
                            
                            target_path = os.path.join(widgets_dir, relative_path)
                            os.makedirs(os.path.dirname(target_path), exist_ok=True)
                            with zf.open(file_info) as source, open(target_path, 'wb') as target:
                                target.write(source.read())

                        import re
                        main_js_path = os.path.join(widgets_dir, 'main.js')
                        widget_name = f"Widget {theme_id}"
                        widget_author = "Local Import"
                        widget_desc = "No description provided."
                        widget_min_version = 1
                        try:
                            with open(main_js_path, 'r', encoding='utf-8') as f:
                                js_content = f.read()
                                name_match = re.search(r'@name:\s*([^\n\r]+)', js_content)
                                if not name_match: name_match = re.search(r'name:\s*[\'"]([^\'"]+)[\'"]', js_content)
                                author_match = re.search(r'@author:\s*([^\n\r]+)', js_content)
                                if not author_match: author_match = re.search(r'author:\s*[\'"]([^\'"]+)[\'"]', js_content)
                                desc_match = re.search(r'@description:\s*([^\n\r]+)', js_content)
                                minv_match = re.search(r'@min_version:\s*([^\n\r]+)', js_content)

                                if name_match: widget_name = name_match.group(1).strip()
                                if author_match: widget_author = author_match.group(1).strip()
                                if desc_match: widget_desc = desc_match.group(1).strip()
                                if minv_match: 
                                    try: widget_min_version = int(minv_match.group(1).strip())
                                    except: pass
                        except: pass
                        
                        try:
                            api_url = f"{api_config.API_BASE_URL}?action=get_widgets&query={theme_id}"
                            with urllib.request.urlopen(api_url, timeout=5) as response:
                                api_resp = json.loads(response.read().decode('utf-8'))
                                if api_resp.get('data'):
                                    for w in api_resp['data']:
                                        if str(w.get('id')) == theme_id:
                                            if w.get('name') or w.get('widgetName'):
                                                widget_name = w.get('widgetName', w.get('name'))
                                            if w.get('author'):
                                                widget_author = w.get('author')
                                            break
                        except Exception as e:
                            pass

                        index_path = handler.get_data_path(api_config.WIDGETS_DIR, 'index.json')
                        registry_data = {"widgets": []}
                        if os.path.isfile(index_path):
                            try:
                                with open(index_path, 'r', encoding='utf-8') as f:
                                    registry_data = json.load(f)
                            except: pass
                        
                        existing_entry = next((w for w in registry_data.get('widgets', []) if str(w.get('id')) == str(theme_id)), None)
                        new_entry = { 
                            "id": str(theme_id), 
                            "name": widget_name, 
                            "author": widget_author,
                            "description": widget_desc,
                            "min_version": widget_min_version
                        }
                        if existing_entry: existing_entry.update(new_entry)
                        else: 
                            if 'widgets' not in registry_data: registry_data['widgets'] = []
                            registry_data['widgets'].append(new_entry)
                            
                        with open(index_path, 'w', encoding='utf-8') as f:
                            json.dump(registry_data, f, indent=4)

                        print(f"Successfully imported widget: {theme_id}")
                        self.send_json_response(200, {'status': 'success', 'type': 'widget', 'installed': theme_id})
                    else:
                        theme_path = handler.get_data_path(WALLPAPERS_DIR, theme_id)
                        if os.path.isdir(theme_path):
                            self.send_json_response(400, {'error': f"Theme '{theme_id}' already exists."})
                            return

                        print(f"Importing theme from '{safe_basename}' to '{theme_id}'...")
                        os.makedirs(theme_path, exist_ok=True)

                        for file_info in zf.infolist():
                            if file_info.is_dir(): continue

                            relative_path = file_info.filename
                            if root_folder and relative_path.startswith(root_folder):
                                 relative_path = relative_path[len(root_folder):]

                            if not relative_path: continue

                            target_path = os.path.join(theme_path, relative_path)
                            os.makedirs(os.path.dirname(target_path), exist_ok=True)

                            with zf.open(file_info) as source, open(target_path, 'wb') as target:
                                target.write(source.read())

                        print(f"Successfully imported theme: {theme_id}")
                        self.send_json_response(200, {'status': 'success', 'type': 'wallpaper', 'themeId': theme_id})

            except Exception as e:
                print(f"Error importing theme: {e}")
                self.send_json_response(500, {'error': str(e)})
            return

        elif self.path == '/activate_theme':
            try:
                content_len = int(self.headers.get('Content-Length'))
                post_body = self.rfile.read(content_len)
                data = json.loads(post_body)

                new_theme_id = data.get('themeId')
                if not new_theme_id:
                    self.send_json_response(400, {'error': "Missing 'themeId' in request body"})
                    return

                app_config = read_app_config()
                app_config['active_theme'] = new_theme_id

                config_path = handler.get_app_config_path()
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(app_config, f, indent=2)

                self.send_json_response(200, {'status': 'success', 'activated': new_theme_id})

            except Exception as e:
                print(f"Error activating theme: {e}")
                self.send_json_response(500, {'error': f"Error activating theme: {e}"})
            return

        elif self.path == '/update_theme_config':
            try:
                content_len = int(self.headers.get('Content-Length'))
                post_body = self.rfile.read(content_len)
                data = json.loads(post_body)

                theme_id = str(data.get('themeId'))

                if not theme_id:
                    self.send_json_response(400, {'error': "Missing 'themeId'"})
                    return

                theme_path = handler.get_data_path(WALLPAPERS_DIR, theme_id)
                config_path = os.path.join(theme_path, 'config.json')

                if not os.path.isfile(config_path):
                    self.send_json_response(404, {'error': 'config.json not found for this theme.'})
                    return

                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                if 'enableGlobal' in data:
                    config_data['Enable_Global_Widget'] = bool(data.get('enableGlobal'))

                    if 'Enable_Network_Widget' in config_data:
                        del config_data['Enable_Network_Widget']

                if 'fpsLimit' in data:
                    try:
                        config_data['fpsLimit'] = int(data.get('fpsLimit'))
                    except (ValueError, TypeError):
                        config_data['fpsLimit'] = 60
                
                if 'qualityPreset' in data:
                    config_data['qualityPreset'] = str(data.get('qualityPreset'))

                if 'muteAudio' in data:

                    val = data.get('muteAudio')
                    config_data['muteAudio'] = bool(val) if val is not None else True

                if 'volume' in data:
                    try:
                        config_data['volume'] = int(data.get('volume'))
                    except (ValueError, TypeError):
                        config_data['volume'] = 70

                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2)

                print(f"Updated config for '{theme_id}'")
                self.send_json_response(200, {'status': 'success', 'message': 'Config updated.'})

            except Exception as e:
                print(f"Error updating config: {e}")
                self.send_json_response(500, {'error': str(e)})
            return

        elif self.path == '/install_widget':
            try:
                content_len = int(self.headers.get('Content-Length'))
                post_body = self.rfile.read(content_len)
                data = json.loads(post_body)

                widget_id = str(data.get('widgetId'))
                if not widget_id:
                    self.send_json_response(400, {'error': "Missing 'widgetId'"})
                    return

                api_url = f"{API_BASE_URL}?action=get_widgets&query={widget_id}"
                print(f"Fetching widget info from: {api_url}")
                
                widget_data = None
                with urllib.request.urlopen(api_url, timeout=10) as response:
                    api_resp = json.load(response)
                    if api_resp.get('data'):
                        for w in api_resp['data']:
                            if str(w.get('id')) == widget_id:
                                widget_data = w
                                break
                
                if not widget_data:
                     self.send_json_response(404, {'error': 'Widget not found or ID mismatch in marketplace.'})
                     return

                zip_url = widget_data.get('zipUrl')
                if not zip_url:
                     self.send_json_response(400, {'error': 'Widget has no download URL.'})
                     return

                print(f"Downloading widget from: {zip_url}")
                with urllib.request.urlopen(zip_url, timeout=30) as response:
                    zip_data = response.read()

                target_folder_name = str(widget_id)
                widgets_dir = handler.get_data_path(api_config.WIDGETS_DIR, target_folder_name)
                os.makedirs(widgets_dir, exist_ok=True)

                with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                     root_folder = ""
                     if len(zf.namelist()) > 0:
                         root_folder_parts = zf.namelist()[0].split('/')
                         if len(root_folder_parts) > 1 and zf.namelist()[0].endswith('/'):
                                root_folder = zf.namelist()[0]
                     
                     for file_info in zf.infolist():
                        if file_info.is_dir(): continue
                        
                        relative_path = file_info.filename
                        if root_folder and relative_path.startswith(root_folder):
                             relative_path = relative_path[len(root_folder):]
                        
                        if not relative_path: continue
                        
                        target_path = os.path.join(widgets_dir, relative_path)
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        with zf.open(file_info) as source, open(target_path, 'wb') as target:
                            target.write(source.read())

                index_path = handler.get_data_path(api_config.WIDGETS_DIR, 'index.json')
                
                registry_data = {"widgets": []}
                if os.path.isfile(index_path):
                    try:
                        with open(index_path, 'r', encoding='utf-8') as f:
                            registry_data = json.load(f)
                    except: pass
                
                existing_entry = next((w for w in registry_data.get('widgets', []) if str(w.get('id')) == str(widget_id)), None)
                
                new_entry = {
                    "id": str(widget_id),
                    "name": widget_data.get('widgetName', f"Widget {widget_id}"),
                    "author": widget_data.get('author', 'Unknown'),
                }
                
                if existing_entry:
                    existing_entry.update(new_entry)
                else:
                    if 'widgets' not in registry_data: registry_data['widgets'] = []
                    registry_data['widgets'].append(new_entry)

                with open(index_path, 'w', encoding='utf-8') as f:
                    json.dump(registry_data, f, indent=4)
                
                print(f"Successfully installed widget: {widget_id}")
                self.send_json_response(200, {'status': 'success', 'installed': widget_id})

            except Exception as e:
                print(f"Error installing widget: {e}")
                self.send_json_response(500, {'error': str(e)})
            return

        elif self.path == '/start_engine':
            try:
                app_config = read_app_config()
                port = app_config.get('port', 8080)
                
                if is_engine_running(port):
                    print(f"Engine already running on port {port}. Reloading...")
                    try:
                        with urllib.request.urlopen(f"http://localhost:{port}/reload", timeout=2) as r:
                            pass
                    except Exception as e:
                        print(f"Reload request failed: {e}")
                    
                    self.send_json_response(200, {'status': 'success', 'message': 'Engine reloaded.'})
                    return

                start_engine_process()
                self.send_json_response(200, {'status': 'success', 'message': 'Engine start command issued.'})
            except Exception as e:
                print(f"Error starting engine: {e}")
                self.send_json_response(500, {'error': f"Error starting engine: {e}"})
            return

        elif self.path == '/delete_widget':
            try:
                content_len = int(self.headers.get('Content-Length'))
                post_body = self.rfile.read(content_len)
                data = json.loads(post_body)

                widget_id = str(data.get('widgetId'))
                if not widget_id:
                    self.send_json_response(400, {'error': "Missing 'widgetId'"})
                    return

                if '..' in widget_id or '/' in widget_id or '\\' in widget_id:
                     self.send_json_response(400, {'error': "Invalid widget ID"})
                     return

                widget_path = handler.get_data_path(api_config.WIDGETS_DIR, widget_id)
                
                index_path = handler.get_data_path(api_config.WIDGETS_DIR, 'index.json')
                registry_data = {"widgets": []}
                if os.path.isfile(index_path):
                    try:
                        with open(index_path, 'r', encoding='utf-8') as f:
                            registry_data = json.load(f)
                    except: pass
                
                original_count = len(registry_data.get('widgets', []))
                registry_data['widgets'] = [w for w in registry_data.get('widgets', []) if str(w.get('id')) != widget_id]
                new_count = len(registry_data['widgets'])

                if original_count == new_count and not os.path.isdir(widget_path):
                     self.send_json_response(404, {'error': 'Widget not found.'})
                     return

                with open(index_path, 'w', encoding='utf-8') as f:
                    json.dump(registry_data, f, indent=4)

                if os.path.isdir(widget_path):
                    shutil.rmtree(widget_path)
                
                print(f"Successfully deleted widget: {widget_id}")
                self.send_json_response(200, {'status': 'success', 'deleted': widget_id})

            except Exception as e:
                print(f"Error deleting widget: {e}")
                self.send_json_response(500, {'error': str(e)})
            return

        elif self.path == '/delete_theme':
            try:
                content_len = int(self.headers.get('Content-Length'))
                post_body = self.rfile.read(content_len)
                data = json.loads(post_body)

                theme_id = str(data.get('themeId'))
                if not theme_id:
                    self.send_json_response(400, {'error': "Missing 'themeId' in request body"})
                    return

                app_config = read_app_config()
                if app_config.get('active_theme') == theme_id:
                    self.send_json_response(400, {'error': 'Cannot delete the active theme.'})
                    return

                theme_path = handler.get_data_path(WALLPAPERS_DIR, theme_id)
                if not os.path.isdir(theme_path):
                    self.send_json_response(404, {'error': 'Theme directory not found.'})
                    return

                attempts = 0
                max_attempts = 3
                success = False
                last_error = None

                try:
                    thumb_filename = None
                    config_path = os.path.join(theme_path, 'config.json')
                    
                    if os.path.exists(config_path):
                        with open(config_path, 'r', encoding='utf-8') as f:
                            c = json.load(f)
                            thumb_filename = c.get('metadata', {}).get('thumbnailImage')

                    if not thumb_filename or not os.path.isfile(os.path.join(theme_path, thumb_filename)):
                        for test_name in ['thumbnail.gif', 'thumbnail.png']:
                            if os.path.isfile(os.path.join(theme_path, test_name)):
                                thumb_filename = test_name
                                break
                    
                    if thumb_filename:
                        encoded_theme_id = urllib.parse.quote(theme_id)
                        encoded_filename = urllib.parse.quote(thumb_filename)
                        
                        theme_url_path = f"/{WALLPAPERS_DIR}/{encoded_theme_id}/{encoded_filename}"
                        
                        origins = [
                            f"http://127.0.0.1:{EDITOR_PORT}",
                            f"http://localhost:{EDITOR_PORT}"
                        ]
                        
                        for origin in origins:
                            full_url = f"{origin}{theme_url_path}"
                            filename_hash = hashlib.md5(full_url.encode('utf-8')).hexdigest()
                            
                            cached_file = handler.get_data_path(THUMBNAIL_CACHE_DIR, filename_hash + ".jpg")
                            if os.path.exists(cached_file):
                                try:
                                    os.remove(cached_file)
                                    print(f"Deleted cached thumbnail: {cached_file} (Origin: {origin})")
                                except Exception as e:
                                    print(f"Failed to delete {cached_file}: {e}")
                except Exception as cache_err:
                    print(f"Warning: Failed to delete thumbnail cache for theme: {cache_err}")

                while attempts < max_attempts and not success:
                    try:
                        shutil.rmtree(theme_path)
                        success = True
                        print(f"Deleted theme directory: {theme_path}")
                    except Exception as e:
                        last_error = e
                        attempts += 1
                        print(f"Attempt {attempts} to delete '{theme_id}' failed: {e}. Retrying in 0.5s...")
                        time.sleep(0.5)
                if not success:
                    raise Exception(f"Failed to delete '{theme_id}' after {max_attempts} attempts. File may be locked. Error: {last_error}")

                self.send_json_response(200, {'status': 'success', 'message': f"Theme '{theme_id}' deleted."})

            except Exception as e:
                error_message = str(e)
                print(f"Error deleting theme: {error_message}")
                self.send_json_response(500, {'error': error_message})
            return

        elif self.path == '/clear_thumbnail_cache':
            try:
                cache_dir = handler.get_data_path(THUMBNAIL_CACHE_DIR)
                if os.path.exists(cache_dir):
                    shutil.rmtree(cache_dir)
                    os.makedirs(cache_dir, exist_ok=True)
                
                self.send_json_response(200, {'status': 'success', 'message': 'Thumbnail cache cleared.'})
            except Exception as e:
                print(f"Error clearing cache: {e}")
                self.send_json_response(500, {'error': str(e)})
            return

        elif self.path == '/open_external_link':
            try:
                content_len = int(self.headers.get('Content-Length'))
                post_body = self.rfile.read(content_len)
                data = json.loads(post_body)
                url = data.get('url')
                
                if url:
                    webbrowser.open(url)
                    self.send_json_response(200, {'status': 'success'})
                else:
                    self.send_json_response(400, {'error': 'Missing URL'})
            except Exception as e:
                print(f"Error opening link: {e}")
                self.send_json_response(500, {'error': str(e)})
            return

        elif self.path == '/open_app_data_folder':
            try:
                target_dir = handler.get_appdata_dir()
                if os.path.exists(target_dir):
                    if hasattr(os, 'startfile'):
                        os.startfile(target_dir)
                    else:
                        subprocess.Popen(['explorer', target_dir])
                    self.send_json_response(200, {'status': 'success'})
                else:
                    self.send_json_response(404, {'error': 'Directory not found'})
            except Exception as e:
                print(f"Error opening AppData folder: {e}")
                self.send_json_response(500, {'error': str(e)})
            return
        self.send_json_response(404, {'error': "Not Found"})

class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True

def start_editor_server(port):
    Handler = EditorHTTPHandler
    httpd = ThreadingHTTPServer(("", port), Handler)

    print(f"Editor server (Multi-threaded) started at http://localhost:{port}")
    print(f"Serving files from: {SERVER_ROOT}")

    httpd.serve_forever()

class EditorWindow(QMainWindow):
    def __init__(self, url):
        super().__init__()
        self.setWindowTitle(f"librewall {api_config.CURRENT_APP_VERSION_NAME}")
        self.resize(1400, 900)
        self.setMinimumSize(900, 700)
        self.webEngineView = QWebEngineView(self)
        self.webEngineView.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.dev_tools_view = None
        self.dev_tools_window = None
        
        if api_config.developer_enabled:
            dev_action = QAction("DevTools", self)
            dev_action.setShortcut("F12")
            dev_action.triggered.connect(self.toggle_devtools)
            self.addAction(dev_action)
        
        no_select_script = QWebEngineScript()
        no_select_script.setName("DisableSelection")
        no_select_script.setSourceCode("""
            (function() {
                var css = 'body { -webkit-user-select: none; user-select: none; cursor: default; } ' +
                          'input, textarea { -webkit-user-select: text; user-select: text; cursor: auto; }';
                var head = document.head || document.getElementsByTagName('head')[0];
                var style = document.createElement('style');
                style.type = 'text/css';
                style.appendChild(document.createTextNode(css));
                head.appendChild(style);
            })();
        """)
        no_select_script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        no_select_script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        no_select_script.setRunsOnSubFrames(True)
        self.webEngineView.page().profile().scripts().insert(no_select_script)
        
        self.webEngineView.page().profile().setHttpUserAgent(APP_SECURITY_TOKEN)
        
        self.setCentralWidget(self.webEngineView)
        QWebEngineProfile.defaultProfile().clearHttpCache()
        self.webEngineView.settings().setAttribute(self.webEngineView.settings().WebAttribute.WebGLEnabled, True)
        self.webEngineView.settings().setAttribute(self.webEngineView.settings().WebAttribute.LocalContentCanAccessFileUrls, True)
        self.webEngineView.settings().setAttribute(self.webEngineView.settings().WebAttribute.Accelerated2dCanvasEnabled, True)
        self.webEngineView.setHtml(LOADING_HTML_CONTENT, QUrl("about:blank"))
        self.show()

    def toggle_devtools(self):
        if not self.dev_tools_window:
            self.dev_tools_window = QMainWindow()
            self.dev_tools_view = QWebEngineView()
            self.dev_tools_window.setCentralWidget(self.dev_tools_view)
            self.dev_tools_window.setWindowTitle("Developer Tools")
            self.dev_tools_window.resize(800, 600)
            self.webEngineView.page().setDevToolsPage(self.dev_tools_view.page())
            
        if self.dev_tools_window.isVisible():
            self.dev_tools_window.hide()
        else:
            self.dev_tools_window.show()
            self.dev_tools_window.activateWindow()
if __name__ == "__main__":
    os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    def cleanup_old_cache():
        try:
            cache_dir = handler.get_data_path(THUMBNAIL_CACHE_DIR)
            if not os.path.isdir(cache_dir):
                return
            
            max_age = 7 * 24 * 60 * 60
            now = time.time()
            
            print("Running thumbnail cache cleanup...")
            count = 0
            for filename in os.listdir(cache_dir):
                file_path = os.path.join(cache_dir, filename)
                if os.path.isfile(file_path):
                    try:
                        file_age = now - os.path.getmtime(file_path)
                        if file_age > max_age:
                            os.remove(file_path)
                            count += 1
                    except Exception: pass
            
            if count > 0:
                print(f"Cleanup: Removed {count} old thumbnail(s).")
            else:
                print("Cleanup: No old thumbnails found.")
                
        except Exception as e:
            print(f"Cleanup Error: {e}")

    threading.Thread(target=cleanup_old_cache, daemon=True).start()

    icon_path = os.path.join(SERVER_ROOT, '1.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    try:
        myappid = api_config.APP_USER_MODEL_ID
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except: pass

    if not check_single_instance():
        sys.exit(0)

    for html_file in [EDITOR_HTML, DISCOVER_HTML, SETTINGS_HTML]: 
        html_path = os.path.join(SERVER_ROOT, html_file)
        if not os.path.isfile(html_path):
            print(f"Warning: Editor UI file '{html_file}' not found.")

    handler.init_appdata(SERVER_ROOT)

    wallpapers_path = handler.get_data_path(WALLPAPERS_DIR)
    if not os.path.isdir(wallpapers_path):
        print(f"Error: Wallpapers directory not found: {wallpapers_path}")
        try:
            os.makedirs(wallpapers_path)
            print(f"Created 'wallpapers' directory.")
        except Exception as e:
            print(f"Could not create wallpapers directory: {e}")
            sys.exit(1)

    startup_config = read_app_config()
    if startup_config.get('auto_start', True):

        engine_port = startup_config.get('port', 8080)
        print(f"Auto-start enabled. Checking if Engine is running on port {engine_port}...")

        if not is_engine_running(engine_port):
            print("Engine not detected. Launching now...")
            try:
                start_engine_process()
            except Exception as e:
                print(f"Failed to auto-launch engine: {e}")
        else:
            print("Engine is already running.")

    try:
        server_thread = threading.Thread(
            target=start_editor_server, 
            args=(EDITOR_PORT,),
            daemon=True
        )
        server_thread.start()
    except Exception as e:
        print(f"Error: Could not start server thread: {e}")
        sys.exit(1)

    if not updater_module.run_update_check(CURRENT_APP_VERSION, CURRENT_APP_VERSION_NAME, API_BASE_URL):
        sys.exit(0) 

    print("DevTools (Inspect) available at http://localhost:9222") 
    print(f"Loading editor UI from: {EDITOR_SERVER_URL}")

    window = EditorWindow(EDITOR_SERVER_URL)
    sys.exit(app.exec())
