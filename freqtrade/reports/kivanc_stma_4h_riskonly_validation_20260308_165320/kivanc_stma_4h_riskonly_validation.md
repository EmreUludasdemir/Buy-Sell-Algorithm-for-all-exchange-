# Kivanc STMA 4H Risk-Only Hyperopt Validation

Bu ?al??ma mevcut 4h giri? parametrelerini sabit tutup yaln?z `roi + stoploss + trailing` alanlar?n? optimize eder.

Optimum risk parametreleri:
```json
{
  "minimal_roi": {
    "0": 0.138,
    "1105": 0.086,
    "2904": 0.051,
    "5842": 0
  },
  "stoploss": -0.078,
  "trailing_stop": true,
  "trailing_stop_positive": 0.132,
  "trailing_stop_positive_offset": 0.167,
  "trailing_only_offset_is_reached": true
}
```

| Senaryo | Tarih | Getiri | 1000 USDT Sonucu | Islem | Win Rate | PF | MaxDD | Market | Ortalama Tutus |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| train_2022_2025 | 2022-01-01 00:00:00 -> 2025-12-31 00:00:00 | 13.70% | 1136.96 | 319 | 46.71% | 1.07 | 17.16% | 45.98% | 2 days, 22:41:00 |
| bear_2022 | 2022-05-01 00:00:00 -> 2022-12-31 00:00:00 | 12.51% | 1125.12 | 56 | 55.36% | 1.37 | 12.49% | -56.16% | 2 days, 13:51:00 |
| recovery_2023 | 2023-01-01 00:00:00 -> 2023-12-31 00:00:00 | -3.63% | 963.72 | 87 | 42.53% | 0.91 | 17.16% | 253.94% | 3 days, 0:36:00 |
| bull_2024 | 2024-01-01 00:00:00 -> 2024-12-31 00:00:00 | 8.26% | 1082.61 | 74 | 44.59% | 1.22 | 14.56% | 121.61% | 2 days, 21:08:00 |
| choppy_2025 | 2025-01-01 00:00:00 -> 2025-12-31 00:00:00 | -0.91% | 990.93 | 83 | 48.19% | 0.98 | 11.61% | -8.10% | 3 days, 2:04:00 |
| ytd_2026 | 2026-01-01 00:00:00 -> 2026-03-01 00:00:00 | 5.92% | 1059.20 | 12 | 58.33% | 2.70 | 3.33% | -27.07% | 3 days, 10:40:00 |
| full_2022_2026 | 2022-01-01 00:00:00 -> 2026-03-01 00:00:00 | 23.36% | 1233.65 | 333 | 47.45% | 1.12 | 17.16% | 7.88% | 2 days, 23:21:00 |
