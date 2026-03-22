# Spot 1D vs Futures Modes Decision Table

Spot source: `kivanc_spot_1d_regimes_20260311_161905`
Futures source: `kivanc_futures_1d_regimes_20260309_180632`
Filtered futures source: `kivanc_futures_filtered_1d_asym60_regimes_20260319_110832`

## Comparison

| Scenario | Spot Profit | Futures Profit | Filtered Futures Profit | Spot MaxDD | Futures MaxDD | Filtered Futures MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| bear_2022 | -14.18% | -20.18% | -11.51% | 14.18% | 21.23% | 12.43% |
| recovery_2023 | 55.16% | 66.18% | 67.00% | 4.12% | 8.79% | 3.45% |
| bull_2024 | 28.12% | 4.45% | 11.10% | 9.79% | 24.44% | 20.80% |
| choppy_2025 | 35.54% | 52.46% | 60.48% | 8.18% | 9.26% | 7.34% |
| ytd_2026 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| full_2022_2026 | 191.78% | 239.95% | 289.28% | 27.86% | 22.30% | 19.07% |

## Decision Table

| Scenario | Preferred Mode | Reason |
|---|---|---|
| bear_2022 | filtered_futures_1d | Highest return with acceptable drawdown. |
| recovery_2023 | filtered_futures_1d | Highest return with acceptable drawdown. |
| bull_2024 | spot_1d | Highest return with acceptable drawdown. |
| choppy_2025 | filtered_futures_1d | Highest return with acceptable drawdown. |
| ytd_2026 | none | No trades in any mode. |
| full_2022_2026 | filtered_futures_1d | Highest return with acceptable drawdown. |
