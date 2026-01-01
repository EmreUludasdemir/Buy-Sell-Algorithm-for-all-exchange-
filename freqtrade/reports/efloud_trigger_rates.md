# Efloud Boost Trigger Audit - Quick Analysis

**Date:** 2026-01-02 00:57  
**Backtest:** backtest-result-2026-01-01_21-39-19.zip  
**Total Trades:** 248

---

## Executive Summary

**Root Cause: UNCERTAIN (Export Incomplete)** ⚠️

Freqtrade export does NOT include custom indicator values (in_demand_zone, reclaim_eq, htf_bias_bull).
Cannot verify trigger rates from export alone.

**Observations:**
- Stakes vary (248 unique values)
- Would need to recompute indicators on historical data to check trigger rates

---

## 1. Stake Amount Analysis

| Metric | Value |
|--------|-------|
| Column used | `stake_amount` |
| Unique values | 248 |
| Min | 55.55 USDT |
| Median | 510.08 USDT |
| Mean | 583.27 USDT |
| Max | 2070.78 USDT |
| Std Dev | 408.16 USDT |
| Coefficient of Variation | 70.0% |

---

## 2. Exported Fields Check

**No boost-related fields found in export.**

Freqtrade's `--export trades` does NOT include custom indicator columns.
Only standard fields are exported:
- open_date, close_date
- pair, stake_amount, amount
- profit_ratio, profit_abs
- entry_tag, exit_reason

To check trigger rates, must:
1. Reload historical OHLCV data
2. Recompute indicators via `populate_indicators()`
3. Match trades to entry candles
4. Check flag values at entry time

---

## 3. Conclusions

### Partial Answer: Stakes Vary, But Need Deeper Analysis

**Good news:**
- 248 unique stake values → Position sizing IS dynamic
- Std dev 408.16 USDT (70.0% CV)

**Uncertainty:**
- Export doesn't include boost flag values
- Cannot verify if variance is DUE TO boosts or other factors (volatility, SMC, etc.)

**Next Steps:**

To definitively answer (A) vs (B):
1. Re-run audit with full indicator recalculation
2. Match each trade to its entry candle
3. Check `in_demand_zone`, `reclaim_eq`, `htf_bias_bull` values at entry
4. Calculate expected boost multipliers
5. Correlate with actual stake amounts

OR check Freqtrade logs from backtest for custom_stake_amount() calls.

---

## Appendix: Sample Trades

### Top 10 Profitable

| Pair | Date | Profit % | Stake |
|------|------|----------|-------|
| XRP/USDT | 2024-11-21 | 11.99% | 279.57 |
| XRP/USDT | 2024-12-02 | 11.99% | 98.82 |
| BNB/USDT | 2024-12-03 | 11.99% | 809.37 |
| XRP/USDT | 2024-11-16 | 11.99% | 94.57 |
| XRP/USDT | 2024-11-21 | 11.99% | 280.29 |
| BTC/USDT | 2024-11-11 | 7.99% | 922.36 |
| XRP/USDT | 2024-07-13 | 7.99% | 525.76 |
| XRP/USDT | 2024-11-10 | 7.99% | 748.35 |
| XRP/USDT | 2024-11-12 | 7.99% | 194.00 |
| XRP/USDT | 2024-11-12 | 7.99% | 149.50 |

### Top 10 Losing

| Pair | Date | Profit % | Stake |
|------|------|----------|-------|
| BNB/USDT | 2024-11-12 | -8.18% | 222.30 |
| SOL/USDT | 2024-10-24 | -8.18% | 200.62 |
| BTC/USDT | 2024-12-05 | -8.18% | 1257.97 |
| BTC/USDT | 2024-08-24 | -8.18% | 846.39 |
| ETH/USDT | 2024-08-14 | -8.18% | 902.35 |
| SOL/USDT | 2024-07-29 | -8.18% | 638.85 |
| XRP/USDT | 2024-09-29 | -8.18% | 219.63 |
| SOL/USDT | 2024-11-12 | -8.18% | 172.14 |
| XRP/USDT | 2024-11-24 | -8.18% | 246.50 |
| BNB/USDT | 2024-12-09 | -8.18% | 607.58 |
