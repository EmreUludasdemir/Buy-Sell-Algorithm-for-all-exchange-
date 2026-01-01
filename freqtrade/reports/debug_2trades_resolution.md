# Debug Report: 2-Trade Issue Resolution

**Date:** 2026-01-01  
**Issue:** All strategies producing only 2 trades in 7 months  

## Root Cause: Insufficient Trading Pairs

The original config only had **2 pairs** (BTC/USDT, BNB/USDT), which severely limited trade opportunities on a 4H timeframe.

### Before Fix
```json
"pair_whitelist": [
    "BTC/USDT",
    "BNB/USDT"
]
```
**Result:** 2 trades

### After Fix
```json
"pair_whitelist": [
    "BTC/USDT",
    "BNB/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT"
]
```
**Result:** 98-173 trades

## Backtest Results Summary (2024-06-01 to 2024-12-31)

| Strategy | Trades | Win Rate | Profit % | Drawdown |
|----------|--------|----------|----------|----------|
| EPAMinimalTest (EMA) | 105 | 31.4% | +6.61% | 2.88% |
| EPAStrategyV2 | 173 | 63.0% | -17.5% | 21.67% |
| EPAUltimateV3 | 98 | 68.4% | -6.65% | 10.87% |

## Key Findings

### ✅ Kıvanç Indicators ARE Working
- Supertrend, HalfTrend, and QQE are producing valid signals
- No indicator bugs found
- All strategies generate trades when given sufficient pairs

### ⚠️ Strategy Performance Needs Optimization
Despite high win rates (63-68%), both advanced strategies are unprofitable:

1. **EPAStrategyV2** (173 trades, 63% wins):
   - Stop losses (-5.19% avg) are too expensive
   - 44 stop loss exits costing -696 USDT
   - Trailing stops are working well (+618 USDT)

2. **EPAUltimateV3** (98 trades, 68.4% wins):
   - Better than V2 but still -6.65%
   - 24 stop losses costing -463 USDT
   - ROI and trailing stops profitable (+541 USDT)

### 📊 Simple EMA Strategy Outperforms
The minimal EMA cross strategy (+6.61%) outperforms the complex strategies, suggesting:
- Over-filtering of entries
- Stop losses too tight (-5% stoploss is triggered too often)
- Need to tune Kıvanç indicator thresholds

## Recommendations

1. **Increase pairs to 10+** for more diversification
2. **Widen stoploss** from -5% to -8% or -10%
3. **Reduce min_kivanc_signals** from 3 to 2 for more entries
4. **Add trailing stop earlier** to lock in smaller profits
5. **Run hyperopt** on new 5-pair configuration

## Files Changed

- `user_data/config.json`: Added ETH, SOL, XRP pairs
- Created test strategies: EPAMinimalTest.py, EPASimpleTest.py
- Created debug_indicators.py (not executed due to Docker limitations)

## Next Steps

1. Add more pairs (AVAX, DOGE, ADA, LINK, MATIC)
2. Download 1D data for HTF analysis
3. Run hyperopt to optimize parameters
4. Consider simpler strategy as baseline
