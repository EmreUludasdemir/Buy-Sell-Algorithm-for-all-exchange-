import json

def analyze_backtest(filepath):
    with open(filepath, encoding='utf-8') as f:
        d = json.load(f)
    
    strat_name = list(d['strategy'].keys())[0]
    s = d['strategy'][strat_name]
    trades = s['trades']
    
    total = len(trades)
    if total == 0:
        return None
    
    profit_trades = [t for t in trades if t.get('profit_ratio', 0) > 0]
    total_profit = sum(t.get('profit_abs', 0) for t in trades)
    
    roi = len([t for t in trades if 'roi' in str(t.get('exit_reason', ''))])
    sl = len([t for t in trades if 'stop_loss' in str(t.get('exit_reason', ''))])
    sig = len([t for t in trades if 'exit_signal' in str(t.get('exit_reason', ''))])
    
    running = 0
    peak = 0
    max_dd = 0
    for t in trades:
        running += t.get('profit_abs', 0)
        peak = max(peak, running)
        dd = (peak - running) / 2000 * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)
    
    pairs = set(t['pair'] for t in trades)
    
    return {
        'strategy': strat_name,
        'trades': total,
        'pairs': len(pairs),
        'wins': len(profit_trades),
        'winrate': len(profit_trades)/total*100,
        'profit_usdt': total_profit,
        'profit_pct': total_profit/2000*100,
        'max_dd': max_dd,
        'roi_exits': roi,
        'sl_exits': sl,
        'sig_exits': sig,
    }

# Analyze all 3 scenarios
baseline = analyze_backtest('user_data/backtest_results/temp_baseline/backtest-result-2026-01-02_08-30-54.json')
aggressive_10p = analyze_backtest('user_data/backtest_results/temp_latest/backtest-result-2026-01-02_08-27-06.json')
roi_only = analyze_backtest('user_data/backtest_results/temp_roi_only/backtest-result-2026-01-02_08-39-02.json')

with open('final_result.txt', 'w', encoding='utf-8') as f:
    f.write("=" * 90 + "\n")
    f.write("FULL COMPARISON: Baseline vs Aggressive ROI (5 pairs) vs Aggressive ROI (10 pairs)\n")
    f.write("=" * 90 + "\n\n")
    f.write(f"{'Metric':<18} {'V3 Patient ROI':<22} {'V3_Agg (5 pairs)':<22} {'V3_Agg (10 pairs)':<22}\n")
    f.write("-" * 90 + "\n")

    for name, b, r, a in [
        ('Strategy', baseline['strategy'][:18], roi_only['strategy'][:18], aggressive_10p['strategy'][:18]),
        ('Pairs', str(baseline['pairs']), str(roi_only['pairs']), str(aggressive_10p['pairs'])),
        ('Trades', str(baseline['trades']), str(roi_only['trades']), str(aggressive_10p['trades'])),
        ('Win Rate', f"{baseline['winrate']:.1f}%", f"{roi_only['winrate']:.1f}%", f"{aggressive_10p['winrate']:.1f}%"),
        ('Profit USDT', f"{baseline['profit_usdt']:.2f}", f"{roi_only['profit_usdt']:.2f}", f"{aggressive_10p['profit_usdt']:.2f}"),
        ('Profit %', f"{baseline['profit_pct']:.2f}%", f"{roi_only['profit_pct']:.2f}%", f"{aggressive_10p['profit_pct']:.2f}%"),
        ('Max DD', f"{baseline['max_dd']:.2f}%", f"{roi_only['max_dd']:.2f}%", f"{aggressive_10p['max_dd']:.2f}%"),
        ('ROI Exits', str(baseline['roi_exits']), str(roi_only['roi_exits']), str(aggressive_10p['roi_exits'])),
        ('SL Exits', str(baseline['sl_exits']), str(roi_only['sl_exits']), str(aggressive_10p['sl_exits'])),
    ]:
        f.write(f"{name:<18} {b:<22} {r:<22} {a:<22}\n")

    f.write("\n" + "=" * 90 + "\n")

    results = [
        ('V3 Patient ROI (5 pairs)', baseline),
        ('V3_Agg ROI only (5 pairs)', roi_only),
        ('V3_Agg + 10 pairs', aggressive_10p),
    ]

    winner = max(results, key=lambda x: x[1]['profit_pct'] if x[1]['max_dd'] <= 12 else -999)
    f.write(f"WINNER: {winner[0]}\n")
    f.write(f"  Profit: {winner[1]['profit_pct']:.2f}% | DD: {winner[1]['max_dd']:.2f}% | Trades: {winner[1]['trades']}\n")
    f.write("=" * 90 + "\n")

print("Done - check final_result.txt")
