import json
from pathlib import Path

results_dir = Path("user_data/backtest_results")

# Latest results
files = [
    "backtest-result-2026-01-08_17-01-09.meta.json",  # EPABuyHold
    "backtest-result-2026-01-08_17-16-34.meta.json",  # EPAFuturesTrend
]

print("=" * 80)
print("STRATEGY COMPARISON: Buy-Hold vs Active Trading")
print("Timerange: 2023-01-01 to 2026-01-01")
print("=" * 80)
print()

for f in files:
    filepath = results_dir / f
    with open(filepath) as fp:
        data = json.load(fp)
    
    for strat_name, strat_data in data.items():
        print(f"\n{'='*60}")
        print(f"Strategy: {strat_name}")
        print(f"{'='*60}")
        
        # Print all available keys and values
        for key, value in strat_data.items():
            if key.startswith('backtest'):
                continue  # Skip timestamps
            print(f"  {key}: {value}")
