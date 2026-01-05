#!/usr/bin/env python3
"""
Batch Backtest Script for EPA Trading Strategies
Tests all strategies and generates comparison report
"""

import subprocess
import json
import os
from datetime import datetime

STRATEGIES = [
    "EPAAlphaTrend",
    "EPAAlphaTrendV1",
    "EPAUltimateV3",
    "EPAUltimateV3_1H",
    "EPAUltimateV3_1H_MACD",
    "EPAUltimateV3_Aggressive",
    "EPAUltimateV3_Balanced",
    "EPAUltimateV3_MinimalTweak",
    "EPAUltimateV3_Optimized",
    "EPAUltimateV3_RegimeBTC",
    "EPAUltimateV4",
    "AlphaTrendAdaptive",
    "AlphaTrendBaseline",
]

TIMERANGE = "20230101-20250101"
TIMEFRAME = "2h"
PAIRS = "BTC/USDT ETH/USDT SOL/USDT BNB/USDT XRP/USDT"

results = []

for strategy in STRATEGIES:
    print(f"\n{'='*50}")
    print(f"Testing: {strategy}")
    print(f"{'='*50}")
    
    try:
        # Check if 1H strategy - use 1h timeframe
        tf = "1h" if "_1H" in strategy else TIMEFRAME
        
        cmd = f"freqtrade backtesting --strategy {strategy} --timerange {TIMERANGE} --timeframe {tf} -p {PAIRS} --export none"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600)
        
        output = result.stdout + result.stderr
        
        # Parse results from output
        profit_line = [l for l in output.split('\n') if 'Total profit' in l]
        trades_line = [l for l in output.split('\n') if 'Total/Avg trades' in l]
        
        results.append({
            "strategy": strategy,
            "status": "OK" if result.returncode == 0 else "ERROR",
            "output": output[-500:] if len(output) > 500 else output
        })
        
    except subprocess.TimeoutExpired:
        results.append({"strategy": strategy, "status": "TIMEOUT", "output": ""})
    except Exception as e:
        results.append({"strategy": strategy, "status": "ERROR", "output": str(e)})

# Save results
with open("user_data/backtest_results/batch_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\n" + "="*50)
print("BATCH BACKTEST COMPLETE")
print("="*50)
print(f"Results saved to: user_data/backtest_results/batch_results.json")
