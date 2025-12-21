# Freqtrade + Smart Money Concepts Trading Bot

Bu dizin, **Freqtrade** trading botu ve **Smart Money Concepts (SMC/ICT)** stratejisi için gerekli dosyaları içerir.

## 🚀 Hızlı Başlangıç

### 1. Ön Gereksinimler

- [Docker Desktop](https://www.docker.com/products/docker-desktop) kurulu olmalı
- WSL2 etkinleştirilmiş olmalı
- Binance hesabı (API key için)

### 2. Kurulum

PowerShell'de çalıştırın:

```powershell
cd "C:\Users\Emre\Desktop\Buy-sell Algorithm\Buy-Sell-Algorithm-for-all-exchange-\freqtrade"
.\setup_freqtrade.ps1
```

### 3. Binance API Key

1. Binance'e giriş yapın
2. [API Management](https://www.binance.com/en/my/settings/api-management) sayfasına gidin
3. Yeni API key oluşturun
4. **Sadece** şu izinleri verin:
   - ✅ Enable Reading
   - ✅ Enable Spot & Margin Trading
   - ❌ Enable Withdrawals (KAPALI!)
5. IP whitelist ekleyin (güvenlik için)

### 4. Konfigürasyon

`user_data/config.json` dosyasını düzenleyin:

```json
{
  "exchange": {
    "key": "BINANCE_API_KEY_BURAYA",
    "secret": "BINANCE_SECRET_KEY_BURAYA"
  }
}
```

### 5. Veri İndirme

```bash
docker compose run --rm freqtrade download-data \
    --pairs BTC/USDT ETH/USDT SOL/USDT \
    --timeframe 15m 1h 4h \
    --days 180
```

### 6. Backtest

```bash
docker compose run --rm freqtrade backtesting \
    --strategy SMCStrategy \
    --timeframe 15m \
    --timerange 20240601-
```

### 7. Paper Trading Başlatma

```bash
docker compose up -d
```

Web UI: http://localhost:8080

- Kullanıcı: `freqtrade`
- Şifre: `freqtrade123`

## 📁 Dosya Yapısı

```
freqtrade/
├── docker-compose.yml        # Docker konfigürasyonu
├── setup_freqtrade.ps1       # Kurulum scripti
├── README.md                 # Bu dosya
└── user_data/
    ├── config.json           # Bot konfigürasyonu
    ├── strategies/
    │   ├── SMCStrategy.py    # Ana SMC stratejisi
    │   └── smc_indicators.py # SMC indikatör modülü
    ├── data/                 # Tarihsel veri
    ├── backtest_results/     # Backtest sonuçları
    └── logs/                 # Log dosyaları
```

## 📊 SMC Strateji Mantığı

### Giriş Koşulları (Long)

1. **Trend Filter**: EMA50 > EMA200
2. **Market Structure**: Bullish BOS veya CHOCH
3. **Entry Zone**: Fiyat bullish Order Block içinde
4. **Confirmation**: FVG veya Liquidity sweep
5. **Volume**: Ortalama üzerinde hacim

### Çıkış Koşulları

- **Stop Loss**: Entry'nin 1.5 ATR altında
- **Take Profit**: Karşı FVG'ye kadar
- **Trailing Stop**: %1.5 profit sonrası aktif

## ⚠️ Risk Uyarısı

> **Bu sistem sadece eğitim amaçlıdır.** Kripto para ticareti yüksek risk içerir. Paper trading ile en az 4-8 hafta test etmeden gerçek para kullanmayın.

## 🔧 Faydalı Komutlar

```bash
# Container durumunu kontrol et
docker compose ps

# Logları görüntüle
docker compose logs -f

# Strateji listele
docker compose run --rm freqtrade list-strategies

# Hyperopt (optimizasyon)
docker compose run --rm freqtrade hyperopt \
    --strategy SMCStrategy \
    --hyperopt-loss SharpeHyperOptLoss \
    --epochs 100

# Container'ı durdur
docker compose down
```
