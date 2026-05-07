@echo off
setlocal
cd /d "%~dp0"

net session >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [TypeStream] Fordere Admin-Rechte an ...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

if not exist ".venv\Scripts\python.exe" (
    echo [TypeStream] Keine venv gefunden — lege .venv an und installiere Abhaengigkeiten ...
    py -3 -m venv .venv || python -m venv .venv
    if errorlevel 1 (
        echo [TypeStream] venv-Erstellung fehlgeschlagen.
        pause
        exit /b 1
    )
    call ".venv\Scripts\activate.bat"
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
) else (
    call ".venv\Scripts\activate.bat"
)

echo [TypeStream] Starte App als Admin ... (Ctrl+C zum Beenden)
python main.py
echo [TypeStream] Beendet (rc=%ERRORLEVEL%).
pause
endlocal
