import json

f = open(r'user_data/backtest_results/temp_latest/backtest-result-2026-01-02_08-27-06.json')
d = json.load(f)
s = d['strategy']['EPAUltimateV3_Aggressive']

# Print all keys to understand structure
print("Available keys:", list(s.keys()))
print()

# Print trades stats
trades = s['trades']
total = len(trades)
profit_trades = [t for t in trades if t.get('profit_ratio', 0) > 0]
loss_trades = [t for t in trades if t.get('profit_ratio', 0) <= 0]
total_profit = sum(t.get('profit_abs', 0) for t in trades)

print(f"Total Trades: {total}")
print(f"Wins: {len(profit_trades)}")
print(f"Losses: {len(loss_trades)}")
print(f"Win Rate: {len(profit_trades)/total*100:.1f}%")
print(f"Total Profit: {total_profit:.2f} USDT")

# Exit reasons
roi = len([t for t in trades if 'roi' in str(t.get('exit_reason', ''))])
sl = len([t for t in trades if 'stop_loss' in str(t.get('exit_reason', ''))])
sig = len([t for t in trades if 'exit_signal' in str(t.get('exit_reason', ''))])

print(f"\nROI exits: {roi}")
print(f"Stop Loss exits: {sl}")
print(f"Signal exits: {sig}")

# Max drawdown - calculate from trades
running = 0
peak = 0
max_dd = 0
for t in trades:
    running += t.get('profit_abs', 0)
    peak = max(peak, running)
    dd = (peak - running) / 2000 * 100 if peak > 0 else 0
    max_dd = max(max_dd, dd)

print(f"\nApprox Max DD: {max_dd:.2f}%")
print(f"Final Balance: {2000 + total_profit:.2f} USDT")
print(f"Profit%: {total_profit/2000*100:.2f}%")

