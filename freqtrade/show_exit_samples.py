#!/usr/bin/env python3
"""
Generate comprehensive exit_signal improvement report
"""

import json
from pathlib import Path

analysis_file = Path("user_data/backtest_results/exit_signal_analysis.json")
data = json.load(open(analysis_file))

print("=" * 80)
print("EXIT_SIGNAL TRADE SAMPLES")
print("=" * 80)
print()

for i, trade in enumerate(data['sample_trades'], 1):
    print(f"{i}. {trade['pair']}")
    print(f"   Profit: {trade['profit_ratio']*100:.2f}% ({trade['profit_abs']:.2f} USDT)")
    print(f"   Duration: {trade.get('trade_duration', 'N/A')}")
    print(f"   Open: {trade['open_date']}")
    print(f"   Close: {trade['close_date']}")
    print(f"   Entry: {trade['open_rate']:.4f}, Exit: {trade['close_rate']:.4f}")
    print()
