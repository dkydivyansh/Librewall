import os
import sys
import winreg
import subprocess
import time
import ctypes

kernel32 = ctypes.windll.kernel32
mutex_handle = None

def get_engine_path():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
        return os.path.join(base_dir, "engine.exe")
    else:
        return os.path.abspath(sys.executable)

def get_gpu_info() -> list:
    try:
        cmd = [
            'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-Command',
            "(Get-CimInstance Win32_VideoController).Name"
        ]
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0 
        result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW, timeout=3)
        names = [name.strip() for name in result.stdout.strip().split('\n') if name.strip()]
        if len(names) == 2:
            igpu_idx = 0
            dgpu_idx = 1
            for i, name in enumerate(names):
                name_lower = name.lower()
                if any(brand in name_lower for brand in ['nvidia', 'geforce', 'rtx', 'gtx', 'dedicated']):
                    dgpu_idx = i
                    igpu_idx = 1 if i == 0 else 0
                elif 'radeon' in name_lower and 'rx' in name_lower:
                    dgpu_idx = i
                    igpu_idx = 1 if i == 0 else 0
            return [names[igpu_idx], names[dgpu_idx]]
        return names if names else ["Unknown GPU"]
    except Exception as e:
        print(f"Error getting GPU names: {e}")
        return ["Unknown GPU"]

def get_gpu_preference() -> int:
    engine_path = get_engine_path()
    reg_path = r"SOFTWARE\Microsoft\DirectX\UserGpuPreferences"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, engine_path)
        winreg.CloseKey(key)
        if "GpuPreference=1" in value: return 1
        elif "GpuPreference=2" in value: return 2
        return 0
    except (FileNotFoundError, OSError):
        return 0

def set_gpu_preference(level: int) -> bool:
    engine_path = get_engine_path()
    reg_path = r"SOFTWARE\Microsoft\DirectX\UserGpuPreferences"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_READ)
    except FileNotFoundError:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
    try:
        if level == 0:
            try: winreg.DeleteValue(key, engine_path)
            except FileNotFoundError: pass
        else:
            value_str = f"GpuPreference={level};"
            winreg.SetValueEx(key, engine_path, 0, winreg.REG_SZ, value_str)
        return True
    except Exception as e:
        print(f"GPU Registry Error: {e}")
        return False
    finally:
        winreg.CloseKey(key)

def release_mutex():
    global mutex_handle
    if mutex_handle:
        kernel32.ReleaseMutex(mutex_handle)
        kernel32.CloseHandle(mutex_handle)
        mutex_handle = None

def restart_librewall():
    try:
        release_mutex() 
    except Exception as e:
        print(f"Mutex release failed: {e}")
    time.sleep(0.3) 
    try:
        subprocess.run('taskkill /F /IM engine.exe /IM main.exe /T', shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except:
        pass
    if getattr(sys, 'frozen', False):
        exe = sys.executable
        args = [exe]
    else:
        exe = sys.executable
        args = [exe, os.path.abspath(sys.argv[0])]
    os.execv(exe, args)
