import json
import os

def analyze_backtest(filepath, name):
    with open(filepath, encoding='utf-8') as f:
        d = json.load(f)
    
    # Get first strategy in the file
    strat_name = list(d['strategy'].keys())[0]
    s = d['strategy'][strat_name]
    trades = s['trades']
    
    total = len(trades)
    if total == 0:
        return None
    
    profit_trades = [t for t in trades if t.get('profit_ratio', 0) > 0]
    loss_trades = [t for t in trades if t.get('profit_ratio', 0) <= 0]
    total_profit = sum(t.get('profit_abs', 0) for t in trades)
    
    roi = len([t for t in trades if 'roi' in str(t.get('exit_reason', ''))])
    sl = len([t for t in trades if 'stop_loss' in str(t.get('exit_reason', ''))])
    sig = len([t for t in trades if 'exit_signal' in str(t.get('exit_reason', ''))])
    
    # Calculate drawdown
    running = 0
    peak = 0
    max_dd = 0
    for t in trades:
        running += t.get('profit_abs', 0)
        peak = max(peak, running)
        dd = (peak - running) / 2000 * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)
    
    # Get unique pairs
    pairs = set(t['pair'] for t in trades)
    
    return {
        'name': name,
        'strategy': strat_name,
        'trades': total,
        'pairs': len(pairs),
        'wins': len(profit_trades),
        'losses': len(loss_trades),
        'winrate': len(profit_trades)/total*100,
        'profit_usdt': total_profit,
        'profit_pct': total_profit/2000*100,
        'max_dd': max_dd,
        'roi_exits': roi,
        'sl_exits': sl,
        'sig_exits': sig,
    }

# Analyze both
baseline = analyze_backtest(
    'user_data/backtest_results/temp_baseline/backtest-result-2026-01-02_08-30-54.json',
    'Baseline (5 pairs)'
)
aggressive = analyze_backtest(
    'user_data/backtest_results/temp_latest/backtest-result-2026-01-02_08-27-06.json',
    'Aggressive (10 pairs)'
)

# Write to file instead of stdout
import sys
with open('comparison_output.txt', 'w', encoding='utf-8') as out:
    out.write("=" * 70 + "\n")
    out.write("BACKTEST COMPARISON: EPAUltimateV3 vs EPAUltimateV3_Aggressive\n")
    out.write("Timerange: 20240601-20241231 (7 months) | Wallet: 2000 USDT\n")
    out.write("=" * 70 + "\n\n")

    header = f"{'Metric':<20} {'Baseline':<20} {'Aggressive':<20} {'Delta':<10}\n"
    out.write(header)
    out.write("-" * 70 + "\n")

    if baseline and aggressive:
        metrics = [
            ('Strategy', baseline['strategy'], aggressive['strategy'], ''),
            ('Pairs', str(baseline['pairs']), str(aggressive['pairs']), f"+{aggressive['pairs']-baseline['pairs']}"),
            ('Trades', str(baseline['trades']), str(aggressive['trades']), f"+{aggressive['trades']-baseline['trades']}"),
            ('Win Rate', f"{baseline['winrate']:.1f}%", f"{aggressive['winrate']:.1f}%", f"{aggressive['winrate']-baseline['winrate']:+.1f}%"),
            ('Profit USDT', f"{baseline['profit_usdt']:.2f}", f"{aggressive['profit_usdt']:.2f}", f"{aggressive['profit_usdt']-baseline['profit_usdt']:+.2f}"),
            ('Profit %', f"{baseline['profit_pct']:.2f}%", f"{aggressive['profit_pct']:.2f}%", f"{aggressive['profit_pct']-baseline['profit_pct']:+.2f}%"),
            ('Max DD', f"{baseline['max_dd']:.2f}%", f"{aggressive['max_dd']:.2f}%", f"{aggressive['max_dd']-baseline['max_dd']:+.2f}%"),
            ('ROI Exits', str(baseline['roi_exits']), str(aggressive['roi_exits']), f"+{aggressive['roi_exits']-baseline['roi_exits']}"),
            ('SL Exits', str(baseline['sl_exits']), str(aggressive['sl_exits']), f"+{aggressive['sl_exits']-baseline['sl_exits']}"),
            ('Signal Exits', str(baseline['sig_exits']), str(aggressive['sig_exits']), f"+{aggressive['sig_exits']-baseline['sig_exits']}"),
        ]
        
        for metric, b, a, delta in metrics:
            out.write(f"{metric:<20} {b:<20} {a:<20} {delta:<10}\n")

    out.write("\n")
    out.write("=" * 70 + "\n")
    out.write("VERDICT:\n")
    if aggressive['profit_pct'] > baseline['profit_pct']:
        if aggressive['max_dd'] <= 10:
            out.write(f"[OK] AGGRESSIVE WINS with {aggressive['profit_pct']:.2f}% profit vs {baseline['profit_pct']:.2f}%\n")
            out.write(f"   DD is acceptable at {aggressive['max_dd']:.2f}%\n")
        else:
            out.write(f"[WARN] AGGRESSIVE has higher profit but DD ({aggressive['max_dd']:.2f}%) exceeds 10%\n")
    else:
        out.write(f"[FAIL] BASELINE performs better. Consider ROI-only change without new pairs.\n")
    out.write("=" * 70 + "\n")

print("Results written to comparison_output.txt")
