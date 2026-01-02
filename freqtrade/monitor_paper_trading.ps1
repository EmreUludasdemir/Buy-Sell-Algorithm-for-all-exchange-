# EPA Paper Trading Monitor
# Usage: .\monitor_paper_trading.ps1

param(
    [switch]$Quick,
    [switch]$Detailed,
    [switch]$Status
)

$ErrorActionPreference = "Stop"

Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  EPA Paper Trading Monitor v1.0        ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if Docker container is running
Write-Host "🔍 Checking bot status..." -ForegroundColor Yellow
$containerStatus = docker ps --filter "name=freqtrade" --format "{{.Status}}"

if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrEmpty($containerStatus)) {
    Write-Host "❌ Bot is NOT running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "To start paper trading:" -ForegroundColor Yellow
    Write-Host "cd freqtrade" -ForegroundColor White
    Write-Host "docker-compose up -d" -ForegroundColor White
    exit 1
}

Write-Host "✅ Bot is running: $containerStatus" -ForegroundColor Green
Write-Host ""

# Quick Status Check
if ($Quick -or !$Detailed) {
    Write-Host "📊 Quick Status Check" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    
    $profit = docker exec freqtrade freqtrade trade-stats -c /freqtrade/user_data/config_paper_trading.json 2>&1 | Select-String "Total profit"
    $trades = docker exec freqtrade freqtrade trade-stats -c /freqtrade/user_data/config_paper_trading.json 2>&1 | Select-String "Total trades"
    $winRate = docker exec freqtrade freqtrade trade-stats -c /freqtrade/user_data/config_paper_trading.json 2>&1 | Select-String "Win rate"
    
    Write-Host $profit
    Write-Host $trades
    Write-Host $winRate
    Write-Host ""
}

# Detailed Status
if ($Detailed) {
    Write-Host "📈 Detailed Performance Report" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    
    docker exec freqtrade freqtrade profit -c /freqtrade/user_data/config_paper_trading.json
    
    Write-Host ""
    Write-Host "📋 Current Open Trades" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    
    docker exec freqtrade freqtrade show_trades --open -c /freqtrade/user_data/config_paper_trading.json
    
    Write-Host ""
}

# Status Flag - Just container health
if ($Status) {
    Write-Host "🏥 Container Health" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    
    docker stats freqtrade --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
    
    Write-Host ""
    Write-Host "📝 Recent Logs (last 20 lines)" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    
    docker logs freqtrade --tail 20
}

Write-Host ""
Write-Host "🔗 Quick Commands:" -ForegroundColor Yellow
Write-Host "  View UI:     http://localhost:8080" -ForegroundColor White
Write-Host "  Username:    freqtrade" -ForegroundColor White
Write-Host "  Password:    EPAPaperTrade2026!" -ForegroundColor White
Write-Host ""
Write-Host "  Full Stats:  .\monitor_paper_trading.ps1 -Detailed" -ForegroundColor White
Write-Host "  Logs:        .\monitor_paper_trading.ps1 -Status" -ForegroundColor White
Write-Host "  Stop Bot:    docker-compose down" -ForegroundColor White
Write-Host ""

# Check if we should alert
$profitMatch = docker exec freqtrade freqtrade profit -c /freqtrade/user_data/config_paper_trading.json 2>&1 | Select-String "Absolute profit"

if ($profitMatch) {
    $profitValue = $profitMatch -replace '.*Absolute profit.*?(-?\d+\.?\d*)\s*USDT.*', '$1'
    
    if ([double]$profitValue -lt -100) {
        Write-Host "⚠️  WARNING: Loss exceeds -$100 USDT!" -ForegroundColor Red
        Write-Host "    Consider reviewing strategy performance." -ForegroundColor Yellow
        Write-Host ""
    }
}

Write-Host "✅ Monitor check complete - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Green
