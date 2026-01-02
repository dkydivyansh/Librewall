# Build Instructions for Librewall

This guide provides step-by-step instructions on how to build **Librewall** from source.

## Prerequisites

* [Python 3.10+](https://www.python.org/downloads/)
* [Git](https://git-scm.com/downloads)

---

## 1. Clone the Repository

First, clone the repository and navigate to the source directory.

```bash
git clone https://github.com/dkydivyansh/Librewall.git
cd Librewall/src
```

## 2. Set Up Virtual Environment

It is recommended to run the build inside a virtual environment to avoid conflicting dependencies.

**Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install Dependencies

Install the required Python packages.

```bash
pip install -r requirements.txt
```

---

## 4. API Configuration (Optional)

By default, the application don't have marketplace API. If you are hosting your own marketplace or testing a local API, you can modify the API endpoint.

1. Open `Launcher.py`.
2. Locate the `API_BASE_URL` variable.
3. Update it with your custom URL:

```python
API_BASE_URL = "https://your-custom-api.com/api/v1"
```

---

## 5. Embed Frontend Assets

Librewall uses a custom script to embed HTML/CSS/JS frontend files directly into Python byte code. This ensures the frontend cannot be easily tampered with and is bundled correctly.

Run the asset builder:

```bash
python build-assets.py
```

* **What this does:** This creates a Python package folder named `frontend`.
* **Note:** If you skip this step, the application may fail to load the UI in the compiled build. PyInstaller is configured to automatically include this generated `frontend` module.

---

## 6. Build the Executable

We use **PyInstaller** to compile the application.

### >  Important Build Warning
**STRICTLY create a "One Directory" (`onedir`) build.**
Do **NOT** attempt to build this application as a "One File" (`--onefile`) executable. Creating a single `.exe` file will break the application logic and internal asset loading.

### Run the Build

Run the automated build script:

```bash
python build.py
```

This script will:
1. Run PyInstaller using `librewall_suite.spec`.
2. Clone necessary directories (`wallpapers`, `include`, `hdr`, `build`, `library`) and config files into the distribution folder.

## 7. Locate Your Build

Once the process finishes, your compiled application will be available in the `dist` directory:

* Go to: `Librewall/src/dist/`
* You will find a folder named **`librewall_suite`**.
* Run the **`librewall.exe`** executable inside that folder to start the app.