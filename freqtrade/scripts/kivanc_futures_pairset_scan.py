from __future__ import annotations

import argparse
import itertools
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
BACKTEST_RESULTS_DIR = ROOT / "user_data" / "backtest_results"
STRATEGY_NAME = "KivancSupertrendedMovingAveragesFutures1D"
PAIR_LIST = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "BNB/USDT:USDT",
    "SOL/USDT:USDT",
    "XRP/USDT:USDT",
]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def run_command(args: list[str]) -> None:
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = result.stderr.strip() if result.stderr else result.stdout.strip()
        raise RuntimeError(detail or f"Command failed: {' '.join(args)}")


def new_files(directory: Path, pattern: str, before: set[Path]) -> list[Path]:
    return sorted(
        [path for path in directory.glob(pattern) if path not in before],
        key=lambda item: item.stat().st_mtime,
    )


def parse_backtest_zip(zip_path: Path) -> dict:
    with ZipFile(zip_path) as archive:
        payload_name = next(
            name
            for name in archive.namelist()
            if name.endswith(".json")
            and "_config" not in name
            and "_market_change.feather" not in name
            and "_signals.pkl" not in name
            and "_rejected.pkl" not in name
            and "_exited.pkl" not in name
        )
        payload = json.loads(archive.read(payload_name))
    strategy = payload["strategy"][STRATEGY_NAME]
    profit_pct = round((strategy.get("profit_total", 0) or 0) * 100, 2)
    pf = round(strategy.get("profit_factor", 0) or 0, 2)
    dd_pct = round((strategy.get("max_drawdown_account", 0) or 0) * 100, 2)
    profit_n = (min(max(profit_pct, -100.0), 300.0) + 100.0) / 400.0
    pf_n = min(max(pf, 0.0), 3.0) / 3.0
    dd_n = 1.0 - (min(max(dd_pct, 0.0), 60.0) / 60.0)
    score = round(0.5 * profit_n + 0.3 * pf_n + 0.2 * dd_n, 4)
    return {
        "profit_pct": profit_pct,
        "final_balance": round(strategy.get("final_balance", 0) or 0, 2),
        "trades": strategy.get("total_trades", 0),
        "profit_factor": pf,
        "max_dd_pct": dd_pct,
        "market_change_pct": round((strategy.get("market_change", 0) or 0) * 100, 2),
        "score": score,
        "zip_file": zip_path.name,
    }


def run_backtest(pairs: tuple[str, ...], timerange: str) -> dict:
    before = set(BACKTEST_RESULTS_DIR.glob("backtest-result-*.zip"))
    command = [
        "docker",
        "compose",
        "run",
        "--rm",
        "bot1_btceth",
        "backtesting",
        "--config",
        "user_data/config_futures_research.json",
        "--strategy",
        STRATEGY_NAME,
        "--strategy-path",
        "user_data/strategies_research",
        "--timeframe",
        "1d",
        "--timerange",
        timerange,
        "--pairs",
        *pairs,
        "--data-format-ohlcv",
        "feather",
        "--cache",
        "none",
        "--enable-protections",
        "--export",
        "trades",
    ]
    run_command(command)
    created = new_files(BACKTEST_RESULTS_DIR, "backtest-result-*.zip", before)
    if not created:
        raise RuntimeError(f"No backtest result produced for pairs: {pairs}")
    metrics = parse_backtest_zip(created[-1])
    metrics["pairs"] = list(pairs)
    metrics["pair_count"] = len(pairs)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan futures pair subsets for Kivanc STMA.")
    parser.add_argument("--timerange", default="20220101-20260301")
    parser.add_argument("--min-pairs", type=int, default=3)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    report_dir = REPORTS_DIR / f"kivanc_futures_1d_pairset_scan_{utc_timestamp()}"
    report_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for size in range(args.min_pairs, len(PAIR_LIST) + 1):
        for pairs in itertools.combinations(PAIR_LIST, size):
            rows.append(run_backtest(pairs, args.timerange))

    by_score = sorted(rows, key=lambda row: (row["score"], row["profit_pct"]), reverse=True)
    by_profit = sorted(rows, key=lambda row: (row["profit_pct"], -row["max_dd_pct"]), reverse=True)
    best_by_size = {
        size: max((row for row in rows if row["pair_count"] == size), key=lambda row: (row["score"], row["profit_pct"]))
        for size in range(args.min_pairs, len(PAIR_LIST) + 1)
    }

    summary = {
        "timerange": args.timerange,
        "rows": rows,
        "top_by_score": by_score[: args.top],
        "top_by_profit": by_profit[: args.top],
        "best_by_size": best_by_size,
    }
    (report_dir / "pairset_scan_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Kivanc Futures 1D Pairset Scan",
        "",
        f"Timerange: `{args.timerange}`",
        f"Pair universe: `{', '.join(PAIR_LIST)}`",
        "",
        "## Best By Pair Count",
        "",
        "| Pair Count | Pairs | Profit | PF | MaxDD | Score | Trades |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for size in sorted(best_by_size):
        row = best_by_size[size]
        lines.append(
            f"| {size} | {', '.join(row['pairs'])} | {row['profit_pct']:.2f}% | {row['profit_factor']:.2f} | {row['max_dd_pct']:.2f}% | {row['score']:.4f} | {row['trades']} |"
        )

    lines.extend(
        [
            "",
            "## Top By Score",
            "",
            "| Rank | Pairs | Profit | PF | MaxDD | Score | Trades |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for index, row in enumerate(by_score[: args.top], start=1):
        lines.append(
            f"| {index} | {', '.join(row['pairs'])} | {row['profit_pct']:.2f}% | {row['profit_factor']:.2f} | {row['max_dd_pct']:.2f}% | {row['score']:.4f} | {row['trades']} |"
        )

    lines.extend(
        [
            "",
            "## Top By Profit",
            "",
            "| Rank | Pairs | Profit | PF | MaxDD | Score | Trades |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for index, row in enumerate(by_profit[: args.top], start=1):
        lines.append(
            f"| {index} | {', '.join(row['pairs'])} | {row['profit_pct']:.2f}% | {row['profit_factor']:.2f} | {row['max_dd_pct']:.2f}% | {row['score']:.4f} | {row['trades']} |"
        )

    (report_dir / "pairset_scan_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report_dir)


if __name__ == "__main__":
    main()
