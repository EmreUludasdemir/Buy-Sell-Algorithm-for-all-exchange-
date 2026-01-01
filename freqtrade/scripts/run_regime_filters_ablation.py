#!/usr/bin/env python3
"""
Entry Regime Filters Ablation Runner

Systematically tests combinations of entry regime filters:
- Baseline (both OFF)
- Filter 1 ON (EMA200 slope)
- Filter 2 ON (ADX minimum)
- Both ON

Compares results against baseline acceptance criteria.
"""

import subprocess
import json
import re
from pathlib import Path
from datetime import datetime
import zipfile

# Test configuration
VARIANTS = [
    {
        'name': 'Baseline',
        'ema200_filter': False,
        'adx_filter': False,
        'description': 'Both filters OFF (baseline)'
    },
    {
        'name': 'EMA200_Only',
        'ema200_filter': True,
        'adx_filter': False,
        'description': 'Only EMA200 slope filter (uptrend only)'
    },
    {
        'name': 'ADX_Only',
        'ema200_filter': False,
        'adx_filter': True,
        'description': 'Only ADX minimum filter (strong trend only)'
    },
    {
        'name': 'Both_Filters',
        'ema200_filter': True,
        'adx_filter': True,
        'description': 'Both filters ON (EMA200 uptrend + ADX >= 20)'
    }
]

ACCEPTANCE_CRITERIA = {
    'min_profit_pct': 10.03,  # Must be >= baseline
    'max_stop_loss_count': 9,  # Must be <= baseline
    'exit_signal_improvement_threshold': 100.0  # Improvement in USDT
}

def modify_strategy_params(strategy_path: Path, use_ema200: bool, use_adx: bool):
    """Modify strategy parameters for testing"""
    with open(strategy_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace ema200 filter
    content = re.sub(
        r'use_ema200_slope_filter = BooleanParameter\(default=(True|False)',
        f'use_ema200_slope_filter = BooleanParameter(default={use_ema200}',
        content
    )
    
    # Replace adx filter
    content = re.sub(
        r'use_adx_min_filter = BooleanParameter\(default=(True|False)',
        f'use_adx_min_filter = BooleanParameter(default={use_adx}',
        content
    )
    
    with open(strategy_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] Modified strategy: EMA200={use_ema200}, ADX={use_adx}")


def run_backtest(variant_name: str):
    """Run backtest and return path to result files"""
    print(f"\n{'='*60}")
    print(f"RUNNING: {variant_name}")
    print('='*60)
    
    cmd = [
        'docker', 'compose', 'run', '--rm', 'freqtrade', 'backtesting',
        '--strategy', 'EPAUltimateV3',
        '--timerange', '20240601-20241231',
        '--timeframe', '4h',
        '--export', 'trades',
        '--cache', 'none'
    ]
    
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Backtest failed for {variant_name}")
        print(result.stderr)
        return None
    
    # Extract key metrics from output
    output = result.stdout
    print(output)
    
    return output


def parse_backtest_output(output: str) -> dict:
    """Extract key metrics from backtest output"""
    metrics = {}
    
    # Total profit %
    match = re.search(r'Total profit %\s+│\s+([-\d.]+)%', output)
    if match:
        metrics['profit_pct'] = float(match.group(1))
    
    # Max drawdown
    match = re.search(r'Max % of account underwater\s+│\s+([-\d.]+)%', output)
    if match:
        metrics['max_dd_pct'] = float(match.group(1))
    
    # Total trades
    match = re.search(r'Total/Daily Avg Trades\s+│\s+(\d+)', output)
    if match:
        metrics['total_trades'] = int(match.group(1))
    
    # Exit reasons
    exit_reasons = {}
    
    # roi
    match = re.search(r'│\s+roi\s+│\s+(\d+)\s+│.*?│\s+([-\d.]+)\s+│', output)
    if match:
        exit_reasons['roi'] = {'count': int(match.group(1)), 'profit_usdt': float(match.group(2))}
    
    # stop_loss
    match = re.search(r'│\s+stop_loss\s+│\s+(\d+)\s+│.*?│\s+([-\d.]+)\s+│', output)
    if match:
        exit_reasons['stop_loss'] = {'count': int(match.group(1)), 'profit_usdt': float(match.group(2))}
    
    # exit_signal
    match = re.search(r'│\s+exit_signal\s+│\s+(\d+)\s+│.*?│\s+([-\d.]+)\s+│', output)
    if match:
        exit_reasons['exit_signal'] = {'count': int(match.group(1)), 'profit_usdt': float(match.group(2))}
    
    # tiered_tp
    match = re.search(r'│\s+tiered_tp_\S+\s+│\s+(\d+)\s+│.*?│\s+([-\d.]+)\s+│', output)
    if match:
        exit_reasons['tiered_tp'] = {'count': int(match.group(1)), 'profit_usdt': float(match.group(2))}
    
    metrics['exit_reasons'] = exit_reasons
    
    return metrics


def check_acceptance(variant_results: dict, baseline: dict) -> dict:
    """Check if variant meets acceptance criteria"""
    checks = {}
    
    # Check profit
    profit_ok = variant_results['profit_pct'] >= ACCEPTANCE_CRITERIA['min_profit_pct']
    checks['profit'] = {
        'pass': profit_ok,
        'value': variant_results['profit_pct'],
        'baseline': baseline['profit_pct'],
        'delta': variant_results['profit_pct'] - baseline['profit_pct']
    }
    
    # Check stop_loss count
    variant_sl = variant_results['exit_reasons'].get('stop_loss', {}).get('count', 0)
    baseline_sl = baseline['exit_reasons'].get('stop_loss', {}).get('count', 0)
    sl_ok = variant_sl <= ACCEPTANCE_CRITERIA['max_stop_loss_count']
    checks['stop_loss'] = {
        'pass': sl_ok,
        'value': variant_sl,
        'baseline': baseline_sl,
        'delta': variant_sl - baseline_sl
    }
    
    # Check exit_signal improvement
    variant_es = variant_results['exit_reasons'].get('exit_signal', {}).get('profit_usdt', 0)
    baseline_es = baseline['exit_reasons'].get('exit_signal', {}).get('profit_usdt', 0)
    es_improvement = variant_es - baseline_es  # Less negative = improvement
    es_ok = es_improvement >= ACCEPTANCE_CRITERIA['exit_signal_improvement_threshold']
    checks['exit_signal'] = {
        'pass': es_ok,
        'value': variant_es,
        'baseline': baseline_es,
        'improvement': es_improvement
    }
    
    # Overall pass
    checks['overall_pass'] = checks['profit']['pass'] and checks['stop_loss']['pass']
    
    return checks


def generate_report(all_results: list, output_path: Path):
    """Generate comprehensive ablation report"""
    
    baseline = all_results[0]['metrics']  # First is always baseline
    
    report = f"""# Entry Regime Filters Ablation Study
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Strategy:** EPAUltimateV3  
**Timerange:** 2024-06-01 to 2024-12-31  
**Timeframe:** 4h  

---

## Executive Summary

**Tested Filters:**
1. **EMA200 Slope Filter:** Only enter when 4h EMA200 slope > 0 (uptrend)
2. **ADX Minimum Filter:** Only enter when ADX >= 20 (strong trend)

**Acceptance Criteria:**
- ✅ Total profit >= 10.03% (baseline)
- ✅ stop_loss count <= 9 (baseline)
- ⚠️ exit_signal improvement >= +100 USDT (aspirational)

---

## Results Summary

| Variant | EMA200 Filter | ADX Filter | Profit % | Max DD % | Total Trades | stop_loss | exit_signal (USDT) | Status |
|---------|---------------|------------|----------|----------|--------------|-----------|-------------------|--------|
"""
    
    for result in all_results:
        var = result['variant']
        met = result['metrics']
        
        ema_icon = '✅' if var['ema200_filter'] else '❌'
        adx_icon = '✅' if var['adx_filter'] else '❌'
        
        profit = met.get('profit_pct', 0)
        dd = met.get('max_dd_pct', 0)
        trades = met.get('total_trades', 0)
        sl_count = met['exit_reasons'].get('stop_loss', {}).get('count', 0)
        es_profit = met['exit_reasons'].get('exit_signal', {}).get('profit_usdt', 0)
        
        # Status icon
        if result == all_results[0]:
            status = '📊 Baseline'
        elif 'acceptance' in result and result['acceptance']['overall_pass']:
            status = '✅ PASS'
        else:
            status = '❌ FAIL'
        
        report += f"| {var['name']} | {ema_icon} | {adx_icon} | {profit:.2f}% | {dd:.2f}% | {trades} | {sl_count} | {es_profit:.2f} | {status} |\n"
    
    report += "\n---\n\n## Detailed Analysis\n\n"
    
    for i, result in enumerate(all_results):
        if i == 0:
            continue  # Skip baseline in detailed section
        
        var = result['variant']
        met = result['metrics']
        acc = result.get('acceptance', {})
        
        report += f"### {var['name']}\n\n"
        report += f"**Configuration:** {var['description']}\n\n"
        
        if 'profit' in acc:
            report += "**Acceptance Checks:**\n"
            report += f"- **Profit:** {met['profit_pct']:.2f}% "
            report += f"({'✅ PASS' if acc['profit']['pass'] else '❌ FAIL'}) "
            report += f"(Δ {acc['profit']['delta']:+.2f}%)\n"
            
            report += f"- **stop_loss Count:** {acc['stop_loss']['value']} "
            report += f"({'✅ PASS' if acc['stop_loss']['pass'] else '❌ FAIL'}) "
            report += f"(Δ {acc['stop_loss']['delta']:+d})\n"
            
            report += f"- **exit_signal Improvement:** {acc['exit_signal']['improvement']:+.2f} USDT "
            report += f"({'✅ GOOD' if acc['exit_signal']['pass'] else '⚠️ MODEST'})\n\n"
        
        report += f"**Exit Reason Breakdown:**\n"
        for reason, data in met['exit_reasons'].items():
            report += f"- {reason}: {data['count']} trades, {data['profit_usdt']:.2f} USDT\n"
        
        report += "\n"
    
    report += "---\n\n## Recommendation\n\n"
    
    # Find winners
    winners = [r for r in all_results[1:] if r.get('acceptance', {}).get('overall_pass', False)]
    
    if winners:
        best = max(winners, key=lambda x: x['metrics']['profit_pct'])
        report += f"**✅ ENABLE:** {best['variant']['name']}\n\n"
        report += f"- **Profit:** {best['metrics']['profit_pct']:.2f}% (baseline: {baseline['profit_pct']:.2f}%)\n"
        report += f"- **stop_loss:** {best['metrics']['exit_reasons']['stop_loss']['count']} (baseline: {baseline['exit_reasons']['stop_loss']['count']})\n"
        report += f"- **Trade Count:** {best['metrics']['total_trades']} (baseline: {baseline['total_trades']})\n\n"
        report += f"**Rationale:** This configuration beats baseline while maintaining hard constraints.\n\n"
    else:
        report += "**❌ REJECT ALL FILTERS**\n\n"
        report += "No variant met acceptance criteria. Baseline remains optimal.\n\n"
        report += "**Possible reasons:**\n"
        report += "- Filters too restrictive, miss profitable setups\n"
        report += "- exit_signal losses are inherent to trend-following, not filterable at entry\n"
        report += "- BTC/USDT losses (72% of exit_signal) may require pair-specific logic, not regime filters\n\n"
    
    report += "---\n\n"
    report += "*Note: This ablation focused on entry regime filters per attribution analysis in exit_signal_attribution.md*\n"
    
    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n[OK] Report written to: {output_path}")


def main():
    print("=" * 70)
    print("ENTRY REGIME FILTERS ABLATION STUDY")
    print("=" * 70)
    
    strategy_path = Path(__file__).parent.parent / 'user_data' / 'strategies' / 'EPAUltimateV3.py'
    report_path = Path(__file__).parent.parent / 'reports' / 'entry_regime_filters_ablation.md'
    
    all_results = []
    
    for variant in VARIANTS:
        print(f"\n{'#'*70}")
        print(f"VARIANT: {variant['name']}")
        print(f"Description: {variant['description']}")
        print(f"{'#'*70}")
        
        # Modify strategy
        modify_strategy_params(
            strategy_path,
            variant['ema200_filter'],
            variant['adx_filter']
        )
        
        # Run backtest
        output = run_backtest(variant['name'])
        if not output:
            print(f"⚠️ Skipping {variant['name']} due to backtest failure")
            continue
        
        # Parse results
        metrics = parse_backtest_output(output)
        
        result = {
            'variant': variant,
            'metrics': metrics
        }
        
        # Check acceptance (skip for baseline)
        if len(all_results) > 0:
            baseline = all_results[0]['metrics']
            result['acceptance'] = check_acceptance(metrics, baseline)
        
        all_results.append(result)
        
        print(f"\n[OK] Completed {variant['name']}")
        print(f"  Profit: {metrics.get('profit_pct', 0):.2f}%")
        print(f"  Trades: {metrics.get('total_trades', 0)}")
        print(f"  stop_loss: {metrics['exit_reasons'].get('stop_loss', {}).get('count', 0)}")
    
    # Generate report
    print("\n" + "="*70)
    print("GENERATING REPORT")
    print("="*70)
    
    generate_report(all_results, report_path)
    
    # Restore baseline settings
    print("\n" + "="*70)
    print("RESTORING BASELINE SETTINGS")
    print("="*70)
    modify_strategy_params(strategy_path, False, False)
    
    print("\n" + "="*70)
    print("ABLATION COMPLETE")
    print("="*70)


if __name__ == '__main__':
    main()
