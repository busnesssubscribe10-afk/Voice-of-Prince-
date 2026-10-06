@echo off
title YouTube Channel One-Time Authentication
color 0E

echo ========================================================
echo        YouTube Channel One-Time Login Authentication
echo               Channel: Rohmot YT (রহমত ওয়াইটি)
echo ========================================================
echo.
echo [*] Opening Google OAuth login in your browser...
echo [*] Please select your YouTube Google Account and click "Allow/Continue".
echo.

python youtube_uploader.py

echo.
echo ========================================================
if exist token.json (
    echo [SUCCESS] token.json has been created successfully!
    echo Your YouTube authentication is complete and portable.
) else (
    echo [!] token.json was not created. Please check the error above.
)
echo ========================================================
echo.
pause
