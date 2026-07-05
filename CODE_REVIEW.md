# Librewall Source Code Review

This document contains a comprehensive review of the `src/` directory, focusing on maintainability, performance, and functional bugs.

## 1. Refactoring & Maintainability

* **Duplicated Utility Functions**: The functions `get_reliable_windows_id()` and `get_os_version_string()` are identically implemented in both `src/main.py` and `src/Launcher.py`. These should be extracted to a shared utility module (e.g., `utils.py`) to keep the codebase DRY.
* **Duplicated Console Output Suppression**: Both `src/main.py` and `src/Launcher.py` have the exact same `NullWriter` class and logic for suppressing `sys.stdout` and `sys.stderr` when developer mode is disabled. This logic should also be moved to a shared initialization module.
* **Monolithic HTTP Handlers**: `MyHandler` in `main.py` and `EditorHTTPHandler` in `Launcher.py` are extremely long and handle all API logic within giant `if/elif` chains in `do_GET` and `do_POST`. Consider adopting a routing dictionary pattern (mapping URL paths to specific handler functions) to improve code readability and maintainability.
* **Hardcoded Constants**: There are several instances of hardcoded string identifiers (e.g., Mutex names like `r"Local\librewall"`) scattered in the code. These should be centralized in `api_config.py`.

## 2. Performance Improvements

* **Frequent Subprocess Calls**: In `gpu_utils.py`, `get_gpu_info()` calls out to PowerShell using a blocking subprocess to query `Win32_VideoController`. This takes time and can block the UI or startup. Consider caching this result to a local file after the first run, or executing it asynchronously so it doesn't block startup threads.
* **Synchronous Theme Validation**: In `Launcher.py`, `scan_all_wallpapers()` sequentially reads the `config.json` for every installed theme using synchronous disk I/O. If a user has a large number of themes, this could slow down the API request. Consider fetching these configurations asynchronously or maintaining a cached index file that updates when themes are added/removed.
* **Aggressive Network Monitoring**: `psutil.net_connections(kind='inet')` in `main.py`'s `live_traffic_updater` is called repeatedly. On systems with many active network connections, iterating and extracting this info frequently uses significant CPU. The polling rate should be optimized or conditionally scaled based on whether the data is actually being consumed.

## 3. Existing Bugs & Logic Errors

* **Error Handling Logic Error in `main.py`**:
  Around line 204 in `main.py` (inside `check_single_instance`):
  ```python
  try:
       user32.MessageBoxW(None, "Another instance of librewall engine is already running.", "librewall_engine", 0x10)
  except NameError:
      user32.MessageBoxW(None, "Another instance of librewall engine is already running.", "librewall_engine", 0x10)
  ```
  If `user32` is not defined (triggering the `NameError`), calling `user32.MessageBoxW` inside the `except` block will immediately raise another `NameError`. It should fall back to using `ctypes.windll.user32.MessageBoxW` explicitly.

* **String Splitting for Path Extraction**:
  In `Launcher.py` (around line 1142), the code uses `value_raw.split('\\')[-1]` to extract a filename from an INF file string. If the `.inf` file was written with forward slashes (`/`), this split will fail to extract the filename correctly. It's safer to use `os.path.basename` (after normalizing slashes) or string replacements before splitting.

* **File Cleanup Race Conditions**:
  In `Launcher.py` (`cleanup_old_cache`), the script iterates through cached thumbnails and deletes them if they exceed the maximum age. Although it wraps the check in a `try-except` block, iterating over `os.listdir()` and subsequently operating on those files without checking if they still exist can cause an `OSError` if another process or thread deletes the file in between the list and the `getmtime` call. Explicit concurrent access controls or pre-checks could improve stability.
