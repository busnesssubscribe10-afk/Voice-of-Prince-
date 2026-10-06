@echo off
chcp 65001 >nul
title YouTube Shorts Reaction Bot - Voice of Prince
color 0B

:loop
cls
echo ========================================================
echo        Running YouTube Shorts Automation Bot
echo              Channel: Voice of Prince
echo ========================================================
echo.
echo [*] Starting Telegram Bot...
echo [*] Press Ctrl+C in this window anytime to stop.
echo.

python bot.py

echo.
echo ========================================================
echo [!] Bot stopped or network disconnected.
echo [*] Auto-restarting in 5 seconds to keep bot alive...
echo ========================================================
echo.
timeout /t 5
goto loop
