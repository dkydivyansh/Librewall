import sys
import os
import json
import hashlib
import urllib.request
import urllib.error
import subprocess
import time
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, 
    QProgressBar, QHBoxLayout, QApplication, QFrame
)

# --- Stylesheet for High Contrast (Black/White) ---
STYLESHEET = """
QWidget {
    background-color: #121212;
    color: #ffffff;
    font-family: 'Segoe UI', sans-serif;
}
QLabel {
    font-size: 14px;
    color: #cccccc;
}
QLabel#Title {
    font-size: 22px;
    font-weight: bold;
    color: #ffffff;
}
QLabel#Stats {
    font-size: 13px;
    font-weight: bold;
    color: #ffffff;
    margin-bottom: 5px;
}
QLabel#VersionInfo {
    color: #aaaaaa;
    margin-bottom: 10px;
}
QPushButton {
    background-color: #ffffff;
    color: #000000;
    border: none;
    padding: 10px 20px;
    font-weight: bold;
    font-size: 14px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #e0e0e0;
}
QPushButton#SecondaryBtn {
    background-color: #333333;
    color: #ffffff;
    border: 1px solid #555555;
}
QPushButton#SecondaryBtn:hover {
    background-color: #444444;
}
QPushButton:disabled {
    background-color: #555555;
    color: #888888;
}
QProgressBar {
    border: 1px solid #444444;
    background-color: #222222;
    height: 12px;
    text-align: right; 
}
QProgressBar::chunk {
    background-color: #ffffff;
}
"""

class DownloadWorker(QThread):
    progress = pyqtSignal(int)
    stats = pyqtSignal(str) # Emits formatted string "50MB / 150MB - 2 MB/s"
    finished = pyqtSignal(str) # Emits path to downloaded file
    error = pyqtSignal(str)

    def __init__(self, url, filename, expected_hash=None):
        super().__init__()
        self.url = url
        self.filename = filename
        self.expected_hash = expected_hash
        self.is_running = True
        self.is_paused = False

    def format_bytes(self, size):
        power = 2**10
        n = 0
        power_labels = {0 : '', 1: 'KB', 2: 'MB', 3: 'GB'}
        while size > power:
            size /= power
            n += 1
        return f"{size:.1f} {power_labels.get(n, 'TB')}"

    def run(self):
        try:
            temp_dir = os.environ.get('TEMP', os.getcwd())
            filepath = os.path.join(temp_dir, self.filename)
            
            with urllib.request.urlopen(self.url) as response:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                block_size = 8192
                
                start_time = time.time()
                last_time = start_time
                last_downloaded = 0

                with open(filepath, 'wb') as f:
                    while self.is_running:
                        # Pause Logic
                        while self.is_paused:
                            time.sleep(0.1)
                            if not self.is_running: break
                        
                        if not self.is_running: break

                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        
                        downloaded += len(buffer)
                        f.write(buffer)
                        
                        # Stats Calculation
                        current_time = time.time()
                        if current_time - last_time >= 1.0: # Update every second
                            speed = (downloaded - last_downloaded) / (current_time - last_time)
                            
                            speed_str = f"{self.format_bytes(speed)}/s"
                            progress_str = f"{self.format_bytes(downloaded)} / {self.format_bytes(total_size)}"
                            
                            self.stats.emit(f"{progress_str} - {speed_str}")
                            
                            last_time = current_time
                            last_downloaded = downloaded

                        if total_size > 0:
                            percent = int(downloaded * 100 / total_size)
                            self.progress.emit(percent)
            
            if not self.is_running:
                # Cleanup if cancelled
                if os.path.exists(filepath):
                    os.remove(filepath)
                return

            # Verify Hash
            if self.expected_hash:
                self.stats.emit("Verifying integrity...")
                file_hash = self.calculate_sha256(filepath)
                if file_hash.lower() != self.expected_hash.lower():
                    self.error.emit("Hash verification failed! File may be corrupted.")
                    return

            self.progress.emit(100)
            self.finished.emit(filepath)

        except Exception as e:
            self.error.emit(str(e))

    def calculate_sha256(self, filepath):
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def stop(self):
        self.is_running = False
    
    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False


class UpdateWindow(QWidget):
    def __init__(self, current_ver_name, current_ver_code, update_data):
        super().__init__()
        self.update_data = update_data
        self.current_ver_code = current_ver_code # Store for arguments
        self.worker = None
        
        self.setWindowTitle("Librewall Update")
        self.setFixedSize(500, 300)
        # Frameless window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(STYLESHEET)
        
        # --- UI Initialization ---
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(10)
        
        # 1. Header (Dynamic)
        self.title_label = QLabel("Update Available")
        self.title_label.setObjectName("Title")
        self.layout.addWidget(self.title_label)
        
        # 2. Version Info (Visible initially)
        info_text = (
            f"Current Version: {current_ver_name}\n"
            f"New Version: {update_data['version_name']}\n"
            f"Size: {update_data['file_size']}"
        )
        self.info_label = QLabel(info_text)
        self.info_label.setObjectName("VersionInfo")
        self.layout.addWidget(self.info_label)
        
        # 3. Stats Label (Hidden initially)
        self.stats_label = QLabel("")
        self.stats_label.setObjectName("Stats")
        self.stats_label.hide()
        self.layout.addWidget(self.stats_label)

        self.layout.addStretch()

        # 4. Progress Bar (Hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        self.layout.addWidget(self.progress_bar)
        
        # 5. Buttons Layout
        self.btn_layout = QHBoxLayout()
        
        # Initial Buttons
        self.skip_btn = QPushButton("Skip")
        self.skip_btn.setObjectName("SecondaryBtn")
        self.skip_btn.clicked.connect(self.close)
        
        self.update_btn = QPushButton("Update")
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.clicked.connect(self.start_download)
        
        # Download Mode Buttons (Hidden initially)
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setObjectName("SecondaryBtn")
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.hide()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("SecondaryBtn")
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.hide()

        # Retry Button (Added for error state)
        self.retry_btn = QPushButton("Retry")
        # Use primary style for Retry to encourage action, or Secondary if preferred
        self.retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.retry_btn.clicked.connect(self.retry_update)
        self.retry_btn.hide()

        self.btn_layout.addWidget(self.skip_btn)
        self.btn_layout.addWidget(self.update_btn)
        self.btn_layout.addWidget(self.retry_btn) # Added to layout
        self.btn_layout.addWidget(self.pause_btn)
        self.btn_layout.addWidget(self.cancel_btn)
        
        self.layout.addLayout(self.btn_layout)
        self.setLayout(self.layout)
        
        # Center on screen
        if QApplication.primaryScreen():
            geo = self.frameGeometry()
            center = QApplication.primaryScreen().availableGeometry().center()
            geo.moveCenter(center)
            self.move(geo.topLeft())
            
        # For Mouse Move
        self.drag_pos = None

    # --- Mouse Events for Dragging ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    # --- Logic ---

    def start_download(self):
        # UI Transition
        self.info_label.hide()
        self.skip_btn.hide()
        self.update_btn.hide()
        self.retry_btn.hide() # Ensure retry is hidden
        
        self.title_label.setText("Downloading Update...")
        self.stats_label.show()
        self.stats_label.setStyleSheet("color: #ffffff;") # Reset color
        self.stats_label.setText("Starting...")
        self.progress_bar.show()
        self.pause_btn.show()
        self.cancel_btn.show()
        
        # Start Worker
        url = self.update_data.get('installer_url')
        expected_hash = self.update_data.get('installer_hash')
        filename = "librewall_setup.exe"
        
        self.worker = DownloadWorker(url, filename, expected_hash)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.stats.connect(self.stats_label.setText)
        self.worker.finished.connect(self.run_installer)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def toggle_pause(self):
        if not self.worker: return
        
        if self.worker.is_paused:
            self.worker.resume()
            self.pause_btn.setText("Pause")
            self.title_label.setText("Downloading Update...")
        else:
            self.worker.pause()
            self.pause_btn.setText("Resume")
            self.title_label.setText("Paused")

    def cancel_download(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.worker = None
        
        # Reset UI to initial state
        self.stats_label.hide()
        self.progress_bar.hide()
        self.pause_btn.hide()
        self.cancel_btn.hide()
        self.retry_btn.hide() # Hide retry
        self.progress_bar.setValue(0)
        self.stats_label.setStyleSheet("color: #ffffff;")
        
        self.title_label.setText("Update Available")
        self.info_label.show()
        self.skip_btn.show()
        self.update_btn.show()
        self.pause_btn.setText("Pause")

    def run_installer(self, path):
        self.title_label.setText("Installing...")
        self.stats_label.setText("Launching installer...")
        try:
            # 1. Check if file exists
            if not os.path.exists(path):
                raise Exception("Installer file missing after download.")

            # 2. Prepare Command with Arguments
            # Arguments: /PREV_VERSION=1
            cmd = [path, f"/PREV_VERSION={self.current_ver_code}"]
            
            # 3. Launch Process
            subprocess.Popen(cmd)
            
            # 4. Success? Force Exit
            QApplication.quit() 
            sys.exit(0)

        except Exception as e:
            # 5. Failure? Show Error
            self.on_error(f"Launch failed: {e}")

    def on_error(self, err_msg):
        self.stats_label.setText(f"Error: {err_msg}")
        self.stats_label.setStyleSheet("color: #ff5555;")
        
        # Hide Pause, Show Retry AND Cancel
        self.pause_btn.hide()
        self.retry_btn.show()
        self.cancel_btn.show()

    def retry_update(self):
        self.start_download()

def run_update_check(current_version_code, current_version_name, api_base_url):
    """
    Returns True if the main app should continue, False if it should exit (update running).
    """
    try:
        url = f"{api_base_url}?action=get_latest_update"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.load(response)
            
        update_info = data.get('data')
        if not update_info:
            return True 
            
        server_ver = int(update_info.get('version', 0))
        
        # Check Version CODE (int), but display Version NAME (str)
        if server_ver > current_version_code:
            # Pass BOTH Name and Code to Window
            window = UpdateWindow(current_version_name, current_version_code, update_info)
            window.show()
            loop = QApplication.exec() 
            return True
            
    except Exception as e:
        print(f"Update check failed: {e}")
        return True

    return True