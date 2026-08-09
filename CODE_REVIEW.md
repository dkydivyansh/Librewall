# Librewall Source Code Review

## 1. Identified Bugs
- **Platform-Dependent Imports (`gpu_utils.py`):** The `winreg` module is imported at the top-level. Since it is a Windows-only module, any execution on Linux or macOS will immediately fail with a `ModuleNotFoundError` (as observed during testing). Consider wrapping it in a `sys.platform == 'win32'` check or creating a dummy class for non-Windows platforms.
- **Unused Globals:** In `src/main.py` (line 1552), `global AUTH_TOKEN` is declared but never assigned or effectively used within that specific scope, which can cause confusion.
- **Abrupt Exits:** The usage of `os._exit(0)` instead of `sys.exit()` (found in `src/main.py` and `src/Launcher.py`) abruptly terminates the process without calling cleanup handlers, flushing stdio buffers, etc. This could lead to corrupted data or deadlocked mutexes.
- **Bare Exceptions:** Widespread usage of bare `except:` or `except Exception:` instead of catching specific errors. This masks bugs, intercepts `KeyboardInterrupt`, and makes debugging difficult.

## 2. Architecture & Maintainability
- **Code Duplication:**
    - The `check_single_instance` function logic utilizing `kernel32.CreateMutexW` is duplicated across `src/main.py` and `src/Launcher.py`.
    - The `NullWriter` stub class and stdio overrides are exactly duplicated in `src/main.py` and `src/Launcher.py`.
    - These shared functionalities should be extracted into a common utility module (e.g., `utils.py` or similar) to enforce DRY principles.
- **Large Files:** `src/main.py` and `src/Launcher.py` are over 1500 and 2300 lines respectively. This indicates they handle too many responsibilities (UI layout, HTTP request handling, backend processing, startup sequences). They should be refactored into smaller, focused modules.
- **Hardcoded Values & Global State:** Extensive use of global variables (e.g., locks, `CURRENT_STATS`, etc.) introduces risks for race conditions. Encapsulating this state within classes would be safer and more maintainable.

## 3. Performance Improvements
- **Inline Imports in Loops/Functions:** The `import psutil` statement is used repeatedly inside tight loops or functions (e.g., in `main.py` lines ~1276, ~1408, ~1416). While Python caches imported modules, the repeated function call overhead to check `sys.modules` inside a loop can be avoided. Import these dependencies once at the module level.
- **WebSocket Broadcasting:** In `main.py`, the `ws_data_push_loop` converts sets and constructs large strings frequently. Ensure that only updated diffs are sent, or throttling is correctly balanced to avoid high CPU usage.

## 4. Code Quality & Formatting
- **PEP 8 Violations:** Extensive violations found via `flake8` and `pylint`. These include:
    - Multiple statements on one line (e.g., `self.send_error(403, "Forbidden"); return False`).
    - Incorrect import groupings and placement (imports scattered throughout the file rather than at the top).
    - Line lengths severely exceeding 79/100 characters limits.
- **Type Hinting & Docstrings:** Minimal type hinting and a widespread absence of docstrings for functions and classes making it harder to track data flow and intent.
- **Unused Variables and Imports:** Pylint identified unused imports (e.g., `time`, `win32api`, `mimetypes`, `zlib`) and unformatted f-strings (f-strings with no interpolated variables).
