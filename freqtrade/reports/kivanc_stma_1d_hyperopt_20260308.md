# Kivanc STMA 1D Hyperopt

## Best Parameters

```python
buy_params = {
    "atr_multiplier": 1.9,
    "atr_period": 29,
    "ma_length": 225,
    "ma_type": "TSF",
    "t3_volume_factor": 0.2,
    "use_builtin_atr": False,
}
```

## Regime Table

| Scenario | Profit | Trades | Winrate | PF | MaxDD |
|---|---:|---:|---:|---:|---:|
| `bear_2022` | `-14.18%` | 6 | `0.00%` | `0.00` | `14.18%` |
| `recovery_2023` | `+55.16%` | 9 | `77.78%` | `11.77` | `4.12%` |
| `bull_2024` | `+28.12%` | 8 | `50.00%` | `3.87` | `9.79%` |
| `choppy_2025` | `+35.54%` | 8 | `50.00%` | `3.14` | `8.18%` |
| `ytd_2026` | `0.00%` | 0 | `0.00%` | `0.00` | `0.00%` |
| `full_2022_2026` | `+191.78%` | 34 | `47.06%` | `3.35` | `27.86%` |

## Notes

- Full-period result: `1000 -> 2917.81 USDT`
- The model is strongest in recovery and trend-following conditions.
- Average hold time is about `82` days, so this is a slow swing system.
- Hard bear conditions remain the weakest regime and should be treated as the next improvement target.
