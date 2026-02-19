# Core-5 Spot 3-Rejim Backtest Raporu

- Run klasoru: `c:\Users\Emre\Desktop\Buy-sell Algorithm\freqtrade\user_data\backtest_results\core5_3regime_20260219_140041`
- Uretim zamani: `2026-02-19T14:05:56`
- Beklenen dosya: `15` | Bulunan: `15`
- Eksik dosya: `0`

## Rejim Bazli Sonuclar

| Scenario | Strategy | Trades | Win% | Return% | PF | Sharpe | MaxDD% | Score |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| bull | EPASimpleTrend | 313 | 79.9 | 32.15 | 1.30 | 3.66 | 20.31 | 0.721 |
| bull | EMABreakoutVolume | 106 | 62.3 | 3.21 | 1.08 | 0.39 | 12.04 | 0.349 |
| bull | MACDVSupertrendStrategy | 70 | 77.1 | 5.48 | 1.27 | 0.83 | 4.10 | 0.527 |
| bull | RegimeStrategy | 86 | 24.4 | 26.68 | 2.19 | 2.31 | 3.40 | 0.916 |
| bull | RSI2Strategy | 137 | 81.0 | 5.82 | 1.21 | 1.12 | 10.52 | 0.543 |
| bear | EPASimpleTrend | 279 | 67.7 | -39.29 | 0.64 | -3.79 | 39.58 | 0.128 |
| bear | EMABreakoutVolume | 66 | 53.0 | -8.82 | 0.72 | -0.76 | 14.93 | 0.170 |
| bear | MACDVSupertrendStrategy | 35 | 65.7 | -3.31 | 0.77 | -0.31 | 5.40 | 0.227 |
| bear | RegimeStrategy | 105 | 17.1 | -15.59 | 0.62 | -1.48 | 18.40 | 0.132 |
| bear | RSI2Strategy | 103 | 68.9 | -16.59 | 0.53 | -1.96 | 22.38 | 0.106 |
| sideways | EPASimpleTrend | 157 | 67.5 | -17.51 | 0.73 | -2.51 | 17.51 | 0.159 |
| sideways | EMABreakoutVolume | 37 | 43.2 | -5.32 | 0.67 | -0.85 | 6.44 | 0.202 |
| sideways | MACDVSupertrendStrategy | 24 | 66.7 | -2.20 | 0.76 | -0.37 | 6.38 | 0.219 |
| sideways | RegimeStrategy | 100 | 13.0 | -16.21 | 0.54 | -2.64 | 16.21 | 0.126 |
| sideways | RSI2Strategy | 71 | 80.3 | -1.15 | 0.92 | -0.27 | 6.37 | 0.252 |

## Genel Risk-Ayarli Siralama

| Rank | Strategy | Score | Avg Return% | Avg PF | Avg Sharpe | Avg MaxDD% | Total Trades | BullScore | BearScore |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | RegimeStrategy | 0.392 | -1.71 | 1.12 | -0.60 | 12.67 | 291 | 0.916 | 0.132 |
| 2 | EPASimpleTrend | 0.336 | -8.22 | 0.89 | -0.88 | 25.80 | 749 | 0.721 | 0.128 |
| 3 | MACDVSupertrendStrategy | 0.324 | -0.01 | 0.93 | 0.05 | 5.29 | 129 | 0.527 | 0.227 |
| 4 | RSI2Strategy | 0.300 | -3.98 | 0.89 | -0.37 | 13.09 | 311 | 0.543 | 0.106 |
| 5 | EMABreakoutVolume | 0.240 | -3.64 | 0.82 | -0.40 | 11.14 | 209 | 0.349 | 0.170 |

## Ilk 2 Strateji: Kisa Neden

### 1. RegimeStrategy (WARN)
- En yuksek skor grubu: `0.392`
- Risk/Getiri dengesi: Avg PF `1.12`, Avg MaxDD `12.67%`, Avg Sharpe `-0.60`
- Rejim tutarliligi: Bull `0.916`, Bear `0.132`
- Kalite kriteri: PF>=1.2 `False`, MaxDD<=20% `True`, Trades>=30 `True`

### 2. EPASimpleTrend (WARN)
- En yuksek skor grubu: `0.336`
- Risk/Getiri dengesi: Avg PF `0.89`, Avg MaxDD `25.80%`, Avg Sharpe `-0.88`
- Rejim tutarliligi: Bull `0.721`, Bear `0.128`
- Kalite kriteri: PF>=1.2 `False`, MaxDD<=20% `False`, Trades>=30 `True`
