# Rollback Coklu Market Kosulu Backtest

- Run: `top3_rollback_multicond_20260220_162623`
- Mod: `stabil strateji surumleri` (LEAN degisiklikleri geri alindi)

## Bull (`20231001-20240315`)

| Rank | Strategy | Return% | Final (1000$) | PF | Sharpe | MaxDD% | Trades | Win% | Score |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | EPASimpleTrend | 52.82 | $1528.17 | 3.83 | 3.53 | 4.95 | 71 | 60.6 | 0.975 |
| 2 | RegimeStrategy | 27.93 | $1279.33 | 2.13 | 2.41 | 5.89 | 88 | 27.3 | 0.910 |
| 3 | MACDVSupertrendStrategy | 16.81 | $1168.08 | 1.66 | 1.22 | 10.29 | 62 | 54.8 | 0.709 |

## Bear (`20220501-20221231`)

| Rank | Strategy | Return% | Final (1000$) | PF | Sharpe | MaxDD% | Trades | Win% | Score |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | MACDVSupertrendStrategy | -0.79 | $992.10 | 0.95 | -0.04 | 4.45 | 31 | 41.9 | 0.268 |
| 2 | RegimeStrategy | -0.15 | $998.50 | 1.00 | -0.01 | 13.98 | 119 | 18.5 | 0.229 |
| 3 | EPASimpleTrend | -26.73 | $732.72 | 0.26 | -1.36 | 29.61 | 34 | 20.6 | 0.052 |

## Sideways (`20240401-20240831`)

| Rank | Strategy | Return% | Final (1000$) | PF | Sharpe | MaxDD% | Trades | Win% | Score |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | RegimeStrategy | -3.01 | $969.85 | 0.91 | -0.40 | 11.31 | 104 | 14.4 | 0.225 |
| 2 | MACDVSupertrendStrategy | -6.97 | $930.31 | 0.45 | -0.90 | 7.48 | 26 | 26.9 | 0.153 |
| 3 | EPASimpleTrend | -6.71 | $932.91 | 0.40 | -0.73 | 8.29 | 19 | 31.6 | 0.138 |

## Recovery (`20230101-20230930`)

| Rank | Strategy | Return% | Final (1000$) | PF | Sharpe | MaxDD% | Trades | Win% | Score |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | MACDVSupertrendStrategy | 30.44 | $1304.35 | 2.05 | 0.84 | 8.11 | 64 | 46.9 | 0.780 |
| 2 | EPASimpleTrend | 14.30 | $1143.03 | 1.56 | 0.59 | 11.78 | 60 | 50.0 | 0.542 |
| 3 | RegimeStrategy | 2.06 | $1020.62 | 1.04 | 0.12 | 17.18 | 189 | 15.3 | 0.255 |

## Choppy-2025 (`20250101-20251231`)

| Rank | Strategy | Return% | Final (1000$) | PF | Sharpe | MaxDD% | Trades | Win% | Score |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | MACDVSupertrendStrategy | -4.99 | $950.05 | 0.82 | -0.24 | 9.39 | 67 | 41.8 | 0.216 |
| 2 | RegimeStrategy | -15.65 | $843.54 | 0.76 | -1.09 | 23.06 | 232 | 15.1 | 0.152 |
| 3 | EPASimpleTrend | -20.43 | $795.66 | 0.63 | -0.57 | 20.55 | 69 | 40.6 | 0.125 |

## Genel Ortalama Siralama (5 Senaryo)

| Rank | Strategy | Avg Return% | Avg Final (1000$) | Avg PF | Avg Sharpe | Avg MaxDD% | Total Trades | Avg Score |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | MACDVSupertrendStrategy | 6.90 | $1068.98 | 1.19 | 0.18 | 7.95 | 250 | 0.425 |
| 2 | EPASimpleTrend | 2.65 | $1026.50 | 1.33 | 0.29 | 15.04 | 253 | 0.367 |
| 3 | RegimeStrategy | 2.24 | $1022.37 | 1.16 | 0.21 | 14.28 | 732 | 0.354 |

## Lean vs Rollback Fark Ozeti

| Scenario | Strategy | Rollback Ret% | Lean Ret% | Delta Ret% | Rollback Score | Lean Score | Delta Score |
|---|---|---:|---:|---:|---:|---:|---:|
| bear | EPASimpleTrend | -26.73 | -27.46 | +0.73 | 0.052 | 0.040 | +0.012 |
| bear | MACDVSupertrendStrategy | -0.79 | -12.08 | +11.29 | 0.268 | 0.134 | +0.134 |
| bear | RegimeStrategy | -0.15 | -18.09 | +17.95 | 0.229 | 0.145 | +0.085 |
| bull | EPASimpleTrend | 52.82 | 22.44 | +30.38 | 0.975 | 0.812 | +0.164 |
| bull | MACDVSupertrendStrategy | 16.81 | 6.47 | +10.34 | 0.709 | 0.467 | +0.242 |
| bull | RegimeStrategy | 27.93 | 75.42 | -47.49 | 0.910 | 0.894 | +0.017 |
| choppy2025 | EPASimpleTrend | -20.43 | -21.98 | +1.55 | 0.125 | 0.113 | +0.012 |
| choppy2025 | MACDVSupertrendStrategy | -4.99 | -12.50 | +7.51 | 0.216 | 0.140 | +0.076 |
| choppy2025 | RegimeStrategy | -15.65 | -3.66 | -11.99 | 0.152 | 0.193 | -0.041 |
| recovery | EPASimpleTrend | 14.30 | -1.15 | +15.45 | 0.542 | 0.225 | +0.317 |
| recovery | MACDVSupertrendStrategy | 30.44 | 2.33 | +28.10 | 0.780 | 0.293 | +0.487 |
| recovery | RegimeStrategy | 2.06 | -12.66 | +14.72 | 0.255 | 0.171 | +0.083 |
| sideways | EPASimpleTrend | -6.71 | -12.12 | +5.42 | 0.138 | 0.094 | +0.043 |
| sideways | MACDVSupertrendStrategy | -6.97 | -14.05 | +7.08 | 0.153 | 0.043 | +0.110 |
| sideways | RegimeStrategy | -3.01 | -25.92 | +22.91 | 0.225 | 0.095 | +0.130 |
