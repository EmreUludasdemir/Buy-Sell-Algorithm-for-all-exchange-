# US Indices Backtest

- Generated: `2026-02-19T14:19:15`
- Strategy params: `{'donchian_w': 20, 'exit_ma': 20, 'ma_fast': 10, 'ma_mid': 20, 'ma_slow': 50, 'atr_stop_mult': 2.0, 'use_trailing': True}`
- Backtest config: `{'fee_bps': 10.0, 'slippage_bps': 5.0, 'initial_capital': 100000.0, 'position_size_pct': 1.0}`
- Walk-forward config: `{'train_days': 200, 'test_days': 50, 'step_days': 50, 'warmup_days': 60, 'min_windows': 2, 'min_trades': 2}`

| Index | Ticker | Data Range | Rows | Buy&Hold % | Strategy % | OOS % | OOS MaxDD % | OOS Trades | Windows |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| NASDAQ | ^IXIC | 2016-02-19 -> 2026-02-18 | 2514 | 405.14 | 45.66 | -1.49 | -1.49 | 5 | 45 |
| SP500 | ^GSPC | 2016-02-19 -> 2026-02-18 | 2514 | 258.82 | 6.38 | -0.30 | -0.30 | 1 | 45 |