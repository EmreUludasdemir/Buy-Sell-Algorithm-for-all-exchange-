# Kivanc STMA 1D Regime Filter Research

## Summary

- The strategy now exposes an optional regime filter layer and research-only short-side signals.
- Production remains daily spot and long-only.
- A fresh 1D buy hyperopt with the new filter surface did not beat the current production profile.

## Baseline Validation

- Full timerange: `20220101-20260301`
- Baseline result: `+191.78%`
- Starting balance: `1000 USDT`
- Final balance: `2917.811 USDT`
- Trades: `34`
- Profit factor: `3.35`
- Max drawdown: `27.86%`

## Fresh 1D Hyperopt Result

- Hyperopt result file: `strategy_KivancSupertrendedMovingAverages1D_2026-03-09_13-48-39.fthypt`
- Best result matched baseline performance exactly: `+191.78%`
- The winning epoch kept `use_regime_filter=false`, so the new entry filter was not selected as beneficial.

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

## Interpretation

- The new regime filter hooks are implemented and ready for further research.
- On the current daily spot dataset, the filter did not improve the best achievable result.
- The repository should keep the current production profile for now.

## Short-Side Note

- `research_short_signal` is now computed inside the strategy for analysis.
- Real short execution is still disabled because the repository config is `spot`.
- To validate long+short properly, the next step is a separate futures research config with futures pairs such as `BTC/USDT:USDT` and downloaded futures OHLCV.
