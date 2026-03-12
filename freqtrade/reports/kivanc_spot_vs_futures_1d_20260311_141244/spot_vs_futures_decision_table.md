# Spot 1D vs Futures 1D Decision Table

Spot source: `kivanc_spot_1d_regimes_20260311_161905`
Futures source: `kivanc_futures_1d_regimes_20260309_180632`

## Comparison

| Scenario | Spot Profit | Futures Profit | Delta | Spot MaxDD | Futures MaxDD | Delta |
|---|---:|---:|---:|---:|---:|---:|
| bear_2022 | -14.18% | -20.18% | -6.00% | 14.18% | 21.23% | 7.05% |
| recovery_2023 | 55.16% | 66.18% | 11.02% | 4.12% | 8.79% | 4.67% |
| bull_2024 | 28.12% | 4.45% | -23.67% | 9.79% | 24.44% | 14.65% |
| choppy_2025 | 35.54% | 52.46% | 16.92% | 8.18% | 9.26% | 1.08% |
| ytd_2026 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| full_2022_2026 | 191.78% | 239.95% | 48.17% | 27.86% | 22.30% | -5.56% |

## Decision Table

| Scenario | Preferred Mode | Reason |
|---|---|---|
| bear_2022 | spot_1d | Better return with lower or equal drawdown. |
| recovery_2023 | futures_1d | Higher return with acceptable drawdown increase. |
| bull_2024 | spot_1d | Better return with lower or equal drawdown. |
| choppy_2025 | futures_1d | Higher return with acceptable drawdown increase. |
| ytd_2026 | none | No trades in either mode. |
| full_2022_2026 | futures_1d | Higher return with acceptable drawdown increase. |
