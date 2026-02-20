# Top-3 Hyperopt Raporu

- Run: `top3_hyperopt_20260220_151216`
- Mod: `spot`
- Timeframe: `4h`
- Timerange: `20220101-20240831`
- Pairler: `BTC/USDT ETH/USDT BNB/USDT SOL/USDT XRP/USDT`

## Performans Siralama (Optimize Parametrelerle Backtest)

| Rank | Strategy | Score | Return% | PF | Sharpe | MaxDD% | Trades | Win% |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | MACDVSupertrendStrategy | 0.594 | 43.67 | 1.41 | 0.43 | 14.78 | 203 | 45.8 |
| 2 | EPASimpleTrend | 0.361 | 16.52 | 1.17 | 0.22 | 31.17 | 204 | 46.1 |
| 3 | RegimeStrategy | 0.273 | 7.01 | 1.04 | 0.13 | 19.09 | 572 | 17.1 |

## Hyperopt Parametre Dosyalari

- `MACDVSupertrendStrategy`: `user_data/strategies/MACDVSupertrendStrategy.json`
- `EPASimpleTrend`: `user_data/strategies/EPASimpleTrend.json`
- `RegimeStrategy`: `user_data/strategies/RegimeStrategy.json`

## Backtest Artefactlari

- `MACDVSupertrendStrategy`: `user_data/backtest_results/backtest-result-2026-02-20_12-20-05.zip` (`backtest-result-2026-02-20_12-20-05.meta.json`)
- `EPASimpleTrend`: `user_data/backtest_results/backtest-result-2026-02-20_12-19-46.zip` (`backtest-result-2026-02-20_12-19-46.meta.json`)
- `RegimeStrategy`: `user_data/backtest_results/backtest-result-2026-02-20_12-20-28.zip` (`backtest-result-2026-02-20_12-20-28.meta.json`)
