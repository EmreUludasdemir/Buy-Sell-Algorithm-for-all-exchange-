# Efloud Price Action Trading System

TradingView platformu icin gelistirilmis, @EfloudTheSurfer'in metodolojisine dayali kapsamli bir price action gostergesi.

## Ozellikler

### 1. Range Structure Engine (RH/RL/EQ)
- **Range High (RH)**: Belirlenen fiyat araliginin ust siniri - Direnç seviyesi
- **Range Low (RL)**: Belirlenen fiyat araliginin alt siniri - Destek seviyesi
- **Equilibrium (EQ)**: Orta nokta `(RH + RL) / 2` - Kritik karar bolgesi

### 2. Supply/Demand Zone Kutulari
- **Yesil Kutu (Demand Zone)**: Destek bolgesi - Long giris alani
- **Kirmizi Kutu (Supply Zone)**: Direnç bolgesi - Short giris alani
- **Mavi Kutu (EQ Zone)**: Denge bolgesi - Trend degisim sinyali

### 3. Giris Onay Paternleri

#### Swing Failure Pattern (SFP)
Fiyat bir swing high/low'un otesine fitil atar ancak onceki aralik icerisinde kapanir. Bu, breakout trader'lari yakalar ve donusum sinyali verir.

#### Breaker Block
Gecerli bir order block basarisiz oldugunda ve daha sonra karsi taraftan yeniden test edildiginde olusur. Piyasa yapisi degisimini gosterir.

#### Mitigation Block
Fiyat yeni bir yuksek (bearish) veya dusuk (bullish) olusturamadigi, sonra yapiyi degistirdigi bir donusum paterni.

### 4. Equal Highs/Lows (EQH/EQL) Likidite Haritalama
- **EQH (Esit Zirveler)**: Ayni seviyede birden fazla zirve - Bearish bias (stop hunt potansiyeli)
- **EQL (Esit Dipler)**: Ayni seviyede birden fazla dip - Bullish bias (stop hunt potansiyeli)
- ATR tabanli esitlik esigi
- Yapilandiriilabilir bar sonrasi otomatik silme

### 5. Multi-Timeframe Dashboard
| Zaman Dilimi | Fonksiyon | Kullanim |
|--------------|-----------|----------|
| Gunluk/Haftalik (HTF) | Trend yonu | RSI/OBV analizi; ana S/R tespiti |
| 4 Saat | Yapi onayi | Short pozisyon olusturma bolgesi |
| 1 Saat | Giris dogrulamasi | Breaker/Mitigation/SFP onayi |
| 15 Dakika | Giris rafine etme | LTF bullish/bearish yapi tespiti |

### 6. Opsiyonel Gostergeler (Sadece HTF)
- **RSI (14)**: 50 ustu = bullish momentum, 50 alti = bearish
- **OBV**: Hacim trend yonu karsilastirmasi
- **DMA (50 EMA)**: Trend yonu proxy'si

### 7. Risk/Odul Hesaplayici
- Otomatik stop loss yerlesimi (bolge sinirinin otesinde)
- R:R orani gosterimi (minimum 1:2 onerilen)
- RH/RL'de kismi kar alma seviyeleri

## Giris Kurallari

### Long Giris Kosullari (hepsi uyusmali)
1. Fiyat yesil/mavi talep bolgesine (destek kutusu) girer
2. HTF trendi bullish (Gunluk kapanis 50 EMA uzerinde veya RSI > 50)
3. LTF (1H veya 15M) bullish yapi gosterir (higher low olusumu)
4. SFP, Breaker retest veya Mitigation block ile onay
5. OBV yukari trendde (opsiyonel hacim onayi)

### Short Giris Kosullari (hepsi uyusmali)
1. Fiyat kirmizi arz bolgesine (direnç kutusu) girer
2. HTF trendi bearish (Gunluk kapanis 50 EMA altinda veya RSI < 50)
3. LTF (1H veya 15M) bearish yapi gosterir (lower high olusumu)
4. SFP, Breaker retest veya Mitigation block ile onay
5. OBV asagi trendde (opsiyonel hacim onayi)

### Cikis Protokolu
- Ilk hedef: Long icin RH, Short icin RL (kismi: %75)
- Ilk hedeften sonra stop'u giriste tasi
- Son hedef: Sonraki ana yapi seviyesi veya kalan %25'i takip et

## Alarm Kosullari

Gosterge asagidaki alarm kosullarini destekler:
- Fiyat talep bolgesine girer
- Fiyat arz bolgesine girer
- SFP olusumu tespit edildi
- EQ seviyesi kirildigi (bullish/bearish)
- Breaker block retesti
- EQH/EQL olusumu
- Long/Short giris confluence sinyalleri

## Kurulum

1. TradingView'i acin
2. Pine Editor'e gidin
3. `EfloudPriceAction.pine` dosyasinin icerigini yapistirin
4. "Add to Chart" butonuna tiklayin
5. Gosterge ayarlarindan tercihleri yapilandirin

## Ayarlar

### Yapi Ayarlari
- Pivot Lookback Period: Swing high/low tespiti icin geriye bakis bar sayisi
- Pivot Lookforward Period: Swing onayi icin ileriye bakis bar sayisi
- Zone Extension: Bolgerin kac bar boyunca uzatilacagi

### Zone Gorunumu
- Demand/Supply/EQ zone renkleri
- Cerceve kalinligi
- Etiket boyutu

### Pattern Tespiti
- SFP fitil/govde orani
- Breaker/Mitigation block gosterimi

### EQH/EQL Ayarlari
- Esitlik esigi (%)
- Suresi dolmus seviyelerin silinme suresi

### Dashboard
- Konum secimi
- HTF/LTF zaman dilimleri
- Gosterge durumu (RSI, OBV, DMA)

## Risk Yonetimi Felsefesi

Efloud'un temel uyarisi: *"ASLA tum paranizla girmeyin. Tuzak olabilir, proje basarisiz olabilir, BTC dusebilir, ani FUD olusabilir."*

**Portfoy Yapi Kurallari:**
- Ayri **Futures** ve **Spot** hesap bakiyeleri tutun
- Futures karlarini 2-3 yillik yatirimlar icin spot "kumbara"ya aktarin
- Futures'ta asiri buyume seanslarini onleyin
- "Evvuru" denemeler yerine tutarli kucuk yuzde kazanclarina odaklanin
- Portfoyde minimum **4+ coin**; maksimum = etkili sekilde izleyebildiginiz kadar

**Pozisyon Yonetimi:**
- RH hedeflerinde **kismi cikislar** (ornek: RH'da %42 kar realize edildi, %25 pozisyon acik kaldi)
- **Stop-to-entry** takibi: ilk hedeften sonra stop'u giris fiyatina tasiyin
- Kanaat yuksekse kazanan islemlerde minimum **%10 pozisyon** veya kar tutarin

## Lisans

Mozilla Public License 2.0

## Referans

@EfloudTheSurfer'in price action metodolojisi ve ICT Smart Money Concepts'e dayanmaktadir.
