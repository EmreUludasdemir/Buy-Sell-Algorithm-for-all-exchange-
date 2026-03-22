# Kivanc Futures 1D Risk Hyperopt Validation

Decision: `rejected_no_improvement`
Hyperopt file: `strategy_KivancSupertrendedMovingAveragesFutures1D_2026-03-12_08-03-00.fthypt`

## Baseline

- Profit: `271.54%`
- Final balance: `3715.37`
- Trades: `62`
- Profit factor: `2.75`
- MaxDD: `18.72%`

## Candidate

- Profit: `77.71%`
- Final balance: `1777.13`
- Trades: `62`
- Profit factor: `2.15`
- MaxDD: `19.34%`

## Candidate Params

```json
{
  "params": {
    "adx_threshold": 20,
    "atr_multiplier": 1.9,
    "atr_period": 29,
    "ma_length": 225,
    "ma_type": "TSF",
    "regime_ema_length": 200,
    "regime_slope_lookback": 10,
    "regime_slope_min": 0.0,
    "t3_volume_factor": 0.2,
    "use_adx_filter": false,
    "use_builtin_atr": false,
    "use_regime_filter": false
  },
  "minimal_roi": {
    "0": 1.062,
    "7691": 0.366,
    "24262": 0.156,
    "36397": 0
  },
  "stoploss": -0.322,
  "trailing_stop": true,
  "trailing_stop_positive": 0.288,
  "trailing_stop_positive_offset": 0.388,
  "trailing_only_offset_is_reached": true,
  "max_open_trades": 4
}
```
