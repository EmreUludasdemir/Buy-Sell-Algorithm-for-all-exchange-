import json
import os

batch_dir = 'user_data/backtest_results/temp_batch'
json_files = [f for f in os.listdir(batch_dir) if f.endswith('.json') and not f.endswith('_config.json')]
json_file = [f for f in json_files if 'backtest-result' in f][0]

d = json.load(open(os.path.join(batch_dir, json_file)))

results = []
for name, s in d['strategy'].items():
    trades = s['total_trades']
    profit = s['profit_total_abs']
    wins = s['wins']
    win_rate = (wins / max(trades, 1)) * 100
    sharpe = s.get('sharpe', 0)
    pf = s.get('profit_factor', 0)
    
    results.append({
        'name': name,
        'trades': trades,
        'profit': round(profit, 2),
        'win_rate': round(win_rate, 1),
        'sharpe': round(sharpe, 3),
        'pf': round(pf, 3),
        'status': 'KEEP' if profit > 0 and sharpe > 0 else 'DELETE'
    })

results.sort(key=lambda x: x['profit'], reverse=True)

with open('strategy_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("Results saved to strategy_results.json")
for r in results:
    print(f"{r['name']}: ${r['profit']} | Sharpe {r['sharpe']} | {r['status']}")
