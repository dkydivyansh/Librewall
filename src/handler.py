import os
import json
import shutil

import api_config

_APP_DATA_DIR = None

def get_appdata_dir():
    """Return the root AppData directory for Librewall."""
    global _APP_DATA_DIR
    if _APP_DATA_DIR is None:
        local = os.getenv("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        _APP_DATA_DIR = os.path.join(local, "Librewall")
    return _APP_DATA_DIR


def get_data_path(*parts):
    """Return full path to a subfolder/file inside the AppData directory."""
    return os.path.join(get_appdata_dir(), *parts)


def get_app_config_path():
    """Return the path to app_config.json in AppData."""
    return os.path.join(get_appdata_dir(), api_config.APP_CONFIG_FILE)

_SEED_DIRS = [api_config.WALLPAPERS_DIR, api_config.WIDGETS_DIR]
_EMPTY_DIRS = [api_config.THUMBNAIL_CACHE_DIR, api_config.BROWSER_DATA_DIR]


def init_appdata(install_dir):
    """Create AppData structure. On first run, copy wallpapers/, widgets/,
    and app_config.json from install_dir."""

    base = get_appdata_dir()
    print(f"[handler] AppData: {base}")
    print(f"[handler] Install: {install_dir}")
    os.makedirs(base, exist_ok=True)
    for name in _SEED_DIRS:
        dst = os.path.join(base, name)
        src = os.path.join(install_dir, name)
        if os.path.isdir(dst) and os.listdir(dst):
            continue
        if os.path.isdir(src):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"[handler] Copied {name}/")
        else:
            os.makedirs(dst, exist_ok=True)

    dst_cfg = get_app_config_path()
    if not os.path.isfile(dst_cfg):
        src_cfg = os.path.join(install_dir, api_config.APP_CONFIG_FILE)
        if os.path.isfile(src_cfg):
            shutil.copy2(src_cfg, dst_cfg)
            print(f"[handler] Copied {api_config.APP_CONFIG_FILE}")
        else:
            with open(dst_cfg, "w", encoding="utf-8") as f:
                json.dump({
                "active_theme": "29",
                "port": 60600,
                "auto_start": False,
                "hide_icons": False,
                "tour": False,
                "tour_v2": False,
                "ws_port": 60601
            }, f, indent=2)
            print(f"[handler] Created default {api_config.APP_CONFIG_FILE}")

    for name in _EMPTY_DIRS:
        os.makedirs(os.path.join(base, name), exist_ok=True)

    print(f"[handler] Ready.")
