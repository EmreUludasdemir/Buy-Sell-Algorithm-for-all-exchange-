#!/usr/bin/env python3
"""
Ablation study: Baseline vs Exit Signal Protection
Tests the impact of min_hold_exit_protection feature on exit_signal losses.
"""

import subprocess
import json
import zipfile
from pathlib import Path
from datetime import datetime

def run_backtest(variant_name, config_updates):
    """Run a backtest variant with specific config updates."""
    
    print(f"\n{'='*60}")
    print(f"Running: {variant_name}")
    print(f"{'='*60}")
    
    # Create temporary config
    import json
    with open('user_data/config.json', 'r') as f:
        config = json.load(f)
    
    # Apply updates
    config.update(config_updates)
    
    # Write temp config
    temp_config = f'user_data/config_ablation_{variant_name.lower().replace(" ", "_")}.json'
    with open(temp_config, 'w') as f:
        json.dump(config, f, indent=2)
    
    # Run backtest
    cmd = [
        'docker', 'compose', 'run', '--rm', 'freqtrade', 'backtesting',
        '--strategy', 'EPAUltimateV3',
        '--config', temp_config,
        '--timerange', '20240601-20241231',
        '--timeframe', '4h',
        '--export', 'trades',
        '--breakdown', 'day'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Parse output
    lines = result.stdout.split('\n')
    
    # Extract metrics
    metrics = {}
    for line in lines:
        if 'Total profit %' in line:
            metrics['profit_pct'] = line.split('│')[-2].strip()
        elif 'Total trades' in line and 'Absolute' not in line:
            metrics['total_trades'] = line.split('│')[-2].strip()
        elif 'Max % of account underwater' in line:
            metrics['max_dd'] = line.split('│')[-2].strip()
        elif 'Wins  / Draws / Losses' in line:
            parts = line.split('│')[-2].strip().split('/')
            metrics['wins'] = parts[0].strip()
            metrics['losses'] = parts[2].strip()
    
    # Extract exit reasons
    exit_reasons = {}
    in_exit_section = False
    for line in lines:
        if 'EXIT REASON STATS' in line:
            in_exit_section = True
        elif in_exit_section and '│' in line and 'Exit Reason' not in line and '─' not in line:
            parts = [p.strip() for p in line.split('│') if p.strip()]
            if len(parts) >= 2:
                reason = parts[0]
                count = parts[1]
                if reason and count and count.isdigit():
                    exit_reasons[reason] = int(count)
    
    metrics['exit_reasons'] = exit_reasons
    
    # Get latest result file for detailed analysis
    results_dir = Path('user_data/backtest_results')
    latest_file = max(results_dir.glob('backtest-result-*.zip'), key=lambda p: p.stat().st_mtime)
    metrics['result_file'] = str(latest_file)
    
    return metrics

def compare_results(baseline, fix_enabled):
    """Generate comparison report."""
    
    report = f"""# Exit Signal Fix Ablation Study

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Strategy:** EPAUltimateV3  
**Timerange:** 2024-06-01 to 2024-12-31  
**Feature:** Minimum Hold Period with MFE Protection

## Variants Tested

### Baseline (use_min_hold_exit_protection=False)
- **Configuration:** Default V3 settings, 2-of-3 exit consensus
- **Parameters:** No exit_signal protection

### Fix Enabled (use_min_hold_exit_protection=True)
- **Configuration:** Exit signal protection active
- **Parameters:**
  - `min_hold_exit_signal_hours`: 12.0 (block exit_signal for first 12h)
  - `mfe_protection_threshold`: 2.0% (if trade reached +2% profit)
  - `mfe_extended_hold_hours`: 24.0 (extend hold to 24h for profitable trades)

## Results Comparison

| Metric | Baseline | Fix Enabled | Change | Impact |
|--------|----------|-------------|--------|--------|
| **Total Profit %** | {baseline.get('profit_pct', 'N/A')} | {fix_enabled.get('profit_pct', 'N/A')} | TBD | {'✓' if 'TODO' else '?'} |
| **Total Trades** | {baseline.get('total_trades', 'N/A')} | {fix_enabled.get('total_trades', 'N/A')} | TBD | - |
| **Max Drawdown** | {baseline.get('max_dd', 'N/A')} | {fix_enabled.get('max_dd', 'N/A')} | TBD | {'✓' if 'TODO' else '?'} |
| **Win Rate** | TBD | TBD | TBD | - |

## Exit Reason Breakdown

### Baseline
"""
    
    for reason, count in baseline.get('exit_reasons', {}).items():
        report += f"- **{reason}**: {count}\n"
    
    report += "\n### Fix Enabled\n"
    
    for reason, count in fix_enabled.get('exit_reasons', {}).items():
        report += f"- **{reason}**: {count}\n"
    
    baseline_exit_signal = baseline.get('exit_reasons', {}).get('exit_signal', 0)
    fix_exit_signal = fix_enabled.get('exit_reasons', {}).get('exit_signal', 0)
    
    report += f"""
## Key Findings

### Exit Signal Reduction
- **Baseline exit_signal count:** {baseline_exit_signal}
- **Fix enabled exit_signal count:** {fix_exit_signal}
- **Reduction:** {baseline_exit_signal - fix_exit_signal} trades ({(baseline_exit_signal - fix_exit_signal) / baseline_exit_signal * 100:.1f}% decrease)

### Performance Impact
- **Profit improvement:** TODO after full analysis
- **Trade frequency impact:** {int(fix_enabled.get('total_trades', '0')) - int(baseline.get('total_trades', '0'))} trades
- **Risk impact:** Drawdown change TODO

## Recommendation

Based on this ablation study:

**IMPLEMENT** if:
- Exit signal count reduced by >30%
- Total profit improved by >1%
- Max DD unchanged or improved

**REJECT** if:
- Profit decreased
- DD significantly worsened
- Trade frequency dropped dramatically

## Implementation Notes

The fix is already implemented behind feature flag `use_min_hold_exit_protection`.

To enable permanently:
1. Set `use_min_hold_exit_protection = BooleanParameter(default=True, ...)`
2. Commit changes with reference to this ablation report
3. Monitor live performance for 2-4 weeks

## Files
- Implementation: [EPAUltimateV3.py](../user_data/strategies/EPAUltimateV3.py) (lines ~178-185, ~630-685)
- Loss profile: [exit_signal_loss_profile.md](exit_signal_loss_profile.md)
"""
    
    return report

def main():
    """Run ablation study."""
    
    print("Starting Exit Signal Fix Ablation Study...")
    print("This will run 2 backtests - estimated time: 4-6 minutes")
    
    # Variant 1: Baseline (protection disabled)
    baseline = run_backtest("Baseline", {
        "use_min_hold_exit_protection": False
    })
    
    # Variant 2: Fix enabled
    fix_enabled = run_backtest("Fix_Enabled", {
        "use_min_hold_exit_protection": True,
        "min_hold_exit_signal_hours": 12.0,
        "mfe_protection_threshold": 2.0,
        "mfe_extended_hold_hours": 24.0
    })
    
    # Generate report
    report = compare_results(baseline, fix_enabled)
    
    # Write report
    output_path = Path('reports/exit_signal_fix_ablation.md')
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Ablation study complete!")
    print(f"📊 Report: {output_path}")
    
    # Print headline comparison
    print(f"\n{'='*60}")
    print("HEADLINE COMPARISON")
    print(f"{'='*60}")
    print(f"Baseline:      Profit={baseline.get('profit_pct', 'N/A'):>10}  Trades={baseline.get('total_trades', 'N/A'):>5}  DD={baseline.get('max_dd', 'N/A'):>8}")
    print(f"Fix Enabled:   Profit={fix_enabled.get('profit_pct', 'N/A'):>10}  Trades={fix_enabled.get('total_trades', 'N/A'):>5}  DD={fix_enabled.get('max_dd', 'N/A'):>8}")
    print(f"{'='*60}")
    print(f"Exit_signal:   Baseline={baseline.get('exit_reasons', {}).get('exit_signal', 0):>3}  →  Fix={fix_enabled.get('exit_reasons', {}).get('exit_signal', 0):>3}")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()
