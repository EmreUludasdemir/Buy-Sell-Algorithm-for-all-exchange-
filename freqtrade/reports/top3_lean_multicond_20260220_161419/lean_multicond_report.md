# LEAN-Uyarlamali Coklu Market Kosulu Backtest

- Run: `top3_lean_multicond_20260220_161419`
- Stratejiler: `EPASimpleTrend`, `MACDVSupertrendStrategy`, `RegimeStrategy`
- Timeframe: `4h`
- Pairler: `BTC/USDT ETH/USDT BNB/USDT SOL/USDT XRP/USDT`

## Bull (`20231001-20240315`)

| Rank | Strategy | Return% | Final (1000$) | PF | Sharpe | MaxDD% | Trades | Win% | Score |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | RegimeStrategy | 75.42 | $1754.22 | 1.85 | 4.24 | 15.28 | 154 | 51.9 | 0.894 |
| 2 | EPASimpleTrend | 22.44 | $1224.42 | 1.74 | 2.49 | 9.66 | 117 | 45.3 | 0.812 |
| 3 | MACDVSupertrendStrategy | 6.47 | $1064.65 | 1.29 | 0.59 | 8.04 | 65 | 52.3 | 0.467 |

## Bear (`20220501-20221231`)

| Rank | Strategy | Return% | Final (1000$) | PF | Sharpe | MaxDD% | Trades | Win% | Score |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | RegimeStrategy | -18.09 | $819.05 | 0.72 | -1.11 | 24.35 | 118 | 29.7 | 0.145 |
| 2 | MACDVSupertrendStrategy | -12.08 | $879.17 | 0.47 | -0.80 | 12.08 | 36 | 41.7 | 0.134 |
| 3 | EPASimpleTrend | -27.46 | $725.38 | 0.20 | -2.40 | 27.46 | 53 | 20.8 | 0.040 |

## Sideways (`20240401-20240831`)

| Rank | Strategy | Return% | Final (1000$) | PF | Sharpe | MaxDD% | Trades | Win% | Score |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | RegimeStrategy | -25.92 | $740.78 | 0.48 | -2.86 | 25.92 | 81 | 24.7 | 0.095 |
| 2 | EPASimpleTrend | -12.12 | $878.76 | 0.28 | -1.41 | 12.12 | 25 | 28.0 | 0.094 |
| 3 | MACDVSupertrendStrategy | -14.05 | $859.49 | 0.07 | -1.97 | 14.05 | 23 | 21.7 | 0.043 |

## Recovery (`20230101-20230930`)

| Rank | Strategy | Return% | Final (1000$) | PF | Sharpe | MaxDD% | Trades | Win% | Score |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | MACDVSupertrendStrategy | 2.33 | $1023.33 | 1.09 | 0.09 | 10.98 | 64 | 37.5 | 0.293 |
| 2 | EPASimpleTrend | -1.15 | $988.49 | 0.97 | -0.08 | 13.59 | 92 | 39.1 | 0.225 |
| 3 | RegimeStrategy | -12.66 | $873.39 | 0.86 | -0.71 | 30.45 | 179 | 29.6 | 0.171 |

## Choppy-2025 (`20250101-20251231`)

| Rank | Strategy | Return% | Final (1000$) | PF | Sharpe | MaxDD% | Trades | Win% | Score |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | RegimeStrategy | -3.66 | $963.41 | 0.96 | -0.14 | 20.31 | 198 | 32.8 | 0.193 |
| 2 | MACDVSupertrendStrategy | -12.50 | $874.96 | 0.59 | -0.58 | 15.50 | 64 | 40.6 | 0.140 |
| 3 | EPASimpleTrend | -21.98 | $780.17 | 0.56 | -0.96 | 21.98 | 92 | 38.0 | 0.113 |

## Genel Ortalama Siralama (5 Senaryo)

| Rank | Strategy | Avg Return% | Avg Final (1000$) | Avg PF | Avg Sharpe | Avg MaxDD% | Total Trades | Avg Score |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | RegimeStrategy | 3.02 | $1030.17 | 0.97 | -0.12 | 23.26 | 730 | 0.300 |
| 2 | EPASimpleTrend | -8.06 | $919.44 | 0.75 | -0.47 | 16.96 | 379 | 0.257 |
| 3 | MACDVSupertrendStrategy | -5.97 | $940.32 | 0.70 | -0.54 | 12.13 | 252 | 0.216 |
