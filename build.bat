@echo off
setlocal

cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    echo .venv missing - run: py -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

echo [1/3] Installing build deps
.venv\Scripts\python.exe -m pip install -q pyinstaller pillow
if errorlevel 1 exit /b 1

echo [2/3] Generating icon.ico from icon.svg
.venv\Scripts\python.exe tools\make_icon.py
if errorlevel 1 exit /b 1

echo [3/4] Running PyInstaller
.venv\Scripts\python.exe -m PyInstaller ^
    --name TypeStream ^
    --windowed ^
    --noconfirm ^
    --clean ^
    --icon assets\icon.ico ^
    --add-data "assets;assets" ^
    --hidden-import PyQt6.sip ^
    --collect-submodules openai ^
    main.py
if errorlevel 1 exit /b 1

echo [4/4] Building Windows installer
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"        set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe"             set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"    set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"

if not defined ISCC (
    echo   Inno Setup 6 not found - skipping installer.
    echo   Install from https://jrsoftware.org/isinfo.php and rerun build.bat.
    echo.
    echo Done. Portable build at dist\TypeStream\TypeStream.exe
    exit /b 0
)

"%ISCC%" /Qp installer\typestream.iss
if errorlevel 1 exit /b 1

echo.
echo Done. Installer at dist\installer\TypeStream-Setup-0.1.0.exe
endlocal
