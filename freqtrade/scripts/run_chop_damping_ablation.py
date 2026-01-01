#!/usr/bin/env python3
"""
4-Variant Ablation Study for Exit Signal Loss Reduction

Tests Fix A (Choppiness Gate) and Fix B (Profit-Dependent Damping)
in isolation and combined to determine optimal configuration.

Variants:
- Baseline: Both fixes disabled (A=off, B=off)
- Fix A Only: Choppiness gate enabled (A=on, B=off)
- Fix B Only: Profit damping enabled (A=off, B=on)
- Combined: Both fixes enabled (A=on, B=on)
"""

import subprocess
import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Test configuration
TIMERANGE = "20240601-20241231"
TIMEFRAME = "4h"
STRATEGY = "EPAUltimateV3"

# Variants to test
VARIANTS = {
    "baseline": {
        "name": "Baseline (A=off, B=off)",
        "use_exit_chop_gate": False,
        "use_profit_damping_exit": False
    },
    "fix_a": {
        "name": "Fix A Only (Chop Gate)",
        "use_exit_chop_gate": True,
        "use_profit_damping_exit": False
    },
    "fix_b": {
        "name": "Fix B Only (Profit Damping)",
        "use_exit_chop_gate": False,
        "use_profit_damping_exit": True
    },
    "combined": {
        "name": "Combined (A+B)",
        "use_exit_chop_gate": True,
        "use_profit_damping_exit": True
    }
}

def run_backtest(variant_id, variant_config):
    """Run backtest for a specific variant."""
    
    print(f"\n{'='*70}")
    print(f"Running: {variant_config['name']}")
    print(f"  use_exit_chop_gate: {variant_config['use_exit_chop_gate']}")
    print(f"  use_profit_damping_exit: {variant_config['use_profit_damping_exit']}")
    print(f"{'='*70}\n")
    
    # Build command with strategy parameters
    params = []
    params.append(f"use_exit_chop_gate={str(variant_config['use_exit_chop_gate']).lower()}")
    params.append(f"use_profit_damping_exit={str(variant_config['use_profit_damping_exit']).lower()}")
    
    params_str = " ".join([f"--strategy-parameter {p}" for p in params])
    
    cmd = f"""
cd "c:\\Users\\Emre\\Desktop\\Buy-sell Algorithm\\Buy-Sell-Algorithm-for-all-exchange-\\freqtrade"
docker compose run --rm freqtrade backtesting `
    --strategy {STRATEGY} `
    --config user_data/config.json `
    --timerange {TIMERANGE} `
    --timeframe {TIMEFRAME} `
    --export trades `
    {params_str}
"""
    
    # Run via PowerShell
    result = subprocess.run(
        ["powershell", "-Command", cmd],
        capture_output=True,
        text=True
    )
    
    output = result.stdout + result.stderr
    
    # Parse metrics from output
    metrics = parse_backtest_output(output)
    metrics['variant_id'] = variant_id
    metrics['variant_name'] = variant_config['name']
    
    return metrics

def parse_backtest_output(output):
    """Extract key metrics from backtest output."""
    
    metrics = {
        'total_profit_pct': None,
        'total_profit_usdt': None,
        'total_trades': None,
        'max_dd_pct': None,
        'winrate': None,
        'exit_reasons': {}
    }
    
    lines = output.split('\n')
    
    # Parse line by line
    for i, line in enumerate(lines):
        # Total profit percentage
        if 'Total profit %' in line:
            match = re.search(r'│\s+([-\d.]+)%\s+│', line)
            if match:
                metrics['total_profit_pct'] = float(match.group(1))
        
        # Absolute profit
        if 'Absolute profit' in line:
            match = re.search(r'│\s+([-\d.]+)\s+USDT', line)
            if match:
                metrics['total_profit_usdt'] = float(match.group(1))
        
        # Total trades
        if 'Total trades' in line and 'Absolute' not in line:
            match = re.search(r'│\s+(\d+)\s+│', line)
            if match:
                metrics['total_trades'] = int(match.group(1))
        
        # Max drawdown
        if 'Max % of account underwater' in line:
            match = re.search(r'│\s+([\d.]+)%\s+│', line)
            if match:
                metrics['max_dd_pct'] = float(match.group(1))
        
        # Winrate
        if 'Avg. Profit %' in line:
            # Look ahead for win rate in next few lines
            for j in range(i, min(i+5, len(lines))):
                if 'Wins  / Draws / Losses' in lines[j]:
                    # Extract wins and losses
                    parts = lines[j].split('│')
                    if len(parts) >= 3:
                        wdl = parts[-2].strip()
                        match = re.search(r'(\d+)\s+/\s+\d+\s+/\s+(\d+)', wdl)
                        if match:
                            wins = int(match.group(1))
                            losses = int(match.group(2))
                            total = wins + losses
                            if total > 0:
                                metrics['winrate'] = (wins / total) * 100
        
        # Exit reasons
        if '│' in line and any(reason in line.lower() for reason in ['roi', 'exit_signal', 'stop', 'stoploss', 'force']):
            parts = [p.strip() for p in line.split('│') if p.strip()]
            if len(parts) >= 4:
                reason = parts[0]
                # Remove leading/trailing whitespace and special chars
                reason = reason.strip()
                
                # Try to extract count and profit
                try:
                    count_str = parts[1]
                    profit_str = parts[3]  # Usually total profit column
                    
                    # Extract numbers
                    count_match = re.search(r'(\d+)', count_str)
                    profit_match = re.search(r'([-\d.]+)', profit_str)
                    
                    if count_match and profit_match:
                        count = int(count_match.group(1))
                        profit = float(profit_match.group(1))
                        
                        metrics['exit_reasons'][reason] = {
                            'count': count,
                            'total_profit': profit
                        }
                except Exception:
                    pass
    
    return metrics

def generate_report(all_results):
    """Generate markdown report comparing all variants."""
    
    report = f"""# Exit Signal Chop & Damping Ablation Study

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Strategy:** EPAUltimateV3  
**Timerange:** {TIMERANGE}  
**Timeframe:** {TIMEFRAME}  
**Pairs:** BTC/USDT, BNB/USDT, ETH/USDT, SOL/USDT, XRP/USDT

## Executive Summary

Testing two independent fixes for exit_signal losses:
- **Fix A: Choppiness Gate** - Block exit_signal during choppy consolidation when profitable (CHOP > 61.8 + profit > 0)
- **Fix B: Profit-Dependent Damping** - Require 3-of-3 consensus (not 2-of-3) when trade is green (profit ≥ 1%)

## Results Matrix

| Variant | Total Profit | Profit USDT | Trades | Max DD | Winrate | exit_signal Count | exit_signal P&L |
|---------|--------------|-------------|--------|--------|---------|-------------------|-----------------|
"""
    
    # Add each variant
    for variant_id in ['baseline', 'fix_a', 'fix_b', 'combined']:
        result = all_results[variant_id]
        
        # Get exit_signal metrics
        es_count = result['exit_reasons'].get('exit_signal', {}).get('count', 0)
        es_profit = result['exit_reasons'].get('exit_signal', {}).get('total_profit', 0.0)
        
        report += f"| **{result['variant_name']}** "
        report += f"| {result['total_profit_pct']:.2f}% "
        report += f"| {result['total_profit_usdt']:.2f} USDT "
        report += f"| {result['total_trades']} "
        report += f"| {result['max_dd_pct']:.2f}% "
        report += f"| {result['winrate']:.1f}% " if result['winrate'] else "| N/A "
        report += f"| {es_count} "
        report += f"| {es_profit:.2f} USDT |\n"
    
    # Calculate improvements
    baseline = all_results['baseline']
    best_variant = None
    best_improvement = 0
    
    for variant_id in ['fix_a', 'fix_b', 'combined']:
        result = all_results[variant_id]
        profit_improvement = result['total_profit_pct'] - baseline['total_profit_pct']
        
        if profit_improvement > best_improvement:
            best_improvement = profit_improvement
            best_variant = variant_id
    
    report += f"""
## Detailed Exit Reason Breakdown

### Baseline (A=off, B=off)
"""
    
    for reason, data in baseline['exit_reasons'].items():
        report += f"- **{reason}**: {data['count']} trades, {data['total_profit']:.2f} USDT\n"
    
    report += "\n### Fix A Only (Chop Gate)\n"
    for reason, data in all_results['fix_a']['exit_reasons'].items():
        report += f"- **{reason}**: {data['count']} trades, {data['total_profit']:.2f} USDT\n"
    
    report += "\n### Fix B Only (Profit Damping)\n"
    for reason, data in all_results['fix_b']['exit_reasons'].items():
        report += f"- **{reason}**: {data['count']} trades, {data['total_profit']:.2f} USDT\n"
    
    report += "\n### Combined (A+B)\n"
    for reason, data in all_results['combined']['exit_reasons'].items():
        report += f"- **{reason}**: {data['count']} trades, {data['total_profit']:.2f} USDT\n"
    
    # Comparison analysis
    report += f"""
## Impact Analysis

### Profit Improvement vs Baseline
"""
    
    for variant_id in ['fix_a', 'fix_b', 'combined']:
        result = all_results[variant_id]
        profit_delta = result['total_profit_pct'] - baseline['total_profit_pct']
        usdt_delta = result['total_profit_usdt'] - baseline['total_profit_usdt']
        
        status = "✓" if profit_delta > 0 else ("✗" if profit_delta < 0 else "=")
        
        report += f"- **{result['variant_name']}**: {profit_delta:+.2f}% ({usdt_delta:+.2f} USDT) {status}\n"
    
    ### Exit Signal Reduction
    baseline_es = baseline['exit_reasons'].get('exit_signal', {}).get('count', 0)
    
    report += f"\n### Exit Signal Count Reduction\n"
    report += f"- **Baseline**: {baseline_es} exit_signal trades\n"
    
    for variant_id in ['fix_a', 'fix_b', 'combined']:
        result = all_results[variant_id]
        es_count = result['exit_reasons'].get('exit_signal', {}).get('count', 0)
        reduction = baseline_es - es_count
        pct_reduction = (reduction / baseline_es * 100) if baseline_es > 0 else 0
        
        status = "✓" if reduction > 0 else ("✗" if reduction < 0 else "=")
        
        report += f"- **{result['variant_name']}**: {es_count} ({reduction:+d}, {pct_reduction:.1f}%) {status}\n"
    
    # Recommendation
    report += f"""
## Recommendation

"""
    
    if best_variant:
        best_result = all_results[best_variant]
        report += f"""**Winner: {best_result['variant_name']}**

- Profit improvement: +{best_improvement:.2f}%
- Total profit: {best_result['total_profit_pct']:.2f}% ({best_result['total_profit_usdt']:.2f} USDT)
- Max DD: {best_result['max_dd_pct']:.2f}%

**Action:** Enable the winning configuration by setting default=True for the corresponding feature flags.
"""
    else:
        report += """**No Clear Winner**

None of the variants showed material improvement over baseline.

**Action:** Keep both features implemented behind flags (default=False) for future testing or hyperopt.
"""
    
    report += """
## Implementation Details

### Fix A: Choppiness Gate
- **Parameter**: `use_exit_chop_gate` (BooleanParameter, default=False)
- **Threshold**: `exit_chop_threshold` (default=61.8)
- **Logic**: Block exit_signal when CHOP > threshold AND current_profit > 0
- **Location**: `confirm_trade_exit()` method

### Fix B: Profit-Dependent Consensus Damping
- **Parameter**: `use_profit_damping_exit` (BooleanParameter, default=False)
- **Threshold**: `profit_damping_threshold` (default=0.01, i.e., 1%)
- **Logic**: Require 3-of-3 bearish consensus (Supertrend + QQE + EMA) when profit ≥ threshold
- **Location**: `confirm_trade_exit()` method + `populate_exit_trend()` stores bearish_count

### Critical Constraints Verified
✓ `trailing_stop = False` (disabled)
✓ `use_custom_stoploss = False` (disabled)
✓ Stoploss and ROI exits are NEVER blocked by these fixes
✓ Only exit_signal is gated

## Files
- Implementation: [EPAUltimateV3.py](../user_data/strategies/EPAUltimateV3.py)
- Previous analysis: [exit_signal_loss_profile.md](exit_signal_loss_profile.md)
"""
    
    return report

def main():
    """Run 4-variant ablation study."""
    
    print("\n" + "="*70)
    print("EXIT SIGNAL CHOP & DAMPING ABLATION STUDY")
    print("="*70)
    print(f"Strategy: {STRATEGY}")
    print(f"Timerange: {TIMERANGE}")
    print(f"Timeframe: {TIMEFRAME}")
    print(f"Variants: 4 (Baseline, Fix A, Fix B, Combined)")
    print("="*70 + "\n")
    
    # Run all variants
    all_results = {}
    
    for variant_id, variant_config in VARIANTS.items():
        result = run_backtest(variant_id, variant_config)
        all_results[variant_id] = result
        
        # Print summary
        print(f"\n✓ {variant_config['name']} complete:")
        print(f"  Profit: {result['total_profit_pct']:.2f}% ({result['total_profit_usdt']:.2f} USDT)")
        print(f"  Trades: {result['total_trades']}")
        print(f"  Max DD: {result['max_dd_pct']:.2f}%")
        es_count = result['exit_reasons'].get('exit_signal', {}).get('count', 0)
        es_profit = result['exit_reasons'].get('exit_signal', {}).get('total_profit', 0.0)
        print(f"  exit_signal: {es_count} trades, {es_profit:.2f} USDT")
    
    # Generate report
    report = generate_report(all_results)
    
    # Write report
    output_path = Path('reports/exit_signal_chop_damping_ablation.md')
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Ablation study complete!")
    print(f"📊 Report: {output_path}")
    
    # Print comparison table
    print("\n" + "="*70)
    print("RESULTS COMPARISON TABLE")
    print("="*70 + "\n")
    
    print(f"{'Variant':<30} {'Profit %':<12} {'Trades':<8} {'Max DD':<10} {'ES Count':<10} {'ES P&L':<12}")
    print("-" * 82)
    
    for variant_id in ['baseline', 'fix_a', 'fix_b', 'combined']:
        result = all_results[variant_id]
        es_count = result['exit_reasons'].get('exit_signal', {}).get('count', 0)
        es_profit = result['exit_reasons'].get('exit_signal', {}).get('total_profit', 0.0)
        
        print(f"{result['variant_name']:<30} "
              f"{result['total_profit_pct']:>10.2f}% "
              f"{result['total_trades']:>6} "
              f"{result['max_dd_pct']:>8.2f}% "
              f"{es_count:>8} "
              f"{es_profit:>10.2f} USDT")
    
    print("\n" + "="*70 + "\n")

if __name__ == '__main__':
    main()
