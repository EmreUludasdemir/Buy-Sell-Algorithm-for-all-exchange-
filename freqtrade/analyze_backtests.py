import json
import os
from pathlib import Path
from datetime import datetime

results_dir = Path("user_data/backtest_results")

# Get latest meta files from today
meta_files = sorted(results_dir.glob("backtest-result-2026-01-08*.meta.json"), 
                   key=lambda x: x.stat().st_mtime, reverse=True)[:7]

print("=" * 80)
print("EPA MULTI-STRATEGY BACKTEST RESULTS")
print("Timerange: 2023-01-01 to 2026-01-01 (Full Market Conditions)")
print("=" * 80)
print()

results = []
for mf in meta_files:
    with open(mf) as f:
        data = json.load(f)
    
    for strat_name, strat_data in data.items():
        trades = strat_data.get("total_trades", 0)
        
        # Try different ways to get profit
        profit_abs = strat_data.get("profit_total_abs", 0)
        profit_pct = strat_data.get("profit_total", 0) * 100 if strat_data.get("profit_total") else 0
        
        # Get drawdown
        dd_abs = strat_data.get("max_drawdown_abs", 0)
        dd_pct = strat_data.get("max_drawdown", 0) * 100 if strat_data.get("max_drawdown") else 0
        
        # Win rate
        wins = strat_data.get("wins", 0)
        win_rate = wins / trades * 100 if trades > 0 else 0
        
        # Get backtest end time to validate range
        run_id = strat_data.get("run_id", "")
        
        results.append({
            "name": strat_name,
            "trades": trades,
            "profit_abs": profit_abs,
            "profit_pct": profit_pct,
            "drawdown_abs": dd_abs,
            "drawdown_pct": dd_pct,
            "win_rate": win_rate,
            "wins": wins,
            "file": mf.name
        })
        
        print(f"{strat_name}")
        print(f"  Trades: {trades}, Wins: {wins} ({win_rate:.1f}%)")  
        print(f"  Profit: ${profit_abs:.2f} ({profit_pct:.2f}%)")
        print(f"  Max DD: ${dd_abs:.2f} ({dd_pct:.2f}%)")
        print()

# Summary table
print("=" * 80)
print("SUMMARY TABLE (sorted by profit)")
print("=" * 80)
print(f"{'Strategy':<28} {'Trades':>7} {'Profit$':>10} {'Profit%':>9} {'Win%':>8} {'MaxDD%':>8}")
print("-" * 80)

for r in sorted(results, key=lambda x: x["profit_abs"], reverse=True):
    print(f"{r['name']:<28} {r['trades']:>7} ${r['profit_abs']:>8.2f} {r['profit_pct']:>8.2f}% {r['win_rate']:>7.1f}% {r['drawdown_pct']:>7.2f}%")

# Top 3
print()
print("=" * 80)
print("TOP 3 PERFORMERS")
print("=" * 80)
top3 = sorted(results, key=lambda x: x["profit_abs"], reverse=True)[:3]
for i, r in enumerate(top3, 1):
    print(f"{i}. {r['name']}: ${r['profit_abs']:.2f} profit ({r['profit_pct']:.2f}%), {r['win_rate']:.1f}% win rate")

# Save markdown report
report_path = results_dir / "strategy_comparison_final.md"
with open(report_path, "w", encoding="utf-8") as f:
    f.write("# EPA Multi-Strategy Backtest Results\n\n")
    f.write("**Timerange:** 2023-01-01 to 2026-01-01 (Full Market Conditions)\n\n")
    f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
    
    f.write("## Strategy Comparison\n\n")
    f.write("| Strategy | Trades | Profit ($) | Profit (%) | Win Rate | Max DD |\n")
    f.write("|----------|--------|------------|------------|----------|--------|\n")
    
    for r in sorted(results, key=lambda x: x["profit_abs"], reverse=True):
        f.write(f"| {r['name']} | {r['trades']} | ${r['profit_abs']:.2f} | {r['profit_pct']:.2f}% | {r['win_rate']:.1f}% | {r['drawdown_pct']:.2f}% |\n")
    
    f.write("\n## Top 3 Strategies for Optimization\n\n")
    for i, r in enumerate(top3, 1):
        f.write(f"{i}. **{r['name']}**: ${r['profit_abs']:.2f} profit ({r['profit_pct']:.2f}%), {r['win_rate']:.1f}% win rate, {r['drawdown_pct']:.2f}% max drawdown\n")
    
    f.write("\n## Next Steps\n\n")
    f.write("1. Run hyperopt on top 3 strategies to optimize parameters\n")
    f.write("2. Re-run backtests with optimized parameters\n")
    f.write("3. Compare and select best strategy for live trading\n")

print(f"\nReport saved to: {report_path}")
