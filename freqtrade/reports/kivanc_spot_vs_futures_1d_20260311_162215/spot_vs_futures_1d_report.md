# Spot 1D vs Futures 1D Comparison

This report compares the current spot production strategy against the separate futures long/short research variant.
The fresh futures hyperopt candidate was not adopted because it did not improve the current futures baseline.

## Regime Comparison

| Scenario | Spot Profit | Futures Profit | Delta | Spot MaxDD | Futures MaxDD | Delta | Spot Trades | Futures Trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bear_2022 | -14.18% | -20.18% | -6.00% | 14.18% | 21.23% | 7.05% | 6 | 11 |
| recovery_2023 | 55.16% | 66.18% | 11.02% | 4.12% | 8.79% | 4.67% | 9 | 15 |
| bull_2024 | 28.12% | 4.45% | -23.67% | 9.79% | 24.44% | 14.65% | 8 | 17 |
| choppy_2025 | 35.54% | 52.46% | 16.92% | 8.18% | 9.26% | 1.08% | 8 | 20 |
| ytd_2026 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0 | 0 |
| full_2022_2026 | 191.78% | 239.95% | 48.17% | 27.86% | 22.30% | -5.56% | 34 | 70 |

## Full Period Snapshot

- Spot `2022-01-01 -> 2026-03-01`: `191.78%`, `PF 3.35`, `MaxDD 27.86%`, `Trades 34`
- Futures `2022-01-01 -> 2026-03-01`: `239.95%`, `PF 2.33`, `MaxDD 22.30%`, `Trades 70`
- Futures long contribution: `162.85%`
- Futures short contribution: `77.10%`

## Futures Hyperopt Decision

- Hyperopt mode: `buy` space only
- Candidate status: `rejected_no_improvement`
- Reason: best epoch matched current futures baseline full-period result, so the parameter file was left unchanged.

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
