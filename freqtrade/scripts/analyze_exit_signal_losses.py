#!/usr/bin/env python3
"""
Exit Signal Loss Attribution Analysis

Analyzes backtest trades to identify:
1. Which pairs contribute most to exit_signal losses
2. Indicator states at entry for losing exit_signal trades
3. Whether losses are concentrated in specific regimes
"""

import json
import pandas as pd
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import zipfile

def load_latest_backtest(backtest_dir: Path) -> Tuple[pd.DataFrame, Dict]:
    """Load most recent backtest result"""
    meta_files = sorted(backtest_dir.glob("backtest-result-*.meta.json"), reverse=True)
    if not meta_files:
        raise FileNotFoundError(f"No backtest results found in {backtest_dir}")
    
    meta_file = meta_files[0]
    print(f"Loading: {meta_file.name}")
    
    with open(meta_file) as f:
        meta = json.load(f)
    
    # Load trades - check for ZIP file first
    zip_file = meta_file.parent / meta_file.name.replace('.meta.json', '.zip')
    json_file = meta_file.parent / meta_file.name.replace('.meta.json', '.json')
    
    if zip_file.exists():
        # Extract from ZIP
        with zipfile.ZipFile(zip_file) as z:
            # Find the JSON file inside
            json_files = [f for f in z.namelist() if f.endswith('.json')]
            if not json_files:
                raise FileNotFoundError(f"No JSON file found in {zip_file}")
            with z.open(json_files[0]) as f:
                data = json.load(f)
    elif json_file.exists():
        # Read JSON directly
        with open(json_file) as f:
            data = json.load(f)
    else:
        raise FileNotFoundError(f"Neither {zip_file} nor {json_file} found")
    
    # Handle nested strategy structure
    if 'strategy' in data:
        # Get first strategy
        strategy_name = list(data['strategy'].keys())[0]
        trades_df = pd.DataFrame(data['strategy'][strategy_name]['trades'])
    elif 'trades' in data:
        trades_df = pd.DataFrame(data['trades'])
    else:
        raise KeyError(f"Cannot find trades in data. Keys: {list(data.keys())}")
    
    return trades_df, meta


def analyze_exit_signal_losses(trades_df: pd.DataFrame) -> pd.DataFrame:
    """Filter and analyze exit_signal losses"""
    exit_sig = trades_df[trades_df['exit_reason'] == 'exit_signal'].copy()
    
    # Calculate profit in USDT
    exit_sig['profit_usdt'] = exit_sig['profit_abs']
    
    # Add helpful columns
    exit_sig['duration_hours'] = (pd.to_datetime(exit_sig['close_date']) - 
                                   pd.to_datetime(exit_sig['open_date'])).dt.total_seconds() / 3600
    
    return exit_sig


def pair_attribution(exit_sig: pd.DataFrame) -> pd.DataFrame:
    """Rank pairs by exit_signal losses"""
    pair_stats = exit_sig.groupby('pair').agg({
        'profit_usdt': ['sum', 'mean', 'count'],
        'profit_ratio': 'mean'
    }).round(3)
    
    pair_stats.columns = ['total_loss_usdt', 'avg_loss_usdt', 'trade_count', 'avg_loss_pct']
    pair_stats = pair_stats.sort_values('total_loss_usdt')
    return pair_stats


def analyze_entry_indicators(exit_sig: pd.DataFrame) -> Dict:
    """
    Analyze indicator states at entry for losing exit_signal trades.
    Note: This requires the trades CSV has indicator columns.
    """
    results = {}
    
    # Check which indicator columns are available
    indicator_cols = [col for col in exit_sig.columns if col.startswith('enter_')]
    
    if not indicator_cols:
        results['warning'] = "No entry indicator columns found in trades export"
        return results
    
    # For each indicator column, show distribution
    for col in indicator_cols:
        if exit_sig[col].dtype in ['int64', 'float64']:
            results[col] = {
                'mean': float(exit_sig[col].mean()),
                'median': float(exit_sig[col].median()),
                'min': float(exit_sig[col].min()),
                'max': float(exit_sig[col].max())
            }
        elif exit_sig[col].dtype == 'bool':
            results[col] = {
                'true_count': int(exit_sig[col].sum()),
                'false_count': int((~exit_sig[col]).sum()),
                'true_pct': float(exit_sig[col].mean() * 100)
            }
    
    return results


def regime_analysis(exit_sig: pd.DataFrame) -> Dict:
    """
    Identify if losses are concentrated in specific regimes.
    Uses available columns to infer regime characteristics.
    """
    results = {}
    
    # Check for ADX
    if 'enter_adx' in exit_sig.columns:
        low_adx = exit_sig[exit_sig['enter_adx'] < 20]
        high_adx = exit_sig[exit_sig['enter_adx'] >= 20]
        
        results['adx_regime'] = {
            'low_adx_lt20': {
                'count': len(low_adx),
                'total_loss': float(low_adx['profit_usdt'].sum()),
                'avg_loss': float(low_adx['profit_usdt'].mean())
            },
            'high_adx_gte20': {
                'count': len(high_adx),
                'total_loss': float(high_adx['profit_usdt'].sum()),
                'avg_loss': float(high_adx['profit_usdt'].mean())
            }
        }
    
    # Check for volume regime
    if 'enter_volume' in exit_sig.columns and 'enter_volume_mean_30' in exit_sig.columns:
        low_vol = exit_sig[exit_sig['enter_volume'] < exit_sig['enter_volume_mean_30']]
        high_vol = exit_sig[exit_sig['enter_volume'] >= exit_sig['enter_volume_mean_30']]
        
        results['volume_regime'] = {
            'low_volume': {
                'count': len(low_vol),
                'total_loss': float(low_vol['profit_usdt'].sum()),
                'avg_loss': float(low_vol['profit_usdt'].mean())
            },
            'high_volume': {
                'count': len(high_vol),
                'total_loss': float(high_vol['profit_usdt'].sum()),
                'avg_loss': float(high_vol['profit_usdt'].mean())
            }
        }
    
    # Check for trend regime (EMA slope)
    if 'enter_ema200_slope' in exit_sig.columns:
        down_trend = exit_sig[exit_sig['enter_ema200_slope'] < 0]
        up_trend = exit_sig[exit_sig['enter_ema200_slope'] >= 0]
        
        results['trend_regime'] = {
            'ema200_slope_down': {
                'count': len(down_trend),
                'total_loss': float(down_trend['profit_usdt'].sum()),
                'avg_loss': float(down_trend['profit_usdt'].mean())
            },
            'ema200_slope_up': {
                'count': len(up_trend),
                'total_loss': float(up_trend['profit_usdt'].sum()),
                'avg_loss': float(up_trend['profit_usdt'].mean())
            }
        }
    
    return results


def generate_markdown_report(pair_stats: pd.DataFrame, 
                             indicator_analysis: Dict,
                             regime_analysis: Dict,
                             total_exit_sig_loss: float,
                             output_path: Path):
    """Generate comprehensive markdown report"""
    
    report = f"""# Exit Signal Loss Attribution Analysis
**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Strategy:** EPAUltimateV3  
**Timerange:** 2024-06-01 to 2024-12-31  

---

## Executive Summary

**Total exit_signal losses:** {total_exit_sig_loss:.2f} USDT across {len(pair_stats)} pairs

**Key Finding:** This report identifies which pairs, indicator states, and market regimes contribute most to exit_signal losses, enabling targeted entry/regime filters.

---

## 1. Pair Attribution

Ranked by total loss contribution:

| Pair | Trade Count | Total Loss (USDT) | Avg Loss (USDT) | Avg Loss (%) |
|------|-------------|-------------------|-----------------|--------------|
"""
    
    for pair, row in pair_stats.iterrows():
        report += f"| {pair} | {int(row['trade_count'])} | {row['total_loss_usdt']:.2f} | {row['avg_loss_usdt']:.2f} | {row['avg_loss_pct']*100:.2f}% |\n"
    
    report += "\n**Analysis:**\n"
    worst_pair = pair_stats.index[0]
    worst_loss = pair_stats.iloc[0]['total_loss_usdt']
    worst_pct = (worst_loss / total_exit_sig_loss) * 100
    report += f"- **{worst_pair}** is the worst contributor: {worst_loss:.2f} USDT ({worst_pct:.1f}% of total)\n"
    
    top_3_loss = pair_stats.head(3)['total_loss_usdt'].sum()
    top_3_pct = (top_3_loss / total_exit_sig_loss) * 100
    report += f"- **Top 3 pairs** account for {top_3_loss:.2f} USDT ({top_3_pct:.1f}% of total losses)\n"
    
    report += "\n---\n\n## 2. Entry Indicator States\n\n"
    
    if 'warning' in indicator_analysis:
        report += f"⚠️ {indicator_analysis['warning']}\n\n"
        report += "**Action Required:** Re-run backtest with `--export trades` to capture indicator data:\n"
        report += "```bash\n"
        report += "docker compose run --rm freqtrade backtesting \\\n"
        report += "  --strategy EPAUltimateV3 \\\n"
        report += "  --timerange 20240601-20241231 \\\n"
        report += "  --timeframe 4h \\\n"
        report += "  --export trades\n"
        report += "```\n"
    else:
        report += "Indicator states at entry for losing exit_signal trades:\n\n"
        
        # Numeric indicators
        numeric_indicators = {k: v for k, v in indicator_analysis.items() 
                            if isinstance(v, dict) and 'mean' in v}
        if numeric_indicators:
            report += "### Numeric Indicators\n\n"
            report += "| Indicator | Mean | Median | Min | Max |\n"
            report += "|-----------|------|--------|-----|-----|\n"
            for ind, stats in numeric_indicators.items():
                report += f"| {ind} | {stats['mean']:.3f} | {stats['median']:.3f} | {stats['min']:.3f} | {stats['max']:.3f} |\n"
            report += "\n"
        
        # Boolean indicators
        bool_indicators = {k: v for k, v in indicator_analysis.items() 
                         if isinstance(v, dict) and 'true_count' in v}
        if bool_indicators:
            report += "### Boolean Indicators\n\n"
            report += "| Indicator | True Count | False Count | True % |\n"
            report += "|-----------|------------|-------------|--------|\n"
            for ind, stats in bool_indicators.items():
                report += f"| {ind} | {stats['true_count']} | {stats['false_count']} | {stats['true_pct']:.1f}% |\n"
            report += "\n"
    
    report += "---\n\n## 3. Regime Analysis\n\n"
    
    if not regime_analysis:
        report += "⚠️ No regime columns found in trades data.\n\n"
    else:
        if 'adx_regime' in regime_analysis:
            report += "### ADX Regime\n\n"
            adx = regime_analysis['adx_regime']
            low = adx['low_adx_lt20']
            high = adx['high_adx_gte20']
            
            report += "| Regime | Trade Count | Total Loss (USDT) | Avg Loss (USDT) |\n"
            report += "|--------|-------------|-------------------|------------------|\n"
            report += f"| ADX < 20 (weak trend) | {low['count']} | {low['total_loss']:.2f} | {low['avg_loss']:.2f} |\n"
            report += f"| ADX >= 20 (strong trend) | {high['count']} | {high['total_loss']:.2f} | {high['avg_loss']:.2f} |\n"
            report += "\n"
            
            if low['count'] > 0 and high['count'] > 0:
                low_pct = (low['total_loss'] / total_exit_sig_loss) * 100
                report += f"**Finding:** Low ADX (weak trend) trades contribute {low_pct:.1f}% of exit_signal losses.\n\n"
        
        if 'volume_regime' in regime_analysis:
            report += "### Volume Regime\n\n"
            vol = regime_analysis['volume_regime']
            low = vol['low_volume']
            high = vol['high_volume']
            
            report += "| Regime | Trade Count | Total Loss (USDT) | Avg Loss (USDT) |\n"
            report += "|--------|-------------|-------------------|------------------|\n"
            report += f"| Below avg volume | {low['count']} | {low['total_loss']:.2f} | {low['avg_loss']:.2f} |\n"
            report += f"| Above avg volume | {high['count']} | {high['total_loss']:.2f} | {high['avg_loss']:.2f} |\n"
            report += "\n"
        
        if 'trend_regime' in regime_analysis:
            report += "### EMA200 Trend Regime\n\n"
            trend = regime_analysis['trend_regime']
            down = trend['ema200_slope_down']
            up = trend['ema200_slope_up']
            
            report += "| Regime | Trade Count | Total Loss (USDT) | Avg Loss (USDT) |\n"
            report += "|--------|-------------|-------------------|------------------|\n"
            report += f"| EMA200 slope DOWN | {down['count']} | {down['total_loss']:.2f} | {down['avg_loss']:.2f} |\n"
            report += f"| EMA200 slope UP | {up['count']} | {up['total_loss']:.2f} | {up['avg_loss']:.2f} |\n"
            report += "\n"
            
            if down['count'] > 0 and up['count'] > 0:
                down_pct = (down['total_loss'] / total_exit_sig_loss) * 100
                report += f"**Finding:** Entries during EMA200 downtrend contribute {down_pct:.1f}% of exit_signal losses.\n\n"
    
    report += "---\n\n## 4. Recommendations\n\n"
    report += "Based on this attribution analysis, consider implementing:\n\n"
    
    report += "### Filter Candidate 1: EMA200 Slope Filter\n"
    report += "- **Logic:** Only enter long trades when 4h EMA200 slope > 0 (uptrend)\n"
    report += "- **Rationale:** If EMA200 downtrend trades show disproportionate losses\n"
    report += "- **Risk:** May reduce trade count significantly\n\n"
    
    report += "### Filter Candidate 2: ADX Minimum Threshold\n"
    report += "- **Logic:** Only enter when ADX >= 20 (strong trend)\n"
    report += "- **Rationale:** Weak trend entries may be prone to whipsaw\n"
    report += "- **Risk:** May miss early trend entries\n\n"
    
    report += "### Next Steps\n"
    report += "1. Implement both filters as feature flags (default OFF)\n"
    report += "2. Run 4-variant ablation:\n"
    report += "   - Baseline (both OFF)\n"
    report += "   - Filter1 ON (EMA200 slope)\n"
    report += "   - Filter2 ON (ADX threshold)\n"
    report += "   - Both ON\n"
    report += "3. Compare:\n"
    report += "   - Total profit (must be >= baseline 10.03%)\n"
    report += "   - stop_loss count (must be <= 9)\n"
    report += "   - exit_signal loss reduction\n"
    report += "   - Trade count impact\n"
    report += "4. Enable winner if acceptance criteria met\n\n"
    
    report += "---\n\n"
    report += "*Note: This analysis focuses on identifying root causes at entry, not exit tweaks.*\n"
    
    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Report written to: {output_path}")


def main():
    # Paths
    repo_root = Path(__file__).parent.parent
    backtest_dir = repo_root / 'user_data' / 'backtest_results'
    output_path = repo_root / 'reports' / 'exit_signal_attribution.md'
    
    print("=" * 60)
    print("EXIT SIGNAL LOSS ATTRIBUTION ANALYSIS")
    print("=" * 60)
    
    # Load data
    trades_df, meta = load_latest_backtest(backtest_dir)
    print(f"Loaded {len(trades_df)} total trades")
    
    # Filter exit_signal trades
    exit_sig = analyze_exit_signal_losses(trades_df)
    print(f"Found {len(exit_sig)} exit_signal trades")
    
    total_loss = exit_sig['profit_usdt'].sum()
    print(f"Total exit_signal loss: {total_loss:.2f} USDT")
    
    # Run analyses
    print("\n1. Analyzing pair attribution...")
    pair_stats = pair_attribution(exit_sig)
    
    print("2. Analyzing entry indicator states...")
    indicator_analysis = analyze_entry_indicators(exit_sig)
    
    print("3. Analyzing regime concentration...")
    regime_results = regime_analysis(exit_sig)
    
    # Generate report
    print("\n4. Generating markdown report...")
    generate_markdown_report(pair_stats, indicator_analysis, regime_results, 
                           total_loss, output_path)
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
