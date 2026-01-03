# 1H Strategy Debugging Session - 2026-01-03

## Goal

Optimize EPAUltimateV3 for 1H timeframe to increase trade frequency (target: 200-300 trades)

## Attempts

| Version | Entry Logic                      | ROI/SL       | Result   | Learning                   |
| ------- | -------------------------------- | ------------ | -------- | -------------------------- |
| v1.0    | 9 conditions (EMA, OBV, RSI, ST) | 2% / -8%     | 5 trades | Over-filtering             |
| v1.1    | 4 conditions (removed EMA)       | 2% / -8%     | 5 trades | Still too strict           |
| v1.2    | RSI crossover (dynamic)          | 2% / -8%     | 5 trades | RSI rarely crosses in bull |
| v1.3    | SuperTrend flip                  | 2% / -8%     | 5 trades | ST flips are rare          |
| v1.4    | Ultra-tight 0.5% ROI/SL          | 0.5% / -0.5% | 5 trades | Trades don't cycle         |
| v1.5    | 5m detail (tick-level)           | 0.5% / -0.5% | 5 trades | Still no cycling           |

## Root Cause

1H backtest limitation: Trades enter but never exit (ROI/SL not triggered within candles)

- Even 0.5% ROI/SL not hit
- Even with 5m intra-candle checks
- Even "always-true" entry = 5 trades only

## Comparison: 4H vs 1H

| Metric | 4H (EPAUltimateV3) | 1H (all variants) |
| ------ | ------------------ | ----------------- |
| Trades | 181 ✅             | 5 ❌              |
| Profit | 24.53% ✅          | N/A               |
| Works? | YES                | NO                |

## Decision: ABANDON 1H

Reasons:

1. 8 hours debugging = 0 progress
2. 4H proven (181 trades, 24.53%)
3. 1H needs different indicators (MACD, StochRSI) not RSI/ST
4. Time better spent on 4H live deployment

## Key Learnings

1. **Static vs Dynamic Signals**: Static (RSI > 35) holds for hours = 1 trade. Dynamic (RSI crosses) triggers multiple times BUT not in bull markets
2. **Timeframe Suitability**: Not every indicator works on every timeframe. RSI/SuperTrend = 4H good, 1H bad
3. **Know When to Stop**: "Good enough" (4H 24.53%) > "perfect on paper" (1H theory)
4. **Fail Forward**: 8 hours = learned 1H won't work with current indicators. That's valuable.

## Actions Taken

- ✅ Cleaned repo (removed old strategies, AI modules)
- ✅ Restored 1H to realistic settings (archive for future)
- ✅ Started 4H paper trading (7-day trial)
- ✅ Created paper_trading_log.md

## Next Steps

1. Monitor 4H paper trading daily (7 days)
2. If Day 7 profit > 1% → Live with $100
3. Document lessons in CLAUDE.md
