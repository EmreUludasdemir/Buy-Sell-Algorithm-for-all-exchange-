"""
Efloud Range + HTF Bias Trigger Rate Audit
===========================================

Analyzes why range/HTF boosts had ZERO impact on profitability.

Checks:
1. How often boost flags trigger at entry time
2. What boost values were computed
3. Whether stake amounts actually changed

Answers:
- (A) Boosts rarely trigger?
- (B) Stake sizing not applied?
- (C) Both?
"""

import json
import zipfile
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# Import strategy to recompute indicators
import sys
sys.path.append(str(Path(__file__).parent.parent / 'user_data' / 'strategies'))

from EPAUltimateV4 import EPAUltimateV4


def load_latest_backtest():
    """Load the most recent backtest result (Variant 2 with both boosts)."""
    backtest_dir = Path(__file__).parent.parent / 'user_data' / 'backtest_results'
    
    # Find most recent backtest ZIP
    zips = sorted(backtest_dir.glob('backtest-result-*.zip'), reverse=True)
    if not zips:
        raise FileNotFoundError("No backtest results found")
    
    latest_zip = zips[0]
    print(f"Loading backtest: {latest_zip.name}")
    
    # Extract trades
    with zipfile.ZipFile(latest_zip, 'r') as z:
        trades_file = [f for f in z.namelist() if f.endswith('.json') and 'trades' in f.lower()]
        if not trades_file:
            raise FileNotFoundError(f"No trades file in {latest_zip.name}")
        
        with z.open(trades_file[0]) as f:
            data = json.load(f)
    
    # Convert to DataFrame
    if isinstance(data, dict) and 'EPAUltimateV4' in data:
        trades = data['EPAUltimateV4']['trades']
    elif isinstance(data, list):
        trades = data
    else:
        raise ValueError(f"Unexpected data format: {type(data)}")
    
    df = pd.DataFrame(trades)
    print(f"Loaded {len(df)} trades")
    return df, latest_zip.name


def load_analyzed_dataframes(strategy, pairs, timerange):
    """Load and analyze dataframes for all pairs (simplified version)."""
    
    # For now, load from feather files directly
    data_dir = Path(__file__).parent.parent / 'user_data' / 'data' / 'binance'
    
    analyzed_dfs = {}
    
    for pair in pairs:
        print(f"Loading and analyzing {pair}...")
        
        # Try to find the pair's data file
        pair_filename = pair.replace('/', '_').lower()
        feather_files = list(data_dir.glob(f"{pair_filename}*.feather"))
        
        if not feather_files:
            print(f"  WARNING: No data file found for {pair}")
            continue
        
        # Load the 4h timeframe data
        timeframe_files = [f for f in feather_files if '4h' in f.name.lower()]
        if not timeframe_files:
            timeframe_files = feather_files  # Fallback
        
        try:
            df = pd.read_feather(timeframe_files[0])
            
            # Populate indicators
            df = strategy.populate_indicators(df, {'pair': pair})
            
            print(f"  Loaded {len(df)} candles")
            analyzed_dfs[pair] = df
        except Exception as e:
            print(f"  ERROR loading {pair}: {e}")
            continue
    
    return analyzed_dfs


def analyze_entry_triggers(trades_df, analyzed_dfs):
    """Analyze boost trigger rates at entry time."""
    
    results = {
        'total_trades': len(trades_df),
        'in_demand_zone_count': 0,
        'reclaim_eq_count': 0,
        'htf_bias_bull_count': 0,
        'range_boost_applied': 0,
        'htf_boost_applied': 0,
        'combined_boost_distribution': {},
        'trades_with_boosts': []
    }
    
    for idx, trade in trades_df.iterrows():
        pair = trade['pair']
        open_date = pd.to_datetime(trade['open_date'])
        
        if pair not in analyzed_dfs:
            continue
        
        df = analyzed_dfs[pair]
        
        # Find the entry candle
        df['date'] = pd.to_datetime(df['date'])
        entry_candle = df[df['date'] == open_date]
        
        if len(entry_candle) == 0:
            # Try finding closest candle
            closest_idx = (df['date'] - open_date).abs().idxmin()
            entry_candle = df.loc[[closest_idx]]
        
        if len(entry_candle) == 0:
            continue
        
        candle = entry_candle.iloc[0]
        
        # Check boost flags
        in_demand = candle.get('in_demand_zone', 0) == 1
        reclaim = candle.get('reclaim_eq', 0) == 1
        htf_bull = candle.get('htf_bias_bull_1d', 0) == 1
        
        if in_demand:
            results['in_demand_zone_count'] += 1
        if reclaim:
            results['reclaim_eq_count'] += 1
        if htf_bull:
            results['htf_bias_bull_count'] += 1
        
        # Calculate boost values (matching EPAUltimateV4.py logic)
        range_boost = 1.0
        if in_demand:
            range_boost += 0.10
        if reclaim:
            range_boost += 0.05
        range_boost = min(range_boost, 1.25)
        
        htf_boost = 1.10 if htf_bull else 1.0
        
        combined_boost = range_boost * htf_boost
        
        if range_boost > 1.0:
            results['range_boost_applied'] += 1
        if htf_boost > 1.0:
            results['htf_boost_applied'] += 1
        
        # Track distribution
        boost_key = f"{combined_boost:.2f}"
        results['combined_boost_distribution'][boost_key] = \
            results['combined_boost_distribution'].get(boost_key, 0) + 1
        
        # Store trade details
        results['trades_with_boosts'].append({
            'pair': pair,
            'open_date': open_date,
            'profit_pct': trade.get('profit_ratio', 0) * 100,
            'in_demand_zone': in_demand,
            'reclaim_eq': reclaim,
            'htf_bias_bull': htf_bull,
            'range_boost': range_boost,
            'htf_boost': htf_boost,
            'combined_boost': combined_boost,
            'stake_amount': trade.get('stake_amount', trade.get('amount', 0))
        })
    
    return results


def analyze_stake_amounts(trades_df, results):
    """Analyze whether stake amounts varied."""
    
    # Extract stake amounts
    if 'stake_amount' in trades_df.columns:
        stakes = trades_df['stake_amount'].dropna()
    elif 'amount' in trades_df.columns:
        stakes = trades_df['amount'].dropna()
    else:
        return {
            'stake_field_found': False,
            'message': "No stake_amount or amount field in trades"
        }
    
    stake_analysis = {
        'stake_field_found': True,
        'unique_stakes': len(stakes.unique()),
        'min_stake': stakes.min(),
        'median_stake': stakes.median(),
        'max_stake': stakes.max(),
        'std_stake': stakes.std(),
        'stake_distribution': stakes.value_counts().to_dict()
    }
    
    # Check correlation with boost
    if results['trades_with_boosts']:
        boosts = [t['combined_boost'] for t in results['trades_with_boosts']]
        stakes_list = [t['stake_amount'] for t in results['trades_with_boosts']]
        
        if len(set(stakes_list)) > 1:  # Stakes vary
            correlation = np.corrcoef(boosts, stakes_list)[0, 1]
            stake_analysis['boost_stake_correlation'] = correlation
        else:
            stake_analysis['boost_stake_correlation'] = None
            stake_analysis['stake_constant'] = True
    
    return stake_analysis


def generate_report(results, stake_analysis, backtest_name):
    """Generate markdown report."""
    
    total = results['total_trades']
    
    report = f"""# Efloud Range + HTF Bias Trigger Rate Audit

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**Backtest:** {backtest_name}  
**Total Trades:** {total}

---

## Executive Summary

"""
    
    # Determine root cause
    boost_rarely_triggers = (results['range_boost_applied'] + results['htf_boost_applied']) < total * 0.1
    stake_not_applied = stake_analysis.get('stake_constant', False) or stake_analysis.get('boost_stake_correlation', 0) < 0.1
    
    if boost_rarely_triggers and stake_not_applied:
        cause = "(C) BOTH"
        report += "**Root Cause:** (C) **BOTH** - Boosts rarely trigger AND stake sizing not applied\n\n"
    elif boost_rarely_triggers:
        cause = "(A) BOOSTS RARELY TRIGGER"
        report += "**Root Cause:** (A) **BOOSTS RARELY TRIGGER** - Conditions almost never met at entry time\n\n"
    elif stake_not_applied:
        cause = "(B) STAKE SIZING NOT APPLIED"
        report += "**Root Cause:** (B) **STAKE SIZING NOT APPLIED** - Boosts computed but not affecting capital allocation\n\n"
    else:
        cause = "UNKNOWN"
        report += "**Root Cause:** UNKNOWN - Further investigation needed\n\n"
    
    report += f"""---

## 1. Boost Trigger Rates at Entry Time

### Range Structure Boost

| Condition | Count | % of Trades |
|-----------|-------|-------------|
| `in_demand_zone` | {results['in_demand_zone_count']} | {results['in_demand_zone_count']/total*100:.1f}% |
| `reclaim_eq` | {results['reclaim_eq_count']} | {results['reclaim_eq_count']/total*100:.1f}% |
| **Range boost applied** (either flag) | **{results['range_boost_applied']}** | **{results['range_boost_applied']/total*100:.1f}%** |

### HTF Bias Boost

| Condition | Count | % of Trades |
|-----------|-------|-------------|
| `htf_bias_bull_1d` | {results['htf_bias_bull_count']} | {results['htf_bias_bull_count']/total*100:.1f}% |
| **HTF boost applied** | **{results['htf_boost_applied']}** | **{results['htf_boost_applied']/total*100:.1f}%** |

**Interpretation:**
"""
    
    if results['range_boost_applied'] < total * 0.05:
        report += f"- Range boost triggered in only {results['range_boost_applied']} trades ({results['range_boost_applied']/total*100:.1f}%) → **RARELY ACTIVE**\n"
    if results['htf_boost_applied'] < total * 0.05:
        report += f"- HTF bias triggered in only {results['htf_boost_applied']} trades ({results['htf_boost_applied']/total*100:.1f}%) → **RARELY ACTIVE**\n"
    
    report += f"""
---

## 2. Combined Boost Distribution

| Boost Multiplier | Trade Count | % of Trades |
|------------------|-------------|-------------|
"""
    
    # Sort by boost value
    sorted_dist = sorted(results['combined_boost_distribution'].items(), key=lambda x: float(x[0]))
    for boost, count in sorted_dist:
        report += f"| {boost}x | {count} | {count/total*100:.1f}% |\n"
    
    baseline_pct = results['combined_boost_distribution'].get('1.00', 0) / total * 100
    report += f"""
**Key Insight:** {baseline_pct:.1f}% of trades had NO boost applied (1.00x baseline)

---

## 3. Stake Amount Analysis

"""
    
    if not stake_analysis['stake_field_found']:
        report += f"""**ERROR:** {stake_analysis['message']}

Cannot verify if boosts affected position sizing without stake_amount data.
"""
    else:
        report += f"""| Metric | Value |
|--------|-------|
| Unique stake values | {stake_analysis['unique_stakes']} |
| Min stake | {stake_analysis['min_stake']:.2f} USDT |
| Median stake | {stake_analysis['median_stake']:.2f} USDT |
| Max stake | {stake_analysis['max_stake']:.2f} USDT |
| Std deviation | {stake_analysis['std_stake']:.2f} USDT |
"""
        
        if stake_analysis.get('stake_constant'):
            report += f"""
**CRITICAL:** All stakes are identical → Boosts did NOT affect position sizing!
"""
        elif stake_analysis.get('boost_stake_correlation') is not None:
            corr = stake_analysis['boost_stake_correlation']
            report += f"""
**Boost ↔ Stake Correlation:** {corr:.3f}
"""
            if corr < 0.1:
                report += "- **Near zero correlation** → Boosts not affecting stake amounts\n"
            elif corr > 0.5:
                report += "- **Strong positive correlation** → Boosts ARE affecting stakes\n"
            else:
                report += "- **Weak correlation** → Boosts may have small effect\n"
        
        # Show stake distribution
        if len(stake_analysis['stake_distribution']) <= 10:
            report += "\n**Stake Distribution:**\n\n"
            for stake, count in sorted(stake_analysis['stake_distribution'].items())[:10]:
                report += f"- {stake:.2f} USDT: {count} trades\n"
    
    report += f"""
---

## 4. Top Trades Comparison

### Top 10 Profitable Trades WITH Boosts

"""
    
    trades_with = [t for t in results['trades_with_boosts'] if t['combined_boost'] > 1.0]
    trades_with.sort(key=lambda x: x['profit_pct'], reverse=True)
    
    if trades_with:
        report += "| Pair | Date | Profit % | Boost | Flags |\n"
        report += "|------|------|----------|-------|-------|\n"
        for t in trades_with[:10]:
            flags = []
            if t['in_demand_zone']: flags.append('DEMAND')
            if t['reclaim_eq']: flags.append('EQ_RECLAIM')
            if t['htf_bias_bull']: flags.append('HTF_BULL')
            report += f"| {t['pair']} | {t['open_date'].strftime('%Y-%m-%d')} | {t['profit_pct']:.2f}% | {t['combined_boost']:.2f}x | {', '.join(flags)} |\n"
    else:
        report += "*No trades had boosts applied*\n"
    
    report += f"""
### Top 10 Profitable Trades WITHOUT Boosts

"""
    
    trades_without = [t for t in results['trades_with_boosts'] if t['combined_boost'] == 1.0]
    trades_without.sort(key=lambda x: x['profit_pct'], reverse=True)
    
    if trades_without:
        report += "| Pair | Date | Profit % |\n"
        report += "|------|------|----------|\n"
        for t in trades_without[:10]:
            report += f"| {t['pair']} | {t['open_date'].strftime('%Y-%m-%d')} | {t['profit_pct']:.2f}% |\n"
    else:
        report += "*All trades had boosts*\n"
    
    report += f"""
---

## 5. Conclusion

**Root Cause:** {cause}

"""
    
    if boost_rarely_triggers:
        report += """
### (A) Boosts Rarely Trigger

**Why:**
- **Range structure conditions** (in_demand_zone, reclaim_eq) align infrequently with entry signals
- **HTF bias** (RSI + OBV + EMA alignment on 1d) is too strict or out of phase with 4h entries
- Entry logic may fire at wrong times relative to range/HTF structure

**Evidence:**
"""
        report += f"- Range boost: {results['range_boost_applied']}/{total} trades ({results['range_boost_applied']/total*100:.1f}%)\n"
        report += f"- HTF boost: {results['htf_boost_applied']}/{total} trades ({results['htf_boost_applied']/total*100:.1f}%)\n"
    
    if stake_not_applied:
        report += """
### (B) Stake Sizing Not Applied

**Why:**
Freqtrade's `custom_stake_amount()` may not be called during backtesting, or the computed boosts are not reaching the stake calculation.

**Evidence:**
"""
        if stake_analysis.get('stake_constant'):
            report += "- All stake amounts identical\n"
        if stake_analysis.get('boost_stake_correlation', 0) < 0.1:
            report += f"- Near-zero correlation ({stake_analysis.get('boost_stake_correlation', 0):.3f}) between boost and stake\n"
    
    report += f"""
---

## 6. Recommendations

"""
    
    if boost_rarely_triggers and stake_not_applied:
        report += """
### Immediate: Remove Feature Entirely

**Reasoning:**
1. Boosts almost never trigger (design flaw)
2. Even when computed, they don't affect stakes (implementation flaw)
3. Zero value + added complexity = negative ROI

**Action:**
```python
# In EPAUltimateV4.py - DELETE these sections:
# - Lines for use_range_boost, use_htf_bias_boost params
# - Range structure integration in populate_indicators()
# - HTF bias calculation
# - Boost application in custom_stake_amount()
```

Also delete:
- `price_action_ranges.py` (unused)
- Range/HTF sections from strategy file

"""
    elif boost_rarely_triggers:
        report += """
### Keep as Research Flags (Default=False)

**Reasoning:**
- Implementation is correct (stake sizing works)
- But conditions rarely align with entries
- May work with different parameters or entry logic

**Future Research:**
1. Try as **entry filters** instead of sizing boosts (may reduce trades but increase quality)
2. Relax HTF bias (e.g., 2-of-3 instead of 3-of-3)
3. Wider demand zones (2x ATR instead of 1x)

"""
    elif stake_not_applied:
        report += """
### Fix Stake Application (If Desired)

**Problem:** Boosts computed but not reaching Freqtrade's position sizing.

**Minimal Fix:**

In `EPAUltimateV4.custom_stake_amount()`, verify:

```python
def custom_stake_amount(self, pair, current_time, current_rate, 
                        proposed_stake, min_stake, max_stake, 
                        leverage, entry_tag, side, **kwargs):
    # ... existing code ...
    
    # EFLOUD BOOSTS (verify this section exists and executes)
    if self.use_range_boost.value:
        range_boost = self._calculate_range_boost(last_candle)
        risk_amount *= range_boost  # ← Must execute
    
    if self.use_htf_bias_boost.value:
        htf_boost = self._calculate_htf_boost(last_candle)
        risk_amount *= htf_boost  # ← Must execute
    
    # Convert risk to stake
    final_stake = risk_amount / stop_distance_pct
    return min(max(final_stake, min_stake), max_stake)
```

**Test:** Re-run backtest with logging to verify boosts applied.

"""
    
    report += """
---

## Appendix: Raw Data

### Trades with Boosts > 1.0

"""
    
    boosted = [t for t in results['trades_with_boosts'] if t['combined_boost'] > 1.0]
    report += f"Count: {len(boosted)}\n\n"
    
    if boosted:
        report += "| Pair | Date | Profit % | Range Boost | HTF Boost | Combined | Stake |\n"
        report += "|------|------|----------|-------------|-----------|----------|-------|\n"
        for t in boosted[:20]:  # First 20
            report += f"| {t['pair']} | {t['open_date'].strftime('%Y-%m-%d %H:%M')} | {t['profit_pct']:.2f}% | {t['range_boost']:.2f}x | {t['htf_boost']:.2f}x | {t['combined_boost']:.2f}x | {t['stake_amount']:.2f} |\n"
    
    return report


def main():
    """Run the audit."""
    print("="*60)
    print("EFLOUD RANGE + HTF BIAS TRIGGER AUDIT")
    print("="*60)
    print()
    
    # Load backtest trades
    trades_df, backtest_name = load_latest_backtest()
    
    # Initialize strategy
    strategy = EPAUltimateV4()
    
    # Load and analyze dataframes
    pairs = trades_df['pair'].unique().tolist()
    timerange = '20240601-20241231'
    
    print(f"\nAnalyzing {len(pairs)} pairs...")
    analyzed_dfs = load_analyzed_dataframes(strategy, pairs, timerange)
    
    # Analyze entry triggers
    print("\nAnalyzing boost triggers at entry time...")
    results = analyze_entry_triggers(trades_df, analyzed_dfs)
    
    # Analyze stake amounts
    print("\nAnalyzing stake amounts...")
    stake_analysis = analyze_stake_amounts(trades_df, results)
    
    # Generate report
    print("\nGenerating report...")
    report = generate_report(results, stake_analysis, backtest_name)
    
    # Save report
    report_path = Path(__file__).parent.parent / 'reports' / 'efloud_trigger_rates.md'
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(report, encoding='utf-8')
    
    print(f"\n{'='*60}")
    print(f"Report saved to: {report_path}")
    print(f"{'='*60}\n")
    
    # Print summary
    print("SUMMARY:")
    print(f"  Total trades: {results['total_trades']}")
    print(f"  Range boost applied: {results['range_boost_applied']} ({results['range_boost_applied']/results['total_trades']*100:.1f}%)")
    print(f"  HTF boost applied: {results['htf_boost_applied']} ({results['htf_boost_applied']/results['total_trades']*100:.1f}%)")
    
    if stake_analysis['stake_field_found']:
        print(f"  Unique stakes: {stake_analysis['unique_stakes']}")
        if stake_analysis.get('boost_stake_correlation') is not None:
            print(f"  Boost ↔ Stake correlation: {stake_analysis['boost_stake_correlation']:.3f}")


if __name__ == "__main__":
    main()
