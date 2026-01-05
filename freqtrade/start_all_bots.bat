@echo off
echo ========================================
echo EPA Trading Bot - Multi-Bot Starter
echo ========================================
echo.

cd /d "%~dp0"

echo Starting all 3 bots...
docker compose up -d

echo.
echo Bot Status:
docker compose ps

echo.
echo ========================================
echo Bot 1 (BTC/ETH):    http://localhost:8080
echo Bot 2 (Altcoins):   http://localhost:8081
echo Bot 3 (Paper):      http://localhost:8082
echo ========================================
echo.
echo Use 'docker compose logs -f' to view logs
echo Use 'docker compose down' to stop all bots
pause
