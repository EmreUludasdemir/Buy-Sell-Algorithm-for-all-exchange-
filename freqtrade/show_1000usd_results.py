import json
from pathlib import Path

results_dir = Path("user_data/backtest_results")
meta_file = results_dir / "backtest-result-2026-01-08_18-25-52.meta.json"

with open(meta_file) as f:
    data = json.load(f)

print("=" * 70)
print("$1000 INVESTMENT BACKTEST RESULTS")
print("Strategy: EPAFuturesTrend | Timerange: 2023-2026")
print("=" * 70)

for strat_name, strat_data in data.items():
    print(f"\nStrategy: {strat_name}")
    print("-" * 50)
    
    # Key metrics
    trades = strat_data.get('total_trades', 0)
    wins = strat_data.get('wins', 0)
    losses = strat_data.get('losses', 0)
    draws = strat_data.get('draws', 0)
    
    # Financial results
    profit_pct = strat_data.get('profit_total', 0) * 100 if strat_data.get('profit_total') else 0
    profit_abs = strat_data.get('profit_total_abs', 0)
    
    # Drawdown
    max_dd = strat_data.get('max_drawdown', 0) * 100 if strat_data.get('max_drawdown') else 0
    max_dd_abs = strat_data.get('max_drawdown_abs', 0)
    
    # Win rate
    win_rate = (wins / trades * 100) if trades > 0 else 0
    
    print(f"\nStarting Capital: $1,000.00")
    print(f"Total Trades: {trades}")
    print(f"Win/Draw/Loss: {wins}/{draws}/{losses}")
    print(f"Win Rate: {win_rate:.1f}%")
    print()
    print(f"Total Profit: ${profit_abs:.2f} ({profit_pct:.2f}%)")
    print(f"Final Balance: ${1000 + profit_abs:.2f}")
    print()
    print(f"Max Drawdown: ${max_dd_abs:.2f} ({max_dd:.2f}%)")
    
    # All available keys for debugging
    print("\n[All available metrics]")
    for key in sorted(strat_data.keys()):
        if not key.startswith('backtest'):
            val = strat_data[key]
            if isinstance(val, float):
                print(f"  {key}: {val:.4f}")
            else:
                print(f"  {key}: {val}")
