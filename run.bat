@echo off
title Employee Wellness Management Analytics

cd /d "%~dp0"

echo ===================================================
echo   Employee Wellness Management Analytics
echo ===================================================
echo.

REM 1. Activate virtual environment if present
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment .venv...
    call .venv\Scripts\activate.bat
    goto CHECK_PYTHON
)

if exist venv\Scripts\activate.bat (
    echo Activating virtual environment venv...
    call venv\Scripts\activate.bat
    goto CHECK_PYTHON
)

echo No virtual environment found. Using system Python...

:CHECK_PYTHON
echo.
REM 2. Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found! Please install Python 3.10+ and add it to PATH.
    echo.
    pause
    exit /b 1
)

REM 3. Check dependencies
echo Checking dependencies...
python -c "import flask, flask_login, flask_sqlalchemy, flask_bcrypt" >nul 2>&1
if errorlevel 1 (
    echo Missing required Python packages. Installing requirements...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies from requirements.txt.
        echo.
        pause
        exit /b 1
    )
)

REM 4. Check & Start Ollama AI Service
echo.
echo Checking Ollama AI engine...
where ollama >nul 2>&1
if %errorlevel% equ 0 (
    echo Starting Ollama AI server background service...
    start /b "" ollama serve >nul 2>&1
) else (
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        echo Starting Ollama AI server background service...
        start /b "" "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve >nul 2>&1
    ) else (
        echo Ollama executable was not found in PATH or default installation folder.
    )
)

REM 5. Run Flask Application
echo.
echo Starting Employee Wellness Management Analytics server...
echo Web App URL: http://127.0.0.1:5000
echo ===================================================
echo.

python app.py

echo.
echo Server stopped.
pause
