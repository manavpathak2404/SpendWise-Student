@echo off
title SpendWise Student - Launcher
color 0b
echo ===================================================================
echo                     SPENDWISE STUDENT LAUNCHER
echo              Personal Finance Tracker for Students
echo ===================================================================
echo.

:: Step 1: Check if MySQL is running
echo [1/3] Checking MySQL database status...
netstat -ano | findstr :3306 >nul
if %errorlevel% neq 0 (
    echo [INFO] Starting MySQL from XAMPP...
    if exist "C:\xampp\mysql\bin\mysqld.exe" (
        start "" "C:\xampp\mysql\bin\mysqld.exe" --defaults-file="C:\xampp\mysql\bin\my.ini" --standalone
        timeout /t 3 /nobreak >nul
        echo [OK] MySQL started successfully.
    ) else (
        echo [WARNING] Please ensure MySQL is started in XAMPP Control Panel.
    )
) else (
    echo [OK] MySQL is active and listening on port 3306.
)

echo.
:: Step 2: Open website in default browser
echo [2/3] Launching web browser at http://127.0.0.1:5000 ...
start http://127.0.0.1:5000

echo.
:: Step 3: Run the Flask application
echo [3/3] Starting SpendWise Student Python server...
echo -------------------------------------------------------------------
echo Application is running! Keep this window open while using the site.
echo Press Ctrl + C to stop the server when you are finished.
echo -------------------------------------------------------------------
cd /d "%~dp0"
python app.py

pause
