#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Scenario Backtest Runner
==============================
Runs EPAStrategyV2 across 3 different market regimes:
- Bull Market (2023-Q4 to 2024-Q1: BTC 25k → 70k)
- Bear Market (2022-Q2 to 2022-Q4: BTC 45k → 16k)
- Sideways Market (2024-Q2 to 2024-Q3: BTC 60k-70k range)

Outputs consolidated report with PF, WR, MDD, Sharpe, Sortino.

Usage:
    python scripts/run_backtests.py
    docker compose run --rm freqtrade python user_data/../scripts/run_backtests.py
"""

import json
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

# ============================================================================
#                           CONFIGURATION
# ============================================================================

# Strategy and config
STRATEGY = "EPAStrategyV2"
CONFIG = "user_data/config_production.json"
TIMEFRAME = "4h"

# Market regime scenarios with historical crypto periods
SCENARIOS = {
    "bull_market": {
        "name": "🐂 Bull Market",
        "description": "BTC rally from $25k to $70k ATH",
        "timerange": "20231001-20240315",
        "expected_bias": "Long-favored"
    },
    "bear_market": {
        "name": "🐻 Bear Market",
        "description": "BTC crash from $45k to $16k (FTX collapse)",
        "timerange": "20220501-20221231",
        "expected_bias": "Defensive/Short-favored"
    },
    "sideways_market": {
        "name": "🦀 Sideways Market",
        "description": "BTC consolidation $58k-$72k range",
        "timerange": "20240401-20240831",
        "expected_bias": "Range trading"
    }
}

# Output paths
SCRIPT_DIR = Path(__file__).parent
FREQTRADE_DIR = SCRIPT_DIR.parent
REPORTS_DIR = FREQTRADE_DIR / "reports"


# ============================================================================
#                           HELPER FUNCTIONS
# ============================================================================

def run_backtest(scenario_id: str, scenario: dict) -> dict:
    """Run backtest for a single scenario and parse results."""
    print(f"\n{'='*60}")
    print(f"Running: {scenario['name']}")
    print(f"Period: {scenario['timerange']}")
    print(f"Description: {scenario['description']}")
    print(f"{'='*60}\n")
    
    cmd = [
        "docker", "compose", "run", "--rm", "freqtrade", "backtesting",
        "--strategy", STRATEGY,
        "--config", CONFIG,
        "--timeframe", TIMEFRAME,
        "--timerange", scenario["timerange"],
        "--export", "none",  # Don't export trades, just get stats
        "--no-header"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=FREQTRADE_DIR,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        output = result.stdout + result.stderr
        return parse_backtest_output(output, scenario_id, scenario)
        
    except subprocess.TimeoutExpired:
        print(f"  ⚠️ Timeout for {scenario['name']}")
        return create_error_result(scenario_id, scenario, "Timeout")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return create_error_result(scenario_id, scenario, str(e))


def parse_backtest_output(output: str, scenario_id: str, scenario: dict) -> dict:
    """Parse backtest stdout to extract key metrics."""
    result = {
        "scenario_id": scenario_id,
        "scenario_name": scenario["name"],
        "timerange": scenario["timerange"],
        "description": scenario["description"],
        "profit_factor": None,
        "win_rate": None,
        "max_drawdown": None,
        "sharpe": None,
        "sortino": None,
        "total_profit_pct": None,
        "total_trades": None,
        "avg_profit_pct": None,
        "status": "success"
    }
    
    lines = output.split('\n')
    
    for line in lines:
        line_lower = line.lower()
        
        # Total profit
        if "total profit" in line_lower and "%" in line:
            try:
                # Extract percentage value
                parts = line.split()
                for i, p in enumerate(parts):
                    if "%" in p:
                        result["total_profit_pct"] = float(p.replace("%", "").replace(",", ""))
                        break
            except: pass
        
        # Profit factor
        if "profit factor" in line_lower:
            try:
                parts = line.split()
                for p in parts:
                    try:
                        val = float(p)
                        if 0 < val < 100:  # Reasonable PF range
                            result["profit_factor"] = round(val, 2)
                            break
                    except: pass
            except: pass
        
        # Win rate / Wins
        if ("win" in line_lower and "rate" in line_lower) or "wins" in line_lower:
            try:
                parts = line.split()
                for p in parts:
                    if "%" in p:
                        result["win_rate"] = float(p.replace("%", ""))
                        break
            except: pass
        
        # Max drawdown
        if "max drawdown" in line_lower or "drawdown" in line_lower:
            try:
                parts = line.split()
                for p in parts:
                    if "%" in p:
                        val = float(p.replace("%", "").replace("-", ""))
                        if val < 100:  # Reasonable DD
                            result["max_drawdown"] = round(val, 2)
                            break
            except: pass
        
        # Sharpe ratio
        if "sharpe" in line_lower:
            try:
                parts = line.split()
                for p in parts:
                    try:
                        val = float(p)
                        if -10 < val < 10:  # Reasonable Sharpe range
                            result["sharpe"] = round(val, 2)
                            break
                    except: pass
            except: pass
        
        # Sortino ratio
        if "sortino" in line_lower:
            try:
                parts = line.split()
                for p in parts:
                    try:
                        val = float(p)
                        if -20 < val < 20:  # Reasonable Sortino range
                            result["sortino"] = round(val, 2)
                            break
                    except: pass
            except: pass
        
        # Total trades
        if "total trades" in line_lower or "trades:" in line_lower:
            try:
                parts = line.split()
                for p in parts:
                    try:
                        val = int(p)
                        if 0 < val < 10000:
                            result["total_trades"] = val
                            break
                    except: pass
            except: pass
    
    return result


def create_error_result(scenario_id: str, scenario: dict, error: str) -> dict:
    """Create result dict for failed backtest."""
    return {
        "scenario_id": scenario_id,
        "scenario_name": scenario["name"],
        "timerange": scenario["timerange"],
        "description": scenario["description"],
        "profit_factor": None,
        "win_rate": None,
        "max_drawdown": None,
        "sharpe": None,
        "sortino": None,
        "total_profit_pct": None,
        "total_trades": None,
        "status": "error",
        "error": error
    }


def generate_report(results: list) -> dict:
    """Generate consolidated report from all scenario results."""
    report = {
        "generated_at": datetime.now().isoformat(),
        "strategy": STRATEGY,
        "timeframe": TIMEFRAME,
        "config": CONFIG,
        "scenarios": results,
        "summary": {}
    }
    
    # Calculate averages for successful runs
    successful = [r for r in results if r["status"] == "success"]
    
    if successful:
        def avg(key):
            vals = [r[key] for r in successful if r[key] is not None]
            return round(sum(vals) / len(vals), 2) if vals else None
        
        report["summary"] = {
            "total_scenarios": len(results),
            "successful_runs": len(successful),
            "avg_profit_factor": avg("profit_factor"),
            "avg_win_rate": avg("win_rate"),
            "avg_max_drawdown": avg("max_drawdown"),
            "avg_sharpe": avg("sharpe"),
            "avg_sortino": avg("sortino"),
            "avg_total_profit_pct": avg("total_profit_pct")
        }
    
    return report


def print_report(report: dict):
    """Print formatted report to console."""
    print("\n" + "=" * 70)
    print("📊 MULTI-SCENARIO BACKTEST REPORT")
    print("=" * 70)
    print(f"Strategy: {report['strategy']}")
    print(f"Timeframe: {report['timeframe']}")
    print(f"Generated: {report['generated_at']}")
    print("-" * 70)
    
    # Table header
    print(f"\n{'Scenario':<20} {'Profit%':<10} {'PF':<8} {'WR%':<8} {'MDD%':<8} {'Sharpe':<8} {'Trades':<8}")
    print("-" * 70)
    
    for r in report["scenarios"]:
        if r["status"] == "success":
            print(f"{r['scenario_name']:<20} "
                  f"{r['total_profit_pct'] or 'N/A':<10} "
                  f"{r['profit_factor'] or 'N/A':<8} "
                  f"{r['win_rate'] or 'N/A':<8} "
                  f"{r['max_drawdown'] or 'N/A':<8} "
                  f"{r['sharpe'] or 'N/A':<8} "
                  f"{r['total_trades'] or 'N/A':<8}")
        else:
            print(f"{r['scenario_name']:<20} ❌ {r.get('error', 'Unknown error')}")
    
    print("-" * 70)
    
    # Summary
    s = report.get("summary", {})
    if s:
        print(f"\n📈 AVERAGES:")
        print(f"  Profit Factor: {s.get('avg_profit_factor', 'N/A')}")
        print(f"  Win Rate: {s.get('avg_win_rate', 'N/A')}%")
        print(f"  Max Drawdown: {s.get('avg_max_drawdown', 'N/A')}%")
        print(f"  Sharpe Ratio: {s.get('avg_sharpe', 'N/A')}")
        print(f"  Sortino Ratio: {s.get('avg_sortino', 'N/A')}")
    
    print("\n" + "=" * 70)


def save_report(report: dict) -> Path:
    """Save report to JSON file."""
    REPORTS_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = REPORTS_DIR / f"multi_scenario_backtest_{timestamp}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return filename


# ============================================================================
#                              MAIN
# ============================================================================

def main():
    print("\n" + "=" * 70)
    print("🚀 MULTI-SCENARIO BACKTEST RUNNER")
    print("=" * 70)
    print(f"Strategy: {STRATEGY}")
    print(f"Timeframe: {TIMEFRAME}")
    print(f"Scenarios: {len(SCENARIOS)}")
    print("=" * 70)
    
    # Check if we're in correct directory
    if not (FREQTRADE_DIR / "docker-compose.yml").exists():
        print("❌ Error: docker-compose.yml not found!")
        print(f"   Expected location: {FREQTRADE_DIR}")
        print("   Please run from freqtrade directory or adjust paths.")
        sys.exit(1)
    
    # Run all scenarios
    results = []
    for scenario_id, scenario in SCENARIOS.items():
        result = run_backtest(scenario_id, scenario)
        results.append(result)
    
    # Generate and save report
    report = generate_report(results)
    report_file = save_report(report)
    
    # Print report
    print_report(report)
    
    print(f"\n✅ Report saved: {report_file}")
    print("\n" + "=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
