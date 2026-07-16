@echo off
echo.
echo ============================================================
echo   🌿 EcoPlant Pro — Python/FastAPI Backend
echo ============================================================
echo.

REM Install Python dependencies
echo [1/2] Installing Python dependencies...
pip install -r python-backend\requirements.txt

echo.
echo [2/2] Starting FastAPI server on http://localhost:5000
echo       API Docs: http://localhost:5000/docs
echo.

cd python-backend
uvicorn main:app --reload --port 5000 --host 0.0.0.0
