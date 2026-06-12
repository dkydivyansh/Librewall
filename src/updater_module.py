import sys
import os
import json
import urllib.request
import subprocess
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QApplication
)

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
QLabel#VersionInfo {
    color: #aaaaaa;
    margin-bottom: 20px;
    font-size: 16px;
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
"""

class MandatoryUpdateWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mandatory Update")
        self.setFixedSize(400, 200)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(STYLESHEET)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(15)

        self.title_label = QLabel("Mandatory Update Required")
        self.title_label.setObjectName("Title")
        self.title_label.setStyleSheet("color: #ff5555;")
        self.layout.addWidget(self.title_label)

        self.info_label = QLabel("Please update from launcher.")
        self.info_label.setObjectName("VersionInfo")
        self.layout.addWidget(self.info_label)

        self.layout.addStretch()

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.clicked.connect(self.on_exit)
        self.layout.addWidget(self.exit_btn)

        self.setLayout(self.layout)

        if QApplication.primaryScreen():
            geo = self.frameGeometry()
            center = QApplication.primaryScreen().availableGeometry().center()
            geo.moveCenter(center)
            self.move(geo.topLeft())

        self.drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_pos:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def on_exit(self):
        try:
            exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher.exe")
            if os.path.exists(exe_path):
                subprocess.Popen([exe_path])
            else:
                subprocess.Popen(["launcher.exe"])
        except Exception as e:
            print(f"Could not launch launcher.exe: {e}")
        
        QApplication.quit()

def run_update_check(current_version_code, current_version_name, api_base_url, user_agent="Mozilla/5.0"):
    """
    Returns True if the main app should continue, False if it should exit.
    Checks server version and ONLY enforces mandatory updates.
    """
    try:
        url = f"{api_base_url}?action=get_latest_update"
        req = urllib.request.Request(url, headers={'User-Agent': user_agent})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.load(response)

        update_info = data.get('data')
        if not update_info:
            return True 

        server_ver = int(update_info.get('version', 0))
        min_required_ver = int(update_info.get('min_required_version', 0))

        if server_ver > current_version_code:
            is_force_update = (current_version_code < min_required_ver)

            if not is_force_update:
                return True
                
            print("Mandatory update required. Showing update prompt.")
            window = MandatoryUpdateWindow()
            window.show()
            QApplication.exec()
            sys.exit(0)
            return False 

    except Exception as e:
        print(f"Update check failed: {e}")
        return True

    return True