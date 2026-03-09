# Kivanc STMA 4H Hyperopt Validation

Bu ?al??ma iki a?amada yap?ld?:
1. Sadece `buy` alan? ile 4h hyperopt denendi ve en iyi sonu? mevcut 1d parametrelerinin ayn?s? ??kt?.
2. `buy roi stoploss trailing` alanlar? ile ikinci 4h hyperopt ?al??t?r?ld?.

## Claimed Best 4H Hyperopt Epoch

- E?itim aral???: 2022-01-01 -> 2025-12-31
- Hyperopt i?i raporlanan sonu?: 8.13% | 1000 -> 1081.27 | PF 1.05 | MaxDD 18.33% | Trades 318

En iyi g?r?nen parametreler:
```json
{
  "buy": {
    "atr_multiplier": 0.1,
    "atr_period": 29,
    "ma_length": 134,
    "ma_type": "DEMA",
    "t3_volume_factor": 0.3,
    "use_builtin_atr": true
  },
  "minimal_roi": {
    "0": 0.456,
    "537": 0.146,
    "1765": 0.081,
    "5743": 0
  },
  "stoploss": -0.094,
  "trailing_stop": true,
  "trailing_stop_positive": 0.146,
  "trailing_stop_positive_offset": 0.224,
  "trailing_only_offset_is_reached": false,
  "max_open_trades": 4
}
```

## Reproduction Check

Ayn? parametreler ger?ek backtestte yeniden ?retildi?inde sonu?lar tutmad?. Bu nedenle bu 4h hyperopt seti g?venilir kabul edilmedi ve ana stratejiye uygulanmad?.

| Senaryo | Tarih | Getiri | 1000 USDT Sonucu | ??lem | PF | MaxDD | Market |
|---|---|---:|---:|---:|---:|---:|---:|
| train_2022_2025 | 2022-01-01 00:00:00 -> 2025-12-31 00:00:00 | -57.25% | 427.52 | 1212 | 0.79 | 57.74% | 45.98% |
| bear_2022 | 2022-05-01 00:00:00 -> 2022-12-31 00:00:00 | -11.60% | 883.95 | 204 | 0.86 | 24.04% | -56.16% |
| recovery_2023 | 2023-01-01 00:00:00 -> 2023-12-31 00:00:00 | -17.98% | 820.17 | 299 | 0.77 | 25.63% | 253.94% |
| bull_2024 | 2024-01-01 00:00:00 -> 2024-12-31 00:00:00 | -0.88% | 991.21 | 281 | 0.99 | 24.91% | 121.61% |
| choppy_2025 | 2025-01-01 00:00:00 -> 2025-12-31 00:00:00 | -19.63% | 803.66 | 319 | 0.81 | 24.80% | -8.10% |
| ytd_2026 | 2026-01-01 00:00:00 -> 2026-03-01 00:00:00 | 5.61% | 1056.11 | 31 | 1.64 | 5.94% | -27.07% |
| full_2022_2026 | 2022-01-01 00:00:00 -> 2026-03-01 00:00:00 | -54.01% | 459.87 | 1244 | 0.80 | 57.78% | 7.88% |

## Comparison

- Baseline 4h train result with current strategy params: 29.26% | 1000 -> 1292.64 | PF 1.08 | MaxDD 37.43% | Trades 284
- Claimed 4h hyperopt best epoch: 8.13% | 1000 -> 1081.27 | PF 1.05 | MaxDD 18.33% | Trades 318
- Reproduced train backtest with claimed params: -57.25% | 1000 -> 427.52 | PF 0.79 | MaxDD 57.74% | Trades 1212

## Decision

- 4h hyperopt sonucu ana stratejiye yaz?lmad?.
- Repo, mevcut do?rulanm?? 1d parametre seti ile b?rak?ld?.
- 4h i?in bir sonraki mant?kl? ad?m, ayr? bir 4h strateji varyant? tasarlay?p sadece exit ve trade-frequency davran???n? yeniden kurgulamak olur.
