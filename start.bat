@echo off
echo.
echo  ================================================================
echo   EcoPlant Pro - Starting Full-Stack Application
echo  ================================================================
echo.
echo  Open your browser at: http://localhost:5000
echo.
cd /d "%~dp0backend"
node server.js
pause
