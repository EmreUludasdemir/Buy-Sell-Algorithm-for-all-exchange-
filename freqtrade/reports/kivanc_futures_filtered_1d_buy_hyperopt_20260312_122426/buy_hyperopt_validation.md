# Kivanc Filtered Futures 1D Buy Hyperopt Validation

Decision: `rejected_no_improvement`
Hyperopt file: `strategy_KivancSupertrendedMovingAveragesFutures1D_2026-03-12_12-24-48.fthypt`

## Baseline

- Profit: `271.54%`
- Final balance: `3715.37`
- Trades: `62`
- Profit factor: `2.75`
- MaxDD: `18.72%`

## Candidate

- Profit: `23.54%`
- Final balance: `1235.44`
- Trades: `44`
- Profit factor: `1.23`
- MaxDD: `45.94%`

## Candidate Params

```json
{
  "params": {
    "adx_threshold": 21,
    "atr_multiplier": 4.8,
    "atr_period": 24,
    "ma_length": 188,
    "ma_type": "ZLEMA",
    "regime_ema_length": 136,
    "regime_slope_lookback": 11,
    "regime_slope_min": 0.053,
    "t3_volume_factor": 0.5,
    "use_adx_filter": false,
    "use_builtin_atr": false,
    "use_regime_filter": false
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
