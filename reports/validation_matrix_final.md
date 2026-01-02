# V2 Regime Exit Validation Matrix

**Date**: 2026-01-02  
**Strategy**: EPAUltimateV3 vs EPAUltimateV3_RegimeBTC  
**Timeframe**: 4H  
**Pairs**: BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT, XRP/USDT

---

## 1. Data Availability Check

| Pair     | 4H Data | 1D Data | Status |
| -------- | ------- | ------- | ------ |
| BTC/USDT | ✅      | ✅      | OK     |
| ETH/USDT | ✅      | ✅      | OK     |
| BNB/USDT | ✅      | ✅      | OK     |
| SOL/USDT | ✅      | ✅      | OK     |
| XRP/USDT | ✅      | ✅      | OK     |

**Timeranges Available**:

- T1: 20240101-20240531 ✅
- T2: 20240601-20241231 ✅
- T3: 20250101-20251231 ✅

---

## 2. Full Results Table

| Timerange         | Strategy                | Profit%    | USDT    | DD%       | Trades | WR%   | SL  | ES  | ROI | Delta       |
| ----------------- | ----------------------- | ---------- | ------- | --------- | ------ | ----- | --- | --- | --- | ----------- |
| T1 (Jan-May 2024) | EPAUltimateV3           | **17.39%** | +347.76 | 8.44%     | 44     | 79.5% | 3   | 6   | 35  | baseline    |
| T1 (Jan-May 2024) | EPAUltimateV3_RegimeBTC | 7.92%      | +158.37 | 8.78%     | 44     | 65.9% | 3   | 18  | 23  | **-9.47%**  |
| T2 (Jun-Dec 2024) | EPAUltimateV3           | 5.84%      | +116.75 | 8.10%     | 72     | 70.8% | 10  | 11  | 49  | baseline    |
| T2 (Jun-Dec 2024) | EPAUltimateV3_RegimeBTC | **6.18%**  | +123.55 | **7.23%** | 73     | 52.1% | 9   | 29  | 33  | **+0.34%**  |
| T3 (2025)         | EPAUltimateV3           | **7.45%**  | +149.02 | 10.19%    | 104    | 66.3% | 19  | 16  | 68  | baseline    |
| T3 (2025)         | EPAUltimateV3_RegimeBTC | -5.31%     | -106.17 | 10.60%    | 108    | 52.8% | 13  | 47  | 45  | **-12.76%** |

> **Legend**: SL = stop_loss exits, ES = exit_signal exits, ROI = roi exits

---

## 3. Per-Timerange Verdict

### T1: 2024-01-01 to 2024-05-31 (Alt Window)

| Metric          | Baseline (V3) | V2 (RegimeBTC) | Comparison     |
| --------------- | ------------- | -------------- | -------------- |
| Profit %        | 17.39%        | 7.92%          | ❌ V2 -9.47%   |
| Max DD %        | 8.44%         | 8.78%          | ❌ V2 worse DD |
| Stop Loss Count | 3             | 3              | = same         |
| Win Rate        | 79.5%         | 65.9%          | ❌ V2 worse    |

**ACCEPTANCE CRITERIA**:

- SL count: 3 ≤ 3 ✅
- Profit: 7.92% < 17.39% ❌
- Profit drop (9.47%) > 1% AND DD worse ❌

> **T1 VERDICT: ❌ FAIL** - Massive profit degradation with no DD improvement

---

### T2: 2024-06-01 to 2024-12-31 (Benchmark)

| Metric          | Baseline (V3) | V2 (RegimeBTC) | Comparison          |
| --------------- | ------------- | -------------- | ------------------- |
| Profit %        | 5.84%         | 6.18%          | ✅ V2 +0.34%        |
| Max DD %        | 8.10%         | 7.23%          | ✅ V2 -0.87% better |
| Stop Loss Count | 10            | 9              | ✅ V2 better        |
| Win Rate        | 70.8%         | 52.1%          | ❌ V2 worse         |

**ACCEPTANCE CRITERIA**:

- SL count: 9 ≤ 10 ✅
- Profit: 6.18% > 5.84% ✅
- DD improved by 0.87% ✅

> **T2 VERDICT: ✅ PASS** - V2 wins with slightly higher profit AND significantly lower DD

---

### T3: 2025-01-01 to 2025-12-28 (Forward Test)

| Metric          | Baseline (V3) | V2 (RegimeBTC) | Comparison     |
| --------------- | ------------- | -------------- | -------------- |
| Profit %        | 7.45%         | -5.31%         | ❌ V2 -12.76%  |
| Max DD %        | 10.19%        | 10.60%         | ❌ V2 worse DD |
| Stop Loss Count | 19            | 13             | ✅ V2 better   |
| Win Rate        | 66.3%         | 52.8%          | ❌ V2 worse    |

**ACCEPTANCE CRITERIA**:

- SL count: 13 ≤ 19 ✅
- Profit: -5.31% << 7.45% ❌ (NEGATIVE vs POSITIVE)
- DD worse ❌

> **T3 VERDICT: ❌ FAIL** - V2 turns positive strategy into losing strategy

---

## 4. Final Decision

### Summary Score

| Timerange     | V2 Verdict |
| ------------- | ---------- |
| T1 Alt Window | ❌ FAIL    |
| T2 Benchmark  | ✅ PASS    |
| T3 Forward    | ❌ FAIL    |

**Score: 1/3 PASS**

> [!CAUTION]
>
> ## FINAL VERDICT: ❌ REJECT
>
> V2 (regime_exit + btc_tight_exit) **loses on 2 of 3 timeranges**.
>
> - T1: -9.47% profit degradation
> - T3: Strategy goes from +7.45% to -5.31% (net -12.76%)
> - The regime exit triggers too aggressively, cutting winning trades prematurely

### Root Cause Analysis

1. **Regime Exit Problem**: The `choppiness > 62` threshold triggers exit_signal exits too frequently:

   - T1: exit_signal increased from 6 to 18
   - T2: exit_signal increased from 11 to 29
   - T3: exit_signal increased from 16 to 47

2. **Win Rate Collapse**: All timeranges show reduced win rate (~15-20% lower)

3. **ROI Cannibalization**: Fewer trades reach ROI targets due to premature exits

---

## 5. Recommendation

Keep EPAUltimateV3 defaults unchanged:

```python
use_regime_exit = False  # Keep disabled
use_btc_exit_tightening = False  # Keep disabled
```

### Future Investigation Options

1. **Tune choppiness threshold**: Try 70+ instead of 62
2. **Add profit protection**: Only trigger regime exit if profit < 0
3. **Time-based filter**: Don't exit within first 8h of trade

---

## 6. Commands Used

```bash
# Data check
docker compose run --rm freqtrade list-data --config user_data/config.json

# Backtest commands (6 total)
docker compose run --rm freqtrade backtesting --strategy EPAUltimateV3 --timerange 20240101-20240531 --timeframe 4h --cache none
docker compose run --rm freqtrade backtesting --strategy EPAUltimateV3_RegimeBTC --timerange 20240101-20240531 --timeframe 4h --cache none
docker compose run --rm freqtrade backtesting --strategy EPAUltimateV3 --timerange 20240601-20241231 --timeframe 4h --cache none
docker compose run --rm freqtrade backtesting --strategy EPAUltimateV3_RegimeBTC --timerange 20240601-20241231 --timeframe 4h --cache none
docker compose run --rm freqtrade backtesting --strategy EPAUltimateV3 --timerange 20250101-20251231 --timeframe 4h --cache none
docker compose run --rm freqtrade backtesting --strategy EPAUltimateV3_RegimeBTC --timerange 20250101-20251231 --timeframe 4h --cache none
```

---

## Raw Results Files

- [T1_baseline.txt](file:///c:/Users/Emre/Desktop/Buy-sell%20Algorithm/Buy-Sell-Algorithm-for-all-exchange-/freqtrade/T1_baseline.txt)
- [T1_v2.txt](file:///c:/Users/Emre/Desktop/Buy-sell%20Algorithm/Buy-Sell-Algorithm-for-all-exchange-/freqtrade/T1_v2.txt)
- [T2_baseline.txt](file:///c:/Users/Emre/Desktop/Buy-sell%20Algorithm/Buy-Sell-Algorithm-for-all-exchange-/freqtrade/T2_baseline.txt)
- [T2_v2.txt](file:///c:/Users/Emre/Desktop/Buy-sell%20Algorithm/Buy-Sell-Algorithm-for-all-exchange-/freqtrade/T2_v2.txt)
- [T3_baseline.txt](file:///c:/Users/Emre/Desktop/Buy-sell%20Algorithm/Buy-Sell-Algorithm-for-all-exchange-/freqtrade/T3_baseline.txt)
- [T3_v2.txt](file:///c:/Users/Emre/Desktop/Buy-sell%20Algorithm/Buy-Sell-Algorithm-for-all-exchange-/freqtrade/T3_v2.txt)
