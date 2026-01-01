#!/usr/bin/env python3
"""
Analyze exit_signal trades from EPAUltimateV3 backtest
Identifies patterns causing losing exit_signal exits
"""

import json
import zipfile
from pathlib import Path
from datetime import datetime, timedelta
import statistics

def load_trades_from_latest_backtest():
    """Load trades from the most recent backtest ZIP file"""
    backtest_dir = Path("user_data/backtest_results")
    
    # Find most recent backtest file
    backtest_files = list(backtest_dir.glob("backtest-result-*.zip"))
    if not backtest_files:
        raise FileNotFoundError("No backtest result files found")
    
    latest_file = max(backtest_files, key=lambda p: p.stem)
    print(f"Loading trades from: {latest_file.name}")
    
    with zipfile.ZipFile(latest_file, 'r') as zf:
        # Find the base JSON file (not .meta.json)
        base_name = latest_file.stem
        main_json = f"{base_name}.json"
        
        with zf.open(main_json) as f:
            data = json.load(f)
            
            # Handle nested strategy structure
            if 'strategy' in data:
                strategy_data = data['strategy']
                strategy_name = list(strategy_data.keys())[0]
                trades = strategy_data[strategy_name].get('trades', [])
            else:
                trades = data.get('trades', [])
            
            return trades

def analyze_exit_signal_trades(trades):
    """Analyze trades that exited with exit_signal"""
    
    exit_signal_trades = [t for t in trades if t.get('exit_reason') == 'exit_signal']
    
    if not exit_signal_trades:
        return {
            'count': 0,
            'message': 'No exit_signal trades found'
        }
    
    # Calculate basic metrics
    total_pnl = sum(t['profit_abs'] for t in exit_signal_trades)
    avg_pnl = total_pnl / len(exit_signal_trades)
    profit_ratios = [t['profit_ratio'] * 100 for t in exit_signal_trades]
    
    # Duration analysis
    durations_hours = []
    early_exits = []  # Within first 8 hours (2 candles)
    
    for trade in exit_signal_trades:
        open_time = datetime.fromisoformat(trade['open_date'].replace('Z', '+00:00'))
        close_time = datetime.fromisoformat(trade['close_date'].replace('Z', '+00:00'))
        duration = (close_time - open_time).total_seconds() / 3600
        durations_hours.append(duration)
        
        if duration <= 8:  # 2 candles = 8 hours
            early_exits.append(trade)
    
    # Profit zones
    profit_zones = {
        'near_zero': [],  # -1% to +1%
        'small_loss': [],  # -1% to -4%
        'big_loss': [],   # < -4%
        'profit': []      # > +1%
    }
    
    for trade in exit_signal_trades:
        pnl_pct = trade['profit_ratio'] * 100
        if -1 <= pnl_pct <= 1:
            profit_zones['near_zero'].append(trade)
        elif -4 <= pnl_pct < -1:
            profit_zones['small_loss'].append(trade)
        elif pnl_pct < -4:
            profit_zones['big_loss'].append(trade)
        else:
            profit_zones['profit'].append(trade)
    
    return {
        'count': len(exit_signal_trades),
        'total_pnl_usdt': total_pnl,
        'avg_pnl_usdt': avg_pnl,
        'avg_pnl_pct': statistics.mean(profit_ratios),
        'median_pnl_pct': statistics.median(profit_ratios),
        'median_duration_hours': statistics.median(durations_hours),
        'avg_duration_hours': statistics.mean(durations_hours),
        'early_exits_count': len(early_exits),
        'early_exits_pct': len(early_exits) / len(exit_signal_trades) * 100,
        'profit_zones': {
            'near_zero': len(profit_zones['near_zero']),
            'small_loss': len(profit_zones['small_loss']),
            'big_loss': len(profit_zones['big_loss']),
            'profit': len(profit_zones['profit'])
        },
        'sample_trades': exit_signal_trades[:5],  # First 5 for examples
        'early_exits_sample': early_exits[:3] if early_exits else []
    }

def main():
    print("=" * 80)
    print("EXIT_SIGNAL TRADE ANALYSIS - EPAUltimateV3")
    print("=" * 80)
    print()
    
    trades = load_trades_from_latest_backtest()
    print(f"Total trades loaded: {len(trades)}")
    print()
    
    analysis = analyze_exit_signal_trades(trades)
    
    if analysis['count'] == 0:
        print(analysis['message'])
        return
    
    print(f"📊 EXIT_SIGNAL TRADES: {analysis['count']}")
    print(f"   Total P&L: {analysis['total_pnl_usdt']:.2f} USDT")
    print(f"   Average P&L: {analysis['avg_pnl_usdt']:.2f} USDT ({analysis['avg_pnl_pct']:.2f}%)")
    print(f"   Median P&L: {analysis['median_pnl_pct']:.2f}%")
    print(f"   Median Duration: {analysis['median_duration_hours']:.1f} hours")
    print(f"   Average Duration: {analysis['avg_duration_hours']:.1f} hours")
    print()
    
    print(f"⚠️  EARLY EXITS (≤ 8 hours / 2 candles): {analysis['early_exits_count']}")
    print(f"   Percentage of exit_signal trades: {analysis['early_exits_pct']:.1f}%")
    print()
    
    print("📈 PROFIT ZONES:")
    zones = analysis['profit_zones']
    print(f"   Near Zero (-1% to +1%): {zones['near_zero']} trades")
    print(f"   Small Loss (-1% to -4%): {zones['small_loss']} trades")
    print(f"   Big Loss (< -4%): {zones['big_loss']} trades")
    print(f"   Profit (> +1%): {zones['profit']} trades")
    print()
    
    if analysis['early_exits_sample']:
        print("🔍 EARLY EXIT EXAMPLES:")
        for i, trade in enumerate(analysis['early_exits_sample'], 1):
            print(f"   {i}. {trade['pair']}: {trade['profit_ratio']*100:.2f}% "
                  f"in {trade.get('trade_duration', 'N/A')}")
    
    # Generate JSON report for further analysis
    output_file = Path("user_data/backtest_results/exit_signal_analysis.json")
    with open(output_file, 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    
    print()
    print(f"✅ Detailed analysis saved to: {output_file}")

if __name__ == "__main__":
    main()
