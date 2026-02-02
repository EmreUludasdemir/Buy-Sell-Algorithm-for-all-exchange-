# Winner Scanner - Lone Stock Trader Methodology

ABD + BIST için otomatik hisse tarama ve walk-forward backtest sistemi.

## 🎯 Amaç

Twitter'daki "gazlı" trade ipuçlarını **ölçülebilir kurallara** çevirmek:
- Survivorship bias'ı elemek
- "Clean chart", "basket momentum" gibi belirsiz kavramları kodlamak
- Walk-forward ile overfit riskini azaltmak

## 📊 Kurallar (Thread'den)

### A) Volatilite Filtreleri
- **ADR% ≥ 1.5**: Gün içi volatilite
- **ATR% ≥ 1.5**: Gap dahil volatilite
- **Likidite**: Ortalama hacim eşiği

### B) Relative Strength (Liderlik)
- RS slope: Benchmark'a göre performans trendi
- RS 50MA: RS line 50 günlük ortalamanın üstünde mi?

### C) Yapı Filtreleri
- **MA Squeeze**: 10/20/50 MA sıkışması (≤ %15)
- **Weekly Base**: Haftalık konsolidasyon kalitesi
- **MA Stack**: Bullish 10 > 20 > 50 düzeni

### D) Walk-Forward Backtest
- Rolling out-of-sample test
- Train/test split her pencerede
- Overfit'e karşı en iyi panzehir

## 🚀 Kurulum

```bash
pip install pandas numpy yfinance pyyaml
```

## 💻 Kullanım

### Hızlı Tarama (Walk-forward olmadan)

```bash
# US Market - Top 15
python -m src.scanner.cli --market us --top 15 --no-walkforward

# BIST Market - Top 10
python -m src.scanner.cli --market bist --top 10 --no-walkforward
```

### Detaylı Tarama (Metriklerle)

```bash
python -m src.scanner.cli --market us --top 20 --detailed --no-walkforward
```

### Walk-Forward ile Tam Tarama

```bash
python -m src.scanner.cli --market us --top 10
```

### Sonuçları Dosyaya Kaydet

```bash
python -m src.scanner.cli --market us --top 20 --no-walkforward --output picks.txt
```

### Özel Filtre Değerleri

```bash
python -m src.scanner.cli --market us \
  --adr-min 3.0 \
  --atr-min 4.0 \
  --squeeze-max 0.05 \
  --top 10
```

## 📁 Proje Yapısı

```
src/scanner/
├── __init__.py
├── cli.py              # CLI arayüzü
├── indicators.py       # Teknik göstergeler (ADR, ATR, RS, MA squeeze, vb.)
├── providers.py        # Veri kaynakları (yfinance, borsapy placeholder)
├── scanner.py          # Ana tarama motoru
├── strategy.py         # Strateji ve backtest engine
├── walkforward.py      # Walk-forward backtester
└── baskets/
    ├── __init__.py
    ├── baskets.py      # Basket/tema yönetimi
    ├── us_baskets.yaml # US tema grupları
    └── bist_baskets.yaml # BIST tema grupları
```

## 📈 Çıktı Örneği

```
========================================
TOP 15 (US)
========================================
 1. META
 2. CLSK
 3. ZM
 4. NVDA
 5. MARA
 6. GOOGL
 7. IONQ
 8. SMCI
 9. AMZN
10. OKTA
11. TSLA
12. MDB
13. ROKU
14. MRVL
15. CRWD
```

## ⚙️ Konfigürasyon

### ScanConfig Preset'leri

```python
from src.scanner.scanner import ScanConfig

# Agresif (küçük hisseler için)
AGGRESSIVE = ScanConfig(
    adr_min=4.0,
    atr_min=5.0,
    squeeze_max=0.03,
)

# Dengeli (büyük+küçük karışık)
BALANCED = ScanConfig(
    adr_min=1.5,
    atr_min=1.5,
    squeeze_max=0.15,
)
```

## 🔮 Gelecek Planları

- [ ] borsapy entegrasyonu (daha iyi BIST verisi)
- [ ] Canlı sinyal uyarısı (Telegram/Discord)
- [ ] Portföy yönetimi modülü
- [ ] Otomatik günlük tarama (cron/scheduler)

## ⚠️ Uyarı

Bu sistem **"para kazandıracak" garantisi vermez**. Amacı:
1. Çöpü elemek
2. İstatistikli aday çıkarmak
3. Walk-forward ile overfit riskini azaltmak

**Gerçek para kazanma** için:
- Evren kalitesi
- Veri kalitesi
- Risk yönetimi
- Disiplin

---

*"Para kazandırsın yeter" değil, "doğru karar verebilmek için bilgi" mantığıyla yaklaşın.*
