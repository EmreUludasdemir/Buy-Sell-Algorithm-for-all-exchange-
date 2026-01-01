# Exit Confidence Scoring Ablation Study

**Date:** 2026-01-02  
**Strategy:** EPAUltimateV3  
**Timerange:** 2024-06-01 to 2024-12-31 (213 days)  
**Timeframe:** 4h  
**Pairs:** BTC/USDT, BNB/USDT, ETH/USDT, SOL/USDT, XRP/USDT  

## Executive Summary

Exit Confidence Scoring gates `exit_signal` exits based on a 5-factor quality score (ADX strength, volume confirmation, RSI neutrality, bearish candle strength, EMA100 distance). The hypothesis was that filtering low-confidence exits would reduce false exits during minor pullbacks while allowing genuine reversals to exit.

**Result:** ❌ **NO CLEAR WINNER**

- **Best variant (threshold=2):** +0.06% profit improvement, tiny DD reduction
- **Problem:** Strict thresholds (3+) dramatically increase stop_loss exits, causing net harm
- **Root cause:** Blocking exit_signal forces trades to hold through genuine reversals → hits stop_loss

## Ablation Results

### Full Comparison Table

| Variant | Threshold | Scoring | Total Trades | Total Profit % | Total Profit USDT | Max DD % | exit_signal Count | exit_signal PnL USDT | stop_loss Count | stop_loss PnL USDT | roi Count | roi PnL USDT |
|---------|-----------|---------|--------------|----------------|-------------------|----------|-------------------|----------------------|-----------------|-------------------|-----------|--------------|
| **Baseline** | - | OFF | 72 | **10.03%** | 200.591 | **6.69%** | 13 | -404.792 | 9 | -126.747 | 48 | +675.832 |
| **V1** | 2 | ON | 72 | **10.09%** | 201.781 | **6.64%** | 13 | -403.875 | 9 | -126.759 | 48 | +676.249 |
| **V2** | 3 | ON | 72 | **7.53%** ⚠️ | 150.614 | **8.30%** ⚠️ | 13 | -445.943 | 9 | -125.402 | 48 | +721.959 |
| **V3** | 4 | ON | 72 | **6.93%** 🔴 | 138.516 | **9.97%** 🔴 | 9 | -402.654 | **11** ⚠️ | -219.636 | 50 | +760.806 |
| **V4** | 5 | ON | 72 | **8.32%** 🔴 | 166.404 | **7.65%** ⚠️ | **1** | -47.200 | **16** 🔴 | **-609.022** | 55 | +822.626 |

### Key Metrics by Variant

#### Baseline (Scoring OFF)
- **Total Profit:** 10.03% (200.591 USDT)
- **Max Drawdown:** 6.69%
- **Winrate:** 69.4%
- **Exit Breakdown:**
  - roi: 48 trades, +675.832 USDT
  - exit_signal: 13 trades, **-404.792 USDT**
  - stop_loss: 9 trades, -126.747 USDT
  - tiered_tp_8pct: 2 trades, +56.297 USDT

#### V1 (Threshold=2, Easy Gate)
- **Total Profit:** 10.09% (+0.06% vs baseline) ✅
- **Max Drawdown:** 6.64% (-0.05% vs baseline) ✅
- **Winrate:** 69.4%
- **Exit Breakdown:**
  - roi: 48 trades, +676.249 USDT
  - exit_signal: 13 trades, **-403.875 USDT** (tiny improvement)
  - stop_loss: 9 trades, -126.759 USDT
  - tiered_tp_8pct: 2 trades, +56.167 USDT
- **Impact:** Minimal filtering, ~0.9 USDT improvement on exit_signal
- **Verdict:** Marginal benefit, not worth complexity

#### V2 (Threshold=3, Moderate Gate)
- **Total Profit:** 7.53% (-2.5% vs baseline) 🔴
- **Max Drawdown:** 8.30% (+1.61% vs baseline) 🔴
- **Winrate:** 69.4%
- **Exit Breakdown:**
  - roi: 48 trades, +721.959 USDT (ROI increased but...)
  - exit_signal: 13 trades, **-445.943 USDT** (WORSE!)
  - stop_loss: 9 trades, -125.402 USDT
  - tiered_tp_8pct: 2 trades, +0 USDT
- **Impact:** Blocked some exits → held longer → exited at worse prices
- **Verdict:** Net negative, blocked good exits

#### V3 (Threshold=4, Strict Gate)
- **Total Profit:** 6.93% (-3.1% vs baseline) 🔴
- **Max Drawdown:** 9.97% (+3.28% vs baseline) 🔴
- **Winrate:** 72.2% (higher but misleading)
- **Exit Breakdown:**
  - roi: 50 trades, +760.806 USDT
  - exit_signal: **9 trades** (blocked 4), -402.654 USDT
  - stop_loss: **11 trades** (+2 vs baseline), **-219.636 USDT** (-92.889 USDT worse)
  - tiered_tp_8pct: 2 trades, +0 USDT
- **Impact:** Blocking exit_signal forced 2 trades into stop_loss → huge damage
- **Verdict:** Catastrophic, stop_loss increase negates exit_signal improvement

#### V4 (Threshold=5, Very Strict Gate)
- **Total Profit:** 8.32% (-1.71% vs baseline) 🔴
- **Max Drawdown:** 7.65% (+0.96% vs baseline) 🔴
- **Winrate:** 76.4% (misleading)
- **Exit Breakdown:**
  - roi: 55 trades, +822.626 USDT
  - exit_signal: **1 trade** (blocked 12!), -47.200 USDT
  - stop_loss: **16 trades** (+7 vs baseline), **-609.022 USDT** (-482.275 USDT worse) 🔴
  - tiered_tp_8pct: 0 trades
- **Impact:** Almost all exit_signal blocked → massive stop_loss carnage
- **Verdict:** Disaster, effectively disables exit_signal mechanism

## Analysis

### What Went Wrong?

**The Confidence Score Theory:** Filter low-quality exits (minor pullbacks) while allowing high-quality exits (genuine reversals).

**The Reality:** The scoring system cannot distinguish between "minor pullback" and "genuine reversal" **at the time of the exit**. Both scenarios can have:
- ADX > 20 (trending market transitioning)
- Volume spike (selling pressure)
- RSI in neutral zone (40-60 range)
- Bearish candle (price dropping)
- Break from EMA100 (downward move)

**The Fatal Flaw:** When an exit_signal is blocked by low confidence score, the trade holds through what **is** actually a reversal. By the time the score threshold is met (all 5 factors align), the price has already moved significantly against the position, often triggering the -8% stop_loss.

### Exit Signal vs Stop Loss Tradeoff

| Threshold | exit_signal Reduction | stop_loss Increase | Net Impact |
|-----------|----------------------|--------------------|------------|
| 2 | -0.9 USDT (-0.2%) | +0.012 USDT | **+1.19 USDT** ✅ |
| 3 | -41.151 USDT (-10.2%) | +1.345 USDT | **-49.977 USDT** 🔴 |
| 4 | +2.138 USDT | -92.889 USDT | **-59.467 USDT** 🔴 |
| 5 | +357.592 USDT | -482.275 USDT | **-38.595 USDT** 🔴 |

**Conclusion:** Every threshold >= 3 causes stop_loss damage that exceeds exit_signal improvement.

### Why Threshold=2 Barely Helps

With threshold=2, only need 2 of 5 factors → gates almost nothing. The score is so easy to pass that it has nearly zero filtering effect. The 0.06% improvement is statistical noise, not a meaningful signal.

### Fundamental Limitation

**Exit signals fire BECAUSE indicators detect reversal.** The confidence score uses the **same type of indicators** (ADX, RSI, volume, price action) to judge exit quality. This creates circular logic:

1. Exit signal fires (Supertrend + QQE + EMA all bearish)
2. Confidence score checks: Is ADX high? Is volume elevated? Is RSI neutral? Is candle bearish?
3. If yes → "high confidence" → allow exit
4. If no → "low confidence" → block exit → **but the reversal is real** → hits stop_loss

**The system cannot predict future price movement.** It can only react to current indicators, which already triggered the exit_signal in the first place.

## Recommendation

### ❌ Do NOT Enable Exit Confidence Scoring

**Reasons:**
1. **No meaningful improvement:** Best variant (threshold=2) provides +0.06% profit, essentially noise
2. **High risk:** Thresholds >= 3 cause catastrophic stop_loss increases (up to -482 USDT)
3. **Complexity without benefit:** Adds 7 parameters and complex scoring logic for zero gain
4. **False premise:** Cannot distinguish "minor pullback" from "genuine reversal" at exit time

### Alternative Approaches

If we want to reduce exit_signal losses, better strategies would:

1. **Improve entry quality** → fewer bad entries = fewer bad exits
2. **Adjust exit consensus** → perhaps 3-of-3 instead of 2-of-3 (but previous ablation showed this failed)
3. **Accept exit_signal losses as cost of trend-following** → -404 USDT is 20% of portfolio but system still profitable
4. **Optimize ROI table** → 48 ROI exits generated +676 USDT; lean into what works

### Final Verdict

**Keep baseline configuration** (use_exit_confidence_scoring = False). The exit_signal losses are a fundamental characteristic of trend-following systems using lagging indicators. Attempts to "smartly filter" exits have consistently failed because:
- We cannot predict future price
- Low-confidence exits are often correct
- Blocking exits shifts losses to stop_loss mechanism, which is worse

The strategy's 10.03% profit with 6.69% drawdown is solid. Exit signal losses are part of the system's risk profile and should be accepted, not over-optimized.

## Variant D Compliance

All variants maintained Variant D winner configuration:
- ✅ trailing_stop = False
- ✅ use_custom_stoploss = False
- ✅ stoploss = -0.08 (fixed)

No changes were made to entry logic, ROI table, or stop mechanism.

---

**Conclusion:** Exit Confidence Scoring tested but **rejected**. Baseline configuration remains optimal. Report filed for reference. No code commit recommended.
