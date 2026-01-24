#!/usr/bin/env python3
"""
Strategy Comparison Tool
========================
Compares backtest results from multiple strategies and ranks them.

Usage:
    python compare_strategies.py --results-dir user_data/backtest_results/
"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StrategyResult:
    """Holds backtest results for a single strategy."""

    name: str
    timeframe: str
    total_profit: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    total_trades: int
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0

    @property
    def score(self) -> float:
        """
        Calculate composite score for ranking.
        Weights:
        - Total Profit: 30%
        - Win Rate: 20%
        - Profit Factor: 25%
        - Max Drawdown (inverted): 15%
        - Trade Count (normalized): 10%
        """
        # Normalize metrics
        profit_score = min(self.total_profit / 100, 2.0)  # Cap at 200%
        win_score = self.win_rate / 100
        pf_score = min(self.profit_factor / 3, 1.0)  # Cap PF at 3
        dd_score = 1 - min(abs(self.max_drawdown) / 50, 1.0)  # Lower DD is better
        trade_score = min(self.total_trades / 200, 1.0)  # Enough trades

        return profit_score * 0.30 + win_score * 0.20 + pf_score * 0.25 + dd_score * 0.15 + trade_score * 0.10


def parse_backtest_result(filepath: Path) -> StrategyResult | None:
    """Parse a Freqtrade backtest JSON result file."""
    try:
        with open(filepath) as f:
            data = json.load(f)

        # Extract strategy name and timeframe from filename
        filename = filepath.stem
        parts = filename.rsplit("_", 1)
        strategy_name = parts[0] if len(parts) > 1 else filename
        timeframe = parts[1] if len(parts) > 1 else "unknown"

        # Navigate to results
        if "strategy" in data:
            # New format
            strategy_data = list(data["strategy"].values())[0]
        else:
            strategy_data = data

        return StrategyResult(
            name=strategy_name,
            timeframe=timeframe,
            total_profit=strategy_data.get("profit_total_pct", 0),
            win_rate=strategy_data.get("wins", 0) / max(strategy_data.get("trades", 1), 1) * 100,
            profit_factor=strategy_data.get("profit_factor", 0),
            max_drawdown=strategy_data.get("max_drawdown_abs", 0),
            total_trades=strategy_data.get("trades", 0),
            sharpe_ratio=strategy_data.get("sharpe", 0),
            sortino_ratio=strategy_data.get("sortino", 0),
        )
    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        print(f"Warning: Could not parse {filepath}: {e}")
        return None


def load_results(results_dir: Path) -> list[StrategyResult]:
    """Load all backtest results from directory."""
    results = []

    for filepath in results_dir.glob("*.json"):
        result = parse_backtest_result(filepath)
        if result:
            results.append(result)

    return results


def print_comparison_table(results: list[StrategyResult]) -> None:
    """Print formatted comparison table."""
    if not results:
        print("No results to display.")
        return

    # Sort by score
    sorted_results = sorted(results, key=lambda x: x.score, reverse=True)

    # Header
    print("\n" + "=" * 100)
    print("STRATEGY COMPARISON RESULTS")
    print("=" * 100)
    print(
        f"{'Rank':<5} {'Strategy':<20} {'TF':<5} {'Profit%':<10} {'WinRate%':<10} "
        f"{'PF':<8} {'MaxDD%':<10} {'Trades':<8} {'Score':<8}"
    )
    print("-" * 100)

    # Results
    for i, result in enumerate(sorted_results, 1):
        print(
            f"{i:<5} {result.name:<20} {result.timeframe:<5} "
            f"{result.total_profit:>8.2f}% {result.win_rate:>8.2f}% "
            f"{result.profit_factor:>6.2f} {result.max_drawdown:>8.2f}% "
            f"{result.total_trades:>6} {result.score:>6.3f}"
        )

    print("=" * 100)


def print_top_performers(results: list[StrategyResult], top_n: int = 3) -> None:
    """Print detailed analysis of top performers."""
    if not results:
        return

    sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
    top_results = sorted_results[:top_n]

    print(f"\n{'=' * 60}")
    print(f"TOP {top_n} PERFORMERS - DETAILED ANALYSIS")
    print("=" * 60)

    for i, result in enumerate(top_results, 1):
        print(f"\n🏆 #{i}: {result.name} ({result.timeframe})")
        print("-" * 40)
        print(f"  Total Profit:   {result.total_profit:>8.2f}%")
        print(f"  Win Rate:       {result.win_rate:>8.2f}%")
        print(f"  Profit Factor:  {result.profit_factor:>8.2f}")
        print(f"  Max Drawdown:   {result.max_drawdown:>8.2f}%")
        print(f"  Total Trades:   {result.total_trades:>8}")
        print(f"  Composite Score:{result.score:>8.3f}")

        # Recommendation
        if result.win_rate > 50 and result.profit_factor > 1.5:
            print("  ✅ Recommendation: STRONG - Good for production")
        elif result.win_rate > 40 and result.profit_factor > 1.2:
            print("  ⚠️  Recommendation: MODERATE - Consider optimization")
        else:
            print("  ❌ Recommendation: WEAK - Needs significant improvement")


def generate_report(results: list[StrategyResult], output_path: Path) -> None:
    """Generate markdown report."""
    sorted_results = sorted(results, key=lambda x: x.score, reverse=True)

    with open(output_path, "w") as f:
        f.write("# Strategy Comparison Report\n\n")
        f.write("## Summary\n\n")
        f.write("| Rank | Strategy | Timeframe | Profit | Win Rate | PF | Max DD | Trades | Score |\n")
        f.write("|------|----------|-----------|--------|----------|-----|--------|--------|-------|\n")

        for i, result in enumerate(sorted_results, 1):
            f.write(
                f"| {i} | {result.name} | {result.timeframe} | "
                f"{result.total_profit:.2f}% | {result.win_rate:.2f}% | "
                f"{result.profit_factor:.2f} | {result.max_drawdown:.2f}% | "
                f"{result.total_trades} | {result.score:.3f} |\n"
            )

        # Top 3 recommendations
        f.write("\n## Top 3 Recommendations\n\n")
        for i, result in enumerate(sorted_results[:3], 1):
            f.write(f"### {i}. {result.name} ({result.timeframe})\n\n")
            f.write(f"- **Total Profit:** {result.total_profit:.2f}%\n")
            f.write(f"- **Win Rate:** {result.win_rate:.2f}%\n")
            f.write(f"- **Profit Factor:** {result.profit_factor:.2f}\n")
            f.write(f"- **Max Drawdown:** {result.max_drawdown:.2f}%\n")
            f.write(f"- **Total Trades:** {result.total_trades}\n\n")

    print(f"\n📄 Report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Compare strategy backtest results")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("user_data/backtest_results"),
        help="Directory containing backtest JSON files",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=3,
        help="Number of top performers to highlight",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Output path for markdown report",
    )

    args = parser.parse_args()

    if not args.results_dir.exists():
        print(f"Error: Results directory not found: {args.results_dir}")
        return 1

    results = load_results(args.results_dir)

    if not results:
        print("No backtest results found.")
        return 1

    print_comparison_table(results)
    print_top_performers(results, args.top)

    if args.report:
        generate_report(results, args.report)

    return 0


if __name__ == "__main__":
    exit(main())
