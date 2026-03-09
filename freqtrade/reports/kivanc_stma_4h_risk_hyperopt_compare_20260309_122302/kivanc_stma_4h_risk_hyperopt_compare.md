# Kivanc STMA 4H Hyperopt Candidate vs Current Risk Profile

Hyperopt source: `kivanc_stma_4h_risk_hyperopt_20260309_121822`
Current profile: `risk_validation_4h`

Parameter match: `yes`

The fresh hyperopt run rediscovered the same buy and risk layer already stored in `risk_validation_4h.json`.
Because the parameter sets are identical, scenario-level profit and drawdown deltas are exactly zero.

| Scenario | Current Profit | Hyperopt Candidate Profit | Delta | Current MaxDD | Hyperopt Candidate MaxDD | Delta |
|---|---:|---:|---:|---:|---:|---:|
| bear_2022 | 12.51% | 12.51% | 0.00% | 12.49% | 12.49% | 0.00% |
| recovery_2023 | -3.63% | -3.63% | 0.00% | 17.16% | 17.16% | 0.00% |
| bull_2024 | 8.26% | 8.26% | 0.00% | 14.56% | 14.56% | 0.00% |
| choppy_2025 | -0.91% | -0.91% | 0.00% | 11.61% | 11.61% | 0.00% |
| ytd_2026 | 5.92% | 5.92% | 0.00% | 3.33% | 3.33% | 0.00% |
| full_2022_2026 | 23.36% | 23.36% | 0.00% | 17.16% | 17.16% | 0.00% |
