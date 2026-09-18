# Development

Requires Windows, Python 3.12, and Traditional Chinese Windows OCR support.
Run commands from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install PyInstaller==6.22.3
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe main.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1 -Python .venv/Scripts/python.exe
```

`app/version.py` is the version source. The build creates a timestamped single-file EXE package and a SHA-256 sidecar without overwriting earlier builds. Only the EXE, README.md, and CHANGELOG.md are distributed. Runtime resources resolve through `sys._MEIPASS`; settings and reports stay in LOCALAPPDATA, outside the temporary extraction folder.

Review and test packaged Tk startup, icon/resource loading, offline OCR (including its PowerShell child process), clean exit, ZIP contents, and checksum. Use temporary LOCALAPPDATA for GUI tests to preserve player progress. Developer evidence remains in ../VALIDATION.md; historical change notes are in DEVELOPMENT_HISTORY.md. Neither is packaged.
