#!/usr/bin/env python3
import json
import os

results_dir = r'c:\Users\Emre\Desktop\Buy-sell Algorithm\Buy-Sell-Algorithm-for-all-exchange-\freqtrade\user_data\backtest_results'

files = [
    ('2023 H2 (Jul-Dec)', 'backtest-result-2025-12-28_23-45-08.json'),
    ('2024 Full Year', 'backtest-result-2025-12-28_23-45-20.json'),
    ('Full 2Y Period', 'backtest-result-2025-12-28_23-14-31.json'),
]

print("=" * 80)
print("MULTI-SCENARIO BACKTEST RESULTS - EPAStrategyV2 (4H)")
print("=" * 80)

for period, f in files:
    path = os.path.join(results_dir, f)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            strat = data.get('strategy', {}).get('EPAStrategyV2', {})
            
            total = strat.get('total_trades', 0)
            wins = strat.get('wins', 0)
            win_rate = (wins / total * 100) if total > 0 else 0
            
            print(f"\n### {period}")
            print(f"   Total Trades:  {total}")
            print(f"   Win Rate:      {win_rate:.1f}% ({wins}/{total})")
            print(f"   Profit Total:  {strat.get('profit_total', 0)*100:.2f}%")
            print(f"   Profit USDT:   {strat.get('profit_total_abs', 0):.2f}")
            print(f"   Sharpe Ratio:  {strat.get('sharpe', 'N/A')}")
            print(f"   Sortino Ratio: {strat.get('sortino', 'N/A')}")
            print(f"   Calmar Ratio:  {strat.get('calmar', 'N/A')}")
            print(f"   Max Drawdown:  {strat.get('max_drawdown_account', 0)*100:.2f}%")
            print(f"   CAGR:          {strat.get('cagr', 0)*100:.2f}%")
            print(f"   Profit Factor: {strat.get('profit_factor', 'N/A')}")
            print(f"   Expectancy:    {strat.get('expectancy', 'N/A')}")
    else:
        print(f"\n### {period}: File not found")

print("\n" + "=" * 80)
