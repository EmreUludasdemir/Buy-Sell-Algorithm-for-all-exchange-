# Exit Signal Loss Attribution Analysis
**Generated:** 2026-01-02 02:09:45  
**Strategy:** EPAUltimateV3  
**Timerange:** 2024-06-01 to 2024-12-31  

---

## Executive Summary

**Total exit_signal losses:** -404.79 USDT across 4 pairs

**Key Finding:** This report identifies which pairs, indicator states, and market regimes contribute most to exit_signal losses, enabling targeted entry/regime filters.

---

## 1. Pair Attribution

Ranked by total loss contribution:

| Pair | Trade Count | Total Loss (USDT) | Avg Loss (USDT) | Avg Loss (%) |
|------|-------------|-------------------|-----------------|--------------|
| BTC/USDT | 9 | -291.48 | -32.39 | -2.90% |
| ETH/USDT | 2 | -66.15 | -33.08 | -4.10% |
| XRP/USDT | 1 | -31.39 | -31.39 | -4.00% |
| BNB/USDT | 1 | -15.77 | -15.77 | -5.70% |

**Analysis:**
- **BTC/USDT** is the worst contributor: -291.48 USDT (72.0% of total)
- **Top 3 pairs** account for -389.03 USDT (96.1% of total losses)

---

## 2. Entry Indicator States

Indicator states at entry for losing exit_signal trades:

---

## 3. Regime Analysis

⚠️ No regime columns found in trades data.

---

## 4. Recommendations

Based on this attribution analysis, consider implementing:

### Filter Candidate 1: EMA200 Slope Filter
- **Logic:** Only enter long trades when 4h EMA200 slope > 0 (uptrend)
- **Rationale:** If EMA200 downtrend trades show disproportionate losses
- **Risk:** May reduce trade count significantly

### Filter Candidate 2: ADX Minimum Threshold
- **Logic:** Only enter when ADX >= 20 (strong trend)
- **Rationale:** Weak trend entries may be prone to whipsaw
- **Risk:** May miss early trend entries

### Next Steps
1. Implement both filters as feature flags (default OFF)
2. Run 4-variant ablation:
   - Baseline (both OFF)
   - Filter1 ON (EMA200 slope)
   - Filter2 ON (ADX threshold)
   - Both ON
3. Compare:
   - Total profit (must be >= baseline 10.03%)
   - stop_loss count (must be <= 9)
   - exit_signal loss reduction
   - Trade count impact
4. Enable winner if acceptance criteria met

---

*Note: This analysis focuses on identifying root causes at entry, not exit tweaks.*
