import json
from pathlib import Path

results_dir = Path("user_data/backtest_results")

# Get latest JSON files (not meta)
json_files = sorted(
    [f for f in results_dir.glob("backtest-result-2026-01-08_16*.json") 
     if not f.name.endswith(".meta.json")],
    key=lambda x: x.stat().st_mtime, 
    reverse=True
)[:5]

print("=" * 90)
print("EPA COIN-SPECIFIC STRATEGY BACKTEST RESULTS")
print("Timerange: 2023-01-01 to 2026-01-01")
print("=" * 90)
print()

results = []
for jf in json_files:
    with open(jf) as f:
        data = json.load(f)
    
    # Get strategy info
    strat = data.get("strategy", {})
    strat_name = strat.get("strategy", "Unknown")
    
    # Get results
    result = data.get("strategy_comparison", [{}])[0] if data.get("strategy_comparison") else {}
    
    # Try different paths to get data
    trades = result.get("trades", 0) or data.get("results_per_strategy", [{}])[0].get("trades", 0) if data.get("results_per_strategy") else 0
    
    # Get from main keys
    if "strategy" in data:
        for key in data:
            if isinstance(data[key], list) and len(data[key]) > 0:
                first = data[key][0]
                if isinstance(first, dict) and "trades" in first:
                    trades = first.get("trades", 0)
                    profit = first.get("profit_total_pct", 0)
                    wins = first.get("wins", 0)
                    drawdown = first.get("max_drawdown_abs", 0)
                    results.append({
                        "strategy": strat_name,
                        "trades": trades,
                        "profit": profit,
                        "wins": wins,
                        "drawdown": drawdown
                    })
                    break

print("Found files:", [f.name for f in json_files])
print()
for r in results:
    print(f"{r['strategy']}: {r['trades']} trades, {r['profit']:.2f}% profit")
