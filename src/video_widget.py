import sys
import os
import ctypes
from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

# --- 1. PyInstaller & DLL Path Logic ---
if getattr(sys, 'frozen', False):
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

LIBMPV_INCLUDE_PATH = os.path.join(ROOT_DIR, "include")

if os.name == 'nt':
    if os.path.exists(LIBMPV_INCLUDE_PATH):
        try:
            os.add_dll_directory(LIBMPV_INCLUDE_PATH)
        except AttributeError:
            pass
        os.environ['PATH'] = LIBMPV_INCLUDE_PATH + ';' + os.environ['PATH']

try:
    import mpv
except OSError as e:
    print(f"CRITICAL: Could not load libmpv.\nError: {e}")
    mpv = None

class NativeVideoWidget(QWidget):
    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.is_paused = False
        
        if not mpv:
            return

        # 1. Setup Widget
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.setStyleSheet("background-color: black;")
        
        # 2. Initialize MPV Engine
        try:
            self.player = mpv.MPV(
                wid=str(int(self.winId())),
                log_handler=print,
                loglevel='warn'
            )

            # --- PERFORMANCE & LOOPING FIXES ---
            
            # 1. Hardware Decoding (Essential for 4K/8K)
            self.player['hwdec'] = 'auto'
            self.player['hwdec-codecs'] = 'all' # Force HW decoding for all codecs
            self.player['vo'] = 'gpu'           
            self.player['gpu-context'] = 'd3d11'
            
            # REPLACEMENT FOR gpu-hq:
            self.player['scale'] = 'spline36'
            self.player['cscale'] = 'spline36'
            self.player['dscale'] = 'mitchell'
            self.player['dither-depth'] = 'auto'
            self.player['correct-downscaling'] = 'yes'
            self.player['linear-downscaling'] = 'yes'
            self.player['sigmoid-upscaling'] = 'yes'
            self.player['deband'] = 'yes'

            # 2. SMOOTHNESS (Fix for Jitter/FPS drops)
            self.player['video-sync'] = 'display-resample' # Sync video to screen refresh rate
            self.player['interpolation'] = 'yes' # Enable motion interpolation
            self.player['tscale'] = 'oversample' # Smooth scaling method

            # 3. SEAMLESS LOOPING (The Fix)
            self.player['loop-file'] = 'inf'
            
            # 4. CACHING (Prevents the "stop" at the end)
            self.player['cache'] = 'yes'
            self.player['demuxer-max-bytes'] = '500M'    # Allow 500MB RAM cache
            self.player['demuxer-readahead-secs'] = '20' # Pre-load 20 seconds ahead

            # 5. Play
            self.player['keep-open'] = 'yes'
            
            if os.path.exists(video_path):
                print(f"Video Engine: Playing {video_path}")
                self.player.play(video_path)
            else:
                print(f"Video Engine Error: File not found {video_path}")
                
        except Exception as e:
            print(f"Video Engine Initialization Failed: {e}")

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        
        # Pause/Resume Action
        if self.is_paused:
            action_pause = QAction("Resume Wallpaper", self)
            action_pause.triggered.connect(lambda: self.set_paused(False))
        else:
            action_pause = QAction("Pause Wallpaper", self)
            action_pause.triggered.connect(lambda: self.set_paused(True))
        
        menu.addAction(action_pause)
        
        # Separator
        menu.addSeparator()
        
        # Stop Action (Optional, typically handled by main app)
        # action_stop = QAction("Stop Engine", self)
        # action_stop.triggered.connect(self.stop) 
        # menu.addAction(action_stop)

        menu.exec(event.globalPos())

    def set_paused(self, paused: bool):
        if hasattr(self, 'player'):
            self.player.pause = paused
            self.is_paused = paused

    def stop(self):
        if hasattr(self, 'player'):
            self.player.terminate()