# Giveback Protector Ablation Study
**Date:** 2026-01-01  
**Strategy:** EPAUltimateV3  
**Test Period:** 2024-06-01 to 2024-12-31 (213 days)  
**Timeframe:** 4h  
**Pairs:** BTC/USDT, BNB/USDT, ETH/USDT, SOL/USDT, XRP/USDT

---

## Executive Summary

❌ **FAILED**: All variants increased stop_loss count from 9→10 trades, violating primary acceptance criteria.

**Recommendation:** **DO NOT enable this feature.** Keep baseline configuration (use_giveback_protector=False).

---

## Hypothesis

Many losing exit_signal trades went green first (MFE > 0) then closed red. Adding an early "giveback protector" exit that triggers when:
- Trade reached meaningful profit (MFE ≥ threshold)
- Current profit gave back to near breakeven
- Trade held for minimum duration
- Not too deeply negative (let stoploss handle deep losses)

This should catch trades before they deteriorate into large exit_signal losses.

---

## Acceptance Criteria

✅ **Must pass:** stop_loss count ≤ 9 (baseline level)  
✅ **Must pass:** Maintain Variant D compliance (trailing_stop=False, use_custom_stoploss=False, stoploss=-0.08)  
⚠️ **Success threshold:** (profit improves ≥+0.5%) OR (exit_signal improves ≥+100 USDT)

**Critical Constraint:** If stop_loss increases materially, the approach is considered a failure regardless of profit improvements.

---

## Results Summary

| Variant | mfe_trigger | giveback_to | min_age | Profit | Max DD | Total Trades | stop_loss | exit_signal | giveback_protector | Status |
|---------|-------------|-------------|---------|--------|--------|--------------|-----------|-------------|--------------------|--------|
| **Baseline** | OFF | OFF | - | **10.03%** | **6.69%** | 72 | **9** (-126.7 USDT) | **13** (-404.8 USDT) | - | ✅ Benchmark |
| **V1** | 0.02 | 0.001 | 12h | 5.73% 🔴 | 8.72% 🔴 | 84 | **10** 🚫 | 14 (-388.1 USDT) | 21 (-25.8 USDT, 19% WR) | ❌ FAIL |
| **V2** | 0.03 | 0.002 | 12h | 3.85% 🔴 | 9.56% 🔴 | 78 | **10** 🚫 | 14 (-397.2 USDT) | 12 (-9.1 USDT, 42% WR) | ❌ FAIL |
| **V3** | 0.04 | 0.003 | 12h | 5.22% 🔴 | 7.87% 🔴 | 75 | **10** 🚫 | 14 (-402.6 USDT) | 7 (-0.06 USDT, 57% WR) | ❌ FAIL |

### Key Findings

1. **stop_loss Violation (Critical):** ALL variants increased stop_loss from 9→10 trades (+1), failing the primary acceptance criterion
2. **Profit Degradation:** All variants showed 4.8-6.2% worse profit than baseline
3. **exit_signal Minimal Change:** exit_signal count remained 13-14 trades across all variants (no meaningful improvement)
4. **Giveback Performance:** Even best variant (V3) with 57% winrate on giveback exits was nearly breakeven (-0.06 USDT total)

---

## Detailed Exit Breakdown

### Baseline (10.03% profit, 6.69% DD)
```
roi:                48 trades,  +675.832 USDT  (100% WR)
tiered_tp_8pct:      2 trades,   +56.192 USDT  (100% WR)
stop_loss:           9 trades,  -126.747 USDT  (  0% WR) ← Benchmark
exit_signal:        13 trades,  -404.792 USDT  (  0% WR) ← Target for improvement
───────────────────────────────────────────────────────
Total:              72 trades,  +200.485 USDT
```

### V1 (5.73% profit, 8.72% DD) - Too Aggressive
```
roi:                37 trades,  +606.352 USDT  (100% WR)
tiered_tp_8pct:      2 trades,   +56.048 USDT  (100% WR)
giveback_protector: 21 trades,   -25.819 USDT  ( 19% WR) ← 4 wins, 17 losses
stop_loss:          10 trades,  -133.974 USDT  (  0% WR) ← +1 FROM BASELINE 🚫
exit_signal:        14 trades,  -388.052 USDT  (  0% WR)
───────────────────────────────────────────────────────
Total:              84 trades,  +114.555 USDT  (-85.9 USDT vs baseline)
```

**Analysis:** mfe_trigger=0.02 too low, triggered 21 times with poor 19% winrate. Protector exits were mostly false alarms on healthy pullbacks that would have recovered to ROI.

### V2 (3.85% profit, 9.56% DD) - Worst Performance
```
roi:                40 trades,  +559.934 USDT  (100% WR)
tiered_tp_8pct:      2 trades,   +55.962 USDT  (100% WR)
giveback_protector: 12 trades,    -9.078 USDT  ( 42% WR) ← 5 wins, 7 losses
stop_loss:          10 trades,  -132.617 USDT  (  0% WR) ← +1 FROM BASELINE 🚫
exit_signal:        14 trades,  -397.206 USDT  (  0% WR)
───────────────────────────────────────────────────────
Total:              78 trades,   +76.995 USDT  (-123.5 USDT vs baseline)
```

**Analysis:** Less aggressive but still harmful. Better winrate (42% vs 19%) but still net negative. stop_loss still increased.

### V3 (5.22% profit, 7.87% DD) - Most Conservative
```
roi:                42 trades,  +585.201 USDT  (100% WR)
tiered_tp_8pct:      2 trades,   +56.056 USDT  (100% WR)
giveback_protector:  7 trades,    -0.064 USDT  ( 57% WR) ← 4 wins, 3 losses, nearly breakeven
stop_loss:          10 trades,  -134.125 USDT  (  0% WR) ← STILL +1 🚫
exit_signal:        14 trades,  -402.581 USDT  (  0% WR)
───────────────────────────────────────────────────────
Total:              75 trades,  +104.487 USDT  (-96.0 USDT vs baseline)
```

**Analysis:** Most conservative variant (mfe=0.04, giveback=0.003), triggers rarely (7 times), best winrate (57%), nearly breakeven on giveback exits. BUT STILL increased stop_loss count by +1 and degraded profit significantly.

---

## Why This Approach Failed

### 1. Trade Flow Problem

**Intended Flow:**
```
Entry → goes green (MFE 2-4%) → starts reversal → giveback_protector exits at +0.1-0.3%
Result: Small profit instead of -3% exit_signal loss ✅
```

**Actual Flows:**

**Flow A: False Exit on Healthy Pullback**
```
Entry → +3% → minor dip to +0.2% → giveback_protector EXITS
→ Price recovers to +5% ROI (missed)
Result: +0.2% exit instead of +5% ROI 🔴
```

**Flow B: Held Until stop_loss**
```
Entry → +4% → pullback starts → giveback_protector doesn't trigger (parameters too conservative)
→ Price continues down → hits -8% stop_loss
Result: -8% stop_loss instead of -3% exit_signal 🔴 WORSE
```

### 2. Cannot Distinguish Pullback Types

The fundamental issue: **at the moment of potential giveback exit, we cannot predict whether the pullback will recover or continue deteriorating.**

- **Healthy pullback:** Price dips to +0.2%, then recovers to +5% ROI ← Protector exits incorrectly
- **Reversal starting:** Price dips to +0.2%, continues to -8% stop_loss ← Protector should exit but doesn't

**Tuning Tradeoff:**
- **Aggressive parameters (V1):** Exit too often → lots of false alarms → miss ROI targets
- **Conservative parameters (V3):** Exit rarely → some trades still hit stop_loss instead of exit_signal

### 3. stop_loss Increase Mechanism

```
Baseline: 9 stop_losses at -8% each
With Protector: Some trades that would exit at -3% via exit_signal are "protected" from early exit
→ Those trades hold longer, hoping to recover
→ Sometimes they hit -8% stop_loss instead (even worse outcome)
```

**Result:** stop_loss count increased from 9→10 in ALL variants, regardless of parameter tuning.

### 4. Insufficient exit_signal Improvement

```
Baseline:     13 exit_signal trades, -404.792 USDT
V1:           14 exit_signal trades, -388.052 USDT  (+16.7 USDT, but stop_loss lost -7.2 USDT)
V2:           14 exit_signal trades, -397.206 USDT  (+7.6 USDT, but stop_loss lost -5.9 USDT)
V3:           14 exit_signal trades, -402.581 USDT  (+2.2 USDT, but stop_loss lost -7.4 USDT)
```

Even the best case (V1) only improved exit_signal losses by ~17 USDT, far below the +100 USDT success threshold. And the stop_loss increase more than offset this small gain.

---

## Implementation Details

### Parameters Added
```python
use_giveback_protector = BooleanParameter(default=False, space='sell', optimize=False)
mfe_trigger = DecimalParameter(0.01, 0.05, default=0.03, space='sell', optimize=False)
giveback_to = DecimalParameter(0.0, 0.01, default=0.002, space='sell', optimize=False)
min_trade_age_hours = DecimalParameter(4.0, 24.0, default=12.0, space='sell', optimize=False)
max_exit_loss_after_green = DecimalParameter(-0.02, 0.0, default=-0.01, space='sell', optimize=False)
```

### custom_exit() Logic
```python
if self.use_giveback_protector.value:
    trade_duration = (current_time - trade.open_date_utc).total_seconds() / 3600
    
    if trade_duration >= self.min_trade_age_hours.value:
        if hasattr(trade, 'max_rate') and trade.max_rate and trade.open_rate:
            max_profit = (trade.max_rate - trade.open_rate) / trade.open_rate
            
            if max_profit >= self.mfe_trigger.value:
                if (current_profit <= self.giveback_to.value and 
                    current_profit >= self.max_exit_loss_after_green.value):
                    return 'giveback_protector'
```

**MFE Tracking:** Uses `trade.max_rate` attribute (freqtrade native tracking) to calculate Maximum Favorable Excursion.

---

## Lessons Learned

1. **Exit timing is inherently difficult:** Cannot distinguish "temporary pullback" from "reversal starting" at the moment of decision
2. **Unintended consequences:** Preventing exit_signal can push trades into stop_loss (worse outcome)
3. **Parameter tuning limited:** Even conservative tuning (V3: mfe=0.04, giveback=0.003) couldn't solve fundamental issue
4. **System tradeoffs:** exit_signal losses may be an acceptable cost of the trend-following system's profitable behavior

### Historical Context

This is the **fourth** failed ablation attempt to reduce exit_signal losses:
1. **Confidence scoring gate:** Added entry confidence threshold → reduced profits
2. **Choppiness gate:** Blocked entries in choppy markets → missed valid setups
3. **Profit damping:** Reduced exit_signal aggressiveness → worse exit timing
4. **Giveback protector (current):** Early exit on giveback → increased stop_loss count

**Pattern:** exit_signal losses appear to be fundamental characteristic of this trend-following system, not a bug to fix.

---

## Recommendation

**DO NOT enable giveback_protector feature.** Keep baseline configuration:
- `use_giveback_protector = False` (default)
- Baseline performance: 10.03% profit, 6.69% DD

### Rationale

1. **Acceptance criteria violated:** stop_loss increased in all variants
2. **Profit degradation:** 4.8-6.2% worse across all variants
3. **Minimal exit_signal improvement:** <20 USDT vs required +100 USDT threshold
4. **Fundamental limitation:** Cannot predict pullback outcomes at exit moment

### Alternative Approach

**Accept exit_signal losses as inherent cost of system design:**
- System generates 10.03% profit with 6.69% DD despite -404 USDT in exit_signal losses
- exit_signal losses (13 trades) are 18% of total trades, but ROI exits (48 trades, 67%) dominate P&L
- Four separate ablation attempts have failed to reduce these losses without harming overall performance
- Conclusion: exit_signal losses are the "cost of doing business" for this trend-following approach

### If Revisiting This Feature

Would need fundamentally different approach:
- **Machine learning classifier:** Train model to predict "healthy pullback" vs "reversal starting" using market microstructure features
- **Regime detection:** Only enable protector in specific market regimes where it performs well
- **Adaptive thresholds:** Dynamically adjust mfe_trigger/giveback_to based on recent trade outcomes
- **Multi-timeframe confirmation:** Require bearish signal on higher timeframe before exiting on giveback

Current rule-based approach with static thresholds is insufficient.

---

## Variant D Compliance

✅ **Maintained throughout testing:**
- `trailing_stop = False`
- `use_custom_stoploss = False`
- `stoploss = -0.08`
- No changes to entry logic or ROI table

---

## Test Configuration

```yaml
Strategy: EPAUltimateV3
Timerange: 2024-06-01 to 2024-12-31 (213 days)
Timeframe: 4h
Stake: 200 USDT (fixed per trade)
Max Open Trades: 5
Pairs: BTC/USDT, BNB/USDT, ETH/USDT, SOL/USDT, XRP/USDT
Fee: 0.1% (maker/taker)
Cache: none (fresh backtest for each variant)
Export: trades (for exit reason analysis)
```

---

## Conclusion

The giveback_protector feature **failed all acceptance criteria** and should **not be enabled**. The baseline strategy's 10.03% profit with 6.69% DD represents the optimal balance for this system. exit_signal losses, while significant (-404 USDT), appear to be an acceptable cost of the trend-following approach that generates consistent ROI exits (+675 USDT).

**Final Status:** ❌ REJECTED - Feature disabled by default, do NOT enable in production.
