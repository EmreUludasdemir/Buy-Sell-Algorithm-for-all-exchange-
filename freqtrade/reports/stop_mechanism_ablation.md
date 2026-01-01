# Stop Mechanism Ablation Study - EPAUltimateV3

**Goal**: Prove whether losses labeled `trailing_stop_loss` are caused by trailing_stop settings or custom_stoploss logic.

**Test Period**: 2024-06-01 to 2024-12-31 (213 days)
**Timeframe**: 4h
**Pairs**: BTC/USDT, BNB/USDT, ETH/USDT, SOL/USDT, XRP/USDT
**Base Stoploss**: -8% (fixed)
**Trailing Settings**: positive=3%, offset=5%, only_offset_is_reached=True
**Custom Stoploss**: ATR-based (max of -8% or 3 ATR)

---

## Variant Summary

| Variant | Trailing | Custom | Trades | Profit USDT | Profit % | Win Rate | Drawdown | Trailing Exits |
|---------|----------|--------|--------|-------------|----------|----------|----------|----------------|
| **A** | ✅ | ❌ | 81 | -34.84 | -1.74% | 69.1% | 9.03% | 15 |
| **B** | ❌ | ✅ | 84 | 113.61 | 5.68% | 57.1% | 7.65% | 34 |
| **C** | ✅ | ✅ | 92 | -54.43 | -2.72% | 51.1% | 8.19% | 48 |
| **D** | ❌ | ❌ | 72 | 116.75 | 5.84% | 70.8% | 8.10% | 0 |

---

## Detailed Analysis

### Variant A: Trailing ON, Custom OFF

**Configuration**:
- `trailing_stop = True`
- `use_custom_stoploss = False`

**Results**:
- Total Trades: 81
- Profit: -34.84 USDT (-1.74%)
- Win Rate: 69.1%
- Max Drawdown: 9.03%

**Exit Reason Distribution**:

| Exit Reason | Count | Total PnL (USDT) | Win Rate |
|------------|-------|------------------|----------|
| roi | 41 | 520.41 | 100.0% |
| trailing_stop_loss | 15 | 81.23 | 100.0% |
| stop_loss | 14 | -252.58 | 0.0% |
| exit_signal | 11 | -383.91 | 0.0% |

**Trailing Stop Loss Analysis**:
- Count: 15 trades
- Total Impact: 81.23 USDT
- Win Rate: 100.0%
- Average: 5.42 USDT per trade


---

### Variant B: Trailing OFF, Custom ON

**Configuration**:
- `trailing_stop = False`
- `use_custom_stoploss = True`

**Results**:
- Total Trades: 84
- Profit: 113.61 USDT (5.68%)
- Win Rate: 57.1%
- Max Drawdown: 7.65%

**Exit Reason Distribution**:

| Exit Reason | Count | Total PnL (USDT) | Win Rate |
|------------|-------|------------------|----------|
| roi | 45 | 642.58 | 100.0% |
| tiered_tp_8pct | 1 | 49.73 | 100.0% |
| trailing_stop_loss | 34 | -494.58 | 5.9% |
| stop_loss | 2 | -20.76 | 0.0% |
| exit_signal | 2 | -63.35 | 0.0% |

**Trailing Stop Loss Analysis**:
- Count: 34 trades
- Total Impact: -494.58 USDT
- Win Rate: 5.9%
- Average: -14.55 USDT per trade

**🚨 CRITICAL FINDING 🚨**:

This variant has `trailing_stop = False`, yet 34 trades are labeled as `trailing_stop_loss`!

**Proof that custom_stoploss is mislabeling its exits as trailing_stop_loss.**


---

### Variant C: Both ON (Baseline)

**Configuration**:
- `trailing_stop = True`
- `use_custom_stoploss = True`

**Results**:
- Total Trades: 92
- Profit: -54.43 USDT (-2.72%)
- Win Rate: 51.1%
- Max Drawdown: 8.19%

**Exit Reason Distribution**:

| Exit Reason | Count | Total PnL (USDT) | Win Rate |
|------------|-------|------------------|----------|
| roi | 40 | 539.43 | 100.0% |
| trailing_stop_loss | 48 | -514.80 | 14.6% |
| stop_loss | 2 | -19.67 | 0.0% |
| exit_signal | 2 | -59.40 | 0.0% |

**Trailing Stop Loss Analysis**:
- Count: 48 trades
- Total Impact: -514.80 USDT
- Win Rate: 14.6%
- Average: -10.72 USDT per trade


---

### Variant D: Both OFF (Fixed Stoploss)

**Configuration**:
- `trailing_stop = False`
- `use_custom_stoploss = False`

**Results**:
- Total Trades: 72
- Profit: 116.75 USDT (5.84%)
- Win Rate: 70.8%
- Max Drawdown: 8.10%

**Exit Reason Distribution**:

| Exit Reason | Count | Total PnL (USDT) | Win Rate |
|------------|-------|------------------|----------|
| roi | 49 | 673.22 | 100.0% |
| tiered_tp_8pct | 2 | 56.17 | 100.0% |
| stop_loss | 10 | -219.68 | 0.0% |
| exit_signal | 11 | -392.96 | 0.0% |

---

## Conclusion

### 🎯 Root Cause Identified

The `trailing_stop_loss` exit reason is triggered by **BOTH mechanisms**, and they interfere with each other:

1. **When `trailing_stop = True` and `use_custom_stoploss = False` (Variant A)**:
   - 15 trailing_stop_loss exits with **100% win rate** (+81 USDT)
   - This is TRUE trailing stops working correctly
   - They lock in profits after +5% threshold

2. **When `trailing_stop = False` and `use_custom_stoploss = True` (Variant B)**:
   - 34 trailing_stop_loss exits with **5.9% win rate** (-495 USDT) ← MISLABELED!
   - Trailing is OFF but exits still labeled as trailing_stop_loss
   - **Proof: custom_stoploss mislabels its ATR-based exits**

3. **When both are ON (Variant C - Original)**:
   - 48 trailing_stop_loss exits with **14.6% win rate** (-515 USDT)
   - Worst of both worlds: interference between mechanisms
   - Custom stoploss overrides trailing logic unpredictably

4. **When both are OFF (Variant D - Winner)**:
   - **0 trailing_stop_loss exits**
   - Fixed -8% stoploss only: 10 exits, -220 USDT
   - **+117 USDT profit (+5.84%), 70.8% win rate**
   - Clean, predictable exit behavior

---

## Recommendation for 4H Timeframe

### ✅ Use Variant D: Both OFF (Fixed Stoploss Only)

```python
stoploss = -0.08  # -8% fixed stop
use_custom_stoploss = False  # Disable ATR-based logic
trailing_stop = False  # Disable trailing stops
```

### Justification:

| Metric | Variant D (Winner) | Variant C (Current) | Improvement |
|--------|-------------------|---------------------|-------------|
| Profit | **+117 USDT** | -54 USDT | **+171 USDT** |
| Profit % | **+5.84%** | -2.72% | **+8.56%** |
| Win Rate | **70.8%** | 51.1% | **+19.7%** |
| Trades | 72 | 92 | -20 (more selective) |
| Drawdown | 8.10% | 8.19% | Similar |
| Trailing Exits | **0** | 48 (-515 USDT) | **Eliminated problem** |

### Why Fixed Stoploss Works Best for 4H:

1. **Predictability**: -8% stop is clear, no interference from ATR or trailing logic
2. **Fewer Trades**: 72 vs 92 = more selective, higher quality entries
3. **Higher Win Rate**: 70.8% vs 51.1% = better entry/exit timing
4. **ROI Table Dominates**: 49 ROI exits with 100% win rate (+673 USDT)
5. **Clean Exit Reasons**: Only 4 types (roi, stop_loss, exit_signal, tiered_tp)

### Alternative: Variant B (If You Want Dynamic Stops)

If you prefer ATR-based dynamic stops:

```python
stoploss = -0.08
use_custom_stoploss = True  # ATR-based logic
trailing_stop = False  # Must disable to avoid mislabeling
```

- Also profitable: +114 USDT (+5.68%)
- But: 34 exits mislabeled as trailing_stop_loss (confusing)
- And: Only 57.1% win rate vs 70.8% for Variant D

---

## Implementation Steps

1. **Open** `user_data/strategies/EPAUltimateV3.py`

2. **Find** the stop configuration section (around line 86-95)

3. **Replace** with:
```python
# Base stoploss - fixed for 4H timeframe
stoploss = -0.08

# Disable dynamic mechanisms for clean behavior
use_custom_stoploss = False

# Disable trailing stops
trailing_stop = False
trailing_stop_positive = 0.03  # Not used
trailing_stop_positive_offset = 0.05  # Not used
trailing_only_offset_is_reached = True  # Not used
```

4. **Commit** changes:
```bash
git add user_data/strategies/EPAUltimateV3.py
git commit -m 'Apply Variant D: Fixed stoploss only - Best performance for 4H'
```

5. **Run final validation backtest**:
```bash
docker compose run --rm freqtrade backtesting \
    --strategy EPAUltimateV3 \
    --config user_data/config.json \
    --timerange 20240601-20241231 \
    --timeframe 4h
```

Expected: +117 USDT, 72 trades, 70.8% win rate, 0 trailing_stop_loss exits

---

## Key Insights

1. **Mislabeling Confirmed**: `custom_stoploss` returns values that get labeled as `trailing_stop_loss` even when trailing is OFF

2. **Interference Effect**: When both mechanisms are ON, they conflict and produce worst results

3. **Simplicity Wins**: Fixed stoploss outperforms complex dynamic logic for 4H timeframe

4. **ROI Table is King**: All variants show ROI exits have 100% win rate - let it do the work

5. **4H Volatility**: -8% fixed stop is wide enough for 4H candle noise, no need for dynamic ATR

---

**Report Generated**: 2026-01-01
**Strategy**: EPAUltimateV3
**Test Period**: 2024-06-01 to 2024-12-31 (213 days)
**Conclusion**: Use Variant D (both OFF) for optimal 4H performance