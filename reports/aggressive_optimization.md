# Aggressive ROI Optimization Report

**Date:** 2026-01-02  
**Timerange:** 2024-06-01 to 2024-12-31 (7 months)  
**Wallet:** 2000 USDT  
**Baseline Reference:** 10.03% profit (full year), 6.69% DD, 72 trades

---

## Executive Summary

**FINDING: The patient ROI table outperforms aggressive ROI.**

Contrary to the hypothesis that faster profit-taking would increase returns, the patient ROI table allows trades to reach higher profit targets, resulting in better overall performance.

---

## Test Configurations

| Variant               | ROI Table                                    | Pairs | Description                    |
| --------------------- | -------------------------------------------- | ----- | ------------------------------ |
| **V3 Patient ROI**    | 0: 12%, 360: 8%, 720: 5%, 1440: 3%, 2880: 2% | 5     | Original baseline              |
| **V3_Agg (5 pairs)**  | 0: 8%, 180: 5%, 360: 3%, 720: 2%, 1440: 1.5% | 5     | Aggressive ROI only            |
| **V3_Agg (10 pairs)** | Same aggressive                              | 10    | + DOGE, AVAX, LINK, ADA, MATIC |

---

## Results Comparison

| Metric          | V3 Patient ROI | V3_Agg (5 pairs) | V3_Agg (10 pairs) |
| --------------- | -------------- | ---------------- | ----------------- |
| **Trades**      | 75             | 94               | 189               |
| **Win Rate**    | 70.7%          | 74.5%            | 74.6%             |
| **Profit USDT** | **122.79**     | 92.70            | 76.50             |
| **Profit %**    | **6.14%**      | 4.63%            | 3.83%             |
| **Max DD**      | 8.67%          | 7.18%            | 12.94%            |
| **ROI Exits**   | 51             | 70               | 141               |
| **Stop Loss**   | 10             | 13               | 31                |

---

## Analysis

### Why Aggressive ROI Underperforms:

1. **Earlier Exit = Lower Per-Trade Profit**
   - Patient ROI allows trades to reach 12% initial target
   - Aggressive ROI caps at 8%, leaving money on the table
2. **More Trades ≠ More Profit**

   - V3_Agg 5 pairs: 94 trades but only 92.70 USDT profit
   - V3 Patient: 75 trades but 122.79 USDT profit
   - **Average profit per trade:** Patient = 1.64 USDT, Aggressive = 0.99 USDT

3. **Pair Expansion Dilutes Quality**
   - Adding pairs increased stop-loss hits from 10 to 31
   - New pairs (DOGE, AVAX, LINK, ADA, MATIC) contributed to higher DD
   - DD jumped from 8.67% to 12.94% (exceeds 10% threshold)

### Why Patient ROI Works Better:

- 4H timeframe trades benefit from holding through volatility
- Market momentum often continues beyond 8% initial move
- Fewer exits = fewer re-entry costs and slippage

---

## Verdict

> **KEEP BASELINE (EPAUltimateV3)**
>
> - Do NOT use aggressive ROI table
> - Do NOT expand to 10 pairs
> - The patient ROI table is optimal for 4H timeframe

---

## Recommendations

1. **Keep current ROI table:** `{"0": 0.12, "360": 0.08, "720": 0.05, "1440": 0.03, "2880": 0.02}`

2. **Keep 5 pairs:** BTC, BNB, ETH, SOL, XRP

3. **Alternative optimization paths:**
   - Focus on entry signal quality (higher WR)
   - Explore trailing stop optimization
   - Consider longer holding periods

---

## Files Modified

- `config.json` - Restored to 5 pairs (was temporarily set to 10)
- `EPAUltimateV3_Aggressive.py` - Available for reference but NOT recommended

---

_Report generated automatically from backtest comparison_
