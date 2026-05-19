@echo off
cd /d "%~dp0"
echo Mengecek Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python tidak ditemukan. Install Python 3.9+ terlebih dahulu.
    pause
    exit /b 1
)
echo Menginstall dependensi...
pip install -r requirements.txt --quiet
echo Menjalankan game...
python main.py
pause
