# Time-Stop A/B Backtest (Rollback Baseline)

- Variant run: `top3_timestop_multicond_20260220_163733`
- Baseline run: `top3_rollback_multicond_20260220_162623`
- Degisiklik: `yalnizca custom_exit time-stop`

## Bull (`20231001-20240315`)

| Strategy | Base Ret% | TimeStop Ret% | Delta Ret% | Base Score | TimeStop Score | Delta Score | Base 1000$ | TimeStop 1000$ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RegimeStrategy | 27.93 | 28.64 | +0.71 | 0.910 | 0.928 | +0.018 | $1279.33 | $1286.39 |
| EPASimpleTrend | 52.82 | 31.98 | -20.84 | 0.975 | 0.724 | -0.251 | $1528.17 | $1319.75 |
| MACDVSupertrendStrategy | 16.81 | 7.32 | -9.49 | 0.709 | 0.625 | -0.084 | $1168.08 | $1073.18 |

## Bear (`20220501-20221231`)

| Strategy | Base Ret% | TimeStop Ret% | Delta Ret% | Base Score | TimeStop Score | Delta Score | Base 1000$ | TimeStop 1000$ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MACDVSupertrendStrategy | -0.79 | -2.85 | -2.06 | 0.268 | 0.234 | -0.034 | $992.10 | $971.48 |
| RegimeStrategy | -0.15 | -14.67 | -14.52 | 0.229 | 0.138 | -0.091 | $998.50 | $853.26 |
| EPASimpleTrend | -26.73 | -39.43 | -12.71 | 0.052 | 0.128 | +0.075 | $732.72 | $605.66 |

## Sideways (`20240401-20240831`)

| Strategy | Base Ret% | TimeStop Ret% | Delta Ret% | Base Score | TimeStop Score | Delta Score | Base 1000$ | TimeStop 1000$ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MACDVSupertrendStrategy | -6.97 | -2.37 | +4.59 | 0.153 | 0.213 | +0.060 | $930.31 | $976.26 |
| EPASimpleTrend | -6.71 | -17.67 | -10.96 | 0.138 | 0.154 | +0.016 | $932.91 | $823.32 |
| RegimeStrategy | -3.01 | -15.42 | -12.41 | 0.225 | 0.134 | -0.091 | $969.85 | $845.78 |

## Recovery (`20230101-20230930`)

| Strategy | Base Ret% | TimeStop Ret% | Delta Ret% | Base Score | TimeStop Score | Delta Score | Base 1000$ | TimeStop 1000$ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MACDVSupertrendStrategy | 30.44 | 11.90 | -18.54 | 0.780 | 0.594 | -0.186 | $1304.35 | $1118.97 |
| EPASimpleTrend | 14.30 | 1.10 | -13.20 | 0.542 | 0.223 | -0.319 | $1143.03 | $1011.02 |
| RegimeStrategy | 2.06 | 0.19 | -1.88 | 0.255 | 0.204 | -0.051 | $1020.62 | $1001.87 |

## Choppy-2025 (`20250101-20251231`)

| Strategy | Base Ret% | TimeStop Ret% | Delta Ret% | Base Score | TimeStop Score | Delta Score | Base 1000$ | TimeStop 1000$ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MACDVSupertrendStrategy | -4.99 | -8.32 | -3.33 | 0.216 | 0.175 | -0.041 | $950.05 | $916.78 |
| EPASimpleTrend | -20.43 | -26.61 | -6.18 | 0.125 | 0.164 | +0.039 | $795.66 | $733.87 |
| RegimeStrategy | -15.65 | -16.41 | -0.76 | 0.152 | 0.148 | -0.004 | $843.54 | $835.90 |

## Ortalama Etki (5 Senaryo)

| Strategy | Base->TimeStop Avg Delta Ret% | Base->TimeStop Avg Delta Score | TimeStop Avg Ret% | TimeStop Avg Score |
|---|---:|---:|---:|---:|
| RegimeStrategy | -5.77 | -0.044 | -3.54 | 0.310 |
| MACDVSupertrendStrategy | -5.76 | -0.057 | 1.13 | 0.368 |
| EPASimpleTrend | -12.78 | -0.088 | -10.13 | 0.279 |
