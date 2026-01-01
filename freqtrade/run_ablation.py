"""
Ablation Study Runner for Efloud Range + HTF Bias Integration
Runs 3 variants and collects metrics:
- Variant 0: Baseline (no boosts)
- Variant 1: Range boost only
- Variant 2: Range boost + HTF bias boost
"""

import json
import re
import subprocess
from pathlib import Path
from datetime import datetime

# Results storage
variants = {
    "Variant 0": {"params": [], "desc": "Baseline (no range/HTF boosts)"},
    "Variant 1": {"params": ["--strategy-path", "user_data/strategies", 
                             "-p", "use_range_boost=true", 
                             "-p", "use_htf_bias_boost=false"], 
                 "desc": "Range boost only"},
    "Variant 2": {"params": ["--strategy-path", "user_data/strategies",
                             "-p", "use_range_boost=true",
                             "-p", "use_htf_bias_boost=true"], 
                 "desc": "Range + HTF bias boosts"}
}

def parse_backtest_output(output: str) -> dict:
    """Extract key metrics from backtest output."""
    metrics = {}
    
    # Total profit %
    match = re.search(r'Total profit %\s+\u2502\s+([-\d.]+)%', output)
    if match:
        metrics['profit_pct'] = float(match.group(1))
    
    # Max drawdown %
    match = re.search(r'Max % of account underwater\s+\u2502\s+([\d.]+)%', output)
    if match:
        metrics['drawdown_pct'] = float(match.group(1))
    
    # Total trades
    match = re.search(r'Total/Daily Avg Trades\s+\u2502\s+(\d+)\s+/', output)
    if match:
        metrics['trades'] = int(match.group(1))
    
    # Win rate
    match = re.search(r'TOTAL\s+\u2502\s+\d+\s+\u2502[^┃]+┃\s+(\d+)\s+0\s+(\d+)\s+([\d.]+)', output)
    if match:
        metrics['winrate'] = float(match.group(3))
    
    # Profit factor
    match = re.search(r'Profit factor\s+\u2502\s+([\d.]+)', output)
    if match:
        metrics['profit_factor'] = float(match.group(1))
    
    # CAGR
    match = re.search(r'CAGR %\s+\u2502\s+([-\d.]+)%', output)
    if match:
        metrics['cagr'] = float(match.group(1))
    
    # Sharpe
    match = re.search(r'Sharpe\s+\u2502\s+([-\d.]+)', output)
    if match:
        metrics['sharpe'] = float(match.group(1))
    
    return metrics

def run_variant(variant_name: str, params: list) -> dict:
    """Run backtest for a variant and return metrics."""
    print(f"\n{'='*60}")
    print(f"Running {variant_name}: {variants[variant_name]['desc']}")
    print(f"{'='*60}\n")
    
    base_cmd = [
        "docker", "compose", "run", "--rm", "freqtrade", "backtesting",
        "--strategy", "EPAUltimateV4",
        "--config", "user_data/config.json",
        "--timerange", "20240601-20241231",
        "--timeframe", "4h",
        "--export", "trades"
    ]
    
    cmd = base_cmd + params
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
            timeout=600
        )
        
        output = result.stdout + result.stderr
        metrics = parse_backtest_output(output)
        metrics['variant'] = variant_name
        metrics['description'] = variants[variant_name]['desc']
        metrics['status'] = 'success' if metrics else 'failed_parse'
        
        return metrics
    
    except subprocess.TimeoutExpired:
        return {'variant': variant_name, 'status': 'timeout'}
    except Exception as e:
        return {'variant': variant_name, 'status': 'error', 'error': str(e)}

def generate_markdown_report(results: list):
    """Generate markdown ablation report."""
    report = f"""# Efloud Range + HTF Bias Ablation Study

**Date:** {datetime.now().strftime('%Y-%m-%d')}  
**Strategy:** EPAUltimateV4  
**Timeframe:** 4h  
**Test Period:** 2024-06-01 to 2024-12-31 (213 days)  
**Pairs:** BTC/USDT, BNB/USDT, ETH/USDT, SOL/USDT, XRP/USDT

---

## Objective

Test whether adding Efloud-style **Range Structure** (RH/RL/EQ + demand/supply zones) and **HTF Bias** (1d RSI/OBV/DMA) as soft position sizing boosts improves profitability without killing trade frequency.

**Hard Constraints:**
- No repainting / live-safe only
- trailing_stop=False, use_custom_stoploss=False (Variant D behavior)
- Boosts are SOFT (position sizing multipliers), NOT entry requirements

---

## Results Summary

| Variant | Description | Profit % | DD % | Trades | Winrate % | PF | CAGR % | Sharpe |
|---------|-------------|----------|------|--------|-----------|----|---------|---------|\n"""
    
    for r in results:
        if r['status'] == 'success':
            report += f"| {r['variant']} | {r['description']} | {r['profit_pct']:.2f} | {r['drawdown_pct']:.2f} | {r['trades']} | {r['winrate']:.1f} | {r['profit_factor']:.2f} | {r['cagr']:.2f} | {r['sharpe']:.2f} |\n"
        else:
            report += f"| {r['variant']} | {r['description']} | ERROR | - | - | - | - | - | - |\n"
    
    report += f"""
---

## Analysis

### Trade Frequency Impact
"""
    
    baseline_trades = next((r['trades'] for r in results if r['variant'] == 'Variant 0' and r['status'] == 'success'), None)
    
    for r in results:
        if r['status'] == 'success' and r['variant'] != 'Variant 0':
            if baseline_trades:
                freq_change = ((r['trades'] - baseline_trades) / baseline_trades) * 100
                report += f"- **{r['variant']}**: {r['trades']} trades ({freq_change:+.1f}% vs baseline)\n"
    
    report += f"""
### Profitability Impact
"""
    
    baseline_profit = next((r['profit_pct'] for r in results if r['variant'] == 'Variant 0' and r['status'] == 'success'), None)
    
    for r in results:
        if r['status'] == 'success' and r['variant'] != 'Variant 0':
            if baseline_profit:
                profit_change = r['profit_pct'] - baseline_profit
                report += f"- **{r['variant']}**: {r['profit_pct']:.2f}% ({profit_change:+.2f}% vs baseline)\n"
    
    report += f"""
### Risk Metrics
"""
    
    baseline_dd = next((r['drawdown_pct'] for r in results if r['variant'] == 'Variant 0' and r['status'] == 'success'), None)
    
    for r in results:
        if r['status'] == 'success' and r['variant'] != 'Variant 0':
            if baseline_dd:
                dd_change = r['drawdown_pct'] - baseline_dd
                report += f"- **{r['variant']}**: {r['drawdown_pct']:.2f}% DD ({dd_change:+.2f}% vs baseline)\n"
    
    report += f"""
---

## Interpretation

[TODO: Add interpretation after reviewing results]

Possible interpretations:
- **Trade count stable** (±10%): Boosts don't filter out entries → SUCCESS
- **Trade count collapse** (>30% drop): Boosts acting as hard filters → FAILURE
- **Profit improved + trades stable**: Boosts capturing better setups → SUCCESS
- **Profit flat + complexity added**: Boosts don't help, remove them → SIMPLIFY

---

## Recommendations

[TODO: Add recommendations based on results]

---

## Implementation Details

### Range Structure (price_action_ranges.py)
- **RH/RL/EQ**: Rolling max/min over 50 candles + midpoint
- **Demand Zone**: RL ± ATR (1.0x multiplier)
- **Supply Zone**: RH ± ATR (1.0x multiplier)
- **Boost**: +10% in demand zone, +5% on EQ reclaim (capped at +15%)

### HTF Bias (1d timeframe)
- **RSI**: Bullish if >50, bearish if <50
- **OBV Slope**: Compare OBV vs OBV.shift(9), rising=bullish
- **DMA Proxy**: EMA(50) slope, rising=bullish
- **Boost**: +10% when all 3 align (bull or bear)

---

## Files Modified
- `price_action_ranges.py` (new helper module)
- `EPAUltimateV4.py` (added range/HTF indicators + boosts)

---

## Next Steps

Based on results:
1. If **both improve profit + maintain trades**: Enable both by default, commit
2. If **only one works**: Enable that one, disable the other
3. If **neither works**: Keep as optional flags, default=False
4. If **trade frequency collapses**: Review entry logic, these may be leaking into filters

"""
    
    return report

def main():
    """Run ablation study."""
    results = []
    
    # NOTE: Variant 0 already run manually, skipping
    print("Variant 0 already completed. Starting Variant 1...")
    
    # Add Variant 0 results manually (from previous run)
    results.append({
        'variant': 'Variant 0',
        'description': 'Baseline (no range/HTF boosts)',
        'profit_pct': 15.88,
        'drawdown_pct': 18.46,
        'trades': 248,
        'winrate': 60.9,
        'profit_factor': 1.13,
        'cagr': 28.73,
        'sharpe': 1.02,
        'status': 'success'
    })
    
    # Run Variant 1 and 2
    for variant_name in ['Variant 1', 'Variant 2']:
        metrics = run_variant(variant_name, variants[variant_name]['params'])
        results.append(metrics)
        print(f"\n{variant_name} completed: {metrics.get('status', 'unknown')}")
        if metrics.get('status') == 'success':
            print(f"  Profit: {metrics.get('profit_pct', 'N/A')}%")
            print(f"  Trades: {metrics.get('trades', 'N/A')}")
    
    # Generate report
    report = generate_markdown_report(results)
    
    # Save report
    report_path = Path(__file__).parent / 'reports' / 'efloud_range_htf_ablation.md'
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(report, encoding='utf-8')
    
    print(f"\n{'='*60}")
    print(f"Ablation study complete!")
    print(f"Report saved to: {report_path}")
    print(f"{'='*60}\n")
    
    # Also save raw JSON
    json_path = report_path.with_suffix('.json')
    json_path.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(f"Raw data saved to: {json_path}\n")

if __name__ == "__main__":
    main()
