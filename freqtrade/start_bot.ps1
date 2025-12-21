# AI Trading Bot Başlatma Scripti
# PowerShell'de çalıştırın

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  AI-Powered Crypto Trading Bot" -ForegroundColor Cyan
Write-Host "  SMC + FinBERT + LSTM Integration" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

$PROJECT_DIR = "C:\Users\Emre\Desktop\Buy-sell Algorithm\Buy-Sell-Algorithm-for-all-exchange-"
$FREQTRADE_DIR = "$PROJECT_DIR\freqtrade"

# Check if AI service is already running
$aiServiceRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5555/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        $aiServiceRunning = $true
        Write-Host "[✓] AI Signal Service zaten çalışıyor" -ForegroundColor Green
    }
}
catch {
    $aiServiceRunning = $false
}

if (-not $aiServiceRunning) {
    Write-Host ""
    Write-Host "[1/3] AI Signal Service başlatılıyor..." -ForegroundColor Yellow
    Write-Host "  (FinBERT + LSTM modelleri yükleniyor, GPU kullanılacak)" -ForegroundColor Gray
    
    # Start AI service in background
    $pythonProcess = Start-Process -FilePath "python" -ArgumentList "-m uvicorn freqtrade.user_data.strategies.ai_signal_service:app --host 0.0.0.0 --port 5555" -WorkingDirectory $PROJECT_DIR -PassThru -WindowStyle Normal
    
    Write-Host "  AI Service PID: $($pythonProcess.Id)" -ForegroundColor Gray
    Write-Host "  Bekleyin, modeller yükleniyor..." -ForegroundColor Gray
    
    # Wait for service to be ready
    $maxRetries = 30
    $retryCount = 0
    while ($retryCount -lt $maxRetries) {
        Start-Sleep -Seconds 2
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:5555/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Host "  [✓] AI Signal Service hazır!" -ForegroundColor Green
                break
            }
        }
        catch {
            $retryCount++
        }
    }
}

Write-Host ""
Write-Host "[2/3] Freqtrade container kontrol ediliyor..." -ForegroundColor Yellow

Set-Location $FREQTRADE_DIR

# Check if container is already running
$containerStatus = docker compose ps --format json 2>$null | ConvertFrom-Json
if ($containerStatus -and $containerStatus.State -eq "running") {
    Write-Host "  [✓] Freqtrade zaten çalışıyor" -ForegroundColor Green
}
else {
    Write-Host "  Freqtrade başlatılıyor..." -ForegroundColor Gray
    docker compose up -d
    Write-Host "  [✓] Freqtrade başlatıldı" -ForegroundColor Green
}

Write-Host ""
Write-Host "[3/3] Sistem durumu kontrol ediliyor..." -ForegroundColor Yellow

# Wait a moment for everything to initialize
Start-Sleep -Seconds 3

# Check AI service
try {
    $aiHealth = Invoke-RestMethod -Uri "http://localhost:5555/health" -TimeoutSec 2
    Write-Host "  [✓] AI Service: $($aiHealth.status)" -ForegroundColor Green
}
catch {
    Write-Host "  [!] AI Service erişilemiyor" -ForegroundColor Yellow
}

# Check Freqtrade
try {
    $ftHealth = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/ping" -TimeoutSec 2
    Write-Host "  [✓] Freqtrade API: Running" -ForegroundColor Green
}
catch {
    Write-Host "  [!] Freqtrade API henüz hazır değil (normal, birkaç saniye bekleyin)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  🚀 BOT ÇALIŞIYOR!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Freqtrade Web UI: http://localhost:8080" -ForegroundColor White
Write-Host "   Kullanıcı: freqtrade" -ForegroundColor Gray
Write-Host "   Şifre: freqtrade123" -ForegroundColor Gray
Write-Host ""
Write-Host "🤖 AI Signal Service: http://localhost:5555/docs" -ForegroundColor White
Write-Host ""
Write-Host "📈 Strateji: SMCAIUltimateStrategy" -ForegroundColor White
Write-Host "   - SMC Patterns (Order Blocks, FVG, BOS/CHOCH)" -ForegroundColor Gray
Write-Host "   - FinBERT Sentiment (GPU)" -ForegroundColor Gray
Write-Host "   - LSTM Price Prediction" -ForegroundColor Gray
Write-Host ""
Write-Host "⚠️  PAPER TRADING modunda çalışıyor (gerçek para kullanılmıyor)" -ForegroundColor Yellow
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Durdurmak için:" -ForegroundColor Gray
Write-Host "  docker compose down" -ForegroundColor Cyan
Write-Host ""
