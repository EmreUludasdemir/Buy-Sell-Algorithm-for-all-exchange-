# Freqtrade + SMC Kurulum Scripti
# PowerShell'de çalıştırın

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Freqtrade + Smart Money Concepts Kurulumu" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Mevcut dizini kontrol et
$FREQTRADE_DIR = "C:\Users\Emre\Desktop\Buy-sell Algorithm\Buy-Sell-Algorithm-for-all-exchange-\freqtrade"
Set-Location $FREQTRADE_DIR

Write-Host ""
Write-Host "[1/5] Docker kurulum kontrolu..." -ForegroundColor Yellow

# Docker kurulu mu kontrol et
try {
    $dockerVersion = docker --version
    Write-Host "  ✓ Docker bulundu: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker bulunamadı!" -ForegroundColor Red
    Write-Host "  Docker Desktop'ı indirin: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[2/5] Docker Desktop çalışıyor mu kontrol ediliyor..." -ForegroundColor Yellow

# Docker daemon çalışıyor mu?
try {
    docker info | Out-Null
    Write-Host "  ✓ Docker daemon çalışıyor" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker daemon çalışmıyor!" -ForegroundColor Red
    Write-Host "  Docker Desktop'ı başlatın ve tekrar deneyin" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[3/5] Freqtrade Docker imajı çekiliyor..." -ForegroundColor Yellow
Write-Host "  (Bu birkaç dakika sürebilir)" -ForegroundColor Gray

docker pull freqtradeorg/freqtrade:stable
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Freqtrade imajı indirildi" -ForegroundColor Green
} else {
    Write-Host "  ✗ İmaj indirilemedi!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[4/5] smartmoneyconcepts kütüphanesi kuruluyor..." -ForegroundColor Yellow

# SMC kütüphanesini pip ile kur (Docker içinde de olacak ama test için)
pip install smartmoneyconcepts -q
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ smartmoneyconcepts kuruldu" -ForegroundColor Green
} else {
    Write-Host "  ! SMC kütüphanesi kurulamadı (fallback kullanılacak)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[5/5] Kurulum tamamlandı!" -ForegroundColor Green

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Sonraki Adımlar:" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Binance API key oluşturun:" -ForegroundColor White
Write-Host "   https://www.binance.com/en/my/settings/api-management" -ForegroundColor Gray
Write-Host "   - Sadece 'Read' ve 'Enable Spot Trading' izni verin" -ForegroundColor Gray
Write-Host "   - 'Enable Withdrawals' KAPALI olmalı!" -ForegroundColor Red
Write-Host ""
Write-Host "2. config.json'u düzenleyin:" -ForegroundColor White
Write-Host "   $FREQTRADE_DIR\user_data\config.json" -ForegroundColor Gray
Write-Host "   - 'key' ve 'secret' alanlarını doldurun" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Tarihsel veri indirin:" -ForegroundColor White
Write-Host "   docker compose run --rm freqtrade download-data --pairs BTC/USDT ETH/USDT --timeframe 15m 1h --days 90" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Backtest çalıştırın:" -ForegroundColor White
Write-Host "   docker compose run --rm freqtrade backtesting --strategy SMCStrategy --timeframe 15m" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. Paper trading başlatın:" -ForegroundColor White
Write-Host "   docker compose up -d" -ForegroundColor Cyan
Write-Host "   Web UI: http://localhost:8080 (freqtrade / freqtrade123)" -ForegroundColor Gray
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
