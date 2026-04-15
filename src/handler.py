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
        
        import sys
        if 'WindowsApps' in getattr(sys, 'base_prefix', ''):
            import glob
            py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
            pkg_pattern = os.path.join(local, "Packages", f"PythonSoftwareFoundation.Python.{py_ver}_*")
            matches = glob.glob(pkg_pattern)
            if matches:
                _APP_DATA_DIR = os.path.join(matches[0], "LocalCache", "Local", "Librewall")

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

        if name == api_config.WIDGETS_DIR:
            os.makedirs(dst, exist_ok=True)
            if os.path.isdir(src):
                for item in os.listdir(src):
                    src_item = os.path.join(src, item)
                    dst_item = os.path.join(dst, item)
                    if os.path.isdir(src_item) and item != "__pycache__":
                        if not os.path.exists(dst_item) or (os.path.isdir(dst_item) and not os.listdir(dst_item)):
                            try:
                                if os.path.exists(dst_item):
                                    shutil.rmtree(dst_item)
                                shutil.copytree(src_item, dst_item)
                                print(f"[handler] Restored/Copied missing system widget: {item}")
                            except Exception as e:
                                print(f"[handler] Failed to copy widget {item}: {e}")
                src_idx = os.path.join(src, "index.json")
                dst_idx = os.path.join(dst, "index.json")
                if os.path.isfile(src_idx):
                    if not os.path.isfile(dst_idx):
                        shutil.copy2(src_idx, dst_idx)
                        print(f"[handler] Created initial widgets/index.json")
                    else:
                        try:
                            with open(src_idx, 'r', encoding='utf-8') as f:
                                s_data = json.load(f)
                            with open(dst_idx, 'r', encoding='utf-8') as f:
                                d_data = json.load(f)

                            s_widgets = s_data.get("widgets", [])
                            d_widgets = d_data.get("widgets", [])
                            d_ids = {str(w.get("id")) for w in d_widgets}

                            added = 0
                            for sw in s_widgets:
                                sw_id = str(sw.get("id"))
                                if sw_id not in d_ids:
                                    d_widgets.append(sw)
                                    added += 1
                                else:
                                    pass

                            if added > 0:
                                d_data["widgets"] = d_widgets
                                with open(dst_idx, 'w', encoding='utf-8') as f:
                                    json.dump(d_data, f, indent=4)
                                print(f"[handler] Added {added} system widgets to local registry")
                        except Exception as e:
                            print(f"[handler] Error merging widget registry: {e}")
            continue

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
