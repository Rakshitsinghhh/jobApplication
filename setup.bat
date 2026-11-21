@echo off
echo ==================================================
echo  Setting up Job Application Mailer Environment
echo ==================================================

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment in .\venv...
    python -m venv venv
) else (
    echo Virtual environment already exists in .\venv.
)

echo Installing dependencies from requirements.txt...
venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt

echo.
echo ==================================================
echo Setup complete! Starting application...
echo ==================================================
call venv\Scripts\activate
python main.py
