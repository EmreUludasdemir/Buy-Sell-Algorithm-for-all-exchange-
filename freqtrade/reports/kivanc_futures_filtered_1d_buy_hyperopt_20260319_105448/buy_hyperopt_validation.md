# Kivanc Filtered Futures 1D Buy Hyperopt Validation

Decision: `rejected_no_improvement`
Hyperopt file: `strategy_KivancSupertrendedMovingAveragesFutures1D_2026-03-19_10-55-18.fthypt`

## Baseline

- Profit: `271.54%`
- Final balance: `3715.37`
- Trades: `62`
- Profit factor: `2.75`
- MaxDD: `18.72%`

## Candidate

- Profit: `46.22%`
- Final balance: `1462.23`
- Trades: `36`
- Profit factor: `1.38`
- MaxDD: `26.61%`

## Candidate Params

```json
{
  "params": {
    "adx_threshold": 14,
    "atr_multiplier": 2.2,
    "atr_period": 30,
    "long_stake_multiplier": 1.66,
    "ma_length": 100,
    "ma_type": "VAR",
    "regime_ema_length": 252,
    "regime_slope_lookback": 7,
    "regime_slope_min": 0.052,
    "rolling_sharpe_threshold": -0.41,
    "rolling_sharpe_window": 36,
    "short_stake_multiplier": 1.16,
    "t3_volume_factor": 0.3,
    "tsmom_lookback": 189,
    "tsmom_threshold": 0.093,
    "use_adx_filter": false,
    "use_builtin_atr": false,
    "use_regime_filter": false,
    "use_rolling_sharpe_filter": false,
    "use_tsmom_filter": false
  },
  "minimal_roi": {
    "0": 1.0
  },
  "stoploss": -0.2,
  "trailing_stop": false,
  "trailing_stop_positive": null,
  "trailing_stop_positive_offset": 0.0,
  "trailing_only_offset_is_reached": false,
  "max_open_trades": 4
}
```
