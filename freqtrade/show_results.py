import json
from pathlib import Path

results_dir = Path("user_data/backtest_results")

# Get all recent meta files
meta_files = sorted(results_dir.glob("backtest-result-2026-01-08*.meta.json"), 
                   key=lambda x: x.stat().st_mtime, reverse=True)[:10]

print("=" * 80)
print("BACKTEST COMPARISON RESULTS")
print("=" * 80)

for mf in meta_files:
    with open(mf) as f:
        data = json.load(f)
    
    for strat_name, strat_data in data.items():
        trades = strat_data.get('total_trades', 0)
        if trades == 0:
            # Try to get from nested structure
            if isinstance(strat_data, dict):
                for key, value in strat_data.items():
                    if isinstance(value, (int, float)) and key == 'total_trades':
                        trades = value
        
        wins = strat_data.get('wins', 0)
        
        print(f"\nStrategy: {strat_name}")
        print(f"  File: {mf.name}")
        print(f"  Total Trades: {trades}")
        print(f"  Wins: {wins}")
        print(f"  All keys: {list(strat_data.keys())[:10]}")
