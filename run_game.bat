@echo off
setlocal

where py >nul 2>nul
if %errorlevel%==0 (
    py -m pip install -r requirements.txt
    py Space_war.py
    goto :end
)

where python >nul 2>nul
if %errorlevel%==0 (
    python -m pip install -r requirements.txt
    python Space_war.py
    goto :end
)

echo Python tidak ditemukan.
echo Install Python dari https://www.python.org/downloads/ lalu centang "Add python.exe to PATH".
pause

:end
endlocal
