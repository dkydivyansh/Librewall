import os
import ctypes
import sys
import win32gui
import win32con
import win32api
import http.server
import socketserver
import threading
import socket
import json
import time
import collections
import datetime
import asyncio
import websockets
import psutil
import secrets 
import string  
from port_map import PORT_PROTOCOL_MAP
# ==============================================================================
def get_real_screen_scale():
    """
    Detects the actual screen scaling (e.g., 1.0, 1.25, 1.5) using Modern Windows API.
    This prevents the '1.0' fallback that causes low-res rendering.
    """
    try:
        # 1. Try to set DPI awareness to get accurate reading
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per Monitor v2
        except: 
            try: ctypes.windll.user32.SetProcessDPIAware()
            except: pass
        
        # 2. Use Shcore.dll (Modern API)
        shcore = ctypes.windll.shcore
        user32 = ctypes.windll.user32
        
        # Get Primary Monitor Handle
        h_monitor = user32.MonitorFromPoint(0, 0, 2) # 2 = MONITOR_DEFAULTTOPRIMARY
        
        dpi_x = ctypes.c_uint()
        dpi_y = ctypes.c_uint()
        
        # Get Effective DPI
        shcore.GetDpiForMonitor(h_monitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y))
        
        scale = dpi_x.value / 96.0
        
        # Safety clamp
        if scale < 1.0: scale = 1.0
        
        print(f"Detected Real Scale: {scale} (DPI: {dpi_x.value})")
        return scale
    except Exception as e:
        print(f"DPI Detection Warning: {e}")
        return 1.0

# 1. Calculate Scale Immediately
current_scale = get_real_screen_scale()

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    f"--force-device-scale-factor={current_scale} "
    "--high-dpi-support=1 "
    "--enable-use-zoom-for-dsf=true "
    "--disable-renderer-backgrounding "
    "--disable-backgrounding-occluded-windows "
    "--disable-features=CalculateNativeWinOcclusion"
)

# 3. Disable Qt's internal scaling (We handle it manually via flags)
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"
# ==============================================================================

from PyQt6.QtCore import QUrl, Qt, QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QMenu
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtGui import QAction

user32   = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

mutex_handle = None  # keep global so it isn't GC'd


def check_single_instance(mutex_name=r"Global\librewall_engine"):
    """
    Returns True if this is the first instance.
    If another instance exists, shows a message and exits the process.
    """
    global mutex_handle

    # Create the named mutex
    mutex_handle = kernel32.CreateMutexW(None, False, mutex_name)

    # ERROR_ALREADY_EXISTS = 183
    if kernel32.GetLastError() == 183:
        # Another instance is already running
        try:
             user32.MessageBoxW(
                None,
                "Another instance of librewall engine is already running.",
                "librewall_engine",
                0x10  # MB_ICONHAND
            )
        except NameError:
            # Fallback: normal message box using WinAPI
            user32.MessageBoxW(
                None,
                "Another instance of librewall engine is already running.",
                "librewall_engine",
                0x10  # MB_ICONHAND
            )

        # Close our mutex handle (we are the second instance)
        if mutex_handle:
            kernel32.CloseHandle(mutex_handle)

        # Exit this (second) instance
        sys.exit(0)

    # This is the first instance
    return True

if getattr(sys, 'frozen', False):
    # PyInstaller "frozen" mode: Use the directory of the executable
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    # Normal script mode
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

print(f"Engine Server Root detected as: {SCRIPT_DIR}")
# --------------------------------------------------------

HTTP_PORT = 60600
WS_PORT = 60601

WALLPAPERS_ROOT_DIR = "wallpapers"
APP_CONFIG_PATH = os.path.join(SCRIPT_DIR, 'app_config.json')

# --- (Network Globals: Unchanged) ---
STATS_LOCK = threading.Lock()
CURRENT_STATS = {
    "upload_bps": 0, "download_bps": 0, "total_sent": 0, "total_recv": 0
}
TRAFFIC_LOCK = threading.Lock()
LIVE_TRAFFIC_LOG = collections.deque(maxlen=50) 
SEEN_CONNECTIONS = set()
PROCESS_HIDE_LIST = [
    'chrome', 'firefox', 'msedge', 'brave', 'safari', 'opera'
]
# PORT_PROTOCOL_MAP imported from port_map.py
APP_CONFIG_LOCK = threading.Lock()

class MyHandler(http.server.SimpleHTTPRequestHandler):
    
    def get_current_wallpaper_path(self):
        default_theme = 'defolt'
        try:
            with APP_CONFIG_LOCK:
                with open(APP_CONFIG_PATH, 'r') as f:
                    app_config = json.load(f)
                    theme_name = app_config.get('active_theme', default_theme)
        except Exception as e:
            print(f"Warning: Could not read 'app_config.json'. Falling back to '{default_theme}'. Error: {e}")
            theme_name = default_theme
        return os.path.join(SCRIPT_DIR, WALLPAPERS_ROOT_DIR, theme_name)

    def do_GET(self):
        current_wallpaper_path = self.get_current_wallpaper_path()
        file_path = ""
        mime_type = ""
        try:
            if self.path == '/':
                # --- MODIFIED: Check for htmlrender mode ---
                config_path = os.path.join(current_wallpaper_path, 'config.json')
                is_html_render = False
                target_html_file = 'index.html' 

                try:
                    if os.path.exists(config_path):
                        with open(config_path, 'r') as f:
                            theme_config = json.load(f)
                            if theme_config.get('htmlrender') is True:
                                is_html_render = True
                                # Prefer the defined htmlWidgetFile, else fallback to index.html
                                target_html_file = theme_config.get('htmlWidgetFile', 'index.html')
                except Exception as e:
                    print(f"Error checking theme config for htmlrender: {e}")

                if is_html_render:
                    # Serve the theme's HTML directly, bypassing the 3D Engine
                    print(f"HTML Render Mode: Serving {target_html_file} from theme folder.")
                    file_path = os.path.join(current_wallpaper_path, target_html_file)
                else:
                    # Serve the Standard 3D Engine
                    file_path = os.path.join(SCRIPT_DIR, 'index.html')
                
                mime_type = 'text/html'
                # ---------------------------------------------

            elif self.path == '/config':
                file_path = os.path.join(current_wallpaper_path, 'config.json')
                try:
                    with open(file_path, 'rb') as f:
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                        self.end_headers()
                        self.wfile.write(f.read())
                except FileNotFoundError: self.send_error(404, f"config.json not found. Full path: {file_path}")
                except Exception as e: self.send_error(500, f"Error reading config: {e}")
                return
            elif self.path == '/widget.json':
                file_path = os.path.join(current_wallpaper_path, 'widget.json')
                try:
                    with open(file_path, 'rb') as f:
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                        self.end_headers()
                        self.wfile.write(f.read())
                except FileNotFoundError: self.send_error(404, f"widget.json not found. Full path: {file_path}")
                except Exception as e: self.send_error(500, f"Error reading widget.json: {e}")
                return
            elif self.path == '/app_config.json':
                file_path = APP_CONFIG_PATH
                try:
                    with APP_CONFIG_LOCK:
                        with open(file_path, 'rb') as f:
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                            self.end_headers()
                            self.wfile.write(f.read())
                except FileNotFoundError: self.send_error(404, "app_config.json not found.")
                except Exception as e: self.send_error(500, f"Error reading app_config: {e}")
                return
            elif self.path == '/model':
                config_path = os.path.join(current_wallpaper_path, 'config.json')
                mime_type = 'model/gltf-binary'
                model_from_config = None
                try:
                    with open(config_path, 'r') as f:
                        model_from_config = json.load(f).get('modelFile')
                except Exception as e:
                    self.send_error(500, f"Error reading config.json: {e}")
                    return
                if model_from_config:
                    file_path = os.path.join(current_wallpaper_path, model_from_config)
                    if not os.path.exists(file_path):
                        self.send_error(404, f"Model '{model_from_config}' not found.")
                        return
                else:
                    self.send_error(404, "No 'modelFile' specified in config.json.")
                    return
            elif self.path.startswith('/build/') or self.path.startswith('/library/') or self.path.startswith('/hdr/'):
                relative_path = self.path.lstrip('/')
                file_path = os.path.join(SCRIPT_DIR, relative_path)
            else:
                relative_path = self.path.lstrip('/')
                file_path = os.path.join(current_wallpaper_path, relative_path)
            
            mime_map = {
                ".css": "text/css", ".js": "application/javascript", ".html": "text/html",
                ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
                ".mp4": "video/mp4", ".webm": "video/webm", ".ogg": "video/ogg",
                ".mov": "video/quicktime", ".hdr": "application/octet-stream",
                ".json": "application/json"
            }
            if not mime_type:
                ext = os.path.splitext(file_path)[1].lower()
                mime_type = mime_map.get(ext, "application/octet-stream")
        except Exception as e:
            self.send_error(500, f"Error resolving path: {e}")
            return
        
        try:
            with open(file_path, 'rb') as f:
                self.send_response(200)
                self.send_header('Content-type', mime_type)
                if self.path in ['/', '/config', '/app_config.json', '/widget.json']: 
                    self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.send_error(404, f"File not found: {file_path}")
        except Exception as e:
            self.send_error(500, f"Error serving file: {e}")

def create_handler_class(window_ref, app_ref, port_num, token_from_main):
    class CustomHandler(MyHandler):
        window = window_ref
        app = app_ref
        http_port = port_num
        auth_token = token_from_main
        
        def check_auth(self):
            """Checks if the request User-Agent matches the secret token."""
            user_agent = self.headers.get('User-Agent')
            if user_agent == self.auth_token:
                return True
            
            print(f"--- SECURITY WARNING: Forbidden Request ---")
            print(f"Address: {self.client_address}")
            print(f"Path: {self.path}")
            print(f"User-Agent: {user_agent}")
            print(f"-------------------------------------------")
            self.send_error(403, "Forbidden: Invalid Auth Token")
            return False
        
        def do_GET(self):
            # --- MODIFIED: Public endpoints are now in a list ---
            public_paths = ['/', '/reload', '/quit', '/port']
            
            if self.path in public_paths:
                if self.path == '/reload':
                    print("Public endpoint '/reload' called. Triggering app restart.")
                    # --- MODIFIED: This now triggers a full application restart ---
                    self.app.is_restarting = True # Set flag for restart
                    QTimer.singleShot(0, self.app.quit) # Tell the app to quit
                    self.send_response(200); self.end_headers(); self.wfile.write(b'Restarting application...')
                    return
                elif self.path == '/quit':
                    print("Public endpoint '/quit' called.")
                    QTimer.singleShot(0, self.app.quit) # This is a normal quit
                    self.send_response(200); self.end_headers(); self.wfile.write(b'Quitting...')
                    return
                elif self.path == '/port':
                    print("Public endpoint '/port' called.")
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                    self.end_headers()
                    self.wfile.write(json.dumps({'http_port': self.http_port}).encode('utf-8'))
                    return
                elif self.path == '/':
                    # Public endpoint '/', let it fall through to super().do_GET()
                    print("Public endpoint '/' called.")
                    pass
            
            else:
                # --- All other endpoints are secured ---
                if not self.check_auth():
                    return
                
            super().do_GET()
            
        def do_POST(self):
            # All POST requests are still secured
            if not self.check_auth():
                return
                
            if self.path == '/save_widget_positions':
                try:
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    
                    current_wallpaper_path = self.get_current_wallpaper_path()
                    widget_config_path = os.path.join(current_wallpaper_path, 'widget.json')
                    
                    with open(widget_config_path, 'wb') as f:
                        f.write(post_data)
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'status': 'success'}).encode('utf-8'))
                    print(f"Saved widget positions to {widget_config_path}")
                except Exception as e:
                    print(f"Error saving widget positions: {e}", file=sys.stderr)
                    self.send_error(500, f"Error saving positions: {e}")
                return
            
            self.send_error(404, "Not Found")
            
    return CustomHandler


def start_server(port, handler_class):
    server = socketserver.ThreadingTCPServer(("localhost", port), handler_class)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print(f"Internal HTTP server running at http://localhost:{port} (Bound to localhost only)")


# --- (Custom QWebEngineView Class: Unchanged) ---
class CustomWebEngineView(QWebEngineView):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.context_menu = QMenu(self)
        reload_action = self.context_menu.addAction("Reload Wallpaper")
        self.context_menu.addSeparator()
        self.pause_action = self.context_menu.addAction("Pause Wallpaper")
        self.resume_action = self.context_menu.addAction("Resume Wallpaper")
        reload_action.triggered.connect(self.reload_page)
        self.pause_action.triggered.connect(self.window.pause_wallpaper)
        self.resume_action.triggered.connect(self.window.resume_wallpaper)
    def contextMenuEvent(self, event):
        if self.window.is_paused:
            self.pause_action.setEnabled(False); self.resume_action.setEnabled(True)
        else:
            self.pause_action.setEnabled(True); self.resume_action.setEnabled(False)
        self.context_menu.exec(event.globalPos())
    def reload_page(self): 
        # --- MODIFIED: Context menu reload should also do a full restart ---
        print("Context menu reload: Triggering app restart.")
        self.window.app.is_restarting = True
        QTimer.singleShot(0, self.window.app.quit)


# --- (AuthWebEnginePage Class: Unchanged) ---
class AuthWebEnginePage(QWebEnginePage):
    def __init__(self, parent, user_agent):
        super().__init__(parent)
        print("Setting custom User-Agent for browser...")
        self.profile().setHttpUserAgent(user_agent)

# --- (WallpaperWindow Class) ---
class WallpaperWindow(QMainWindow):
    def __init__(self1, app_ref, url, auth_token): 
        super().__init__()
        self1.app = app_ref 
        self1.is_paused = False
        self1.browser = CustomWebEngineView(self1)
        
        self1.auth_page = AuthWebEnginePage(self1.browser, auth_token)
        self1.browser.setPage(self1.auth_page)
        
        self1.browser.loadFinished.connect(self1.on_load_finished)
        self1.browser.setUrl(QUrl(url))
        self1.setCentralWidget(self1.browser)
        self1.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnBottomHint)
        self1.window_handle = int(self1.winId())

        # Since we forced scale factor = 1 using env var, logical == physical.
        screen = self1.app.primaryScreen()
        geometry = screen.geometry() 
        
        self1.screen_width = geometry.width()
        self1.screen_height = geometry.height()
        
        # Fallback: If Qt reports weird sizes, try WinAPI physical caps
        try:
             hDC = user32.GetDC(0)
             # DESKTOPHORZRES = 118, DESKTOPVERTRES = 117
             phy_w = user32.GetDeviceCaps(hDC, 118) 
             phy_h = user32.GetDeviceCaps(hDC, 117) 
             user32.ReleaseDC(0, hDC)
             # Use the larger of the two to be safe
             self1.screen_width = max(self1.screen_width, phy_w)
             self1.screen_height = max(self1.screen_height, phy_h)
        except:
             pass

        print(f"Wallpaper Resolution: {self1.screen_width}x{self1.screen_height}")
        # ------------------------------------------

        self1.setGeometry(0, 0, self1.screen_width, self1.screen_height)
        self1.show()

        QTimer.singleShot(100, self1.setup_window_layer)
        self1.check_timer = QTimer(self1); self1.check_timer.timeout.connect(self1.check_fullscreen); self1.check_timer.start(2000)
        print("Status: Live ▶️ (Fully Interactive)")

    def on_load_finished(self, ok):
        if ok:
            js_patch = """
            (function() {
                var canvas = document.getElementById("canvas");
                if (canvas) {
                    var dpr = window.devicePixelRatio || 1;
                    canvas.width = window.innerWidth * dpr;
                    canvas.height = window.innerHeight * dpr;
                    var ctx = canvas.getContext("2d");
                    if(ctx) ctx.scale(dpr, dpr);
                    canvas.style.width = window.innerWidth + "px";
                    canvas.style.height = window.innerHeight + "px";
                }
            })();
            """
            self.browser.page().runJavaScript(js_patch)

    def pause_wallpaper(self):
        if not self.is_paused:
            print("Status: Paused ⏸️ (Manual Pause)"); self.browser.page().runJavaScript("pauseAnimation();"); self.is_paused = True
    def resume_wallpaper(self):
        if self.is_paused:
            print("Status: Live ▶️ (Manual Resume)"); self.browser.page().runJavaScript("resumeAnimation();"); self.is_paused = False
            self.show(); QTimer.singleShot(50, self.setup_window_layer)
    def setup_window_layer(self):
        try:
            # 1. REMOVE TASKBAR ICON (WS_EX_TOOLWINDOW | ~WS_EX_APPWINDOW)
            ex_style = win32gui.GetWindowLong(self.window_handle, win32con.GWL_EXSTYLE)
            ex_style |= win32con.WS_EX_TOOLWINDOW   # Add ToolWindow (Hides from Taskbar/Alt-Tab)
            ex_style &= ~win32con.WS_EX_APPWINDOW   # Remove AppWindow (Forces Taskbar item)
            win32gui.SetWindowLong(self.window_handle, win32con.GWL_EXSTYLE, ex_style)

            # 2. Spawn WorkerW
            progman = win32gui.FindWindow("Progman", None)
            win32gui.SendMessageTimeout(progman, 0x052C, 0, 0, win32con.SMTO_NORMAL, 1000)
            
            # 3. Find correct WorkerW
            workerw = None
            def find_workerw(hwnd, _):
                nonlocal workerw
                if win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None):
                    workerw = win32gui.FindWindowEx(0, hwnd, "WorkerW", None)
                    return False
                return True
            win32gui.EnumWindows(find_workerw, 0)
            
            # 4. Attach to Desktop
            if workerw:
                print(f"Attaching to Desktop (WorkerW: {workerw})")
                win32gui.SetParent(self.window_handle, workerw)
            else:
                print("WorkerW not found. Using Fallback.")
                safe_height = self.screen_height - 1
                self.setGeometry(0, 0, self.screen_width, safe_height)
                win32gui.SetWindowPos(self.window_handle, win32con.HWND_BOTTOM, 0, 0, self.screen_width, safe_height, win32con.SWP_NOACTIVATE)
        
        except Exception as e:
            print(f"Error setting up window layer: {e}")
    def check_fullscreen(self):
        try:
            fg_window = win32gui.GetForegroundWindow()
            if not fg_window or fg_window == self.window_handle: return
            class_name = win32gui.GetClassName(fg_window)
            if class_name in ["Progman", "WorkerW", "Shell_TrayWnd"]:
                if self.is_paused: 
                    print("Status: Live ▶️ (Back to desktop)"); self.browser.page().runJavaScript("resumeAnimation();"); self.is_paused = False
                    self.show(); QTimer.singleShot(50, self.setup_window_layer)
                return
            placement = win32gui.GetWindowPlacement(fg_window)
            is_maximized = placement[1] == win32con.SW_SHOWMAXIZED
            (left, top, right, bottom) = win32gui.GetWindowRect(fg_window)
            is_fullscreen = (left == 0 and top == 0 and right == self.screen_width and bottom == self.screen_height)
            should_pause = is_maximized or is_fullscreen
            if should_pause and not self.is_paused:
                print(f"Status: Paused ⏸️ (App maximized/fullscreen)"); self.browser.page().runJavaScript("pauseAnimation();"); self.is_paused = True
            elif not should_pause and self.is_paused:
                print("Status: Live ▶️ (Resuming from app)"); self.browser.page().runJavaScript("resumeAnimation();"); self.is_paused = False
                self.show(); QTimer.singleShot(50, self.setup_window_layer)
        except Exception as e: pass
    def closeEvent(self, event):
        super().closeEvent(event)

# --- (Network Widget Backend: Unchanged) ---
def network_stats_updater():
    print("Network Monitor: Starting stats updater thread...")
    last_io = psutil.net_io_counters()
    while True:
        try:
            time.sleep(1)
            new_io = psutil.net_io_counters()
            upload_speed_bits = (new_io.bytes_sent - last_io.bytes_sent) * 8
            download_speed_bits = (new_io.bytes_recv - last_io.bytes_recv) * 8
            with STATS_LOCK:
                CURRENT_STATS["upload_bps"] = upload_speed_bits
                CURRENT_STATS["download_bps"] = download_speed_bits
                CURRENT_STATS["total_sent"] = new_io.bytes_sent
                CURRENT_STATS["total_recv"] = new_io.bytes_recv
            last_io = new_io
        except Exception as e:
            print(f"Error in stats updater thread: {e}", file=sys.stderr)
            time.sleep(5)

def get_process_name(pid):
    try:
        if pid is None or pid == 0: return "System"
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied): return "Access Denied"
    except Exception: return "N/A"

def live_traffic_updater(current_process_name):
    print("Network Monitor: Starting live traffic updater thread...")
    loopback_ips = ('127.0.0.1', '::1')
    while True:
        try:
            connections = psutil.net_connections(kind='inet')
            listening_ports = {c.laddr.port for c in connections if c.status == 'LISTEN'}
            new_log_entries = []
            for conn in connections:
                if not conn.raddr or conn.status not in ('ESTABLISHED', 'SYN_SENT'): continue
                
                process = get_process_name(conn.pid)
                if process == current_process_name:
                    is_loopback = conn.laddr.ip in loopback_ips or conn.raddr.ip in loopback_ips
                    if is_loopback:
                        continue 
                
                conn_key = (conn.laddr, conn.raddr, conn.pid, conn.status)
                if conn_key not in SEEN_CONNECTIONS:
                    SEEN_CONNECTIONS.add(conn_key)
                    is_server_port = conn.laddr.port in listening_ports
                    is_attempt = conn.status == 'SYN_SENT'
                    if is_server_port:
                        conn_type = "AT-IN" if is_attempt else "INCOMING"
                        protocol = PORT_PROTOCOL_MAP.get(conn.laddr.port, "Unknown")
                        ip_port = f"{conn.raddr.ip}:{conn.raddr.port}>{conn.laddr.port}"
                    else:
                        conn_type = "AT-OUT" if is_attempt else "OUTGOING"
                        protocol = PORT_PROTOCOL_MAP.get(conn.raddr.port, "Unknown")
                        ip_port = f"{conn.raddr.ip}:{conn.raddr.port}"
                    log_entry = {
                        "timestamp": datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3],
                        "type": conn_type, "ip_port": ip_port,
                        "protocol": protocol, "process": process
                    }
                    new_log_entries.append(log_entry)

            if new_log_entries:
                with TRAFFIC_LOCK:
                    for entry in new_log_entries:
                        LIVE_TRAFFIC_LOG.append(entry)
            
            if len(SEEN_CONNECTIONS) > 2000:
                SEEN_CONNECTIONS.clear()
                current_conns = psutil.net_connections(kind='inet')
                for c in current_conns:
                     if c.raddr and c.status in ('ESTABLISHED', 'SYN_SENT'):
                         SEEN_CONNECTIONS.add((c.laddr, c.raddr, c.pid, c.status))
            time.sleep(0.2)
        except Exception as e:
            print(f"Error in traffic updater thread: {e}", file=sys.stderr)
            time.sleep(5)

def get_network_data(current_process_name):
    with STATS_LOCK: stats = CURRENT_STATS.copy()
    with TRAFFIC_LOCK: live_traffic = list(LIVE_TRAFFIC_LOG)
        
    active_connections_raw, listening_ports_raw = [], []
    loopback_ips = ('1.27.0.0.1', '::1')
    try:
        connections = psutil.net_connections(kind='inet')
        for conn in connections:
            process_name = get_process_name(conn.pid)
            
            if process_name == current_process_name:
                is_loopback = False
                if conn.laddr: is_loopback = is_loopback or conn.laddr.ip in loopback_ips
                if conn.raddr: is_loopback = is_loopback or conn.raddr.ip in loopback_ips
                if is_loopback:
                    continue 
            
            if conn.status == 'ESTABLISHED' and conn.raddr:
                remote_protocol = PORT_PROTOCOL_MAP.get(conn.raddr.port, "Unknown")
                proc_lower = process_name.lower()
                if any(hn in proc_lower for hn in PROCESS_HIDE_LIST) and remote_protocol == "HTTPS":
                    continue
                active_connections_raw.append({
                    "ip": conn.raddr.ip, "port": conn.raddr.port,
                    "type": conn.type.name, "protocol": remote_protocol, "process": process_name
                })
            elif conn.status == 'LISTEN':
                protocol = PORT_PROTOCOL_MAP.get(conn.laddr.port, str(conn.laddr.port))
                listening_ports_raw.append({
                    "port": conn.laddr.port, "type": conn.type.name,
                    "protocol": protocol, "process": process_name
                })
    except (psutil.AccessDenied, psutil.ZombieProcess, psutil.NoSuchProcess): pass
    except Exception as e: print(f"Error getting connections: {e}", file=sys.stderr)
        
    stats.update({
        "active_connections": active_connections_raw,
        "listening_ports": listening_ports_raw,
        "live_traffic_log": live_traffic,
        "active_count": len(active_connections_raw),   
        "listening_count": len(listening_ports_raw) 
    })
    return stats

# --- (WebSocket Server Functions: Unchanged) ---
WEBSOCKET_CLIENTS = set()
async def ws_register(websocket): WEBSOCKET_CLIENTS.add(websocket)
async def ws_unregister(websocket): WEBSOCKET_CLIENTS.remove(websocket)

async def ws_data_push_loop(current_process_name):
    while True:
        if WEBSOCKET_CLIENTS:
            data = get_network_data(current_process_name) 
            data_json = json.dumps(data)
            await asyncio.gather(
                *[client.send(data_json) for client in WEBSOCKET_CLIENTS], return_exceptions=True
            )
        await asyncio.sleep(0.2)

async def ws_handler(websocket):
    global AUTH_TOKEN
    try:
        user_agent = websocket.request.headers['User-Agent']
        if user_agent != AUTH_TOKEN:
            print(f"WebSocket Auth FAILED. Closing connection.")
            await websocket.close(1008, "Invalid Auth Token")
            return
    except KeyError:
        print(f"WebSocket Auth FAILED (No User-Agent). Closing connection.")
        await websocket.close(1008, "Missing Auth Token")
        return
        
    await ws_register(websocket)
    try: await websocket.wait_closed()
    finally: await ws_unregister(websocket)

async def main_websocket_server(current_process_name):
    print(f"Network Monitor: Starting data push loop...")
    asyncio.create_task(ws_data_push_loop(current_process_name)) 
    
    global ws_port 
    print(f"Network Monitor: WebSocket server starting at ws://localhost:{ws_port}")
    async with websockets.serve(ws_handler, "localhost", ws_port):
        await asyncio.Future()

def start_websocket_thread(current_process_name):
    try:
        asyncio.run(main_websocket_server(current_process_name)) 
    except Exception as e:
        print(f"Network Monitor: WebSocket thread failed: {e}")

# --- (Main Execution) ---
if __name__ == "__main__":
    check_single_instance()
    AUTH_TOKEN = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(50))
    os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"
    
    try: current_proc_name = psutil.Process(os.getpid()).name()
    except: sys.exit(1)
    
    current_wallpaper_path = MyHandler.get_current_wallpaper_path(None)
    config_path = os.path.join(current_wallpaper_path, 'config.json')
    
    enable_global_widget = False
    try:
        with open(config_path, 'r') as f:
            c = json.load(f)
            # --- MODIFIED: Check htmlrender logic to force disable global widgets ---
            if c.get("htmlrender") is True:
                enable_global_widget = False
                print("HTML Render Mode detected: Global Widgets forcibly DISABLED.")
            elif c.get("Enable_Global_Widget") == True or c.get("Enable_Network_Widget") == True:
                enable_global_widget = True
            # ----------------------------------------------------------------------
    except: pass

    http_port = HTTP_PORT
    ws_port = WS_PORT if enable_global_widget else 0

    try:
        with APP_CONFIG_LOCK:
            c = {}
            if os.path.exists(APP_CONFIG_PATH):
                with open(APP_CONFIG_PATH, 'r') as f: c = json.load(f)
            c['port'] = http_port
            if enable_global_widget: c['ws_port'] = ws_port
            elif 'ws_port' in c: del c['ws_port']
            with open(APP_CONFIG_PATH, 'w') as f: json.dump(c, f, indent=2)
    except: pass
    
    server_url = f"http://localhost:{http_port}"
    
    app = QApplication(sys.argv)
    app.is_restarting = False
    window = WallpaperWindow(app_ref=app, url=server_url, auth_token=AUTH_TOKEN)
    start_server(http_port, create_handler_class(window, app, http_port, AUTH_TOKEN))
    
    if enable_global_widget:
        print("Starting Global Widget Threads...")
        threading.Thread(target=network_stats_updater, daemon=True).start()
        threading.Thread(target=live_traffic_updater, args=(current_proc_name,), daemon=True).start()
        threading.Thread(target=start_websocket_thread, args=(current_proc_name,), daemon=True).start()
    
    print(f"Engine Running on {server_url}")
    exit_code = app.exec()
    
    if app.is_restarting:
        os.execv(sys.executable, [sys.executable] + [os.path.abspath(sys.argv[0])])
    else:
        os._exit(exit_code)