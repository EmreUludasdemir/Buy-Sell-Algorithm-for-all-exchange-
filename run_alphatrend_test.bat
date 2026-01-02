@echo off
REM Quick test script for AlphaTrend validation
REM Runs the validation test inside Freqtrade Docker container

echo ============================================================
echo ALPHATREND VALIDATION TEST
echo ============================================================
echo.

echo Checking Docker status...
docker ps >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Docker is running. Starting test...
echo.

REM Copy test script to container and run it
docker compose exec -T freqtrade python3 /freqtrade/test_alphatrend.py

echo.
echo ============================================================
echo Test complete. Review output above.
echo ============================================================
pause
