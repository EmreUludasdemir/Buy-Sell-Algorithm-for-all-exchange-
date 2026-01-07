import json

# Read 2x results
with open('user_data/backtest_results/backtest-result-2026-01-06_18-12-51.json', 'r') as f:
    data_2x = json.load(f)

# Read 3x results  
with open('user_data/backtest_results/backtest-result-2026-01-06_18-50-32.json', 'r') as f:
    data_3x = json.load(f)

# Extract key metrics
def get_metrics(data, strategy_name):
    strat = data['strategy'][strategy_name]
    trades = strat['trades']
    total_profit = sum([t['profit_abs'] for t in trades])
    wins = len([t for t in trades if t['profit_abs'] > 0])
    losses = len([t for t in trades if t['profit_abs'] <= 0])
    win_rate = wins / len(trades) * 100 if trades else 0
    avg_win = sum([t['profit_abs'] for t in trades if t['profit_abs'] > 0]) / wins if wins else 0
    avg_loss = sum([t['profit_abs'] for t in trades if t['profit_abs'] <= 0]) / losses if losses else 0
    return {
        'trades': len(trades),
        'profit': total_profit,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss
    }

m2x = get_metrics(data_2x, 'EPASuperTrendFuturesLong')
m3x = get_metrics(data_3x, 'EPASuperTrendFutures3x')

print("=== FUTURES BACKTEST COMPARISON ===")
print("Timerange: 2023-01-01 to 2026-01-01")
print("Pairs: BTC/ETH only")
print()
print("=== 2x LEVERAGE (EPASuperTrendFuturesLong) ===")
print("Total Trades:", m2x['trades'])
print("Total Profit: $%.2f" % m2x['profit'])
print("Win/Loss: %d/%d" % (m2x['wins'], m2x['losses']))
print("Win Rate: %.1f%%" % m2x['win_rate'])
print("Avg Win: $%.2f" % m2x['avg_win'])
print("Avg Loss: $%.2f" % m2x['avg_loss'])
print()
print("=== 3x LEVERAGE (EPASuperTrendFutures3x) ===")
print("Total Trades:", m3x['trades'])
print("Total Profit: $%.2f" % m3x['profit'])
print("Win/Loss: %d/%d" % (m3x['wins'], m3x['losses']))
print("Win Rate: %.1f%%" % m3x['win_rate'])
print("Avg Win: $%.2f" % m3x['avg_win'])
print("Avg Loss: $%.2f" % m3x['avg_loss'])
print()
print("=== COMPARISON ===")
print("Profit Difference: $%.2f (%.1fx)" % (m3x['profit'] - m2x['profit'], m3x['profit'] / m2x['profit'] if m2x['profit'] else 0))
