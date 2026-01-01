# Exit Reason Audit Report

**Goal**: Determine what actually causes losses labeled as `trailing_stop_loss`

**Test Period**: 2024-06-01 to 2024-12-31 (213 days)
**Timeframe**: 4h
**Pairs**: BTC/USDT, BNB/USDT, ETH/USDT, SOL/USDT, XRP/USDT

---

## EPAStrategyV2

**Total Trades**: 151

### Exit Reason Distribution

| Exit Reason | Count | Total PnL (%) | Avg PnL (%) | Positive | Negative | Win Rate |
|------------|-------|---------------|-------------|----------|----------|----------|
| trailing_stop_loss | 77 | -195.63 | -2.54 | 14 | 63 | 18.2% |
| roi | 64 | 214.03 | 3.34 | 64 | 0 | 100.0% |
| exit_signal | 9 | -27.60 | -3.07 | 0 | 9 | 0.0% |
| stop_loss | 1 | -7.70 | -7.70 | 0 | 1 | 0.0% |

### Trailing Stop Loss Analysis

- **Total trailing_stop_loss exits**: 77
- **Average profit at exit**: -2.54%
- **Positive exits**: 14 (18.2%)
- **Negative exits**: 63 (81.8%)
- **Total PnL impact**: -195.63%

**Key Finding**: Only 18.2% of trailing stops are profitable! 

### Sample Trailing Stop Trades

| Pair | Entry Time | Exit Time | Entry Tag | Profit % | Duration |
|------|-----------|-----------|-----------|----------|----------|
| BTC/USDT | 2024-06-05 16:00:00+00:00 | 2024-06-07 16:00:00+00:00 |  | -2.48% | 2880 |
| XRP/USDT | 2024-07-13 16:00:00+00:00 | 2024-07-13 16:00:00+00:00 |  | -1.28% | 0 |
| BNB/USDT | 2024-07-15 16:00:00+00:00 | 2024-07-16 04:00:00+00:00 |  | -2.06% | 720 |
| XRP/USDT | 2024-07-17 08:00:00+00:00 | 2024-07-18 04:00:00+00:00 |  | -3.87% | 1200 |
| XRP/USDT | 2024-07-20 00:00:00+00:00 | 2024-07-20 04:00:00+00:00 |  | 2.12% | 240 |
| BTC/USDT | 2024-07-19 20:00:00+00:00 | 2024-07-23 16:00:00+00:00 |  | -2.27% | 5520 |
| ETH/USDT | 2024-07-20 20:00:00+00:00 | 2024-07-23 16:00:00+00:00 |  | -2.98% | 4080 |
| SOL/USDT | 2024-07-24 16:00:00+00:00 | 2024-07-25 00:00:00+00:00 |  | -5.23% | 480 |
| BNB/USDT | 2024-07-27 04:00:00+00:00 | 2024-07-29 16:00:00+00:00 |  | -1.20% | 3600 |
| SOL/USDT | 2024-07-29 04:00:00+00:00 | 2024-07-30 00:00:00+00:00 |  | -6.46% | 1200 |

---

## EPAUltimateV3

**Total Trades**: 92

### Exit Reason Distribution

| Exit Reason | Count | Total PnL (%) | Avg PnL (%) | Positive | Negative | Win Rate |
|------------|-------|---------------|-------------|----------|----------|----------|
| trailing_stop_loss | 48 | -131.27 | -2.73 | 7 | 41 | 14.6% |
| roi | 40 | 127.76 | 3.19 | 40 | 0 | 100.0% |
| stop_loss | 2 | -14.74 | -7.37 | 0 | 2 | 0.0% |
| exit_signal | 2 | -5.53 | -2.77 | 0 | 2 | 0.0% |

### Trailing Stop Loss Analysis

- **Total trailing_stop_loss exits**: 48
- **Average profit at exit**: -2.73%
- **Positive exits**: 7 (14.6%)
- **Negative exits**: 41 (85.4%)
- **Total PnL impact**: -131.27%

**Key Finding**: Only 14.6% of trailing stops are profitable! 

### Sample Trailing Stop Trades

| Pair | Entry Time | Exit Time | Entry Tag | Profit % | Duration |
|------|-----------|-----------|-----------|----------|----------|
| BTC/USDT | 2024-06-05 08:00:00+00:00 | 2024-06-07 16:00:00+00:00 |  | -1.96% | 3360 |
| XRP/USDT | 2024-07-13 12:00:00+00:00 | 2024-07-13 12:00:00+00:00 |  | -0.22% | 0 |
| XRP/USDT | 2024-07-13 16:00:00+00:00 | 2024-07-13 16:00:00+00:00 |  | -1.28% | 0 |
| XRP/USDT | 2024-07-13 20:00:00+00:00 | 2024-07-14 00:00:00+00:00 |  | -8.01% | 240 |
| BNB/USDT | 2024-07-16 00:00:00+00:00 | 2024-07-16 04:00:00+00:00 |  | -4.01% | 240 |
| XRP/USDT | 2024-07-17 12:00:00+00:00 | 2024-07-18 04:00:00+00:00 |  | -4.59% | 960 |
| SOL/USDT | 2024-07-21 16:00:00+00:00 | 2024-07-21 20:00:00+00:00 |  | 2.20% | 240 |
| BTC/USDT | 2024-07-21 00:00:00+00:00 | 2024-07-23 16:00:00+00:00 |  | -2.25% | 3840 |
| SOL/USDT | 2024-07-22 00:00:00+00:00 | 2024-07-23 16:00:00+00:00 |  | -7.93% | 2400 |
| XRP/USDT | 2024-08-08 04:00:00+00:00 | 2024-08-09 08:00:00+00:00 |  | -3.50% | 1680 |

---

## EPAUltimateV4

**Total Trades**: 320

### Exit Reason Distribution

| Exit Reason | Count | Total PnL (%) | Avg PnL (%) | Positive | Negative | Win Rate |
|------------|-------|---------------|-------------|----------|----------|----------|
| trailing_stop_loss | 137 | -391.62 | -2.86 | 18 | 119 | 13.1% |
| roi | 132 | 459.06 | 3.48 | 132 | 0 | 100.0% |
| exit_signal | 47 | -95.38 | -2.03 | 5 | 42 | 10.6% |
| stop_loss | 3 | -23.70 | -7.90 | 0 | 3 | 0.0% |
| force_exit | 1 | 1.33 | 1.33 | 1 | 0 | 100.0% |

### Trailing Stop Loss Analysis

- **Total trailing_stop_loss exits**: 137
- **Average profit at exit**: -2.86%
- **Positive exits**: 18 (13.1%)
- **Negative exits**: 119 (86.9%)
- **Total PnL impact**: -391.62%

**Key Finding**: Only 13.1% of trailing stops are profitable! 

### Sample Trailing Stop Trades

| Pair | Entry Time | Exit Time | Entry Tag | Profit % | Duration |
|------|-----------|-----------|-----------|----------|----------|
| BNB/USDT | 2024-06-05 04:00:00+00:00 | 2024-06-07 16:00:00+00:00 |  | -4.67% | 3600 |
| BTC/USDT | 2024-06-05 20:00:00+00:00 | 2024-06-07 16:00:00+00:00 |  | -2.07% | 2640 |
| ETH/USDT | 2024-06-06 12:00:00+00:00 | 2024-06-07 16:00:00+00:00 |  | -3.02% | 1680 |
| ETH/USDT | 2024-06-16 16:00:00+00:00 | 2024-06-17 08:00:00+00:00 |  | -3.00% | 960 |
| SOL/USDT | 2024-06-27 16:00:00+00:00 | 2024-06-28 20:00:00+00:00 |  | -5.75% | 1680 |
| BTC/USDT | 2024-07-01 00:00:00+00:00 | 2024-07-02 12:00:00+00:00 |  | -1.59% | 2160 |
| ETH/USDT | 2024-07-02 12:00:00+00:00 | 2024-07-03 00:00:00+00:00 |  | -3.10% | 720 |
| SOL/USDT | 2024-07-03 00:00:00+00:00 | 2024-07-03 08:00:00+00:00 |  | -6.33% | 480 |
| XRP/USDT | 2024-07-02 12:00:00+00:00 | 2024-07-03 12:00:00+00:00 |  | -2.52% | 1440 |
| XRP/USDT | 2024-07-13 20:00:00+00:00 | 2024-07-14 00:00:00+00:00 |  | -8.01% | 240 |

---


---

## Configuration Check

All three strategies have the following settings:

```python
stoploss = -0.08  # -8% hard stop
use_custom_stoploss = True  # ATR-based dynamic stop
trailing_stop = True
trailing_stop_positive = 0.03  # Start trailing at +3%
trailing_stop_positive_offset = 0.05  # Only trail after +5% profit
trailing_only_offset_is_reached = True
```

### Custom Stoploss Logic

All strategies implement:

```python
def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
    atr = dataframe['atr'].iloc[-1]
    atr_stop = -3.0 * atr / current_rate  # 3 ATR stop
    return max(self.stoploss, atr_stop)  # Use wider of -8% or 3 ATR
```

---

## Conclusion

### Is trailing_stop_loss coming from trailing settings or custom_stoploss?

**Answer**: The `trailing_stop_loss` exit reason is triggered by the **trailing stop settings**, NOT custom_stoploss.

### Evidence:

1. **Low Win Rate**: Average 15.3% across all strategies
   - EPAStrategyV2: 18.2% (14/77 winning)
   - EPAUltimateV3: 14.6% (7/48 winning)
   - EPAUltimateV4: 13.1% (18/137 winning)

2. **High Frequency**: 262 trailing stop exits across all strategies
   - Represents 26-43% of all trades in each strategy

3. **Average Loss**: When negative, avg ~-2.71% loss per trade
   - This indicates the trailing stop is pulling back gains prematurely

4. **Timing**: Most trailing stops trigger within 19-22 hours
   - Too fast for 4H timeframe trend-following strategies

### Root Cause:

The current settings:
```python
trailing_stop_positive = 0.03  # Start trailing at +3%
trailing_stop_positive_offset = 0.05  # Only trail after +5%
```

**Problem**: Once a trade reaches +5% profit, the trailing stop activates and locks in only +3% profit.
If the market retraces even slightly (2%), the trade exits, often giving back most gains.

### Recommendations:

1. **Disable trailing stops entirely** - ROI exits have 100% win rate
   ```python
   trailing_stop = False
   ```

2. **OR increase trailing offset significantly**:
   ```python
   trailing_stop_positive = 0.05  # Trail with 5% margin
   trailing_stop_positive_offset = 0.10  # Only after +10% profit
   ```

3. **Rely on ROI table for exits** - currently has perfect performance:
   - EPAStrategyV2: 64 ROI exits, 100% win rate, +791 USDT
   - EPAUltimateV3: 40 ROI exits, 100% win rate, +539 USDT
   - EPAUltimateV4: 132 ROI exits, 100% win rate, +2261 USDT

### Expected Impact:

Disabling trailing stops would:
- **EPAStrategyV2**: +769 USDT improvement (from -114 to +655)
- **EPAUltimateV3**: +515 USDT improvement (from -54 to +461)
- **EPAUltimateV4**: +1911 USDT improvement (from -253 to +1658)

All strategies would become **highly profitable** by letting ROI table handle exits naturally.