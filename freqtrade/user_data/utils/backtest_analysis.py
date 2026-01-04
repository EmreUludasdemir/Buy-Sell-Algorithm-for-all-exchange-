"""
Backtest analysis utilities.
"""
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any, Optional


def analyze_backtest_results(
    results_path: str,
    baseline_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze backtest results and optionally compare to baseline.
    
    Args:
        results_path: Path to backtest results JSON
        baseline_path: Optional path to baseline results for comparison
        
    Returns:
        Analysis dictionary
    """
    results = _load_results(results_path)
    
    analysis = {
        'summary': _extract_summary(results),
        'trades': _analyze_trades(results),
        'metrics': _calculate_metrics(results)
    }
    
    if baseline_path:
        baseline = _load_results(baseline_path)
        analysis['comparison'] = _compare_results(results, baseline)
    
    return analysis


def _load_results(path: str) -> Dict:
    """Load backtest results from JSON."""
    with open(path, 'r') as f:
        return json.load(f)


def _extract_summary(results: Dict) -> Dict:
    """Extract summary statistics."""
    return {
        'total_trades': results.get('total_trades', 0),
        'profit_total': results.get('profit_total', 0),
        'profit_percent': results.get('profit_percent', 0),
        'max_drawdown': results.get('max_drawdown', 0),
        'win_rate': results.get('win_rate', 0)
    }


def _analyze_trades(results: Dict) -> Dict:
    """Analyze individual trades."""
    trades = results.get('trades', [])
    
    if not trades:
        return {'count': 0}
    
    df = pd.DataFrame(trades)
    
    return {
        'count': len(trades),
        'avg_profit': df['profit_ratio'].mean() if 'profit_ratio' in df else 0,
        'best_trade': df['profit_ratio'].max() if 'profit_ratio' in df else 0,
        'worst_trade': df['profit_ratio'].min() if 'profit_ratio' in df else 0,
        'avg_duration': df['trade_duration'].mean() if 'trade_duration' in df else 0
    }


def _calculate_metrics(results: Dict) -> Dict:
    """Calculate additional performance metrics."""
    trades = results.get('trades', [])
    
    if not trades:
        return {}
    
    df = pd.DataFrame(trades)
    profits = df.get('profit_ratio', pd.Series())
    
    if len(profits) == 0:
        return {}
    
    # Sharpe-like ratio (simplified)
    mean_profit = profits.mean()
    std_profit = profits.std()
    sharpe_like = mean_profit / std_profit if std_profit > 0 else 0
    
    # Profit factor
    gains = profits[profits > 0].sum()
    losses = abs(profits[profits < 0].sum())
    profit_factor = gains / losses if losses > 0 else float('inf')
    
    return {
        'sharpe_like': sharpe_like,
        'profit_factor': profit_factor,
        'win_rate': (profits > 0).mean() * 100
    }


def _compare_results(results: Dict, baseline: Dict) -> Dict:
    """Compare results to baseline."""
    r_summary = _extract_summary(results)
    b_summary = _extract_summary(baseline)
    
    return {
        'profit_diff': r_summary['profit_percent'] - b_summary['profit_percent'],
        'trade_count_diff': r_summary['total_trades'] - b_summary['total_trades'],
        'drawdown_diff': r_summary['max_drawdown'] - b_summary['max_drawdown'],
        'win_rate_diff': r_summary['win_rate'] - b_summary['win_rate']
    }


def print_analysis(analysis: Dict) -> None:
    """Pretty print analysis results."""
    print("\n" + "="*60)
    print("BACKTEST ANALYSIS")
    print("="*60)
    
    if 'summary' in analysis:
        print("\nSUMMARY:")
        for k, v in analysis['summary'].items():
            print(f"  {k}: {v}")
    
    if 'trades' in analysis:
        print("\nTRADES:")
        for k, v in analysis['trades'].items():
            print(f"  {k}: {v}")
    
    if 'metrics' in analysis:
        print("\nMETRICS:")
        for k, v in analysis['metrics'].items():
            print(f"  {k}: {v:.4f}")
    
    if 'comparison' in analysis:
        print("\nCOMPARISON TO BASELINE:")
        for k, v in analysis['comparison'].items():
            sign = "+" if v > 0 else ""
            print(f"  {k}: {sign}{v:.2f}")
    
    print("="*60 + "\n")
