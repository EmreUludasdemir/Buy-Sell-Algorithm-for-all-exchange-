# Kivanc Filtered Futures 1D Research Sweep

| Candidate | Profit | Final Balance | Trades | PF | MaxDD | Long PnL | Short PnL |
|---|---:|---:|---:|---:|---:|---:|---:|
| asym_60_40 | 289.28% | 3892.81 | 62 | 2.93 | 19.07% | 222.60% | 66.68% |
| asym_70_30 | 288.49% | 3884.89 | 61 | 3.05 | 19.69% | 234.88% | 53.61% |
| baseline | 271.54% | 3715.37 | 62 | 2.75 | 18.72% | 197.30% | 74.24% |
| sharpe_90_asym | 157.53% | 2575.31 | 25 | 3.92 | 7.75% | 148.97% | 8.56% |
| tsmom_252_asym | 123.24% | 2232.43 | 31 | 2.57 | 13.47% | 101.99% | 21.25% |
| tsmom_252 | 103.50% | 2034.96 | 31 | 2.38 | 14.99% | 80.31% | 23.19% |
| tsmom_sharpe_fast | 88.60% | 1885.96 | 19 | 2.75 | 15.33% | 80.87% | 7.73% |
| tsmom_sharpe_combo | 81.02% | 1810.16 | 19 | 2.83 | 14.80% | 95.39% | -14.37% |
| tsmom_189_asym | 74.48% | 1744.82 | 23 | 2.20 | 22.29% | 66.57% | 7.91% |
| tsmom_189_005 | 61.88% | 1618.78 | 23 | 2.07 | 17.29% | 49.74% | 12.14% |

Best candidate: `asym_60_40` with `289.28%` and `MaxDD 19.07%`.

## Overrides

```json
{
  "long_stake_multiplier": 1.2,
  "short_stake_multiplier": 0.8,
  "use_tsmom_filter": false,
  "use_rolling_sharpe_filter": false
}
```
