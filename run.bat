@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [TypeStream] Keine venv gefunden — lege .venv an und installiere Abhaengigkeiten ...
    py -3 -m venv .venv || python -m venv .venv
    if errorlevel 1 (
        echo [TypeStream] venv-Erstellung fehlgeschlagen.
        exit /b 1
    )
    call ".venv\Scripts\activate.bat"
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
) else (
    call ".venv\Scripts\activate.bat"
)

echo [TypeStream] Starte App ... (Ctrl+C zum Beenden)
python main.py
set EXITCODE=%ERRORLEVEL%
echo [TypeStream] Beendet (rc=%EXITCODE%). venv bleibt aktiv — einfach 'run' fuer Neustart.
endlocal & exit /b %EXITCODE%
