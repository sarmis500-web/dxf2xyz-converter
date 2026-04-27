# Developer Build Instructions

## Mac (Intel i9, Tahoe 26.3)

**Critical:** Install Python 3.12 from https://www.python.org/downloads/macos/ (the universal2 installer). Do NOT use Homebrew Python on Tahoe 26.x — the libexpat ABI break causes pyexpat import failures.

```bash
cd dxf2xyz
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller==6.10
pyinstaller dxf2xyz.spec --clean
# Output: dist/DXF to XYZ.app
```

## Windows 11 (Lenovo)
Install Python 3.12 from python.org (Windows installer, "Add to PATH" checked).
```cmd
cd dxf2xyz
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller==6.10
pyinstaller dxf2xyz.spec --clean
:: Output: dist\DXF to XYZ.exe
```
