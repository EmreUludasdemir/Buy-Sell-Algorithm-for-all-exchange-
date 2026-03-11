# Kivanc Futures 1D Risk Hyperopt Validation

Decision: `rejected_no_improvement`
Hyperopt file: `strategy_KivancSupertrendedMovingAveragesFutures1D_2026-03-11_13-44-28.fthypt`

## Baseline

- Profit: `239.95%`
- Final balance: `3399.46`
- Trades: `70`
- Profit factor: `2.33`
- MaxDD: `22.30%`

## Candidate

- Profit: `77.77%`
- Final balance: `1777.68`
- Trades: `80`
- Profit factor: `1.88`
- MaxDD: `18.68%`

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
    "0": 1.019,
    "9205": 0.323,
    "25776": 0.156,
    "40002": 0
  },
  "stoploss": -0.187,
  "trailing_stop": true,
  "trailing_stop_positive": 0.029,
  "trailing_stop_positive_offset": 0.09,
  "trailing_only_offset_is_reached": true,
  "max_open_trades": 4
}
```
