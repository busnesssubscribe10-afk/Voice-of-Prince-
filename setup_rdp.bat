@echo off
chcp 65001 >nul
title RDP Initial Setup - Voice of Prince Shorts Bot
color 0A

echo ========================================================
echo        RDP Initial Setup & Requirements Installer
echo              Channel: Voice of Prince
echo ========================================================
echo.

:: 1. Check Python
echo [*] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Python is NOT installed on this machine!
    echo [*] Downloading Python 3.12 installer...
    curl -o python_installer.exe https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe
    echo [*] Installing Python silently (Adding to PATH)...
    python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del python_installer.exe
    echo [✓] Python installed! Please restart this setup script if PATH is not loaded.
) else (
    echo [✓] Python is detected!
)

:: 2. Check FFmpeg
echo.
echo [*] Checking FFmpeg installation...
ffmpeg -version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] FFmpeg is NOT detected in PATH!
    echo [*] Installing FFmpeg via winget...
    winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements >nul 2>&1
    ffmpeg -version >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [!] Winget failed or not available. Downloading static FFmpeg build...
        curl -L -o ffmpeg.zip https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
        tar -xf ffmpeg.zip
        for /d %%D in (ffmpeg-*-essentials) do (
            copy "%%D\bin\ffmpeg.exe" ".\ffmpeg.exe" >nul 2>&1
            copy "%%D\bin\ffprobe.exe" ".\ffprobe.exe" >nul 2>&1
        )
        del ffmpeg.zip
        echo [✓] Standalone FFmpeg placed in current directory!
    )
) else (
    echo [✓] FFmpeg is ready!
)

:: 3. Install Python Dependencies
echo.
echo [*] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [*] Installing required Python libraries from requirements.txt...
pip install -r requirements.txt

echo.
echo [*] Updating yt-dlp to latest version...
pip install -U yt-dlp

:: 4. Verify Directories
echo.
echo [*] Creating necessary directories...
if not exist temp mkdir temp
if not exist assets mkdir assets
if not exist assets\fonts mkdir assets\fonts
if not exist assets\decorations mkdir assets\decorations

echo.
echo ========================================================
echo  [SUCCESS] All setup and installations completed!
echo  Starting Telegram Bot now...
echo ========================================================
echo.

:loop
echo [*] Running bot.py...
python bot.py
echo.
echo ========================================================
echo [!] Bot stopped. Auto-restarting in 5 seconds...
echo ========================================================
echo.
timeout /t 5
goto loop
