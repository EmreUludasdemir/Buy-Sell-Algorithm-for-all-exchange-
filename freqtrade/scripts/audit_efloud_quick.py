"""
Quick Efloud Boost Trigger Audit
=================================

Simplified version that analyzes exported trades to determine:
1. Are boost flags present in the exported data?
2. Do stake amounts vary?
3. What can we infer about why boosts had zero impact?
"""

import json
import zipfile
from pathlib import Path
from datetime import datetime
import pandas as pd


def load_latest_backtest():
    """Load the most recent backtest result."""
    backtest_dir = Path(__file__).parent.parent / 'user_data' / 'backtest_results'
    
    # Find most recent backtest ZIP (Variant 2)
    target_zip = backtest_dir / 'backtest-result-2026-01-01_21-39-19.zip'
    
    if not target_zip.exists():
        # Fallback to most recent
        zips = sorted(backtest_dir.glob('backtest-result-*.zip'), reverse=True)
        if not zips:
            raise FileNotFoundError("No backtest results found")
        target_zip = zips[0]
    
    print(f"Loading backtest: {target_zip.name}")
    
    # Extract trades
    with zipfile.ZipFile(target_zip, 'r') as z:
        # List files in ZIP
        files = z.namelist()
        print(f"Files in ZIP: {files}")
        
        # Try different possible filenames
        trades_file = None
        for f in files:
            if '.json' in f.lower():
                trades_file = f
                break
        
        if not trades_file:
            raise FileNotFoundError(f"No JSON file in {target_zip.name}")
        
        print(f"Loading {trades_file}")
        with z.open(trades_file) as f:
            data = json.load(f)
    
    # Convert to DataFrame
    print(f"Data type: {type(data)}")
    print(f"Data keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
    
    if isinstance(data, dict):
        # Freqtrade exports have 'strategy' key
        if 'strategy' in data:
            strategy_data = data['strategy']
            print(f"Found 'strategy' key, type: {type(strategy_data)}")
            print(f"Strategy keys: {list(strategy_data.keys()) if isinstance(strategy_data, dict) else 'not a dict'}")
            
            # Look for strategy name
            if isinstance(strategy_data, dict):
                # Should have strategy name as key
                for strategy_name in strategy_data.keys():
                    if strategy_name not in ['results', 'total_profit']:  # Skip summary keys
                        trades_data = strategy_data[strategy_name]
                        print(f"Found strategy '{strategy_name}', type: {type(trades_data)}")
                        if isinstance(trades_data, dict):
                            print(f"Strategy data keys: {list(trades_data.keys())}")
                            if 'trades' in trades_data:
                                trades = trades_data['trades']
                                break
                        else:
                            trades = trades_data
                            break
        # Check for strategy name key directly
        elif 'EPAUltimateV4' in data:
            trades_data = data['EPAUltimateV4']
            print(f"Found EPAUltimateV4, type: {type(trades_data)}")
            if isinstance(trades_data, dict) and 'trades' in trades_data:
                trades = trades_data['trades']
            else:
                trades = trades_data
        elif 'trades' in data:
            trades = data['trades']
        else:
            # Take first strategy
            first_key = list(data.keys())[0]
            if isinstance(data[first_key], dict) and 'trades' in data[first_key]:
                trades = data[first_key]['trades']
            else:
                trades = data
    elif isinstance(data, list):
        trades = data
    else:
        raise ValueError(f"Unexpected data format: {type(data)}")
    
    print(f"Trades type after extraction: {type(trades)}")
    
    # Ensure we have a list
    if not isinstance(trades, list):
        raise ValueError(f"Expected list of trades, got {type(trades)}. Available keys: {list(trades.keys()) if isinstance(trades, dict) else 'N/A'}")
    
    df = pd.DataFrame.from_records(trades)
    print(f"Loaded {len(df)} trades")
    print(f"Columns: {df.columns.tolist()}")
    
    return df, target_zip.name


def analyze_stake_amounts(trades_df):
    """Analyze stake amount variation."""
    
    print("\n" + "="*60)
    print("STAKE AMOUNT ANALYSIS")
    print("="*60)
    
    # Find stake column
    stake_col = None
    for col in ['stake_amount', 'amount', 'cost']:
        if col in trades_df.columns:
            stake_col = col
            break
    
    if not stake_col:
        print("ERROR: No stake/amount column found")
        print(f"Available columns: {trades_df.columns.tolist()}")
        return None
    
    print(f"Using column: {stake_col}")
    
    stakes = trades_df[stake_col].dropna()
    
    analysis = {
        'column_name': stake_col,
        'total_trades': len(trades_df),
        'unique_stakes': len(stakes.unique()),
        'min': stakes.min(),
        'median': stakes.median(),
        'mean': stakes.mean(),
        'max': stakes.max(),
        'std': stakes.std()
    }
    
    print(f"\nTotal trades: {analysis['total_trades']}")
    print(f"Unique stake values: {analysis['unique_stakes']}")
    print(f"Min: {analysis['min']:.2f}")
    print(f"Median: {analysis['median']:.2f}")
    print(f"Mean: {analysis['mean']:.2f}")
    print(f"Max: {analysis['max']:.2f}")
    print(f"Std Dev: {analysis['std']:.2f}")
    
    # Show distribution
    print(f"\nStake distribution (top 10):")
    stake_counts = stakes.value_counts().head(10)
    for stake, count in stake_counts.items():
        print(f"  {stake:.2f} USDT: {count} trades ({count/len(stakes)*100:.1f}%)")
    
    # Check if constant
    if analysis['unique_stakes'] == 1:
        print("\n⚠️  WARNING: All stakes are IDENTICAL!")
        print("   → custom_stake_amount() boosts NOT affecting position sizing")
    elif analysis['std'] < analysis['mean'] * 0.01:  # <1% variation
        print("\n⚠️  WARNING: Stakes have VERY LOW variation")
        print("   → Boosts may not be applied or too small to matter")
    else:
        print("\n✅ Stakes vary significantly")
        print("   → Position sizing IS dynamic (good)")
    
    return analysis


def check_exported_fields(trades_df):
    """Check what fields are in the export."""
    
    print("\n" + "="*60)
    print("EXPORTED FIELDS CHECK")
    print("="*60)
    
    # Look for boost-related fields
    boost_fields = []
    for col in trades_df.columns:
        if any(keyword in col.lower() for keyword in ['boost', 'demand', 'zone', 'eq', 'reclaim', 'htf', 'bias']):
            boost_fields.append(col)
    
    if boost_fields:
        print(f"\nFound {len(boost_fields)} boost-related fields:")
        for field in boost_fields:
            print(f"  - {field}")
            # Show sample values
            sample = trades_df[field].head(10).tolist()
            print(f"    Sample: {sample}")
    else:
        print("\n⚠️  NO boost-related fields found in export")
        print("   → Freqtrade does NOT export custom indicator values")
        print("   → Cannot verify trigger rates from export alone")
    
    # Check for entry_tag (may contain hints)
    if 'entry_tag' in trades_df.columns:
        print(f"\nentry_tag values:")
        entry_tags = trades_df['entry_tag'].value_counts()
        for tag, count in entry_tags.items():
            print(f"  {tag}: {count} trades")
    
    return boost_fields


def analyze_profit_patterns(trades_df):
    """Look for patterns in profit distribution."""
    
    print("\n" + "="*60)
    print("PROFIT PATTERN ANALYSIS")
    print("="*60)
    
    # Find profit column
    profit_col = None
    for col in ['profit_ratio', 'profit_pct', 'profit_abs']:
        if col in trades_df.columns:
            profit_col = col
            break
    
    if not profit_col:
        print("No profit column found")
        return
    
    print(f"Using column: {profit_col}")
    
    profits = trades_df[profit_col]
    
    print(f"\nWinning trades: {(profits > 0).sum()} ({(profits > 0).sum()/len(profits)*100:.1f}%)")
    print(f"Losing trades: {(profits < 0).sum()} ({(profits < 0).sum()/len(profits)*100:.1f}%)")
    
    # Top winners
    print(f"\nTop 10 profitable trades:")
    top_winners = trades_df.nlargest(10, profit_col)
    for idx, trade in top_winners.iterrows():
        pair = trade.get('pair', 'UNKNOWN')
        profit = trade[profit_col]
        stake = trade.get('stake_amount', trade.get('amount', 0))
        date = trade.get('open_date', 'UNKNOWN')
        print(f"  {pair} @ {date}: {profit*100:.2f}% (stake: {stake:.2f})")
    
    # Top losers
    print(f"\nTop 10 losing trades:")
    top_losers = trades_df.nsmallest(10, profit_col)
    for idx, trade in top_losers.iterrows():
        pair = trade.get('pair', 'UNKNOWN')
        profit = trade[profit_col]
        stake = trade.get('stake_amount', trade.get('amount', 0))
        date = trade.get('open_date', 'UNKNOWN')
        print(f"  {pair} @ {date}: {profit*100:.2f}% (stake: {stake:.2f})")


def generate_report(trades_df, stake_analysis, boost_fields, backtest_name):
    """Generate markdown report."""
    
    report = f"""# Efloud Boost Trigger Audit - Quick Analysis

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**Backtest:** {backtest_name}  
**Total Trades:** {len(trades_df)}

---

## Executive Summary

"""
    
    # Determine root cause
    stakes_constant = stake_analysis and stake_analysis['unique_stakes'] == 1
    no_boost_fields = len(boost_fields) == 0
    
    if stakes_constant:
        report += """**Root Cause: (B) STAKE SIZING NOT APPLIED** ❌

All {unique_stakes} trades have IDENTICAL stake amounts ({median:.2f} USDT).

This means:
- `custom_stake_amount()` is either not being called during backtesting
- OR boosts are computed but not affecting the final stake value
- OR Freqtrade is overriding custom stakes with fixed position sizing

**Evidence:**
- Unique stake values: {unique_stakes} (should be >1 if dynamic)
- All trades: {median:.2f} USDT

""".format(**stake_analysis)
    elif not no_boost_fields:
        report += f"""**Root Cause: UNCERTAIN** ⚠️

Stakes vary ({stake_analysis['unique_stakes']} unique values), suggesting dynamic sizing.
Export contains {len(boost_fields)} boost-related fields: {', '.join(boost_fields)}

Need deeper analysis with indicator recalculation to determine trigger rates.

"""
    else:
        report += f"""**Root Cause: UNCERTAIN (Export Incomplete)** ⚠️

Freqtrade export does NOT include custom indicator values (in_demand_zone, reclaim_eq, htf_bias_bull).
Cannot verify trigger rates from export alone.

**Observations:**
- Stakes {"vary" if stake_analysis['unique_stakes'] > 1 else "are constant"} ({stake_analysis['unique_stakes']} unique values)
- Would need to recompute indicators on historical data to check trigger rates

"""
    
    report += f"""---

## 1. Stake Amount Analysis

| Metric | Value |
|--------|-------|
| Column used | `{stake_analysis['column_name']}` |
| Unique values | {stake_analysis['unique_stakes']} |
| Min | {stake_analysis['min']:.2f} USDT |
| Median | {stake_analysis['median']:.2f} USDT |
| Mean | {stake_analysis['mean']:.2f} USDT |
| Max | {stake_analysis['max']:.2f} USDT |
| Std Dev | {stake_analysis['std']:.2f} USDT |
| Coefficient of Variation | {stake_analysis['std']/stake_analysis['mean']*100:.1f}% |

"""
    
    if stakes_constant:
        report += """**CRITICAL FINDING:** 
All stakes are identical → **Boosts did NOT affect position sizing!**

This is the smoking gun. Regardless of whether boost conditions triggered, they clearly did not result in different stake amounts.

Possible causes:
1. `custom_stake_amount()` not called during backtesting
2. Return value from `custom_stake_amount()` ignored
3. Config overrides (e.g., `stake_amount: "unlimited"` with fixed risk)
4. Implementation bug (boosts computed but not returned)

"""
    
    report += f"""---

## 2. Exported Fields Check

"""
    
    if boost_fields:
        report += f"Found {len(boost_fields)} boost-related fields:\n\n"
        for field in boost_fields:
            report += f"- `{field}`\n"
        report += "\n✅ Custom fields ARE exported (good for deeper analysis)\n"
    else:
        report += """**No boost-related fields found in export.**

Freqtrade's `--export trades` does NOT include custom indicator columns.
Only standard fields are exported:
- open_date, close_date
- pair, stake_amount, amount
- profit_ratio, profit_abs
- entry_tag, exit_reason

To check trigger rates, must:
1. Reload historical OHLCV data
2. Recompute indicators via `populate_indicators()`
3. Match trades to entry candles
4. Check flag values at entry time

"""
    
    report += f"""---

## 3. Conclusions

"""
    
    if stakes_constant:
        report += """### Definitive Answer: (B) Stake Sizing NOT Applied

The identical stake amounts across all trades prove that boosts did not affect position sizing.

**Next Steps:**

1. **Verify Config** (`user_data/config.json`):
   ```json
   "stake_amount": "unlimited",  // Must use risk-based sizing
   "tradable_balance_ratio": 0.99,
   ```

2. **Check custom_stake_amount() Integration**:
   - Is the method defined in EPAUltimateV4?
   - Is it returning a stake value (not None)?
   - Are boosts being applied BEFORE the return statement?

3. **Test with Logging**:
   Add logging to `custom_stake_amount()`:
   ```python
   def custom_stake_amount(self, pair, ...):
       # ... compute boosts ...
       logger.info(f"{pair}: range_boost={range_boost:.2f}, htf_boost={htf_boost:.2f}, final_stake={final_stake:.2f}")
       return final_stake
   ```

4. **Re-run Backtest** with logging enabled to see if method is called.

**Recommendation:**
Fix stake sizing integration OR abandon feature (if too complex to fix).

"""
    else:
        report += f"""### Partial Answer: Stakes Vary, But Need Deeper Analysis

**Good news:**
- {stake_analysis['unique_stakes']} unique stake values → Position sizing IS dynamic
- Std dev {stake_analysis['std']:.2f} USDT ({stake_analysis['std']/stake_analysis['mean']*100:.1f}% CV)

**Uncertainty:**
- Export doesn't include boost flag values
- Cannot verify if variance is DUE TO boosts or other factors (volatility, SMC, etc.)

**Next Steps:**

To definitively answer (A) vs (B):
1. Re-run audit with full indicator recalculation
2. Match each trade to its entry candle
3. Check `in_demand_zone`, `reclaim_eq`, `htf_bias_bull` values at entry
4. Calculate expected boost multipliers
5. Correlate with actual stake amounts

OR check Freqtrade logs from backtest for custom_stake_amount() calls.

"""
    
    report += f"""---

## Appendix: Sample Trades

### Top 10 Profitable
"""
    
    profit_col = None
    for col in ['profit_ratio', 'profit_pct', 'profit_abs']:
        if col in trades_df.columns:
            profit_col = col
            break
    
    if profit_col:
        top_winners = trades_df.nlargest(10, profit_col)
        report += "\n| Pair | Date | Profit % | Stake |\n"
        report += "|------|------|----------|-------|\n"
        for _, trade in top_winners.iterrows():
            pair = trade.get('pair', 'UNKNOWN')
            profit = trade[profit_col] * 100 if 'ratio' in profit_col else trade[profit_col]
            stake = trade.get('stake_amount', trade.get('amount', 0))
            date = str(trade.get('open_date', 'UNKNOWN'))[:10]
            report += f"| {pair} | {date} | {profit:.2f}% | {stake:.2f} |\n"
        
        report += "\n### Top 10 Losing\n\n"
        top_losers = trades_df.nsmallest(10, profit_col)
        report += "| Pair | Date | Profit % | Stake |\n"
        report += "|------|------|----------|-------|\n"
        for _, trade in top_losers.iterrows():
            pair = trade.get('pair', 'UNKNOWN')
            profit = trade[profit_col] * 100 if 'ratio' in profit_col else trade[profit_col]
            stake = trade.get('stake_amount', trade.get('amount', 0))
            date = str(trade.get('open_date', 'UNKNOWN'))[:10]
            report += f"| {pair} | {date} | {profit:.2f}% | {stake:.2f} |\n"
    
    return report


def main():
    """Run quick audit."""
    print("="*60)
    print("EFLOUD BOOST QUICK AUDIT")
    print("="*60)
    print()
    
    # Load trades
    trades_df, backtest_name = load_latest_backtest()
    
    # Analyze stake amounts
    stake_analysis = analyze_stake_amounts(trades_df)
    
    # Check exported fields
    boost_fields = check_exported_fields(trades_df)
    
    # Analyze profit patterns
    analyze_profit_patterns(trades_df)
    
    # Generate report
    if stake_analysis:
        print("\nGenerating report...")
        report = generate_report(trades_df, stake_analysis, boost_fields, backtest_name)
        
        # Save report
        report_path = Path(__file__).parent.parent / 'reports' / 'efloud_trigger_rates.md'
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(report, encoding='utf-8')
        
        print(f"\n{'='*60}")
        print(f"Report saved to: {report_path}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
